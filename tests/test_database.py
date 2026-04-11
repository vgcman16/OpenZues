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
        cadence_minutes=60,
        enabled=True,
        payload={
            "template": "git status",
            "cwd": str(tmp_path),
            "default_variables": {"branch": "main"},
        },
    )
    project_id = await database.create_project(path=str(tmp_path), label="Sandbox")
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
        session_key="launch:mode:saved_lane:task:1:project:1:operator:1:lane:1",
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
    task_id = await database.create_task_blueprint(
        name="Nightly loop",
        summary="Keep shipping.",
        project_id=project_id,
        instance_id=instance_id,
        cadence_minutes=180,
        enabled=True,
        payload={
            "objective_template": "Ship the next slice.",
            "cwd": str(tmp_path),
            "model": "gpt-5.4",
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
        },
    )
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=instance_id,
        preferred_project_id=project_id,
        team_id=team_id,
        operator_id=operator_id,
        task_blueprint_id=task_id,
        last_route_instance_id=instance_id,
        last_route_resolved_at="2026-04-11T00:05:00+00:00",
        default_cwd=str(tmp_path),
        model="gpt-5.4",
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
    await database.upsert_setup_wizard_session(
        {
            "mode": "remote",
            "flow": "advanced",
            "project_path": str(tmp_path),
            "task_name": "Nightly loop",
            "updated_at": "2026-04-11T00:00:00+00:00",
        }
    )
    attention_action_id = await database.append_attention_queue_action(
        signal_id="mission-1-failed",
        signal_fingerprint="mission-1-failed|failed|thread not found",
        signal_level="critical",
        mission_id=mission_id,
        opportunity_id="recover-1",
        target_label="Recover Nightly builder",
        action_kind="launch_opportunity",
        status="executed",
        summary="Launched recovery from the attention queue.",
    )

    instances = await database.list_instances()
    teams = await database.list_teams()
    operators = await database.list_operators()
    events = await database.list_events()
    thread_events = await database.list_thread_events(
        instance_id=instance_id,
        thread_id="thread_1",
    )
    playbooks = await database.list_playbooks()
    missions = await database.list_missions()
    checkpoints = await database.list_mission_checkpoints(mission_id)
    remote_requests = await database.list_remote_requests()
    attention_actions = await database.list_attention_queue_actions()
    gateway_bootstrap = await database.get_gateway_bootstrap()
    wizard_session = await database.get_setup_wizard_session()

    assert instances[0]["name"] == "Local Codex"
    assert teams[0]["slug"] == "remote-ops"
    assert operators[0]["api_key_preview"] == "ozk_abcd...1234"
    assert events[0]["payload"]["ok"] is True
    assert thread_events[0]["method"] == "thread/started"
    assert thread_events[0]["payload"]["ok"] is True
    assert playbook_id == playbooks[0]["id"]
    assert playbooks[0]["cadence_minutes"] == 60
    assert playbooks[0]["enabled"] == 1
    assert playbooks[0]["default_variables"] == {"branch": "main"}
    assert missions[0]["name"] == "Nightly builder"
    assert missions[0]["session_key"] == "launch:mode:saved_lane:task:1:project:1:operator:1:lane:1"
    assert missions[0]["allow_failover"] == 1
    assert checkpoints[0]["summary"] == "Verified the first milestone."
    assert remote_request_id == remote_requests[0]["id"]
    assert remote_requests[0]["payload"]["name"] == "Nightly builder"
    assert remote_requests[0]["result"]["summary"] == "Mission created."
    assert attention_action_id == attention_actions[0]["id"]
    assert attention_actions[0]["target_label"] == "Recover Nightly builder"
    assert gateway_bootstrap is not None
    assert gateway_bootstrap["setup_mode"] == "local"
    assert gateway_bootstrap["setup_flow"] == "quickstart"
    assert gateway_bootstrap["route_binding_mode"] == "saved_lane"
    assert gateway_bootstrap["preferred_project_id"] == project_id
    assert gateway_bootstrap["task_blueprint_id"] == task_id
    assert gateway_bootstrap["last_route_instance_id"] == instance_id
    assert gateway_bootstrap["model"] == "gpt-5.4"
    assert wizard_session is not None
    assert wizard_session["session"]["mode"] == "remote"
    assert wizard_session["session"]["flow"] == "advanced"


@pytest.mark.asyncio
async def test_thread_event_metrics_capture_recent_activity(tmp_path) -> None:
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
        thread_id="thread_metrics",
        method="item/started",
        payload={"item": {"type": "commandExecution", "command": "Get-Date"}},
    )
    await database.append_event(
        instance_id=instance_id,
        thread_id="thread_metrics",
        method="item/commandExecution/outputDelta",
        payload={"delta": "Saturday"},
    )

    metrics = await database.get_thread_event_metrics(
        instance_id=instance_id,
        thread_id="thread_metrics",
    )

    assert metrics["last_event_at"] is not None
    assert metrics["recent_event_count_30s"] >= 2
    assert metrics["recent_event_count_5m"] >= 2
    assert metrics["recent_output_delta_count_30s"] >= 1
    assert metrics["recent_turn_activity_count_30s"] >= 2


@pytest.mark.asyncio
async def test_get_mission_by_thread_prefers_active_shared_owner(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.initialize()

    active_id = await database.create_mission(
        name="Shared hardener",
        objective="Continue the live thread.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_shared",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
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
    completed_id = await database.create_mission(
        name="Shared checkpoint",
        objective="Finished already.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread_shared",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
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
    await database.update_mission(completed_id, last_checkpoint="Finished parity slice.")
    await database.update_mission(active_id, in_progress=1)

    mission = await database.get_mission_by_thread(7, "thread_shared")

    assert mission is not None
    assert mission["id"] == active_id
