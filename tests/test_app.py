from __future__ import annotations

from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.settings import Settings


def make_client(tmp_path):
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    return TestClient(app)


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
