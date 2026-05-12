from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.services.ops_mesh import OpsMeshService
from openzues.settings import Settings


def _line_signature(body: bytes, channel_secret: str) -> str:
    return base64.b64encode(
        hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("ascii")


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


def test_line_webhook_validates_signature_and_dispatches_events(tmp_path, monkeypatch) -> None:
    channel_secret = "line-secret"
    body = json.dumps(
        {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-token-1",
                    "source": {"type": "user", "userId": "U123"},
                    "message": {"id": "msg-1", "type": "text", "text": "hello"},
                }
            ]
        },
        separators=(",", ":"),
    ).encode("utf-8")
    calls: list[dict[str, object]] = []

    with _make_client(tmp_path) as client:
        config = client.app.state.ops_mesh_service.gateway_config_service
        config.patch_object({"channels": {"line": {"channelSecret": channel_secret}}})

        async def fake_handle_line_webhook(self, payload, *, account_id=None):
            calls.append({"payload": payload, "account_id": account_id})
            return {"ok": True, "channel": "line", "eventCount": len(payload["events"])}

        monkeypatch.setattr(OpsMeshService, "handle_line_webhook", fake_handle_line_webhook)

        response = client.post(
            "/line/webhook?accountId=line-main",
            content=body,
            headers={
                "content-type": "application/json",
                "x-line-signature": _line_signature(body, channel_secret),
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert calls == [
        {
            "payload": json.loads(body.decode("utf-8")),
            "account_id": "line-main",
        }
    ]


def test_line_webhook_rejects_missing_or_bad_signature_before_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    channel_secret = "line-secret"
    body = b'{"events":[{"type":"message"}]}'
    calls: list[object] = []

    with _make_client(tmp_path) as client:
        config = client.app.state.ops_mesh_service.gateway_config_service
        config.patch_object({"channels": {"line": {"channelSecret": channel_secret}}})

        async def fake_handle_line_webhook(self, payload, *, account_id=None):
            calls.append(payload)
            return {"ok": True}

        monkeypatch.setattr(OpsMeshService, "handle_line_webhook", fake_handle_line_webhook)

        missing = client.post(
            "/line/webhook",
            content=body,
            headers={"content-type": "application/json"},
        )
        bad = client.post(
            "/line/webhook",
            content=body,
            headers={
                "content-type": "application/json",
                "x-line-signature": "bad-signature",
            },
        )

    assert missing.status_code == 400
    assert missing.json() == {"error": "Missing X-Line-Signature header"}
    assert bad.status_code == 401
    assert bad.json() == {"error": "Invalid signature"}
    assert calls == []
