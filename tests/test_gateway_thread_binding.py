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
