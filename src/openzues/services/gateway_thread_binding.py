from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from openzues.schemas import NotificationRouteView
from openzues.services.gateway_message_actions import (
    GatewayMessageActionDispatcher,
    GatewayMessageActionDispatchRequest,
)
from openzues.services.session_keys import DEFAULT_ACCOUNT_ID

NO_THREAD_BINDING_HOOK_ERROR = (
    "thread=true is unavailable because no channel plugin registered subagent_spawning hooks."
)
SUPPORTED_THREAD_BINDING_CHANNELS = frozenset(
    {"slack", "telegram", "discord", "whatsapp", "zalo", "line", "matrix"}
)
_CURRENT_BINDINGS_ID_PREFIX = "generic:"
_CONVERSATION_KEY_SEPARATOR = "\u241f"
_PROVIDER_CHILD_THREAD_CHANNELS = frozenset({"discord", "matrix"})
_LINE_CONVERSATION_TARGET_PREFIXES = (
    "line:",
    "channel:",
    "conversation:",
    "group:",
    "room:",
    "dm:",
    "user:",
)


class GatewaySubagentThreadBinder(Protocol):
    async def __call__(
        self,
        parent: dict[str, object],
        child: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        """Prepare a persistent subagent thread binding and return delivery metadata."""

    async def unbind(
        self,
        target: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        """Best-effort cleanup for a prepared binding after spawn failure."""


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


def _line_conversation_id(target: str) -> str:
    value = target.strip()
    for _ in range(4):
        normalized = value.lower()
        matched = False
        for prefix in _LINE_CONVERSATION_TARGET_PREFIXES:
            if normalized.startswith(prefix):
                value = value[len(prefix) :].strip()
                matched = True
                break
        if not matched:
            break
    return value or target


def _session_binding_conversation_id(*, channel: str, target: str) -> str:
    if channel == "line":
        return _line_conversation_id(target)
    return target


def _thread_binding_display_name(*, agent_id: str | None, label: str | None) -> str:
    base = label or agent_id or "agent"
    return " ".join(base.split())[:100] or "agent"


def _discord_channel_id(value: str | None) -> str | None:
    text = _optional_string(value)
    if text is None:
        return None
    for _ in range(3):
        normalized = text.lower()
        for prefix in ("discord:channel:", "channel:", "discord:"):
            if normalized.startswith(prefix):
                text = text[len(prefix) :].strip()
                break
        else:
            break
    return text or None


def _provider_thread_id(result: object) -> str | None:
    if not isinstance(result, Mapping):
        return None
    for key in ("threadId", "id"):
        value = _optional_string(result.get(key))
        if value is not None:
            return value
    thread = result.get("thread")
    if isinstance(thread, Mapping):
        for key in ("id", "threadId"):
            value = _optional_string(thread.get(key))
            if value is not None:
                return value
    return None


def _provider_message_id(result: object) -> str | None:
    if not isinstance(result, Mapping):
        return None
    for key in ("messageId", "eventId", "event_id", "threadId", "id"):
        value = _optional_string(result.get(key))
        if value is not None:
            return value
    for nested_key in ("result", "message", "event", "thread"):
        nested = result.get(nested_key)
        if isinstance(nested, Mapping):
            nested_value = _provider_message_id(nested)
            if nested_value is not None:
                return nested_value
    return None


def _matrix_room_id(value: str | None) -> str | None:
    text = _optional_string(value)
    if text is None:
        return None
    for _ in range(3):
        normalized = text.lower()
        for prefix in ("matrix:room:", "room:"):
            if normalized.startswith(prefix):
                text = text[len(prefix) :].strip()
                break
        else:
            break
    return text or None


def _matrix_room_target(room_id: str) -> str:
    return f"room:{room_id}"


def _matrix_binding_intro_text(*, child: dict[str, object]) -> str:
    label = _optional_string(child.get("label"))
    agent_id = _optional_string(child.get("agentId"))
    child_session_key = _optional_string(child.get("sessionKey"))
    session_agent_id: str | None = None
    if child_session_key is not None:
        _prefix, separator, tail = child_session_key.rpartition(":subagent:")
        if separator:
            session_agent_id = _optional_string(tail)
    base = label or agent_id or session_agent_id or "session"
    base = " ".join(base.split()) or "session"
    return (
        "\u2699\ufe0f "
        f"{base} session active. Messages here go directly to this session."
    )


def _session_binding_record(
    *,
    child: dict[str, object],
    channel: str,
    account_id: str,
    conversation_id: str,
    thread_id: str | None,
) -> dict[str, object] | None:
    target_session_key = _optional_string(child.get("sessionKey"))
    if target_session_key is None:
        return None
    bound_at = int(time.time() * 1000)
    conversation: dict[str, object] = {
        "channel": channel,
        "accountId": account_id,
        "conversationId": conversation_id,
    }
    placement = "child" if channel in _PROVIDER_CHILD_THREAD_CHANNELS else "current"
    metadata: dict[str, object] = {
        "placement": placement,
        "lastActivityAt": bound_at,
    }
    if thread_id is not None:
        metadata["threadId"] = thread_id
    binding_key = _CONVERSATION_KEY_SEPARATOR.join(
        [channel, account_id, "", conversation_id]
    )
    return {
        "bindingId": f"{_CURRENT_BINDINGS_ID_PREFIX}{binding_key}",
        "targetSessionKey": target_session_key,
        "targetKind": "subagent",
        "conversation": conversation,
        "status": "active",
        "boundAt": bound_at,
        "metadata": metadata,
    }


def _matrix_child_session_binding_record(
    *,
    child: dict[str, object],
    account_id: str,
    room_id: str,
    thread_id: str,
) -> dict[str, object] | None:
    target_session_key = _optional_string(child.get("sessionKey"))
    if target_session_key is None:
        return None
    bound_at = int(time.time() * 1000)
    metadata: dict[str, object] = {
        "placement": "child",
        "lastActivityAt": bound_at,
        "threadId": thread_id,
        "boundBy": "system",
    }
    agent_id = _optional_string(child.get("agentId"))
    label = _optional_string(child.get("label"))
    if agent_id is not None:
        metadata["agentId"] = agent_id
    if label is not None:
        metadata["label"] = label
    return {
        "bindingId": f"{account_id}:{room_id}:{thread_id}",
        "targetSessionKey": target_session_key,
        "targetKind": "subagent",
        "conversation": {
            "channel": "matrix",
            "accountId": account_id,
            "conversationId": thread_id,
            "parentConversationId": room_id,
        },
        "status": "active",
        "boundAt": bound_at,
        "metadata": metadata,
    }


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
        message_action_dispatcher: GatewayMessageActionDispatcher | None = None,
    ) -> None:
        self._list_notification_route_views = list_notification_route_views
        self._message_action_dispatcher = message_action_dispatcher

    async def _create_discord_child_thread(
        self,
        *,
        parent_channel: str,
        account_id: str,
        child: dict[str, object],
    ) -> str | None:
        if self._message_action_dispatcher is None:
            return None
        channel_id = _discord_channel_id(parent_channel)
        if channel_id is None:
            return None
        child_session_key = _optional_string(child.get("sessionKey"))
        child_agent_id = _optional_string(child.get("agentId"))
        label = _optional_string(child.get("label"))
        result = await self._message_action_dispatcher(
            GatewayMessageActionDispatchRequest(
                channel="discord",
                action="thread-create",
                params={
                    "channelId": channel_id,
                    "threadName": _thread_binding_display_name(
                        agent_id=child_agent_id,
                        label=label,
                    ),
                    "autoArchiveMinutes": 60,
                },
                idempotency_key=(
                    f"subagent-thread-create:{child_session_key}"
                    if child_session_key is not None
                    else "subagent-thread-create"
                ),
                account_id=account_id,
                session_key=child_session_key,
                agent_id=child_agent_id,
            )
        )
        return _provider_thread_id(result)

    async def _create_matrix_child_thread(
        self,
        *,
        parent_room: str,
        account_id: str,
        child: dict[str, object],
    ) -> tuple[str, str, str] | None:
        if self._message_action_dispatcher is None:
            return None
        room_id = _matrix_room_id(parent_room)
        if room_id is None:
            return None
        child_session_key = _optional_string(child.get("sessionKey"))
        child_agent_id = _optional_string(child.get("agentId"))
        result = await self._message_action_dispatcher(
            GatewayMessageActionDispatchRequest(
                channel="matrix",
                action="send",
                params={
                    "to": _matrix_room_target(room_id),
                    "message": _matrix_binding_intro_text(child=child),
                },
                idempotency_key=(
                    f"subagent-thread-create:{child_session_key}"
                    if child_session_key is not None
                    else "subagent-thread-create"
                ),
                account_id=account_id,
                session_key=child_session_key,
                agent_id=child_agent_id,
            )
        )
        thread_id = _provider_message_id(result)
        if thread_id is None:
            return None
        return _matrix_room_target(room_id), room_id, thread_id

    async def __call__(
        self,
        parent: dict[str, object],
        child: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        del parent
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
        provider_created_thread_id: str | None = None
        matrix_parent_room_id: str | None = None
        if channel == "discord" and thread_id is None:
            provider_created_thread_id = await self._create_discord_child_thread(
                parent_channel=resolved_to,
                account_id=account_id,
                child=child,
            )
            if provider_created_thread_id is None:
                return {
                    "status": "error",
                    "error": (
                        "Unable to create or bind a thread for this subagent session. "
                        "Session mode is unavailable for this target."
                    ),
                }
            thread_id = provider_created_thread_id
        if channel == "matrix" and thread_id is None:
            try:
                matrix_created = await self._create_matrix_child_thread(
                    parent_room=resolved_to,
                    account_id=account_id,
                    child=child,
                )
            except Exception as exc:
                return {
                    "status": "error",
                    "error": f"Matrix thread bind failed: {exc}",
                }
            if matrix_created is None:
                return {
                    "status": "error",
                    "error": (
                        "Unable to create or bind a Matrix thread for this subagent session. "
                        "Session mode is unavailable for this target."
                    ),
                }
            resolved_to, matrix_parent_room_id, provider_created_thread_id = matrix_created
            thread_id = provider_created_thread_id
        binding: dict[str, object] = {
            "channel": channel,
            "accountId": account_id,
            "to": resolved_to,
        }
        if thread_id is not None:
            binding["threadId"] = thread_id
        conversation_target = (
            f"channel:{provider_created_thread_id}"
            if provider_created_thread_id is not None
            else resolved_to
        )
        conversation_id = _session_binding_conversation_id(
            channel=channel,
            target=conversation_target,
        )
        if (
            channel == "matrix"
            and matrix_parent_room_id is not None
            and provider_created_thread_id is not None
        ):
            session_binding = _matrix_child_session_binding_record(
                child=child,
                account_id=account_id,
                room_id=matrix_parent_room_id,
                thread_id=provider_created_thread_id,
            )
        else:
            session_binding = _session_binding_record(
                child=child,
                channel=channel,
                account_id=account_id,
                conversation_id=conversation_id,
                thread_id=thread_id,
            )
        result: dict[str, object] = {
            "status": "ok",
            "threadBindingReady": True,
            **binding,
            "deliveryOrigin": dict(binding),
        }
        if provider_created_thread_id is not None:
            result["providerThreadCreated"] = True
            result["providerThreadId"] = provider_created_thread_id
        if session_binding is not None:
            result["sessionBinding"] = session_binding
        return result

    async def unbind(
        self,
        target: dict[str, object],
        context: dict[str, object],
    ) -> dict[str, object]:
        del target, context
        return {"status": "ok", "unbound": False, "reason": "stateless_route_binding"}


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
    if status == "ok" and result.get("threadBindingReady") is not True:
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
    return binding, None
