from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from openzues.app import (
    build_continuity,
    build_cortex,
    build_launchpad,
    build_radar,
    build_reflex_deck,
    create_app,
)
from openzues.schemas import InstanceView, MissionView, ProjectView
from openzues.services.dreams import build_dream_deck
from openzues.settings import Settings


def make_client(tmp_path, *, client_host: str = "testclient"):
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    return TestClient(app, client=(client_host, 50000))


def make_instance_view(
    *,
    instance_id: int = 1,
    name: str = "Local Codex Desktop",
    connected: bool = True,
    unresolved_requests: list[dict[str, object]] | None = None,
) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name=name,
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=connected,
        unresolved_requests=unresolved_requests or [],
    )


def make_project_view(*, project_id: int = 1, label: str = "Sandbox") -> ProjectView:
    now = datetime.now(UTC)
    return ProjectView(
        id=project_id,
        path="C:/workspace",
        label=label,
        exists=True,
        is_git_repo=True,
        branch="main",
        git_status="On branch main\nnothing to commit, working tree clean",
        recent_commits=[],
        pull_requests=[],
        last_scan_at=now.isoformat(),
    )


def make_mission_view(
    *,
    mission_id: int,
    name: str,
    status: str = "active",
    phase: str | None = "ready",
    instance_id: int = 1,
    in_progress: bool = False,
    total_tokens: int = 0,
    command_count: int = 0,
    project_id: int | None = None,
    project_label: str | None = None,
    last_checkpoint: str | None = None,
    last_error: str | None = None,
    last_activity_at: str | None = None,
    suggested_action: str | None = "Inspect the mission and keep it moving.",
    model: str = "gpt-5.4",
    max_turns: int | None = None,
    use_builtin_agents: bool = True,
    run_verification: bool = True,
    auto_commit: bool = True,
    pause_on_approval: bool = True,
    allow_auto_reflexes: bool = True,
    auto_recover: bool = True,
    auto_recover_limit: int = 2,
    reflex_cooldown_seconds: int = 900,
    turns_completed: int = 0,
    failure_count: int = 0,
    last_reflex_kind: str | None = None,
    last_reflex_at: str | None = None,
) -> MissionView:
    now = datetime.now(UTC)
    return MissionView(
        id=mission_id,
        name=name,
        objective="Keep shipping.",
        status=status,  # type: ignore[arg-type]
        instance_id=instance_id,
        instance_name="Local Codex Desktop",
        project_id=project_id,
        project_label=project_label,
        thread_id=f"thread_{mission_id}",
        cwd="C:/workspace",
        model=model,
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=max_turns,
        use_builtin_agents=use_builtin_agents,
        run_verification=run_verification,
        auto_commit=auto_commit,
        pause_on_approval=pause_on_approval,
        allow_auto_reflexes=allow_auto_reflexes,
        auto_recover=auto_recover,
        auto_recover_limit=auto_recover_limit,
        reflex_cooldown_seconds=reflex_cooldown_seconds,
        in_progress=in_progress,
        phase=phase,
        current_command=None,
        command_count=command_count,
        total_tokens=total_tokens,
        output_tokens=0,
        reasoning_tokens=0,
        last_commentary=None,
        suggested_action=suggested_action,
        turns_started=0,
        turns_completed=turns_completed,
        failure_count=failure_count,
        last_turn_id=None,
        last_error=last_error,
        last_checkpoint=last_checkpoint,
        last_reflex_kind=last_reflex_kind,
        last_reflex_at=last_reflex_at,
        last_activity_at=last_activity_at or now.isoformat(),
        checkpoints=[],
        created_at=now,
        updated_at=now,
    )


def test_health_endpoint(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_project_creation_appears_on_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        create_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Sandbox"},
        )
        dashboard_response = client.get("/api/dashboard")

    assert create_response.status_code == 200
    project = create_response.json()
    assert project["label"] == "Sandbox"
    assert project["exists"] is True
    dashboard = dashboard_response.json()
    assert dashboard["brief"]["headline"]
    assert dashboard["dream_deck"]["headline"]
    assert dashboard["missions"] == []
    assert dashboard["projects"][0]["label"] == "Sandbox"
    assert dashboard["playbooks"] == []


def test_playbook_creation_and_diagnostics_endpoint(tmp_path) -> None:
    with make_client(tmp_path) as client:
        create_response = client.post(
            "/api/playbooks",
            json={
                "name": "Status check",
                "description": "Run git status",
                "kind": "command",
                "template": "git status --short --branch",
                "instance_id": None,
                "cwd": str(tmp_path),
                "model": None,
                "reasoning_effort": None,
                "collaboration_mode": None,
                "timeout_ms": 10000,
                "thread_id": None,
            },
        )
        dashboard_response = client.get("/api/dashboard")
        diagnostics_response = client.get("/api/diagnostics")

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "Status check"
    dashboard = dashboard_response.json()
    assert dashboard["brief"]["summary"]
    assert dashboard["missions"] == []
    assert dashboard["playbooks"][0]["name"] == "Status check"
    diagnostics = diagnostics_response.json()
    assert diagnostics["checks"]


