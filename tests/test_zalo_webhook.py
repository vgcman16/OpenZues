from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.services.ops_mesh import OpsMeshService
from openzues.settings import Settings


def _make_client(tmp_path: Path) -> TestClient:
    data_dir = tmp_path / "data"
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                db_path=data_dir / "openzues-test.db",
            )
        )
    )


def test_zalo_webhook_validates_secret_token_and_dispatches_update(
    tmp_path,
    monkeypatch,
) -> None:
    body = json.dumps(
        {
            "event_name": "message.text.received",
            "message": {
                "message_id": "zalo-msg-1",
                "text": "hello from zalo",
                "chat": {"id": "chat-123", "type": "user"},
                "from": {"id": "user-123", "display_name": "Ada"},
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    calls: list[dict[str, object]] = []

    with _make_client(tmp_path) as client:
        config = client.app.state.ops_mesh_service.gateway_config_service
        config.patch_object({"channels": {"zalo": {"webhookSecret": "secret"}}})

        async def fake_handle_zalo_webhook(self, payload, *, account_id=None):
            calls.append({"payload": payload, "account_id": account_id})
            return {"ok": True, "channel": "zalo", "eventName": payload["event_name"]}

        monkeypatch.setattr(
            OpsMeshService,
            "handle_zalo_webhook",
            fake_handle_zalo_webhook,
            raising=False,
        )

        response = client.post(
            "/zalo/webhook?accountId=zalo-bot",
            content=body,
            headers={
                "content-type": "application/json",
                "x-bot-api-secret-token": "secret",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == [
        {
            "payload": json.loads(body.decode("utf-8")),
            "account_id": "zalo-bot",
        }
    ]


def test_zalo_webhook_rejects_missing_or_bad_secret_before_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    body = b'{"event_name":"message.text.received"}'
    calls: list[object] = []

    with _make_client(tmp_path) as client:
        config = client.app.state.ops_mesh_service.gateway_config_service
        config.patch_object({"channels": {"zalo": {"webhookSecret": "secret"}}})

        async def fake_handle_zalo_webhook(self, payload, *, account_id=None):
            del account_id
            calls.append(payload)
            return {"ok": True}

        monkeypatch.setattr(
            OpsMeshService,
            "handle_zalo_webhook",
            fake_handle_zalo_webhook,
            raising=False,
        )

        missing = client.post(
            "/zalo/webhook",
            content=body,
            headers={"content-type": "application/json"},
        )
        bad = client.post(
            "/zalo/webhook",
            content=body,
            headers={
                "content-type": "application/json",
                "x-bot-api-secret-token": "bad-secret",
            },
        )

    assert missing.status_code == 401
    assert missing.json() == {"error": "Invalid Zalo webhook secret token"}
    assert bad.status_code == 401
    assert bad.json() == {"error": "Invalid Zalo webhook secret token"}
    assert calls == []
