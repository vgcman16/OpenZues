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
    assert dashboard["projects"][0]["label"] == "Sandbox"
