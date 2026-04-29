from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from openzues.schemas import NotificationRouteView
from openzues.services.session_keys import DEFAULT_ACCOUNT_ID

NO_THREAD_BINDING_HOOK_ERROR = (
    "thread=true is unavailable because no channel plugin registered subagent_spawning hooks."
)
SUPPORTED_THREAD_BINDING_CHANNELS = frozenset({"slack", "telegram", "discord", "whatsapp"})


class GatewaySubagentThreadBinder(Protocol):
    async def __call__(
        self,
        parent: dict[str, object],
        child: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        """Prepare a persistent subagent thread binding and return delivery metadata."""


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_channel(value: object) -> str | None:
    text = _optional_string(value)
    return text.lower() if text is not None else None


def _normalize_account(value: object) -> str:
    return _optional_string(value) or DEFAULT_ACCOUNT_ID


def _route_target_to(route: NotificationRouteView) -> str | None:
    target = route.conversation_target
    if target is None:
        return None
    return _optional_string(target.peer_id)


def _matches_requested_to(route_to: str | None, requested_to: str | None) -> bool:
    if requested_to is None:
        return True
    if route_to is None:
        return False
    normalized_route_to = route_to.strip().lower()
    normalized_requested_to = requested_to.strip().lower()
    if normalized_route_to == normalized_requested_to:
        return True
    _requested_prefix, requested_sep, requested_tail = normalized_requested_to.partition(":")
    if requested_sep and normalized_route_to == requested_tail:
        return True
    _route_prefix, route_sep, route_tail = normalized_route_to.partition(":")
    return bool(route_sep and route_tail == normalized_requested_to)


def _route_supports_context(
    route: NotificationRouteView,
    *,
    channel: str,
    account_id: str,
    requested_to: str | None,
) -> bool:
    if not route.enabled:
        return False
    if str(route.kind or "").strip().lower() != channel:
        return False
    target = route.conversation_target
    if target is None:
        return False
    if _normalize_channel(target.channel) != channel:
        return False
    if _normalize_account(target.account_id) != account_id:
        return False
    return _matches_requested_to(_route_target_to(route), requested_to)


class GatewaySubagentThreadBinderRegistry:
    def __init__(
        self,
        *,
        list_notification_route_views: Callable[[], Awaitable[list[NotificationRouteView]]],
    ) -> None:
        self._list_notification_route_views = list_notification_route_views

    async def __call__(
        self,
        parent: dict[str, object],
        child: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        del parent, child
        channel = _normalize_channel(context.get("channel"))
        if channel is None or channel not in SUPPORTED_THREAD_BINDING_CHANNELS:
            return {"status": "error", "error": NO_THREAD_BINDING_HOOK_ERROR}
        account_id = _normalize_account(context.get("accountId"))
        requested_to = _optional_string(context.get("to"))
        route = next(
            (
                candidate
                for candidate in await self._list_notification_route_views()
                if _route_supports_context(
                    candidate,
                    channel=channel,
                    account_id=account_id,
                    requested_to=requested_to,
                )
            ),
            None,
        )
        if route is None:
            return {"status": "error", "error": NO_THREAD_BINDING_HOOK_ERROR}
        resolved_to = requested_to or _route_target_to(route)
        if resolved_to is None:
            return {
                "status": "error",
                "error": (
                    "Unable to create or bind a thread for this subagent session. "
                    "Session mode is unavailable for this target."
                ),
            }
        thread_id = _optional_string(context.get("threadId"))
        binding: dict[str, object] = {
            "channel": channel,
            "accountId": account_id,
            "to": resolved_to,
        }
        if thread_id is not None:
            binding["threadId"] = thread_id
        return {
            "status": "ok",
            "threadBindingReady": True,
            **binding,
            "deliveryOrigin": dict(binding),
        }


def resolve_thread_binding_result(
    result: Mapping[str, object],
) -> tuple[dict[str, str] | None, str | None]:
    status = _optional_string(result.get("status"))
    if status == "error":
        return None, _optional_string(result.get("error")) or (
            "Failed to prepare thread binding for this subagent session."
        )
    if status is not None and status != "ok":
        return None, (
            "Unable to create or bind a thread for this subagent session. "
            "Session mode is unavailable for this target."
        )

    source = result.get("deliveryOrigin")
    if not isinstance(source, Mapping):
        source = result
    binding: dict[str, str] = {}
    for key in ("channel", "to", "accountId", "threadId"):
        value = _optional_string(source.get(key))
        if value is not None:
            binding[key] = value
    if not binding and result.get("threadBindingReady") is not True and status == "ok":
        return None, (
            "Unable to create or bind a thread for this subagent session. "
            "Session mode is unavailable for this target."
        )
    return binding, None
