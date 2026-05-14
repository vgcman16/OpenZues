from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.schemas import ConversationTargetView
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.session_keys import build_launch_session_key
from openzues.settings import Settings


def test_googlechat_webhook_accepts_addon_body_system_id_token(tmp_path: Path) -> None:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    data_dir = tmp_path / "data"
    settings_dir = data_dir / "settings"
    settings_dir.mkdir(parents=True)
    (settings_dir / "control-ui-config.json").write_text(
        json.dumps(
            {
                "assistantName": "OpenZues",
                "assistantAvatar": "/static/favicon.svg",
                "assistantAgentId": "main",
                "channels": {
                    "googlechat": {
                        "webhookPath": "/googlechat",
                        "webhookToken": "addon-token",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    app_settings = Settings(
        data_dir=data_dir,
        db_path=data_dir / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        return {"messageId": "googlechat-route-message-1"}

    app.state.ops_mesh_service.session_delivery_service = fake_session_delivery

    with TestClient(app) as client:
        response = client.post(
            "/googlechat",
            json={
                "commonEventObject": {"hostApp": "CHAT"},
                "authorizationEventObject": {"systemIdToken": "addon-token"},
                "chat": {
                    "eventTime": "2026-03-02T00:00:00.000Z",
                    "user": {
                        "name": "users/12345",
                        "displayName": "Test User",
                    },
                    "messagePayload": {
                        "space": {"name": "spaces/AAA", "type": "ROOM"},
                        "message": {
                            "name": "spaces/AAA/messages/msg-1",
                            "text": "Hello from add-on",
                        },
                    },
                },
            },
        )

    expected_target = ConversationTargetView(
        channel="googlechat",
        account_id="default",
        peer_kind="channel",
        peer_id="googlechat:spaces/AAA",
    )
    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=expected_target,
    )

    assert response.status_code == 200
    assert response.json() == {}
    assert session_deliveries == [(expected_session_key, "Hello from add-on")]
