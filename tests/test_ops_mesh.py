from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.schemas import InstanceView, MissionView, ProjectView
from openzues.services.hub import BroadcastHub
from openzues.services.ops_mesh import OpsMeshService, _serialize_task, build_ops_mesh
from openzues.settings import Settings


def make_instance(*, instance_id: int = 1, connected: bool = True) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=connected,
        skills=[],
        models=[],
        apps=[],
        plugins=[],
        threads=[],
        unresolved_requests=[],
    )


def make_project(*, project_id: int = 1, label: str = "OpenZues Workspace") -> ProjectView:
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
        last_scan_at=datetime.now(UTC).isoformat(),
    )


def make_mission(*, mission_id: int = 1, task_blueprint_id: int | None = None) -> MissionView:
    now = datetime.now(UTC)
    return MissionView(
        id=mission_id,
        name="Nightly Ship",
        objective="Ship the next verified slice.",
        status="active",
        instance_id=1,
        instance_name="Local Codex Desktop",
        project_id=1,
        project_label="OpenZues Workspace",
        task_blueprint_id=task_blueprint_id,
        thread_id="thread_1",
        cwd="C:/workspace",
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
        in_progress=False,
        phase="ready",
        current_command=None,
        command_count=0,
        total_tokens=0,
        output_tokens=0,
        reasoning_tokens=0,
        last_commentary=None,
        suggested_action="Run now.",
        turns_started=0,
        turns_completed=0,
        failure_count=0,
        last_turn_id=None,
        last_error=None,
        last_checkpoint="Verified and ready.",
        last_reflex_kind=None,
        last_reflex_at=None,
        last_activity_at=now.isoformat(),
        checkpoints=[],
        created_at=now,
        updated_at=now,
    )


def make_client(tmp_path: Path) -> TestClient:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    return TestClient(create_app(app_settings))


def test_build_ops_mesh_surfaces_due_task_inventory() -> None:
    now = datetime.now(UTC)
    task_blueprints = [
        {
            "id": 7,
            "name": "Daily Drift Sweep",
            "summary": "Check for risky repo drift.",
            "objective_template": "Inspect the repo and report drift.",
            "instance_id": 1,
            "project_id": 1,
            "cadence_minutes": 60,
            "cwd": "C:/workspace",
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
            "last_launched_at": (
                now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
            ).isoformat(),
            "last_status": "completed",
            "last_result_summary": "Last run shipped a verified slice.",
            "created_at": now,
            "updated_at": now,
        }
    ]
    task_view = _serialize_task(task_blueprints[0])
    ops_mesh = build_ops_mesh(
        [make_instance()],
        [],
        [make_project()],
        [task_view],
        [],
        [],
        [],
        [],
    )

    assert ops_mesh.task_inbox.tasks
    assert ops_mesh.task_inbox.tasks[0].status == "due"
    assert ops_mesh.task_inbox.tasks[0].cadence_label == "Every 1h"


class FakeManager:
    def __init__(self) -> None:
        self._instance = make_instance()

    async def list_views(self) -> list[InstanceView]:
        return [self._instance]

    async def get(self, instance_id: int):  # noqa: ANN001
        class Runtime:
            def __init__(self, view: InstanceView) -> None:
                self._view = view

            def view(self) -> InstanceView:
                return self._view

        return Runtime(self._instance)


class FakeMissionService:
    def __init__(self) -> None:
        self.created_payloads = []

    async def create(self, payload):  # noqa: ANN001
        self.created_payloads.append(payload)
        return make_mission(mission_id=10, task_blueprint_id=payload.task_blueprint_id)

    async def list_views(self) -> list[MissionView]:
        return []


@pytest.mark.asyncio
async def test_ops_mesh_service_launches_due_task(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified slice.",
            "cwd": "C:/workspace",
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
        },
    )
    await database.update_task_blueprint(
        1,
        last_launched_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    assert len(fake_missions.created_payloads) == 1
    payload = fake_missions.created_payloads[0]
    assert payload.task_blueprint_id == 1
    stored = await database.get_task_blueprint(1)
    assert stored is not None
    assert stored["last_status"] == "active"


def test_dashboard_ops_mesh_crud_round_trip(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        ).json()

        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Daily Ship",
                "summary": "Ship the next slice.",
                "objective_template": "Ship the next verified slice.",
                "instance_id": instance["id"],
                "project_id": project["id"],
                "cadence_minutes": 60,
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
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Ops Webhook",
                "kind": "webhook",
                "target": "https://example.invalid/webhook",
                "events": ["task/*", "mission/completed"],
                "enabled": True,
                "secret_header_name": "X-OpenZues-Key",
                "secret_token": "super-secret-token",
            },
        )
        integration_response = client.post(
            "/api/integrations",
            json={
                "name": "GitHub",
                "kind": "github",
                "project_id": project["id"],
                "base_url": "https://api.github.com",
                "auth_scheme": "token",
                "secret_label": "GITHUB_TOKEN",
                "secret_value": "ghp_1234567890",
                "notes": "Primary repo automation token.",
                "enabled": True,
            },
        )
        skill_response = client.post(
            "/api/skill-pins",
            json={
                "project_id": project["id"],
                "name": "Browser Verify",
                "prompt_hint": "Use it for browser checks after meaningful UI changes.",
                "source": "agent-browser",
                "enabled": True,
            },
        )
        snapshot_response = client.post(f"/api/instances/{instance['id']}/snapshots")
        dashboard = client.get("/api/dashboard").json()

    assert task_response.status_code == 200
    assert route_response.status_code == 200
    assert integration_response.status_code == 200
    assert skill_response.status_code == 200
    assert snapshot_response.status_code == 200
    assert dashboard["ops_mesh"]["task_inbox"]["tasks"]
    assert dashboard["ops_mesh"]["notification_routes"][0]["has_secret"] is True
    assert dashboard["ops_mesh"]["integrations"][0]["secret_preview"]
    assert dashboard["ops_mesh"]["skillbooks"][0]["skills"][0]["name"] == "Browser Verify"
    assert dashboard["ops_mesh"]["lane_snapshots"]
