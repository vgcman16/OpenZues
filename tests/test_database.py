from __future__ import annotations

import pytest

from openzues.database import Database


@pytest.mark.asyncio
async def test_database_round_trip(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.initialize()

    instance_id = await database.create_instance(
        name="Local Codex",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
    )
    await database.append_event(
        instance_id=instance_id,
        thread_id="thread_1",
        method="thread/started",
        payload={"ok": True},
    )
    playbook_id = await database.create_playbook(
        name="Quick status",
        description=None,
        kind="command",
        instance_id=instance_id,
        payload={"template": "git status", "cwd": str(tmp_path)},
    )
    mission_id = await database.create_mission(
        name="Nightly builder",
        objective="Keep shipping.",
        status="paused",
        instance_id=instance_id,
        project_id=None,
        thread_id=None,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=5,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_1",
        turn_id="turn_1",
        kind="final_answer",
        summary="Verified the first milestone.",
    )

    instances = await database.list_instances()
    events = await database.list_events()
    playbooks = await database.list_playbooks()
    missions = await database.list_missions()
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert instances[0]["name"] == "Local Codex"
    assert events[0]["payload"]["ok"] is True
    assert playbook_id == playbooks[0]["id"]
    assert missions[0]["name"] == "Nightly builder"
    assert checkpoints[0]["summary"] == "Verified the first milestone."
