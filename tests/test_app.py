from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from openzues.app import (
    build_continuity,
    build_cortex,
    build_economy,
    build_interference,
    build_launchpad,
    build_radar,
    build_reflex_deck,
    create_app,
)
from openzues.schemas import (
    DashboardView,
    InstanceView,
    MissionView,
    ProjectView,
    RemoteRequestView,
    TaskBlueprintView,
)
from openzues.services.control_chat import plan_attention_queue, plan_control_chat
from openzues.services.control_plane import ControlPlaneLease
from openzues.services.dreams import build_dream_deck
from openzues.settings import Settings


class FakeControlPlaneLease(ControlPlaneLease):
    def __init__(self, *, owner: bool, owner_pid: int | None = None) -> None:
        super().__init__(Path("control-plane.lock"))
        self._owner = owner
        self._simulated_owner_pid = owner_pid

    def acquire(self, *, metadata: dict[str, object] | None = None) -> bool:
        self.metadata = dict(metadata or {})
        self.acquired = self._owner
        self.owner_pid = (
            self._simulated_owner_pid if not self._owner else 1001
        )
        return self.acquired

    def release(self) -> None:
        self.acquired = False


def make_client(
    tmp_path,
    *,
    client_host: str = "testclient",
    attention_queue_enabled: bool = True,
    control_plane_lease: ControlPlaneLease | None = None,
):
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
        attention_queue_enabled=attention_queue_enabled,
    )
    app = create_app(app_settings, control_plane_lease=control_plane_lease)
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
    cwd: str = "C:/workspace",
    thread_id: str | None = None,
    updated_at: datetime | None = None,
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
        thread_id=thread_id or f"thread_{mission_id}",
        cwd=cwd,
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
        updated_at=updated_at or now,
    )


def make_task_blueprint_view(
    *,
    task_id: int,
    name: str,
    project_id: int | None = None,
    cwd: str = "C:/workspace",
    cadence_minutes: int | None = None,
    enabled: bool = True,
) -> TaskBlueprintView:
    now = datetime.now(UTC)
    return TaskBlueprintView(
        id=task_id,
        name=name,
        summary=f"{name} summary",
        objective_template=f"{name} objective",
        instance_id=1,
        project_id=project_id,
        cadence_minutes=cadence_minutes,
        cwd=cwd,
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
        enabled=enabled,
        last_launched_at=None,
        last_status=None,
        last_result_summary=None,
        created_at=now,
        updated_at=now,
    )


def make_remote_request_view(
    *,
    request_id: int,
    operator_id: int,
    target_kind: str,
    target_id: int,
    requested_at: datetime | None = None,
) -> RemoteRequestView:
    now = requested_at or datetime.now(UTC)
    return RemoteRequestView(
        id=request_id,
        team_id=1,
        team_name="Local Control",
        operator_id=operator_id,
        operator_name=f"Operator {operator_id}",
        operator_role="operator",
        kind="mission.create" if target_kind == "mission" else "task.trigger",
        status="completed",
        source="api_key",
        source_ip="127.0.0.1",
        user_agent="pytest",
        target_kind=target_kind,
        target_id=target_id,
        target_label=f"{target_kind}-{target_id}",
        idempotency_key=f"req-{request_id}",
        summary="Remote request completed.",
        error=None,
        payload_preview=None,
        result_preview=None,
        requested_at=now,
        resolved_at=now,
    )


