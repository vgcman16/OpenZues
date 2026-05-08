from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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
        "git pull",
        "deps install",
        "build",
    ]
    assert command_calls == [
        (["git", "status", "--porcelain"], tmp_path, 1000),
        (["git", "fetch", "--all", "--prune", "--tags"], tmp_path, 1000),
        (["git", "pull", "--ff-only"], tmp_path, 1000),
        ([sys.executable, "-m", "pip", "install", "-e", "."], tmp_path, 1000),
        ([sys.executable, "-m", "compileall", "-q", "src"], tmp_path, 1000),
    ]


@pytest.mark.asyncio
async def test_runtime_update_run_package_update_executes_global_install_step(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")
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
async def test_runtime_update_run_package_update_verifies_expected_version(
    tmp_path,
) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    package_root = tmp_path / "package-root"
    package_root.mkdir()
    (package_root / "package.json").write_text('{"version":"2026.5.1"}', encoding="utf-8")

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
    assert command_calls == [["git", "status", "--porcelain"]]
