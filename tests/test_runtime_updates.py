from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import openzues.services.runtime_updates as runtime_updates_module
from openzues.database import Database
from openzues.services.runtime_updates import RuntimeUpdateService


class RevisionProbe:
    def __init__(self, *revisions: str | None) -> None:
        self._revisions = list(revisions)

    def __call__(self, _repo_root: Path) -> str | None:
        if len(self._revisions) > 1:
            return self._revisions.pop(0)
        return self._revisions[0]


async def _create_live_mission(database: Database) -> int:
    mission_id = await database.create_mission(
        name="Live Mission",
        objective="Keep running.",
        status="active",
        instance_id=1,
        project_id=None,
        task_blueprint_id=None,
        thread_id=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        mission_id,
        in_progress=1,
        phase="executing",
    )
    return mission_id


def _write_package_root(package_root: Path, version: str, *, name: str = "openzues") -> None:
    (package_root / "dist").mkdir(parents=True, exist_ok=True)
    (package_root / "package.json").write_text(
        f'{{"name":"{name}","version":"{version}"}}',
        encoding="utf-8",
    )
    (package_root / "dist" / "index.js").write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, ["dist/index.js"])


def _write_package_dist_inventory(package_root: Path, entries: list[str] | None = None) -> None:
    inventory_path = package_root / "dist" / "postinstall-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(entries or []) + "\n", encoding="utf-8")


def _staged_global_root(stage_prefix: Path) -> Path:
    if os.name == "nt":
        return stage_prefix / "node_modules"
    return stage_prefix / "lib" / "node_modules"


def _staged_bin_dir(stage_prefix: Path) -> Path:
    if os.name == "nt":
        return stage_prefix
    return stage_prefix / "bin"


def _post_update_doctor_args() -> list[str]:
    return [
        sys.executable,
        "-m",
        "openzues.cli",
        "doctor",
        "--non-interactive",
        "--fix",
        "--json",
    ]


@pytest.mark.asyncio
async def test_runtime_update_requests_restart_after_repo_head_changes(tmp_path) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    restart_calls: list[str] = []
    probe = RevisionProbe("rev-a", "rev-b")

    async def restart_callback() -> None:
        restart_calls.append("restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=probe,
    )

    restarted = await service.tick()

    snapshot = service.snapshot()
    assert restarted is True
    assert restart_calls == ["restart"]
    assert snapshot["startup_revision"] == "rev-a"
    assert snapshot["current_revision"] == "rev-b"
    assert snapshot["pending_revision"] == "rev-b"
    assert snapshot["pending_restart"] is True
    assert snapshot["restart_in_progress"] is True
    assert snapshot["safe_to_restart"] is True


@pytest.mark.asyncio
async def test_runtime_update_waits_for_idle_boundary_before_restart(tmp_path) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    mission_id = await _create_live_mission(database)
    restart_calls: list[str] = []
    probe = RevisionProbe("rev-a", "rev-b", "rev-b")

    async def restart_callback() -> None:
        restart_calls.append("restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=probe,
    )

    restarted_while_busy = await service.tick()
    busy_snapshot = service.snapshot()
    assert restarted_while_busy is False
    assert restart_calls == []
    assert busy_snapshot["pending_restart"] is True
    assert busy_snapshot["safe_to_restart"] is False

    await database.update_mission(
        mission_id,
        in_progress=0,
        status="paused",
        phase="paused",
    )

    restarted_when_idle = await service.tick()
    idle_snapshot = service.snapshot()
    assert restarted_when_idle is True
    assert restart_calls == ["restart"]
    assert idle_snapshot["safe_to_restart"] is True
    assert idle_snapshot["restart_in_progress"] is True


