from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from openzues.services.codex_rpc import extract_turn_id
from openzues.services.session_keys import normalize_agent_id

_ACP_TARGET_AGENT_REQUIRED_ERROR = (
    "ACP target agent is not configured. Pass `agentId` in `sessions_spawn` "
    "or set `acp.defaultAgent` in config."
)
_ACP_SPAWN_ACCEPTED_NOTE = (
    "initial ACP task queued in isolated session; follow-ups continue in the bound thread."
)
_ACP_SPAWN_SESSION_ACCEPTED_NOTE = (
    "thread-bound ACP session stays active after this task; continue in-thread for follow-ups."
)
_ACP_THREAD_CONTEXT_REQUIRED_ERROR = "thread=true for ACP sessions requires a channel context."
_CURRENT_BINDINGS_ID_PREFIX = "generic:"
_CONVERSATION_KEY_SEPARATOR = "\u241f"
_CHILD_THREAD_PLACEMENT_CHANNELS = frozenset({"discord", "matrix"})
_CONVERSATION_TARGET_PREFIXES = (
    "channel:",
    "conversation:",
    "group:",
    "room:",
    "dm:",
    "user:",
)


class GatewayAcpSpawnService(Protocol):
    async def spawn(
        self,
        params: Mapping[str, object],
        context: Mapping[str, object],
    ) -> dict[str, object]:
        """Start an ACP-backed child run and return an OpenClaw-shaped result."""

    async def cancel_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
    ) -> dict[str, object]:
        """Cancel any active ACP runtime work before a session mutation."""

    async def close_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
        discard_persistent_state: bool,
        require_acp_session: bool,
        allow_backend_unavailable: bool,
    ) -> dict[str, object]:
        """Close ACP runtime handles before local session state is removed."""


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _optional_agent_id(value: object) -> str | None:
    normalized = _optional_string(value)
    return normalize_agent_id(normalized) if normalized is not None else None


def _requester_channel_from_context(context: Mapping[str, object]) -> str | None:
    for key in ("requesterChannel", "channel", "agentChannel"):
        channel = _optional_string(context.get(key))
        if channel is not None:
            return channel.lower()
    return None


def _requester_account_id_from_context(context: Mapping[str, object]) -> str:
    for key in ("requesterAccountId", "accountId", "agentAccountId"):
        account_id = _optional_string(context.get(key))
        if account_id is not None:
            return account_id
    return "default"


def _requester_to_from_context(context: Mapping[str, object]) -> str | None:
    for key in ("requesterTo", "to", "agentTo"):
        target = _optional_string(context.get(key))
        if target is not None:
            return target
    return None


def _requester_thread_id_from_context(context: Mapping[str, object]) -> str | None:
    for key in ("requesterThreadId", "threadId", "agentThreadId"):
        thread_id = _optional_string(context.get(key))
        if thread_id is not None:
            return thread_id
    return None


def _requester_group_id_from_context(context: Mapping[str, object]) -> str | None:
    for key in ("requesterGroupId", "groupId", "agentGroupId"):
        group_id = _optional_string(context.get(key))
        if group_id is not None:
            return group_id
    return None


def _read_thread_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    thread = result.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"].strip() or None
    thread_id = result.get("threadId")
    if isinstance(thread_id, str):
        return thread_id.strip() or None
    return None


def _display_cwd_for_prompt(cwd: str) -> str:
    home = str(Path.home())
    for separator in ("\\", "/"):
        normalized_home = home.replace("\\", separator).replace("/", separator).rstrip(separator)
        normalized_cwd = cwd.replace("\\", separator).replace("/", separator)
        home_prefix = f"{normalized_home}{separator}"
        if normalized_cwd.lower().startswith(home_prefix.lower()):
            remainder = normalized_cwd[len(home_prefix) :]
            return f"~{separator}{remainder}" if remainder else "~"
        if normalized_cwd.lower() == normalized_home.lower():
            return "~"
    return cwd


def _prefix_acp_prompt_cwd(task: str, cwd: str | None) -> str:
    if cwd is None:
        return task
    return f"[Working directory: {_display_cwd_for_prompt(cwd)}]\n\n{task}"