def make_dashboard_view(
    *,
    instances: list[InstanceView] | None = None,
    missions: list[MissionView] | None = None,
    projects: list[ProjectView] | None = None,
    opportunities: list[dict[str, object]] | None = None,
) -> DashboardView:
    instances = instances or []
    missions = missions or []
    projects = projects or []
    return DashboardView.model_validate(
        {
            "brief": {
                "status": "active" if any(m.status == "active" for m in missions) else "idle",
                "headline": "Control plane summary",
                "summary": "Dashboard summary",
                "focus_mission_id": missions[0].id if missions else None,
                "next_actions": [],
            },
            "control_chat": {
                "headline": "Tell Zues what to do next",
                "summary": "Chat summary",
                "input_placeholder": "Describe the next thing",
                "messages": [],
            },
            "attention_queue": {
                "enabled": True,
                "headline": "Attention queue is standing by",
                "summary": "Queue summary",
                "actions": [],
            },
            "launchpad": {
                "headline": "Launchpad ready",
                "summary": "Launch summary",
                "opportunities": opportunities or [],
            },
            "radar": {"posture": "steady", "summary": "Radar summary", "signals": []},
            "ops_mesh": {
                "headline": "Ops mesh ready",
                "summary": "Ops summary",
                "task_inbox": {"headline": "Task inbox", "summary": "No tasks", "tasks": []},
                "auth_posture": {
                    "headline": "Auth idle",
                    "summary": "No integrations",
                    "satisfied_count": 0,
                    "missing_count": 0,
                    "degraded_count": 0,
                },
                "access_posture": {
                    "headline": "Remote ingress is local-only",
                    "summary": "No remote keys",
                    "team_count": 0,
                    "operator_count": 0,
                    "api_key_count": 0,
                    "recent_remote_request_count": 0,
                },
                "skillbooks": [],
                "teams": [],
                "operators": [],
                "remote_requests": [],
                "vault_secrets": [],
                "integrations": [],
                "notification_routes": [],
                "lane_snapshots": [],
            },
            "economy": {"headline": "Economy idle", "summary": "No economy yet", "scopes": []},
            "interference": {
                "headline": "Interference calm",
                "summary": "No overlaps",
                "vectors": [],
            },
            "continuity": {
                "headline": "Continuity ready",
                "summary": "No packets yet",
                "packets": [],
            },
            "dream_deck": {
                "headline": "No dream candidates yet",
                "summary": "No dreams",
                "dreams": [],
            },
            "cortex": {
                "headline": "Learning",
                "summary": "No doctrine yet",
                "doctrines": [],
                "inoculations": [],
            },
            "reflex_deck": {
                "headline": "No reflexes",
                "summary": "No reflexes yet",
                "reflexes": [],
            },
            "instances": [instance.model_dump(mode="json") for instance in instances],
            "missions": [mission.model_dump(mode="json") for mission in missions],
            "projects": [project.model_dump(mode="json") for project in projects],
            "playbooks": [],
            "task_blueprints": [],
            "integrations": [],
            "notification_routes": [],
            "skill_pins": [],
            "lane_snapshots": [],
            "events": [],
        }
    )