@pytest.mark.asyncio
async def test_runtime_update_run_update_executes_native_git_install_build_steps(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[tuple[list[str], Path, int | None]] = []
    revision_probe = RevisionProbe("rev-a", "rev-b")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv == ["git", "rev-parse", "@{upstream}"]:
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "rev-b\nrev-a\n", "stderr": "", "exitCode": 0}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("run_update should report restart posture, not exec immediately")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=revision_probe,
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "ok"
    assert result["mode"] == "git"
    assert result["root"] == str(tmp_path)
    assert result["before"] == {"sha": "rev-a", "version": None}
    assert result["after"] == {"sha": "rev-b", "version": None}
    assert [step["name"] for step in result["steps"]] == [
        "git status",
        "git fetch",
        "upstream check",
        "git rev-parse @{upstream}",
        "git rev-list",
        "preflight worktree",
        "preflight checkout (rev-b)",
        "preflight deps install (rev-b)",
        "preflight build (rev-b)",
        "preflight cleanup",
        "git rebase",
        "deps install",
        "build",
    ]
    assert command_calls[:5] == [
        (["git", "status", "--porcelain", "--", ":!dist/control-ui/"], tmp_path, 1000),
        (["git", "fetch", "--all", "--prune", "--tags"], tmp_path, 1000),
        (
            [
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}",
            ],
            tmp_path,
            1000,
        ),
        (["git", "rev-parse", "@{upstream}"], tmp_path, 1000),
        (["git", "rev-list", "--max-count=10", "rev-b"], tmp_path, 1000),
    ]
    assert command_calls[5][0][:4] == ["git", "worktree", "add", "--detach"]
    assert command_calls[5][0][-1] == "rev-b"
    assert command_calls[6][0] == ["git", "checkout", "--detach", "rev-b"]
    assert command_calls[6][1] != tmp_path
    assert command_calls[7][0] == [sys.executable, "-m", "pip", "install", "-e", "."]
    assert command_calls[7][1] != tmp_path
    assert command_calls[8][0] == [sys.executable, "-m", "compileall", "-q", "src"]
    assert command_calls[8][1] != tmp_path
    assert command_calls[9][0][:4] == ["git", "worktree", "remove", "--force"]
    assert command_calls[10:] == [
        (["git", "rebase", "rev-b"], tmp_path, 1000),
        ([sys.executable, "-m", "pip", "install", "-e", "."], tmp_path, 1000),
        ([sys.executable, "-m", "compileall", "-q", "src"], tmp_path, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_update_ignores_control_ui_dist_dirty_files(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[tuple[list[str], Path, int | None]] = []
    revision_probe = RevisionProbe("rev-a", "rev-b")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == ["git", "status", "--porcelain"] and ":!dist/control-ui/" in argv:
            return {"stdout": "", "stderr": "", "exitCode": 0}
        if argv[:3] == ["git", "status", "--porcelain"]:
            return {"stdout": " M dist/control-ui/app.js\n", "stderr": "", "exitCode": 0}
        if argv == ["git", "rev-parse", "@{upstream}"]:
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "rev-b\nrev-a\n", "stderr": "", "exitCode": 0}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("run_update should report restart posture, not exec immediately")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=revision_probe,
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == [
        "git status",
        "git fetch",
        "upstream check",
        "git rev-parse @{upstream}",
        "git rev-list",
        "preflight worktree",
        "preflight checkout (rev-b)",
        "preflight deps install (rev-b)",
        "preflight build (rev-b)",
        "preflight cleanup",
        "git rebase",
        "deps install",
        "build",
    ]
    assert command_calls[0] == (
        ["git", "status", "--porcelain", "--", ":!dist/control-ui/"],
        tmp_path,
        1000,
    )


@pytest.mark.asyncio
async def test_runtime_update_run_update_reports_no_upstream_without_pull(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:2] == ["git", "rev-parse"]:
            return {"stdout": "", "stderr": "no upstream\n", "exitCode": 1}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("no-upstream update should not schedule immediate restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "skipped"
    assert result["reason"] == "no-upstream"
    assert result["after"] == {"sha": "rev-a", "version": None}
    assert [step["name"] for step in result["steps"]] == [
        "git status",
        "git fetch",
        "upstream check",
    ]
    assert command_calls == [
        (["git", "status", "--porcelain", "--", ":!dist/control-ui/"], tmp_path, 1000),
        (["git", "fetch", "--all", "--prune", "--tags"], tmp_path, 1000),
        (
            [
                "git",
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{upstream}",
            ],
            tmp_path,
            1000,
        ),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_update_errors_when_preflight_has_no_candidates(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv[:2] == ["git", "rev-parse"] and argv[-1] == "@{upstream}":
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "", "stderr": "", "exitCode": 0}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("preflight failure should not schedule immediate restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "error"
    assert result["reason"] == "preflight-no-candidates"
    assert [step["name"] for step in result["steps"]] == [
        "git status",
        "git fetch",
        "upstream check",
        "git rev-parse @{upstream}",
        "git rev-list",
    ]
    assert command_calls[-1] == ["git", "rev-list", "--max-count=10", "rev-b"]


@pytest.mark.asyncio
async def test_runtime_update_run_update_reports_preflight_worktree_failure(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == ["git", "rev-parse", "@{upstream}"]:
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "rev-b\nrev-a\n", "stderr": "", "exitCode": 0}
        if argv[:3] == ["git", "worktree", "add"]:
            return {"stdout": "", "stderr": "worktree failed\n", "exitCode": 1}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("preflight failure should not schedule immediate restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "error"
    assert result["reason"] == "preflight-worktree-failed"
    assert [step["name"] for step in result["steps"]] == [
        "git status",
        "git fetch",
        "upstream check",
        "git rev-parse @{upstream}",
        "git rev-list",
        "preflight worktree",
    ]
    assert command_calls[-1][:4] == ["git", "worktree", "add", "--detach"]
    assert command_calls[-1][-1] == "rev-b"


@pytest.mark.asyncio
async def test_runtime_update_run_update_selects_first_good_preflight_candidate(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[tuple[list[str], Path]] = []
    revision_probe = RevisionProbe("rev-a", "rev-good")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del timeout_ms
        command_calls.append((argv, cwd))
        if argv == ["git", "rev-parse", "@{upstream}"]:
            return {"stdout": "rev-bad\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "rev-bad\nrev-good\n", "stderr": "", "exitCode": 0}
        if argv[:3] == ["git", "checkout", "--detach"] and argv[-1] == "rev-bad":
            return {"stdout": "", "stderr": "", "exitCode": 0}
        if argv == [sys.executable, "-m", "compileall", "-q", "src"] and cwd != tmp_path:
            first_checkout_seen = any(call[0][-1] == "rev-bad" for call in command_calls)
            second_checkout_seen = any(call[0][-1] == "rev-good" for call in command_calls)
            if first_checkout_seen and not second_checkout_seen:
                return {"stdout": "", "stderr": "bad build\n", "exitCode": 1}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("run_update should report restart posture, not exec immediately")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=revision_probe,
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "ok"
    step_names = [step["name"] for step in result["steps"]]
    assert "preflight checkout (rev-bad)" in step_names
    assert "preflight build (rev-bad)" in step_names
    assert "preflight checkout (rev-good)" in step_names
    assert "preflight build (rev-good)" in step_names
    assert "git rebase" in step_names
    assert any(call[0] == ["git", "rebase", "rev-good"] for call in command_calls)


@pytest.mark.asyncio
async def test_runtime_update_run_update_aborts_failed_rebase(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == ["git", "rev-parse", "@{upstream}"]:
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv[:2] == ["git", "rev-list"]:
            return {"stdout": "rev-b\n", "stderr": "", "exitCode": 0}
        if argv == ["git", "rebase", "rev-b"]:
            return {"stdout": "", "stderr": "conflict\n", "exitCode": 1}
        return {"stdout": "", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("rebase failure should not schedule immediate restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "error"
    assert result["reason"] == "rebase-failed"
    assert [step["name"] for step in result["steps"]][-2:] == [
        "git rebase",
        "git rebase --abort",
    ]
    assert command_calls[-2:] == [["git", "rebase", "rev-b"], ["git", "rebase", "--abort"]]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_executes_global_install_step(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert result["mode"] == "pnpm"
    assert result["root"] == str(package_root)
    assert result["before"] == {"sha": None, "version": "2026.5.1"}
    assert result["after"] == {"sha": None, "version": "2026.5.1"}
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        (["pnpm", "add", "-g", "openzues@latest"], package_root, 1000),
        (_post_update_doctor_args(), package_root, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_cleans_stale_global_rename_dirs(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    stale_dir = global_root / ".openzues-previous"
    stale_dir.mkdir()
    (stale_dir / "marker.txt").write_text("old backup\n", encoding="utf-8")
    matching_file = global_root / ".openzues-file"
    matching_file.write_text("not a directory\n", encoding="utf-8")
    unrelated_dir = global_root / ".other-previous"
    unrelated_dir.mkdir()
    cleanup_seen: list[bool] = []
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if len(command_calls) == 1:
            cleanup_seen.append(
                not stale_dir.exists()
                and matching_file.exists()
                and unrelated_dir.exists()
            )
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert cleanup_seen == [True]
    assert not stale_dir.exists()
    assert matching_file.exists()
    assert unrelated_dir.exists()
    assert command_calls == [
        (["pnpm", "add", "-g", "openzues@latest"], package_root, 1000),
        (_post_update_doctor_args(), package_root, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_reports_low_disk_warning(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    checked_paths: list[Path] = []
    command_calls: list[tuple[list[str], Path, int | None]] = []

    def fake_disk_usage(path: str | os.PathLike[str]) -> object:
        checked_paths.append(Path(path))
        return SimpleNamespace(
            total=2 * 1024 * 1024 * 1024,
            used=1792 * 1024 * 1024,
            free=256 * 1024 * 1024,
        )

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    monkeypatch.setattr("openzues.services.runtime_updates.shutil.disk_usage", fake_disk_usage)
    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert checked_paths == [global_root]
    assert result["warnings"] == [
        f"Low disk space near {global_root}: 256 MiB available; "
        "global package update may fail."
    ]
    assert command_calls == [
        (["pnpm", "add", "-g", "openzues@latest"], package_root, 1000),
        (_post_update_doctor_args(), package_root, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_retries_npm_without_optional_deps(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == [sys.executable, "-m", "openzues.cli"]:
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        if len(command_calls) == 1:
            return {"stdout": "", "stderr": "optional native build failed", "exitCode": 1}
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.1")
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == [
        "global update",
        "global update (omit optional)",
        "global install swap",
        "openzues doctor",
    ]
    assert len(command_calls) == 3
    first_argv, first_cwd, first_timeout = command_calls[0]
    second_argv, second_cwd, second_timeout = command_calls[1]
    doctor_argv, doctor_cwd, doctor_timeout = command_calls[2]
    assert first_argv[:3] == ["npm", "i", "-g"]
    assert second_argv[:3] == ["npm", "i", "-g"]
    assert "--prefix" in first_argv
    assert "--prefix" in second_argv
    assert "openzues@latest" in first_argv
    assert "openzues@latest" in second_argv
    assert "--omit=optional" in second_argv
    assert first_cwd == package_root
    assert second_cwd == package_root
    assert first_timeout == 1000
    assert second_timeout == 1000
    assert doctor_argv == _post_update_doctor_args()
    assert doctor_cwd == package_root
    assert doctor_timeout == 1000


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_stages_npm_install_before_swap(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    stale_runtime = package_root / "dist" / "extensions" / "qa-channel" / "runtime-api.js"
    stale_runtime.parent.mkdir(parents=True)
    stale_runtime.write_text("export const stale = true;\n", encoding="utf-8")
    target_shim = prefix / "bin" / "openzues"
    target_shim.parent.mkdir(parents=True)
    target_shim.write_text("old shim\n", encoding="utf-8")
    command_calls: list[tuple[list[str], Path, int | None]] = []
    stage_prefixes: list[Path] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == [sys.executable, "-m", "openzues.cli"]:
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        stage_prefixes.append(stage_prefix)
        assert stage_prefix.parent == global_root
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.2")
        staged_shim = _staged_bin_dir(stage_prefix) / "openzues"
        staged_shim.parent.mkdir(parents=True, exist_ok=True)
        staged_shim.write_text("new shim\n", encoding="utf-8")
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert result["mode"] == "npm"
    assert result["root"] == str(package_root)
    assert result["before"] == {"sha": None, "version": "2026.5.1"}
    assert result["after"] == {"sha": None, "version": "2026.5.2"}
    assert [step["name"] for step in result["steps"]] == [
        "global update",
        "global install swap",
        "openzues doctor",
    ]
    assert len(command_calls) == 2
    argv, cwd, timeout_ms = command_calls[0]
    assert argv[:3] == ["npm", "i", "-g"]
    assert "--prefix" in argv
    assert "openzues@2026.5.2" in argv
    assert cwd == package_root
    assert timeout_ms == 1000
    doctor_argv, doctor_cwd, doctor_timeout = command_calls[1]
    assert doctor_argv == _post_update_doctor_args()
    assert doctor_cwd == package_root
    assert doctor_timeout == 1000
    assert (package_root / "package.json").read_text(encoding="utf-8") == (
        '{"name":"openzues","version":"2026.5.2"}'
    )
    assert not stale_runtime.exists()
    assert target_shim.read_text(encoding="utf-8") == "new shim\n"
    assert stage_prefixes
    assert all(not stage_prefix.exists() for stage_prefix in stage_prefixes)


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_restores_bin_shim_when_swap_fails(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    target_shim = prefix / "bin" / "openzues"
    target_shim.parent.mkdir(parents=True)
    target_shim.write_text("old shim\n", encoding="utf-8")
    stage_prefixes: list[Path] = []
    staged_shims: list[Path] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        stage_prefixes.append(stage_prefix)
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.2")
        staged_shim = _staged_bin_dir(stage_prefix) / "openzues"
        staged_shim.parent.mkdir(parents=True, exist_ok=True)
        staged_shim.write_text("new shim\n", encoding="utf-8")
        staged_shims.append(staged_shim)
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    original_copy_path_entry = runtime_updates_module._copy_path_entry

    def fake_copy_path_entry(source: Path, destination: Path) -> None:
        if source in staged_shims and destination == target_shim:
            raise OSError("shim copy blocked")
        original_copy_path_entry(source, destination)

    monkeypatch.setattr(runtime_updates_module, "_copy_path_entry", fake_copy_path_entry)

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-swap-failed"
    assert result["failedStep"]["name"] == "global install swap"
    assert result["after"] == {"sha": None, "version": "2026.5.1"}
    assert [step["name"] for step in result["steps"]] == [
        "global update",
        "global install swap",
    ]
    assert result["failedStep"]["log"]["stderrTail"] == "shim copy blocked"
    assert (package_root / "package.json").read_text(encoding="utf-8") == (
        '{"name":"openzues","version":"2026.5.1"}'
    )
    assert target_shim.read_text(encoding="utf-8") == "old shim\n"
    assert stage_prefixes
    assert all(not stage_prefix.exists() for stage_prefix in stage_prefixes)


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_cleans_staged_prefix_when_install_raises(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    stage_prefixes: list[Path] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        prefix_index = argv.index("--prefix")
        stage_prefixes.append(Path(argv[prefix_index + 1]))
        raise RuntimeError("install crashed")

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    with pytest.raises(RuntimeError, match="install crashed"):
        await service.run_package_update(
            package_root=package_root,
            package_manager="npm",
            package_spec="openzues@2026.5.2",
            timeout_ms=1000,
        )

    assert stage_prefixes
    assert all(not stage_prefix.exists() for stage_prefix in stage_prefixes)


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_keeps_live_root_when_staged_verify_fails(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "prefix"
    global_root = prefix / "lib" / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    live_marker = package_root / "dist" / "live-only.js"
    live_marker.write_text("export const live = true;\n", encoding="utf-8")
    stage_prefixes: list[Path] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        stage_prefixes.append(stage_prefix)
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.3")
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["failedStep"]["name"] == "global install verify"
    assert result["after"] == {"sha": None, "version": "2026.5.1"}
    assert [step["name"] for step in result["steps"]] == [
        "global update",
        "global install verify",
    ]
    assert result["steps"][1]["log"]["stderrTail"] == (
        "expected installed version 2026.5.2, found 2026.5.3"
    )
    assert (package_root / "package.json").read_text(encoding="utf-8") == (
        '{"name":"openzues","version":"2026.5.1"}'
    )
    assert live_marker.exists()
    assert stage_prefixes
    assert all(not stage_prefix.exists() for stage_prefix in stage_prefixes)


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_fails_when_post_update_doctor_fails(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == [sys.executable, "-m", "openzues.cli"]:
            return {"stdout": "", "stderr": "doctor repair failed", "exitCode": 1}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "post-update-doctor-failed"
    assert result["failedStep"]["name"] == "openzues doctor"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        (["pnpm", "add", "-g", "openzues@latest"], package_root, 1000),
        (_post_update_doctor_args(), package_root, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_sets_post_update_doctor_env(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    monkeypatch.delenv("NODE_DISABLE_COMPILE_CACHE", raising=False)
    monkeypatch.delenv("OPENCLAW_UPDATE_IN_PROGRESS", raising=False)
    monkeypatch.delenv("OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE", raising=False)
    doctor_env: dict[str, str | None] = {}

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        if argv == _post_update_doctor_args():
            doctor_env.update(
                {
                    "NODE_DISABLE_COMPILE_CACHE": os.environ.get(
                        "NODE_DISABLE_COMPILE_CACHE"
                    ),
                    "OPENCLAW_UPDATE_IN_PROGRESS": os.environ.get(
                        "OPENCLAW_UPDATE_IN_PROGRESS"
                    ),
                    "OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE": os.environ.get(
                        "OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE"
                    ),
                }
            )
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert doctor_env == {
        "NODE_DISABLE_COMPILE_CACHE": "1",
        "OPENCLAW_UPDATE_IN_PROGRESS": "1",
        "OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE": "1",
    }
    assert os.environ.get("NODE_DISABLE_COMPILE_CACHE") is None
    assert os.environ.get("OPENCLAW_UPDATE_IN_PROGRESS") is None
    assert os.environ.get("OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE") is None


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_disables_corepack_download_prompt(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    monkeypatch.delenv("COREPACK_ENABLE_DOWNLOAD_PROMPT", raising=False)
    install_env: dict[str, str | None] = {}

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        if argv == ["pnpm", "add", "-g", "openzues@latest"]:
            install_env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = os.environ.get(
                "COREPACK_ENABLE_DOWNLOAD_PROMPT"
            )
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert install_env == {"COREPACK_ENABLE_DOWNLOAD_PROMPT": "0"}
    assert os.environ.get("COREPACK_ENABLE_DOWNLOAD_PROMPT") is None


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_preserves_corepack_download_prompt(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    monkeypatch.setenv("COREPACK_ENABLE_DOWNLOAD_PROMPT", "1")
    install_env: dict[str, str | None] = {}

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        if argv == ["pnpm", "add", "-g", "openzues@latest"]:
            install_env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = os.environ.get(
                "COREPACK_ENABLE_DOWNLOAD_PROMPT"
            )
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert install_env == {"COREPACK_ENABLE_DOWNLOAD_PROMPT": "1"}
    assert os.environ.get("COREPACK_ENABLE_DOWNLOAD_PROMPT") == "1"


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_sets_windows_install_env(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    monkeypatch.setenv("NPM_CONFIG_UPDATE_NOTIFIER", "true")
    monkeypatch.delenv("NPM_CONFIG_FUND", raising=False)
    monkeypatch.delenv("NPM_CONFIG_AUDIT", raising=False)
    monkeypatch.delenv("NODE_LLAMA_CPP_SKIP_DOWNLOAD", raising=False)
    install_env: dict[str, str | None] = {}

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        if argv == ["pnpm", "add", "-g", "openzues@latest"]:
            install_env.update(
                {
                    "NPM_CONFIG_UPDATE_NOTIFIER": os.environ.get(
                        "NPM_CONFIG_UPDATE_NOTIFIER"
                    ),
                    "NPM_CONFIG_FUND": os.environ.get("NPM_CONFIG_FUND"),
                    "NPM_CONFIG_AUDIT": os.environ.get("NPM_CONFIG_AUDIT"),
                    "NODE_LLAMA_CPP_SKIP_DOWNLOAD": os.environ.get(
                        "NODE_LLAMA_CPP_SKIP_DOWNLOAD"
                    ),
                }
            )
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert install_env == {
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        "NPM_CONFIG_FUND": "false",
        "NPM_CONFIG_AUDIT": "false",
        "NODE_LLAMA_CPP_SKIP_DOWNLOAD": "1",
    }
    assert os.environ.get("NPM_CONFIG_UPDATE_NOTIFIER") == "true"
    assert os.environ.get("NPM_CONFIG_FUND") is None
    assert os.environ.get("NPM_CONFIG_AUDIT") is None
    assert os.environ.get("NODE_LLAMA_CPP_SKIP_DOWNLOAD") is None


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_prepends_portable_git_paths(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)
    local_app_data = tmp_path / "LocalAppData"
    portable_git_root = local_app_data / "OpenClaw" / "deps" / "portable-git"
    expected_prepend = [
        portable_git_root / "mingw64" / "bin",
        portable_git_root / "usr" / "bin",
        portable_git_root / "cmd",
        portable_git_root / "bin",
    ]
    for candidate in expected_prepend:
        candidate.mkdir(parents=True)
    existing_path = str(tmp_path / "existing-bin")
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("PATH", existing_path)
    install_env: dict[str, str | None] = {}

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        if argv == ["pnpm", "add", "-g", "openzues@latest"]:
            install_env["PATH"] = os.environ.get("PATH")
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert install_env["PATH"] == os.pathsep.join(
        [*(str(path) for path in expected_prepend), existing_path]
    )
    assert os.environ.get("PATH") == existing_path


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_prefers_owning_npm_cmd(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "npm-prefix"
    global_root = prefix / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    npm_cmd = prefix / "npm.cmd"
    npm_cmd.write_text("@echo off\n", encoding="utf-8")
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == [sys.executable, "-m", "openzues.cli"]:
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.2")
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert command_calls[0][0][0] == str(npm_cmd)
    assert command_calls[0][0][:3] == [str(npm_cmd), "i", "-g"]
    assert command_calls[0][1] == package_root
    assert command_calls[0][2] == 1000


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_uses_ambient_npm_when_owner_absent(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    prefix = tmp_path / "npm-prefix"
    global_root = prefix / "node_modules"
    package_root = global_root / "openzues"
    _write_package_root(package_root, "2026.5.1")
    command_calls: list[tuple[list[str], Path, int | None]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        command_calls.append((argv, cwd, timeout_ms))
        if argv[:3] == [sys.executable, "-m", "openzues.cli"]:
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        prefix_index = argv.index("--prefix")
        stage_prefix = Path(argv[prefix_index + 1])
        _write_package_root(_staged_global_root(stage_prefix) / "openzues", "2026.5.2")
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="npm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert command_calls[0][0][0] == "npm"
    assert command_calls[0][0][:3] == ["npm", "i", "-g"]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_verifies_expected_version(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["failedStep"]["name"] == "global install verify"
    assert [step["name"] for step in result["steps"]] == [
        "global update",
        "global install verify",
    ]
    verify_step = result["steps"][1]
    assert isinstance(verify_step, dict)
    assert verify_step["log"]["exitCode"] == 1
    assert verify_step["log"]["stderrTail"] == (
        "expected installed version 2026.5.2, found 2026.5.1"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_reports_missing_expected_version(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        (package_root / "package.json").unlink()
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@2026.5.2",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "expected installed version 2026.5.2, found <missing>"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_rejects_source_checkout_root(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / ".git").mkdir()
    (package_root / "src").mkdir()
    (package_root / "extensions").mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.2"}', encoding="utf-8")
    _write_package_dist_inventory(package_root)

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        f"global package root resolves to source checkout: {package_root.resolve()}"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_reports_missing_dist_inventory(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "missing package dist inventory dist/postinstall-inventory.json"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_rejects_invalid_dist_inventory(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    inventory_path = package_root / "dist" / "postinstall-inventory.json"
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text("{not-json}\n", encoding="utf-8")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "invalid package dist inventory dist/postinstall-inventory.json"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_reports_dist_inventory_file_drift(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    _write_package_dist_inventory(package_root, ["dist/index.js"])
    (package_root / "dist" / "stale.js").write_text("export {};\n", encoding="utf-8")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "missing packaged dist file dist/index.js\n"
        "unexpected packaged dist file dist/stale.js"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_enforces_omitted_runtime_sidecar(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    plugin_root = package_root / "dist" / "extensions" / "matrix"
    plugin_root.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    (plugin_root / "package.json").write_text('{"name":"@openzues/matrix"}', encoding="utf-8")
    _write_package_dist_inventory(package_root, ["dist/extensions/matrix/package.json"])

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "missing bundled runtime sidecar dist/extensions/matrix/helper-api.js\n"
        "missing bundled runtime sidecar dist/extensions/matrix/runtime-api.js\n"
        "missing bundled runtime sidecar dist/extensions/matrix/runtime-setter-api.js\n"
        "missing bundled runtime sidecar "
        "dist/extensions/matrix/thread-bindings-runtime.js"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_enforces_legacy_runtime_sidecars(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    plugin_root = package_root / "dist" / "extensions" / "matrix"
    plugin_root.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.14"}', encoding="utf-8")
    (plugin_root / "package.json").write_text('{"name":"@openzues/matrix"}', encoding="utf-8")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "missing bundled runtime sidecar dist/extensions/matrix/helper-api.js\n"
        "missing bundled runtime sidecar dist/extensions/matrix/runtime-api.js\n"
        "missing bundled runtime sidecar dist/extensions/matrix/runtime-setter-api.js\n"
        "missing bundled runtime sidecar "
        "dist/extensions/matrix/thread-bindings-runtime.js"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_omits_legacy_private_qa_sidecars(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    plugin_root = package_root / "dist" / "extensions" / "qa-lab"
    plugin_root.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.14"}', encoding="utf-8")
    (plugin_root / "package.json").write_text('{"name":"@openzues/qa-lab"}', encoding="utf-8")
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        ["pnpm", "add", "-g", "openzues@latest"],
        _post_update_doctor_args(),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_ignores_stale_private_qa_metadata_with_inventory(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    plugin_root = package_root / "dist" / "extensions" / "qa-lab"
    plugin_root.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    (plugin_root / "package.json").write_text('{"name":"@openzues/qa-lab"}', encoding="utf-8")
    _write_package_dist_inventory(package_root, [])
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        ["pnpm", "add", "-g", "openzues@latest"],
        _post_update_doctor_args(),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_ignores_dist_inventory_omissions(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    plugin_root = package_root / "dist" / "extensions" / "alpha"
    plugin_dependency = plugin_root / "node_modules" / "typebox" / "index.js"
    plugin_dependency.parent.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    (package_root / "dist" / ".buildstamp").write_text("local\n", encoding="utf-8")
    (package_root / "dist" / "index.js.map").write_text("{}", encoding="utf-8")
    (plugin_root / "package.json").write_text('{"name":"@openzues/alpha"}', encoding="utf-8")
    plugin_dependency.write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, ["dist/extensions/alpha/package.json"])
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        ["pnpm", "add", "-g", "openzues@latest"],
        _post_update_doctor_args(),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_reports_runtime_install_staging_debris(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    real_file = package_root / "dist" / "real-AbC123.js"
    bare_stage_file = (
        package_root
        / "dist"
        / "extensions"
        / "brave"
        / ".openclaw-install-stage"
        / "node_modules"
        / "typebox"
        / "build"
        / "compile"
        / "code.mjs"
    )
    retry_stage_file = (
        package_root
        / "dist"
        / "extensions"
        / "brave"
        / ".openclaw-install-stage-retry"
        / "node_modules"
        / "typebox"
        / "build"
        / "compile"
        / "code.mjs"
    )
    real_file.parent.mkdir(parents=True)
    bare_stage_file.parent.mkdir(parents=True)
    retry_stage_file.parent.mkdir(parents=True)
    real_file.write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, ["dist/real-AbC123.js"])
    bare_stage_file.write_text("export {};\n", encoding="utf-8")
    retry_stage_file.write_text("export {};\n", encoding="utf-8")

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "unexpected packaged dist file "
        "dist/extensions/brave/.openclaw-install-stage-retry/node_modules/typebox/build/compile/code.mjs"
        "\nunexpected packaged dist file "
        "dist/extensions/brave/.openclaw-install-stage/node_modules/typebox/build/compile/code.mjs"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_rejects_unsafe_dist_symlink(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    unsafe_path = package_root / "dist" / "entry.js"
    unsafe_path.parent.mkdir(parents=True)
    unsafe_path.write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, [])
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == unsafe_path:
            return True
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "Unsafe package dist path: dist/entry.js"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_omits_externalized_extension_dist(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    extension_source = package_root / "extensions" / "brave"
    extension_dist = package_root / "dist" / "extensions" / "brave"
    extension_source.mkdir(parents=True)
    extension_dist.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    extension_source.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "@openzues/brave",
                "openclaw": {"release": {"publishToNpm": True}},
            }
        ),
        encoding="utf-8",
    )
    (extension_dist / "runtime-api.js").write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, [])
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        ["pnpm", "add", "-g", "openzues@latest"],
        _post_update_doctor_args(),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_keeps_include_in_core_extension_dist(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    extension_source = package_root / "extensions" / "core-chat"
    extension_dist = package_root / "dist" / "extensions" / "core-chat"
    extension_source.mkdir(parents=True)
    extension_dist.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    extension_source.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "@openzues/core-chat",
                "openclaw": {
                    "bundle": {"includeInCore": True},
                    "release": {"publishToClawHub": True, "publishToNpm": True},
                },
            }
        ),
        encoding="utf-8",
    )
    (extension_dist / "index.js").write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, [])

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "unexpected packaged dist file dist/extensions/core-chat/index.js"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_rejects_malformed_externalized_manifest(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    extension_source = package_root / "extensions" / "brave"
    extension_dist = package_root / "dist" / "extensions" / "brave"
    extension_source.mkdir(parents=True)
    extension_dist.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    extension_source.joinpath("package.json").write_text("{not-json}\n", encoding="utf-8")
    (extension_dist / "runtime-api.js").write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(
        package_root,
        ["dist/extensions/brave/runtime-api.js"],
    )

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del argv, cwd, timeout_ms
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "error"
    assert result["reason"] == "global-install-verify-failed"
    assert result["steps"][1]["name"] == "global install verify"
    assert result["steps"][1]["log"]["stderrTail"] == (
        "invalid bundled extension manifest extensions/brave/package.json"
    )


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_omits_externalized_symlink_before_safety(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    extension_source = package_root / "extensions" / "brave"
    extension_dist = package_root / "dist" / "extensions" / "brave"
    extension_source.mkdir(parents=True)
    extension_dist.mkdir(parents=True)
    (package_root / "package.json").write_text('{"version":"2026.4.15"}', encoding="utf-8")
    extension_source.joinpath("package.json").write_text(
        json.dumps(
            {
                "name": "@openzues/brave",
                "openclaw": {"release": {"publishToNpm": True}},
            }
        ),
        encoding="utf-8",
    )
    omitted_path = extension_dist / "runtime-api.js"
    omitted_path.write_text("export {};\n", encoding="utf-8")
    _write_package_dist_inventory(package_root, [])
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == omitted_path:
            return True
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        if argv == _post_update_doctor_args():
            return {"stdout": "doctor ok\n", "stderr": "", "exitCode": 0}
        return {"stdout": "updated\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("package update should report restart posture, not restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_package_update(
        package_root=package_root,
        package_manager="pnpm",
        package_spec="openzues@latest",
        timeout_ms=1000,
    )

    assert result["status"] == "ok"
    assert [step["name"] for step in result["steps"]] == ["global update", "openzues doctor"]
    assert command_calls == [
        ["pnpm", "add", "-g", "openzues@latest"],
        _post_update_doctor_args(),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_update_skips_dirty_worktree_before_fetch(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    command_calls: list[list[str]] = []

    async def fake_command_runner(
        argv: list[str],
        cwd: Path,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del cwd, timeout_ms
        command_calls.append(argv)
        return {"stdout": " M README.md\n", "stderr": "", "exitCode": 0}

    async def restart_callback() -> None:
        raise AssertionError("dirty update should not schedule immediate restart")

    service = RuntimeUpdateService(
        database,
        enabled=True,
        poll_interval_seconds=20,
        restart_callback=restart_callback,
        repo_root=tmp_path,
        revision_resolver=RevisionProbe("rev-a"),
        update_command_runner=fake_command_runner,
    )

    result = await service.run_update(timeout_ms=1000)

    assert result["status"] == "skipped"
    assert result["reason"] == "dirty"
    assert [step["name"] for step in result["steps"]] == ["git status"]
    assert command_calls == [["git", "status", "--porcelain", "--", ":!dist/control-ui/"]]