def _strip_conversation_target_prefixes(channel: str, target: str) -> str | None:
    value = target.strip()
    channel_prefix = f"{channel}:"
    for _ in range(4):
        normalized = value.lower()
        if normalized.startswith(channel_prefix):
            value = value[len(channel_prefix) :].strip()
            continue
        matched = False
        for prefix in _CONVERSATION_TARGET_PREFIXES:
            if normalized.startswith(prefix):
                value = value[len(prefix) :].strip()
                matched = True
                break
        if not matched:
            break
    if not value or ":" in value:
        return None
    return value


def _current_conversation_ref(
    *,
    channel: str,
    to: str,
    thread_id: str | None,
) -> dict[str, str] | None:
    parent_conversation_id = _strip_conversation_target_prefixes(channel, to)
    if thread_id is not None:
        conversation: dict[str, str] = {"conversationId": thread_id}
        if parent_conversation_id is not None and parent_conversation_id != thread_id:
            conversation["parentConversationId"] = parent_conversation_id
        return conversation
    if parent_conversation_id is None:
        return None
    return {"conversationId": parent_conversation_id}


def _current_session_binding_record(
    *,
    child_session_key: str,
    target_agent_id: str,
    channel: str,
    account_id: str,
    conversation: Mapping[str, str],
    thread_id: str | None,
) -> dict[str, object]:
    bound_at = int(time.time() * 1000)
    conversation_id = conversation["conversationId"]
    binding_key = _CONVERSATION_KEY_SEPARATOR.join(
        [channel, account_id, "", conversation_id]
    )
    conversation_payload: dict[str, object] = {
        "channel": channel,
        "accountId": account_id,
        "conversationId": conversation_id,
    }
    parent_conversation_id = conversation.get("parentConversationId")
    if parent_conversation_id is not None:
        conversation_payload["parentConversationId"] = parent_conversation_id
    metadata: dict[str, object] = {
        "placement": "current",
        "lastActivityAt": bound_at,
        "agentId": target_agent_id,
        "boundBy": "system",
    }
    if thread_id is not None:
        metadata["threadId"] = thread_id
    return {
        "bindingId": f"{_CURRENT_BINDINGS_ID_PREFIX}{binding_key}",
        "targetSessionKey": child_session_key,
        "targetKind": "session",
        "conversation": conversation_payload,
        "status": "active",
        "boundAt": bound_at,
        "metadata": metadata,
    }


def _current_acp_thread_binding_metadata(
    *,
    context: Mapping[str, object],
    child_session_key: str,
    target_agent_id: str,
) -> dict[str, object] | None:
    channel = _requester_channel_from_context(context)
    if channel is None or channel in _CHILD_THREAD_PLACEMENT_CHANNELS:
        return None
    to = _requester_to_from_context(context)
    if to is None:
        return None
    group_id = _requester_group_id_from_context(context)
    current_conversation_target = group_id or to
    account_id = _requester_account_id_from_context(context)
    requester_thread_id = _requester_thread_id_from_context(context)
    conversation = _current_conversation_ref(
        channel=channel,
        to=current_conversation_target,
        thread_id=requester_thread_id,
    )
    if conversation is None:
        return None
    thread_binding: dict[str, object] = {
        "channel": channel,
        "accountId": account_id,
        "to": current_conversation_target,
    }
    if requester_thread_id is not None:
        thread_binding["threadId"] = requester_thread_id
    session_binding = _current_session_binding_record(
        child_session_key=child_session_key,
        target_agent_id=target_agent_id,
        channel=channel,
        account_id=account_id,
        conversation=conversation,
        thread_id=requester_thread_id,
    )
    return {
        "threadBinding": thread_binding,
        "sessionBinding": session_binding,
        "completionDelivery": {"mode": "thread", **thread_binding},
    }


