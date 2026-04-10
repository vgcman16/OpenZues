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
    team_id = await database.create_team(
        name="Remote Ops",
        slug="remote-ops",
        description="Remote operator team.",
    )
    operator_id = await database.create_operator(
        team_id=team_id,
        name="Remote Operator",
        email="remote@example.com",
        role="operator",
        enabled=True,
        api_key_hash="hash123",
        api_key_preview="ozk_abcd...1234",
        api_key_issued_at="2026-04-10T00:00:00+00:00",
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
        allow_failover=True,
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_1",
        turn_id="turn_1",
        kind="final_answer",
        summary="Verified the first milestone.",
    )
    remote_request_id = await database.create_remote_request(
        team_id=team_id,
        operator_id=operator_id,
        idempotency_key="req-123",
        kind="mission.create",
        status="completed",
        source="api_key",
        source_ip="127.0.0.1",
        user_agent="pytest",
        target_kind="mission",
        target_id=mission_id,
        target_label="Nightly builder",
        payload={"name": "Nightly builder"},
        result={"summary": "Mission created."},
        resolved_at="2026-04-10T00:01:00+00:00",
    )

    instances = await database.list_instances()
    teams = await database.list_teams()
    operators = await database.list_operators()
    events = await database.list_events()
    playbooks = await database.list_playbooks()
    missions = await database.list_missions()
    checkpoints = await database.list_mission_checkpoints(mission_id)
    remote_requests = await database.list_remote_requests()

    assert instances[0]["name"] == "Local Codex"
    assert teams[0]["slug"] == "remote-ops"
    assert operators[0]["api_key_preview"] == "ozk_abcd...1234"
    assert events[0]["payload"]["ok"] is True
    assert playbook_id == playbooks[0]["id"]
    assert missions[0]["name"] == "Nightly builder"
    assert missions[0]["allow_failover"] == 1
    assert checkpoints[0]["summary"] == "Verified the first milestone."
    assert remote_request_id == remote_requests[0]["id"]
    assert remote_requests[0]["payload"]["name"] == "Nightly builder"
    assert remote_requests[0]["result"]["summary"] == "Mission created."
