from __future__ import annotations

import sys
from pathlib import Path

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
