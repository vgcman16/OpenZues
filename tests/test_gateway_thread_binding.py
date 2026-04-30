from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openzues.schemas import ConversationTargetView, NotificationRouteView
from openzues.services.gateway_thread_binding import (
    GatewaySubagentThreadBinderRegistry,
    resolve_thread_binding_result,
)


def _route(
    *,
    channel: str = "slack",
    account_id: str | None = "default",
    peer_id: str = "channel:C123",
    enabled: bool = True,
) -> NotificationRouteView:
    now = datetime.now(UTC)
    return NotificationRouteView(
        id=1,
        name="Slack route",
        kind=channel,
        target="native://route",
        events=["gateway/send"],
        conversation_target=ConversationTargetView(
            channel=channel,
            account_id=account_id,
            peer_kind="channel",
            peer_id=peer_id,
        ),
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )


def _assert_session_binding_record(
    value: object,
    *,
    target_session_key: str = "agent:main:subagent:child",
    channel: str,
    account_id: str,
    conversation_id: str,
    thread_id: str | None,
) -> None:
    assert isinstance(value, dict)
    record_separator = "\u241f"
    assert value["bindingId"] == (
        f"generic:{channel}{record_separator}{account_id}"
        f"{record_separator}{record_separator}{conversation_id}"
    )
    assert value["targetSessionKey"] == target_session_key
    assert value["targetKind"] == "subagent"
    assert value["conversation"] == {
        "channel": channel,
        "accountId": account_id,
        "conversationId": conversation_id,
    }
    assert value["status"] == "active"
    assert isinstance(value["boundAt"], int)
    metadata = value["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["placement"] == "current"
    if thread_id is None:
        assert "threadId" not in metadata
    else:
        assert metadata["threadId"] == thread_id
    assert metadata["lastActivityAt"] == value["boundAt"]


@pytest.mark.asyncio
async def test_thread_binder_registry_resolves_current_provider_thread() -> None:
    async def list_routes() -> list[NotificationRouteView]:
        return [_route()]

    binder = GatewaySubagentThreadBinderRegistry(list_notification_route_views=list_routes)

    result = await binder(
        {"sessionKey": "agent:main:main", "agentId": "main"},
        {"sessionKey": "agent:main:subagent:child", "agentId": "main"},
        {
            "channel": "slack",
            "accountId": "default",
            "to": "channel:C123",
            "threadId": "1710000000.000100",
        },
    )

    session_binding = result.pop("sessionBinding")
    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "channel": "slack",
        "accountId": "default",
        "to": "channel:C123",
        "threadId": "1710000000.000100",
        "deliveryOrigin": {
            "channel": "slack",
            "accountId": "default",
            "to": "channel:C123",
            "threadId": "1710000000.000100",
        },
    }
    _assert_session_binding_record(
        session_binding,
        channel="slack",
        account_id="default",
        conversation_id="channel:C123",
        thread_id="1710000000.000100",
    )


@pytest.mark.asyncio
async def test_thread_binder_registry_resolves_matrix_provider_thread() -> None:
    async def list_routes() -> list[NotificationRouteView]:
        return [
            _route(
                channel="matrix",
                account_id="bot-alpha",
                peer_id="!room:example.org",
            )
        ]

    binder = GatewaySubagentThreadBinderRegistry(list_notification_route_views=list_routes)

    result = await binder(
        {"sessionKey": "agent:main:main", "agentId": "main"},
        {"sessionKey": "agent:main:subagent:child", "agentId": "main"},
        {
            "channel": "matrix",
            "accountId": "bot-alpha",
            "to": "room:!room:example.org",
            "threadId": "$thread-root",
        },
    )

    session_binding = result.pop("sessionBinding")
    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "channel": "matrix",
        "accountId": "bot-alpha",
        "to": "room:!room:example.org",
        "threadId": "$thread-root",
        "deliveryOrigin": {
            "channel": "matrix",
            "accountId": "bot-alpha",
            "to": "room:!room:example.org",
            "threadId": "$thread-root",
        },
    }
    _assert_session_binding_record(
        session_binding,
        channel="matrix",
        account_id="bot-alpha",
        conversation_id="room:!room:example.org",
        thread_id="$thread-root",
    )


@pytest.mark.asyncio
async def test_thread_binder_registry_resolves_line_current_conversation() -> None:
    async def list_routes() -> list[NotificationRouteView]:
        return [
            _route(
                channel="line",
                account_id="default",
                peer_id="line:user:U1234567890abcdef1234567890abcdef",
            )
        ]

    binder = GatewaySubagentThreadBinderRegistry(list_notification_route_views=list_routes)

    result = await binder(
        {"sessionKey": "agent:main:main", "agentId": "main"},
        {"sessionKey": "agent:main:subagent:child", "agentId": "main"},
        {
            "channel": "line",
            "accountId": "default",
            "to": "line:user:U1234567890abcdef1234567890abcdef",
        },
    )

    session_binding = result.pop("sessionBinding")
    assert result == {
        "status": "ok",
        "threadBindingReady": True,
        "channel": "line",
        "accountId": "default",
        "to": "line:user:U1234567890abcdef1234567890abcdef",
        "deliveryOrigin": {
            "channel": "line",
            "accountId": "default",
            "to": "line:user:U1234567890abcdef1234567890abcdef",
        },
    }
    _assert_session_binding_record(
        session_binding,
        channel="line",
        account_id="default",
        conversation_id="U1234567890abcdef1234567890abcdef",
        thread_id=None,
    )


@pytest.mark.asyncio
async def test_thread_binder_registry_preserves_no_hook_error_without_route() -> None:
    async def list_routes() -> list[NotificationRouteView]:
        return []

    binder = GatewaySubagentThreadBinderRegistry(list_notification_route_views=list_routes)

    result = await binder(
        {"sessionKey": "agent:main:main", "agentId": "main"},
        {"sessionKey": "agent:main:subagent:child", "agentId": "main"},
        {
            "channel": "slack",
            "accountId": "default",
            "to": "channel:C123",
            "threadId": "1710000000.000100",
        },
    )

    assert result == {
        "status": "error",
        "error": (
            "thread=true is unavailable because no channel plugin registered "
            "subagent_spawning hooks."
        ),
    }


def test_thread_binding_result_requires_ready_true_even_with_delivery_origin() -> None:
    binding, error = resolve_thread_binding_result(
        {
            "status": "ok",
            "threadBindingReady": False,
            "deliveryOrigin": {
                "channel": "slack",
                "accountId": "default",
                "to": "channel:C123",
                "threadId": "1710000000.000100",
            },
        }
    )

    assert binding is None
    assert error == (
        "Unable to create or bind a thread for this subagent session. "
        "Session mode is unavailable for this target."
    )