def test_desktop_instance_creation_is_supported(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

    assert response.status_code == 200
    created = response.json()
    assert created["transport"] == "desktop"
    assert created["command"] is None
    assert created["args"] is None
    assert created["resolved_transport"] is None


def test_dashboard_bootstraps_remote_access_foundations(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/dashboard")

    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["ops_mesh"]["access_posture"]["team_count"] == 1
    assert dashboard["ops_mesh"]["teams"][0]["name"] == "Local Control"
    assert dashboard["ops_mesh"]["operators"][0]["role"] == "owner"
    assert dashboard["ops_mesh"]["remote_requests"] == []


def test_remote_mission_endpoint_requires_api_key(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/remote/missions",
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "start_immediately": False,
            },
        )

    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_remote_management_requires_admin_auth(tmp_path) -> None:
    with make_client(tmp_path, client_host="203.0.113.7") as client:
        response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_remote_owner_can_manage_teams_with_api_key(tmp_path) -> None:
    with make_client(tmp_path) as local_client:
        issue_response = local_client.post("/api/operators/1/api-key")
        api_key = issue_response.json()["api_key"]
        assert api_key
    with make_client(tmp_path, client_host="203.0.113.7") as remote_client:
        response = remote_client.post(
            "/api/teams",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"name": "Remote Ops"},
        )

    assert response.status_code == 200
    assert response.json()["slug"] == "remote-ops"


def test_remote_mission_rejects_unknown_project(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        api_key = operator_response.json()["api_key"]
        response = client.post(
            "/api/remote/missions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "instance_id": instance_id,
                "project_id": 999,
                "start_immediately": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown project 999"


def test_remote_requests_are_logged_in_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        api_key = operator_response.json()["api_key"]
        assert api_key
        headers = {"Authorization": f"Bearer {api_key}", "Idempotency-Key": "mission-req-1"}
        mission_response = client.post(
            "/api/remote/missions",
            headers=headers,
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "start_immediately": False,
            },
        )
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Remote task",
                "summary": "Task launched from a remote operator.",
                "objective_template": "Check the workspace and leave a checkpoint.",
                "instance_id": instance_id,
                "project_id": None,
                "cadence_minutes": None,
                "cwd": str(tmp_path),
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 2,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "allow_auto_reflexes": True,
                "auto_recover": True,
                "auto_recover_limit": 2,
                "reflex_cooldown_seconds": 900,
                "allow_failover": True,
                "enabled": True,
            },
        )
        task_id = task_response.json()["id"]
        task_remote_response = client.post(
            f"/api/remote/tasks/{task_id}/run",
            headers={"Authorization": f"Bearer {api_key}", "Idempotency-Key": "task-req-1"},
            json={"dry_run": True},
        )
        dashboard_response = client.get("/api/dashboard")

    assert mission_response.status_code == 200
    created_request = mission_response.json()
    assert created_request["status"] == "completed"
    assert created_request["target_kind"] == "mission"
    assert task_remote_response.status_code == 200
    assert task_remote_response.json()["status"] == "dry_run"
    dashboard = dashboard_response.json()
    assert dashboard["missions"][0]["name"] == "Remote launch"
    assert dashboard["ops_mesh"]["access_posture"]["api_key_count"] == 1
    assert dashboard["ops_mesh"]["access_posture"]["recent_remote_request_count"] == 2
    kinds = [request["kind"] for request in dashboard["ops_mesh"]["remote_requests"]]
    assert "mission.create" in kinds
    assert "task.trigger" in kinds