def test_health_endpoint(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["control_plane"] == "leader"


def test_observer_mode_blocks_mutating_requests(tmp_path) -> None:
    lease = FakeControlPlaneLease(owner=False, owner_pid=4242)
    with make_client(tmp_path, control_plane_lease=lease) as client:
        health = client.get("/api/health")
        dashboard = client.get("/api/dashboard")
        response = client.post("/api/control-chat", json={"text": "continue building"})

    assert health.status_code == 200
    assert health.json()["control_plane"] == "observer"
    assert health.json()["owner_pid"] == 4242
    assert dashboard.status_code == 200
    assert dashboard.json()["control_chat"]["headline"] == "Observer mode is active"
    assert dashboard.json()["attention_queue"]["headline"] == "Observer mode is active"
    assert response.status_code == 409
    assert response.json()["control_plane"] == "observer"


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
    assert dashboard["economy"]["headline"]
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
    assert dashboard["control_chat"]["headline"]
    assert dashboard["control_chat"]["input_placeholder"]


def test_control_chat_waits_for_active_mission_instead_of_launching_hardener() -> None:
    active = make_mission_view(
        mission_id=41,
        name="Live Builder",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=7,
        project_label="OpenZues",
    )
    finished = make_mission_view(
        mission_id=42,
        name="Finished Builder",
        status="completed",
        phase="completed",
        project_id=7,
        project_label="OpenZues",
        last_checkpoint="Verified a clean checkpoint and left a handoff.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[active, finished],
        projects=[make_project_view(project_id=7, label="OpenZues")],
        opportunities=[
            {
                "id": "harden-42",
                "kind": "checkpoint_hardener",
                "impact": "high",
                "title": "Harden OpenZues",
                "summary": "Tighten the finished checkpoint.",
                "why_now": "A completed handoff is ready.",
                "action_label": "Load hardener",
                "mission_draft": {
                    "name": "Harden OpenZues",
                    "objective": "Continue from the checkpoint and verify it.",
                    "instance_id": 1,
                    "project_id": 7,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_42",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )

    decision = plan_control_chat("continue building", dashboard)

    assert decision.action_kind == "wait"
    assert decision.mission_id == 41
    assert "Live Builder" in decision.reply
    assert "Harden OpenZues" in decision.reply


def test_control_chat_launches_hardener_when_no_live_loop_is_running() -> None:
    finished = make_mission_view(
        mission_id=52,
        name="ForumForge Slice",
        status="completed",
        phase="completed",
        project_id=9,
        project_label="ForumForge",
        last_checkpoint="Feature shipped and verified.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[finished],
        projects=[make_project_view(project_id=9, label="ForumForge")],
        opportunities=[
            {
                "id": "harden-52",
                "kind": "checkpoint_hardener",
                "impact": "high",
                "title": "Harden ForumForge",
                "summary": "Verify and tighten the checkpoint.",
                "why_now": "The last run already landed a handoff.",
                "action_label": "Load hardener",
                "mission_draft": {
                    "name": "Harden ForumForge",
                    "objective": "Continue from the checkpoint and make it more durable.",
                    "instance_id": 1,
                    "project_id": 9,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_52",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )

    decision = plan_control_chat("continue", dashboard)

    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "harden-52"
    assert decision.mission_payload is not None
    assert decision.mission_payload.name == "Harden ForumForge"


def test_control_chat_builds_new_mission_from_freeform_request() -> None:
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        projects=[make_project_view(project_id=3, label="OpenZues")],
    )

    decision = plan_control_chat(
        "Build a remote notification digest for failed missions and verify the full path",
        dashboard,
    )

    assert decision.action_kind == "create_mission"
    assert decision.mission_payload is not None
    assert decision.mission_payload.instance_id == 1
    assert decision.mission_payload.project_id == 3
    assert decision.mission_payload.start_immediately is True


def test_attention_queue_plans_recovery_from_failed_signal() -> None:
    failed = make_mission_view(
        mission_id=61,
        name="Vault Mesh Finish",
        status="failed",
        phase="failed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint exists",
        last_error="thread not found",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[failed],
        projects=[make_project_view(project_id=11, label="OpenZues")],
        opportunities=[
            {
                "id": "recover-61",
                "kind": "recovery_run",
                "impact": "high",
                "title": "Recover Vault Mesh Finish",
                "summary": "Resume from the failure checkpoint.",
                "why_now": "The failure already has thread context.",
                "action_label": "Recover run",
                "mission_draft": {
                    "name": "Recover Vault Mesh Finish",
                    "objective": "Recover from the failure and verify it.",
                    "instance_id": 1,
                    "project_id": 11,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_61",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )
    dashboard = dashboard.model_copy(
        update={
            "radar": build_radar(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
            "launchpad": build_launchpad(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "recover-61"
    assert decision.mission_payload is not None
    assert decision.status == "executed"


def test_attention_queue_escalates_unsafe_orphan_approval_once(tmp_path) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        runtime = client.app.state.manager.instances[instance_id]
        asyncio.run(
            database.upsert_server_request(
                instance_id=instance_id,
                request_id="approval-unsafe",
                thread_id="thread-orphan",
                method="item/commandExecution/requestApproval",
                payload={
                    "command": 'powershell.exe -Command "Remove-Item -Recurse scratch"',
                    "commandActions": [
                        {
                            "type": "unknown",
                            "command": "Remove-Item -Recurse scratch",
                        }
                    ],
                    "availableDecisions": ["accept", "cancel"],
                },
                status="pending",
            )
        )
        runtime.unresolved_requests = asyncio.run(
            database.list_unresolved_server_requests(instance_id)
        )

        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted_once = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted_twice = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted_once is True
    assert acted_twice is False
    assert len(actions) == 1
    assert actions[0]["status"] == "escalated"
    assert "surfaced it" in actions[0]["summary"]
    assert messages[-1]["action_kind"] == "observe"


def test_attention_queue_auto_approves_safe_orphan_request(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        manager = client.app.state.manager
        runtime = manager.instances[instance_id]
        asyncio.run(
            database.upsert_server_request(
                instance_id=instance_id,
                request_id="approval-safe",
                thread_id="thread-orphan",
                method="item/commandExecution/requestApproval",
                payload={
                    "command": 'powershell.exe -Command "rg -n \\"ForumForge\\" src"',
                    "commandActions": [
                        {
                            "type": "unknown",
                            "command": 'rg -n "ForumForge" src',
                        }
                    ],
                    "availableDecisions": ["accept", "cancel"],
                },
                status="pending",
            )
        )
        runtime.unresolved_requests = asyncio.run(
            database.list_unresolved_server_requests(instance_id)
        )
        resolved: list[dict[str, object]] = []

        async def fake_resolve(instance_id: int, request_id: str, result: object) -> None:
            resolved.append(
                {
                    "instance_id": instance_id,
                    "request_id": request_id,
                    "result": result,
                }
            )
            await database.resolve_server_request(
                instance_id=instance_id,
                request_id=request_id,
                status="resolved",
            )
            runtime.unresolved_requests = await database.list_unresolved_server_requests(
                instance_id
            )

        monkeypatch.setattr(manager, "resolve_request", fake_resolve)

        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted is True
    assert resolved == [
        {
            "instance_id": instance_id,
            "request_id": "approval-safe",
            "result": "accept",
        }
    ]
    assert len(actions) == 1
    assert actions[0]["action_kind"] == "resolve_request"
    assert actions[0]["status"] == "executed"
    assert "auto-approved" in (actions[0]["summary"] or "")
    assert messages[-1]["action_kind"] == "resolve_request"


def test_control_chat_endpoint_persists_wait_messages(tmp_path) -> None:
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
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Sandbox"},
        )

        assert instance_response.status_code == 200
        project_id = project_response.json()["id"]
        database = client.app.state.database

        live_mission_id = asyncio.run(
            database.create_mission(
                name="Live Run",
                objective="Keep building.",
                status="active",
                instance_id=1,
                project_id=project_id,
                task_blueprint_id=None,
                thread_id="thread-live",
                cwd=str(tmp_path),
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
        )
        asyncio.run(
            database.update_mission(
                live_mission_id,
                in_progress=1,
                phase="executing",
                last_activity_at=datetime.now(UTC).isoformat(),
            )
        )
        completed_mission_id = asyncio.run(
            database.create_mission(
                name="Finished Run",
                objective="Leave a checkpoint.",
                status="completed",
                instance_id=1,
                project_id=project_id,
                task_blueprint_id=None,
                thread_id="thread-done",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
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
        )
        asyncio.run(
            database.append_mission_checkpoint(
                mission_id=completed_mission_id,
                thread_id="thread-done",
                turn_id="turn-done",
                kind="final_answer",
                summary="Completed the finished slice and verified it.",
            )
        )
        asyncio.run(
            database.update_mission(
                completed_mission_id,
                phase="completed",
                last_checkpoint="Completed the finished slice and verified it.",
                last_activity_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            )
        )

        response = client.post("/api/control-chat", json={"text": "continue building"})
        dashboard_response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_kind"] == "wait"
    assert payload["executed"] is False
    assert "Live Run" in payload["assistant"]["content"]

    dashboard = dashboard_response.json()
    assert [message["role"] for message in dashboard["control_chat"]["messages"][-2:]] == [
        "user",
        "assistant",
    ]
    assert dashboard["control_chat"]["messages"][-1]["action_kind"] == "wait"
    assert len(dashboard["missions"]) == 2


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


def test_build_interference_detects_lane_braid() -> None:
    project = make_project_view(project_id=5, label="Checkout")
    first = make_mission_view(
        mission_id=31,
        name="Ship checkout",
        project_id=5,
        project_label="Checkout",
    )
    second = make_mission_view(
        mission_id=32,
        name="Harden checkout",
        instance_id=2,
        project_id=5,
        project_label="Checkout",
    )

    interference = build_interference([first, second], [project], [], [])

    assert interference.headline == "Interference forecast is watchful"
    assert interference.vectors[0].kind == "lane_braid"
    assert interference.vectors[0].mission_ids == [31, 32]


def test_build_interference_flags_checkpoint_eclipse() -> None:
    now = datetime.now(UTC)
    project = make_project_view(project_id=7, label="Atlas")
    anchor = make_mission_view(
        mission_id=41,
        name="Atlas anchor",
        status="completed",
        phase="completed",
        project_id=7,
        project_label="Atlas",
        last_checkpoint="Verified the current milestone.",
        thread_id="thread_anchor",
        updated_at=now - timedelta(minutes=5),
    )
    live = make_mission_view(
        mission_id=42,
        name="Atlas live",
        status="active",
        phase="thinking",
        project_id=7,
        project_label="Atlas",
        thread_id="thread_live",
    )

    interference = build_interference([anchor, live], [project], [], [])

    assert any(vector.kind == "checkpoint_eclipse" for vector in interference.vectors)


def test_build_interference_detects_remote_echo() -> None:
    now = datetime.now(UTC)
    project = make_project_view(project_id=8, label="ForumForge")
    task = make_task_blueprint_view(
        task_id=12,
        name="ForumForge loop",
        project_id=8,
        cadence_minutes=60,
    )
    requests = [
        make_remote_request_view(
            request_id=1,
            operator_id=7,
            target_kind="task",
            target_id=12,
            requested_at=now - timedelta(hours=1),
        ),
        make_remote_request_view(
            request_id=2,
            operator_id=8,
            target_kind="task",
            target_id=12,
            requested_at=now - timedelta(minutes=30),
        ),
    ]

    interference = build_interference([], [project], [task], requests)

    assert any(vector.kind == "remote_echo" for vector in interference.vectors)


def test_build_economy_marks_checkpointed_scope_as_compounding() -> None:
    project = make_project_view(project_id=9, label="Atlas")
    missions = [
        make_mission_view(
            mission_id=51,
            name="Ship Atlas",
            status="completed",
            phase="completed",
            project_id=9,
            project_label="Atlas",
            last_checkpoint="Milestone landed.",
            total_tokens=18000,
            command_count=7,
        ),
        make_mission_view(
            mission_id=52,
            name="Harden Atlas",
            status="paused",
            phase="paused",
            project_id=9,
            project_label="Atlas",
            last_checkpoint="Verified and ready.",
            total_tokens=12000,
            command_count=6,
        ),
    ]
    task = make_task_blueprint_view(
        task_id=20,
        name="Atlas upkeep",
        project_id=9,
        cadence_minutes=180,
    )

    economy = build_economy(missions, [project], [task], [])

    assert economy.headline == "Autonomy economy is compounding"
    assert economy.scopes[0].state == "compounding"
    assert economy.scopes[0].project_id == 9


def test_build_economy_marks_high_burn_scope_as_leaking() -> None:
    project = make_project_view(project_id=10, label="Checkout")
    mission = make_mission_view(
        mission_id=61,
        name="Checkout orbit",
        status="active",
        phase="thinking",
        project_id=10,
        project_label="Checkout",
        total_tokens=76000,
        command_count=18,
        last_checkpoint=None,
    )
    remote_requests = [
        make_remote_request_view(
            request_id=10,
            operator_id=1,
            target_kind="mission",
            target_id=61,
        ),
        make_remote_request_view(
            request_id=11,
            operator_id=2,
            target_kind="mission",
            target_id=61,
            requested_at=datetime.now(UTC) - timedelta(minutes=30),
        ),
        make_remote_request_view(
            request_id=12,
            operator_id=3,
            target_kind="mission",
            target_id=61,
            requested_at=datetime.now(UTC) - timedelta(minutes=10),
        ),
    ]

    economy = build_economy([mission], [project], [], remote_requests)

    assert economy.headline == "Autonomy economy is leaking"
    assert economy.scopes[0].state == "leaking"
    assert "compress" in economy.scopes[0].capital_prompt.lower()


def test_dashboard_and_project_economy_endpoint_surface_scope_profile(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        )
        project_id = project_response.json()["id"]
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
        client.post(
            "/api/missions",
            json={
                "name": "Economy probe",
                "objective": "Land a durable checkpoint.",
                "instance_id": instance_id,
                "project_id": project_id,
                "cwd": str(tmp_path),
                "thread_id": "thread_probe",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 2,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        dashboard_response = client.get("/api/dashboard")
        economy_response = client.get("/api/economy")
        project_economy_response = client.get(f"/api/projects/{project_id}/economy")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["economy"]["headline"]
    assert economy_response.status_code == 200
    assert economy_response.json()["headline"]
    assert project_economy_response.status_code == 200
    project_economy = project_economy_response.json()
    assert project_economy["scopes"][0]["project_id"] == project_id


def test_dashboard_and_project_interference_endpoint_surface_scope_overlap(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        )
        project_id = project_response.json()["id"]
        for offset in (0, 1):
            client.post(
                "/api/tasks",
                json={
                    "name": f"Overlap {offset}",
                    "summary": "Overlap detector",
                    "objective_template": "Keep the workspace healthy.",
                    "instance_id": 1,
                    "project_id": project_id,
                    "cadence_minutes": 60 + offset * 30,
                    "cwd": str(tmp_path),
                    "model": "gpt-5.4-mini",
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
        dashboard_response = client.get("/api/dashboard")
        project_interference_response = client.get(f"/api/projects/{project_id}/interference")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert any(vector["kind"] == "task_overlap" for vector in dashboard["interference"]["vectors"])
    assert project_interference_response.status_code == 200
    project_interference = project_interference_response.json()
    assert project_interference["vectors"][0]["project_id"] == project_id


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