class RuntimeManagerAcpSpawnService:
    def __init__(
        self,
        manager: Any,
        *,
        default_model: str = "gpt-5.4",
    ) -> None:
        self._manager = manager
        self._default_model = default_model

    async def spawn(
        self,
        params: Mapping[str, object],
        context: Mapping[str, object],
    ) -> dict[str, object]:
        task = _optional_string(params.get("task"))
        if task is None:
            return {"status": "error", "error": "task is required"}
        requested_mode = _optional_string(params.get("mode"))
        thread_requested = params.get("thread") is True
        mode = requested_mode if requested_mode in {"run", "session"} else (
            "session" if thread_requested else "run"
        )
        if mode == "session" and not thread_requested:
            return {
                "status": "error",
                "errorCode": "thread_required",
                "error": (
                    'mode="session" requires thread=true so the ACP session can stay '
                    "bound to a thread."
                ),
            }
        if thread_requested and _requester_channel_from_context(context) is None:
            return {
                "status": "error",
                "errorCode": "thread_binding_invalid",
                "error": _ACP_THREAD_CONTEXT_REQUIRED_ERROR,
            }
        target_agent_id = _optional_agent_id(params.get("agentId"))
        if target_agent_id is None:
            return {
                "status": "error",
                "errorCode": "target_agent_required",
                "error": _ACP_TARGET_AGENT_REQUIRED_ERROR,
            }
        instance_id = await self._select_instance_id()
        if instance_id is None:
            return {
                "status": "error",
                "error": "runtime=acp sessions_spawn requires a connected Codex instance.",
            }
        cwd = _optional_string(params.get("cwd"))
        resume_session_id = _optional_string(params.get("resumeSessionId"))
        try:
            thread_id: str | None
            if resume_session_id is not None:
                thread_id = resume_session_id
            else:
                thread_result = await self._manager.start_thread(
                    instance_id,
                    model=self._default_model,
                    cwd=cwd,
                    reasoning_effort=None,
                    collaboration_mode=None,
                )
                thread_id = _read_thread_id(thread_result)
                if thread_id is None:
                    return {
                        "status": "error",
                        "error": "ACP runtime did not return a thread id.",
                    }
            turn_result = await self._manager.start_turn(
                instance_id,
                thread_id=thread_id,
                text=_prefix_acp_prompt_cwd(task, cwd),
                cwd=cwd,
                model=None,
                reasoning_effort=None,
                collaboration_mode=None,
            )
        except Exception as exc:  # noqa: BLE001 - surface runtime failures to tool callers.
            return {
                "status": "error",
                "error": str(exc).strip() or type(exc).__name__,
            }

        run_id = extract_turn_id(turn_result) or thread_id
        child_session_key = f"agent:{target_agent_id}:acp:{thread_id}"
        payload: dict[str, object] = {
            "status": "accepted",
            "childSessionKey": child_session_key,
            "runId": run_id,
            "mode": mode,
            "runtimeThreadId": thread_id,
            "runtimeSessionId": thread_id,
            "note": (
                _ACP_SPAWN_SESSION_ACCEPTED_NOTE
                if mode == "session"
                else _ACP_SPAWN_ACCEPTED_NOTE
            ),
        }
        if thread_requested:
            binding_metadata = _current_acp_thread_binding_metadata(
                context=context,
                child_session_key=child_session_key,
                target_agent_id=target_agent_id,
            )
            if binding_metadata is not None:
                payload.update(binding_metadata)
        return payload

    async def _select_instance_id(self) -> int | None:
        views = await self._manager.list_views()
        fallback: int | None = None
        for view in views:
            instance_id = getattr(view, "id", None)
            if isinstance(instance_id, int) and fallback is None:
                fallback = instance_id
            if (
                isinstance(instance_id, int)
                and getattr(view, "connected", False)
                and getattr(view, "initialized", False)
            ):
                return instance_id
        return fallback

    async def cancel_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
    ) -> dict[str, object]:
        del session_key, runtime_session_id, reason
        if runtime_thread_id is None:
            return {"status": "ok", "cancelled": False, "reason": "missing_runtime_thread_id"}
        instance_id = await self._select_instance_id()
        if instance_id is None:
            return {"status": "ok", "cancelled": False, "reason": "runtime_unavailable"}
        result = await self._manager.interrupt_turn(instance_id, runtime_thread_id)
        cancelled = bool(result.get("ok")) if isinstance(result, dict) else True
        return {"status": "ok", "cancelled": cancelled}

    async def close_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
        discard_persistent_state: bool,
        require_acp_session: bool,
        allow_backend_unavailable: bool,
    ) -> dict[str, object]:
        del (
            session_key,
            runtime_thread_id,
            runtime_session_id,
            reason,
            discard_persistent_state,
            require_acp_session,
            allow_backend_unavailable,
        )
        return {"status": "ok", "closed": True}
