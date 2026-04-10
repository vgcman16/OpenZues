from __future__ import annotations

from openzues.services.manager import compact_event_payload


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