def test_mission_creation_rejects_unknown_project(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        response = client.post(
            "/api/missions",
            json={
                "name": "Ship autonomy loop",
                "objective": "Keep improving the product until the mission runner works.",
                "instance_id": instance_id,
                "project_id": 999,
                "cwd": str(tmp_path),
                "thread_id": None,
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown project 999"


def test_mission_creation_appears_on_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Ship autonomy loop",
                "objective": "Keep improving the product until the mission runner works.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": None,
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        dashboard_response = client.get("/api/dashboard")

    assert mission_response.status_code == 200
    created = mission_response.json()
    assert created["status"] == "paused"
    dashboard = dashboard_response.json()
    assert dashboard["missions"][0]["name"] == "Ship autonomy loop"
    assert dashboard["brief"]["focus_mission_id"] == created["id"]


def test_mission_continuity_endpoint_returns_relay_packet(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Continuity probe",
                "objective": "Build a relay-safe mission.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": "thread_probe",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        mission_id = mission_response.json()["id"]
        continuity_response = client.get(f"/api/missions/{mission_id}/continuity")

    assert continuity_response.status_code == 200
    continuity = continuity_response.json()
    assert continuity["mission_id"] == mission_id
    assert continuity["state"] in {"anchored", "warming", "fragile"}
    assert continuity["relay_prompt"].startswith(
        "You are resuming or taking over an OpenZues mission."
    )


def test_build_radar_prioritizes_operator_risks() -> None:
    now = datetime.now(UTC)
    instance = make_instance_view()
    approval_mission = make_mission_view(
        mission_id=1,
        name="Approval aware",
        status="blocked",
        phase="approval",
        last_error="Waiting for approval: approval/request",
        last_activity_at=(now - timedelta(minutes=2)).isoformat(),
        suggested_action=(
            "Review the approval request and decide whether to let the mission "
            "continue."
        ),
    )
    burn_mission = make_mission_view(
        mission_id=2,
        name="Long runner",
        status="active",
        phase="thinking",
        in_progress=True,
        total_tokens=72000,
        last_checkpoint=None,
        last_activity_at=(now - timedelta(minutes=1)).isoformat(),
    )

    radar = build_radar([instance], [approval_mission, burn_mission], [make_project_view()])

    assert radar.posture == "hot"
    signal_ids = [signal.id for signal in radar.signals]
    assert "mission-1-approval" in signal_ids
    assert "mission-2-burn" in signal_ids
    assert radar.signals[0].level == "critical"


def test_build_radar_reports_ready_capacity_when_lane_is_clear() -> None:
    radar = build_radar([make_instance_view()], [], [make_project_view()])

    assert radar.posture == "steady"
    assert any(signal.id == "capacity/idle-connected" for signal in radar.signals)


def test_build_launchpad_suggests_workspace_scout_without_projects() -> None:
    launchpad = build_launchpad([make_instance_view()], [], [])

    assert launchpad.opportunities[0].kind == "workspace_scout"
    assert launchpad.opportunities[0].mission_draft.instance_id == 1
    assert launchpad.opportunities[0].mission_draft.model == "gpt-5.4-mini"


def test_build_launchpad_prioritizes_checkpoint_hardener() -> None:
    mission = make_mission_view(
        mission_id=7,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Implemented the first milestone.",
    )
    project = make_project_view(project_id=5, label="Checkout")

    launchpad = build_launchpad([make_instance_view()], [mission], [project])

    assert launchpad.opportunities[0].kind == "checkpoint_hardener"
    assert launchpad.opportunities[0].mission_draft.thread_id == "thread_7"
    assert launchpad.opportunities[0].mission_draft.project_id == 5


def test_build_launchpad_uses_drift_sweep_for_dirty_projects() -> None:
    project = make_project_view(project_id=3, label="OpenZues")
    project.git_status = " M src/openzues/app.py"

    launchpad = build_launchpad([make_instance_view()], [], [project])

    assert any(opportunity.kind == "drift_sweep" for opportunity in launchpad.opportunities)


def test_build_continuity_prioritizes_fragile_relay_packets() -> None:
    now = datetime.now(UTC)
    fragile = make_mission_view(
        mission_id=21,
        name="Orbiting relay",
        status="active",
        phase="thinking",
        command_count=12,
        turns_completed=1,
        last_checkpoint=None,
        last_activity_at=(now - timedelta(minutes=12)).isoformat(),
    )
    anchored = make_mission_view(
        mission_id=22,
        name="Anchored relay",
        status="paused",
        phase="paused",
        last_checkpoint="Verified milestone and ready for the next thin slice.",
        project_id=3,
        project_label="Atlas",
        last_activity_at=(now - timedelta(minutes=2)).isoformat(),
    )

    continuity = build_continuity(
        [make_instance_view()],
        [fragile, anchored],
        [make_project_view()],
    )

    assert continuity.headline
    assert continuity.packets[0].mission_id == 21
    assert continuity.packets[0].state == "fragile"
    assert continuity.packets[1].state in {"warming", "anchored"}
    assert continuity.packets[0].relay_prompt.startswith(
        "You are resuming or taking over an OpenZues mission."
    )


def test_build_cortex_learns_project_doctrine() -> None:
    project = make_project_view(project_id=4, label="Atlas")
    missions = [
        make_mission_view(
            mission_id=1,
            name="Ship Atlas",
            status="completed",
            project_id=4,
            project_label="Atlas",
            last_checkpoint="Milestone landed.",
            max_turns=4,
            model="gpt-5.4",
        ),
        make_mission_view(
            mission_id=2,
            name="Harden Atlas",
            status="paused",
            project_id=4,
            project_label="Atlas",
            last_checkpoint="Verified and ready.",
            max_turns=4,
            model="gpt-5.4",
        ),
    ]

    cortex = build_cortex([make_instance_view()], missions, [project])

    assert cortex.doctrines
    doctrine = cortex.doctrines[0]
    assert doctrine.project_id == 4
    assert doctrine.recommended_model == "gpt-5.4"
    assert doctrine.recommended_max_turns == 4
    assert doctrine.run_verification is True
    assert doctrine.confidence in {"solid", "strong"}


def test_build_cortex_surfaces_orbit_and_approval_inoculations() -> None:
    now = datetime.now(UTC)
    instance = make_instance_view(
        unresolved_requests=[{"thread_id": "thread_2", "method": "approval/request"}]
    )
    missions = [
        make_mission_view(
            mission_id=1,
            name="Orbiting",
            status="active",
            phase="thinking",
            in_progress=True,
            command_count=10,
            turns_completed=1,
            last_checkpoint=None,
        ),
        make_mission_view(
            mission_id=2,
            name="Approval gate",
            status="blocked",
            phase="approval",
            last_error="Waiting for approval: approval/request",
            last_activity_at=(now - timedelta(minutes=2)).isoformat(),
        ),
    ]

    cortex = build_cortex([instance], missions, [])

    inoculation_ids = [inoculation.id for inoculation in cortex.inoculations]
    assert "checkpoint-compression" in inoculation_ids
    assert "approval-sentry" in inoculation_ids


def test_build_launchpad_applies_learned_doctrine_to_ship_slice() -> None:
    project = make_project_view(project_id=9, label="Beacon")
    completed = make_mission_view(
        mission_id=4,
        name="Ship Beacon",
        status="completed",
        project_id=9,
        project_label="Beacon",
        last_checkpoint="A visible milestone shipped.",
        model="gpt-5.4-mini",
        max_turns=3,
        auto_commit=False,
    )

    launchpad = build_launchpad([make_instance_view()], [completed], [project])

    ship_slice = next(
        opportunity for opportunity in launchpad.opportunities if opportunity.kind == "ship_slice"
    )
    assert ship_slice.mission_draft.model == "gpt-5.4-mini"
    assert ship_slice.mission_draft.max_turns == 3
    assert ship_slice.mission_draft.auto_commit is False


def test_build_reflex_deck_creates_checkpoint_reflex_for_orbiting_mission() -> None:
    mission = make_mission_view(
        mission_id=12,
        name="Orbiting builder",
        status="active",
        phase="thinking",
        in_progress=True,
        command_count=11,
        turns_completed=1,
        project_id=2,
        project_label="Atlas",
    )
    project = make_project_view(project_id=2, label="Atlas")

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [project])

    assert reflex_deck.reflexes
    reflex = reflex_deck.reflexes[0]
    assert reflex.kind == "checkpoint_now"
    assert reflex.mission_id == 12
    assert "Stop expanding scope." in reflex.prompt


def test_build_reflex_deck_offers_resume_reflex_for_paused_checkpoint() -> None:
    mission = make_mission_view(
        mission_id=13,
        name="Paused hardener",
        status="paused",
        phase="paused",
        project_id=5,
        project_label="Beacon",
        last_checkpoint="Verified the first slice.",
    )
    project = make_project_view(project_id=5, label="Beacon")

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [project])

    assert any(reflex.kind == "resume_handoff" for reflex in reflex_deck.reflexes)


def test_build_dream_deck_surfaces_ready_project_memory_pass() -> None:
    project = make_project_view(project_id=8, label="OpenZues")
    missions = [
        make_mission_view(
            mission_id=31,
            name="Ship OpenZues",
            status="completed",
            phase="completed",
            project_id=8,
            project_label="OpenZues",
            last_checkpoint="Mission control shipped a stable relay lane.",
            max_turns=4,
            model="gpt-5.4",
        ),
        make_mission_view(
            mission_id=32,
            name="Harden OpenZues",
            status="paused",
            phase="paused",
            project_id=8,
            project_label="OpenZues",
            last_checkpoint="Autonomy radar now highlights operator risks earlier.",
            max_turns=4,
            model="gpt-5.4",
        ),
    ]

    deck = build_dream_deck([make_instance_view()], missions, [project])

    assert deck.dreams
    dream = deck.dreams[0]
    assert dream.project_id == 8
    assert dream.status == "ready"
    assert dream.mission_draft.project_id == 8
    assert dream.memory_prompt.startswith("# Dream: OpenZues Project Consolidation")


def test_build_dream_deck_stays_empty_without_project_signal() -> None:
    deck = build_dream_deck([make_instance_view()], [], [make_project_view()])

    assert deck.dreams == []
    assert deck.headline == "No dream candidates yet"
