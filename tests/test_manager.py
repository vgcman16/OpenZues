from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from openzues.database import Database
from openzues.services.hub import BroadcastHub
from openzues.services.manager import InstanceRuntime, RuntimeManager, compact_event_payload


def test_compact_event_payload_trims_catalog_updates() -> None:
    payload = {
        "data": [
            {
                "id": "connector_1",
                "name": "GitHub",
                "description": "Access repositories",
                "logoUrl": "https://example.com/logo.png",
                "isAccessible": True,
            },
            {
                "id": "connector_2",
                "name": "Slack",
                "description": "Read channel context",
                "logoUrl": "https://example.com/slack.png",
                "isAccessible": False,
            },
        ]
    }

    compact = compact_event_payload("app/list/updated", payload)

    assert compact["count"] == 2
    assert compact["truncated"] is False
    assert compact["data"] == [
        {
            "id": "connector_1",
            "name": "GitHub",
            "description": "Access repositories",
            "isAccessible": True,
        },
        {
            "id": "connector_2",
            "name": "Slack",
            "description": "Read channel context",
            "isAccessible": False,
        },
    ]


def test_compact_event_payload_keeps_thread_status_signal() -> None:
    payload = {
        "data": [
            {
                "id": "thread_1",
                "title": "Mission workspace",
                "status": {"type": "active", "reason": "running"},
                "updatedAt": "2026-04-10T09:00:00Z",
                "extra": "discard me",
            }
        ]
    }

    compact = compact_event_payload("thread/list/updated", payload)

    assert compact["data"] == [
        {
            "id": "thread_1",
            "title": "Mission workspace",
            "updatedAt": "2026-04-10T09:00:00Z",
            "status": {"type": "active"},
        }
    ]


def test_compact_event_payload_summarizes_account_updates() -> None:
    payload = {
        "account": {
            "type": "chatgpt",
            "email": "operator@example.com",
            "planType": "pro",
            "unused": "drop me",
        }
    }

    compact = compact_event_payload("account/updated", payload)

    assert compact["account"] == {
        "type": "chatgpt",
        "email": "operator@example.com",
        "planType": "pro",
    }


def test_compact_event_payload_truncates_long_server_logs() -> None:
    line = "<html>" + ("abcdef" * 90)

    compact = compact_event_payload("server/stderr", {"line": line})

    assert compact["line"].endswith("... [truncated]")
    assert compact["lineLength"] == len(line)


def test_compact_event_payload_drops_empty_catalog_items() -> None:
    compact = compact_event_payload("skill/list/updated", {"data": [{"name": "Checks"}, {}]})

    assert compact["data"] == [{"name": "Checks"}]


class FakeInterruptClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def interrupt_turn(self, *, thread_id: str, turn_id: str | None = None) -> dict[str, str]:
        self.calls.append({"thread_id": thread_id, "turn_id": turn_id or ""})
        return {"ok": "true"}


@pytest.mark.asyncio
async def test_interrupt_turn_uses_latest_active_turn_from_events(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    await database.append_event(
        instance_id=1,
        thread_id="thread_123",
        method="turn/started",
        payload={"threadId": "thread_123", "turnId": "turn_123"},
    )
    manager.refresh_instance = AsyncMock(return_value=runtime)  # type: ignore[method-assign]

    result = await manager.interrupt_turn(1, "thread_123")

    assert client.calls == [{"thread_id": "thread_123", "turn_id": "turn_123"}]
    assert result == {"ok": "true"}
