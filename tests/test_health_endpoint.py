from __future__ import annotations

from fastapi.testclient import TestClient

from openzues import __version__
from openzues.app import create_app
from openzues.settings import Settings


def test_health_endpoint_surfaces_server_version(tmp_path) -> None:
    data_dir = tmp_path / "data"
    with TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                db_path=data_dir / "openzues-test.db",
            )
        )
    ) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["serverVersion"] == __version__
