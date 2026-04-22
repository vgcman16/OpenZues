from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from openzues.services.gateway_last_heartbeat import GatewayLastHeartbeatService


@dataclass(slots=True)
class _FakeKnownNode:
    display_name: str | None = None
    platform: str | None = None


class _FakeRegistry:
    def __init__(self, known_nodes: dict[str, _FakeKnownNode]) -> None:
        self._known_nodes = dict(known_nodes)

    def describe_known_node(self, node_id: str) -> _FakeKnownNode | None:
        return self._known_nodes.get(node_id)


class _FakeDatabase:
    def __init__(self, event: dict[str, object] | None) -> None:
        self._event = event

    async def get_latest_node_event(self, *, event_name: str) -> dict[str, object] | None:
        assert event_name == "heartbeat"
        return self._event


@pytest.mark.asyncio
async def test_gateway_last_heartbeat_parses_payload_json_and_promotes_openclaw_fields() -> None:
    raw_payload = {
        "ts": 1_776_851_113_365,
        "status": "ok-token",
        "channel": "telegram",
        "accountId": "ops-primary",
        "durationMs": 42,
        "hasMedia": True,
        "preview": "ping",
        "reason": "interval",
    }
    payload_json = json.dumps(raw_payload)
    service = GatewayLastHeartbeatService(
        _FakeDatabase(
            {
                "created_at": "2026-04-22T09:45:13.365+00:00",
                "payload": {
                    "nodeId": "node-1",
                    "payloadJSON": payload_json,
                },
            }
        ),
        registry=_FakeRegistry({"node-1": _FakeKnownNode("Builder Phone", "ios")}),
    )

    heartbeat = await service.build_snapshot()

    assert heartbeat == {
        "heartbeat": {
            "nodeId": "node-1",
            "displayName": "Builder Phone",
            "platform": "ios",
            "event": "heartbeat",
            "payload": raw_payload,
            "payloadJSON": payload_json,
            "createdAt": "2026-04-22T09:45:13.365+00:00",
            "ts": 1_776_851_113_365,
            "status": "ok-token",
            "channel": "telegram",
            "accountId": "ops-primary",
            "durationMs": 42,
            "hasMedia": True,
            "preview": "ping",
            "reason": "interval",
            "indicatorType": "ok",
        }
    }


@pytest.mark.asyncio
async def test_gateway_last_heartbeat_derives_ts_and_indicator_type_from_raw_payload() -> None:
    service = GatewayLastHeartbeatService(
        _FakeDatabase(
            {
                "created_at": "2026-04-22T09:45:13.365+00:00",
                "payload": {
                    "nodeId": "node-2",
                    "payload": {
                        "status": "sent",
                        "to": "+123",
                        "silent": False,
                    },
                },
            }
        ),
        registry=_FakeRegistry({"node-2": _FakeKnownNode("Managed Lane", "desktop")}),
    )

    heartbeat = await service.build_snapshot()

    assert heartbeat == {
        "heartbeat": {
            "nodeId": "node-2",
            "displayName": "Managed Lane",
            "platform": "desktop",
            "event": "heartbeat",
            "payload": {
                "status": "sent",
                "to": "+123",
                "silent": False,
            },
            "payloadJSON": '{"status": "sent", "to": "+123", "silent": false}',
            "createdAt": "2026-04-22T09:45:13.365+00:00",
            "ts": 1_776_851_113_365,
            "status": "sent",
            "to": "+123",
            "silent": False,
            "indicatorType": "alert",
        }
    }


@pytest.mark.asyncio
async def test_gateway_last_heartbeat_falls_back_to_flat_openclaw_payload_fields() -> None:
    service = GatewayLastHeartbeatService(
        _FakeDatabase(
            {
                "created_at": "2026-04-22T09:45:13.365+00:00",
                "payload": {
                    "nodeId": "node-3",
                    "status": "failed",
                    "reason": "delivery-error",
                    "channel": "telegram",
                    "preview": "ping",
                },
            }
        ),
        registry=_FakeRegistry({"node-3": _FakeKnownNode("Builder Phone", "ios")}),
    )

    heartbeat = await service.build_snapshot()

    assert heartbeat == {
        "heartbeat": {
            "nodeId": "node-3",
            "displayName": "Builder Phone",
            "platform": "ios",
            "event": "heartbeat",
            "payload": {
                "status": "failed",
                "reason": "delivery-error",
                "channel": "telegram",
                "preview": "ping",
            },
            "payloadJSON": (
                '{"status": "failed", "reason": "delivery-error", '
                '"channel": "telegram", "preview": "ping"}'
            ),
            "createdAt": "2026-04-22T09:45:13.365+00:00",
            "ts": 1_776_851_113_365,
            "status": "failed",
            "reason": "delivery-error",
            "channel": "telegram",
            "preview": "ping",
            "indicatorType": "error",
        }
    }
