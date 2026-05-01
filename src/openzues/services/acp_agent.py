from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from openzues.services.acp_commands import get_available_commands
from openzues.services.acp_event_mapper import (
    extract_tool_call_content,
    extract_tool_call_locations,
    format_tool_title,
    infer_tool_kind,
)
from openzues.services.acp_session_mapper import parse_session_meta, resolve_session_key
from openzues.services.acp_session_store import (
    InMemoryAcpSessionStore,
    default_acp_session_store,
)
from openzues.services.acp_translator import build_prompt_send_request

ACP_PROTOCOL_VERSION = "0.4.0"
ACP_LOAD_SESSION_REPLAY_LIMIT = 1_000_000
ACP_AGENT_INFO = {
    "name": "openclaw-acp",
    "title": "OpenClaw ACP Gateway",
    "version": "0.0.0-openzues",
}
_THINKING_LEVELS = ["off", "minimal", "low", "medium", "high", "adaptive"]
_SESSION_CREATE_RATE_LIMIT_DEFAULT_MAX_REQUESTS = 120
_SESSION_CREATE_RATE_LIMIT_DEFAULT_WINDOW_MS = 10_000


class AcpGatewayClient(Protocol):
    async def request(self, method: str, params: dict[str, object]) -> Mapping[str, Any]:
        ...


class AcpConnection(Protocol):
    async def session_update(self, payload: dict[str, object]) -> object:
        ...


@dataclass
class _PendingPrompt:
    session_id: str
    session_key: str
    run_id: str
    future: asyncio.Future[dict[str, object]]
    send_accepted: bool = False
    sent_text_length: int = 0
    sent_thought_length: int = 0
    tool_calls: dict[str, dict[str, object]] = field(default_factory=dict)


def _normalize_optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _read_positive_int(record: Mapping[str, object] | None, key: str, fallback: int) -> int:
    if record is None:
        return fallback
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return fallback
    return max(1, int(value))


def _is_admin_scope_provenance_rejection(error: Exception) -> bool:
    gateway_code = getattr(error, "gatewayCode", None) or getattr(error, "gateway_code", None)
    error_name = getattr(error, "name", None) or type(error).__name__
    return (
        error_name == "GatewayClientRequestError"
        and gateway_code == "INVALID_REQUEST"
        and "system provenance fields require admin scope" in str(error)
    )


def _format_thinking_level_name(level: str) -> str:
    if level == "xhigh":
        return "Extra High"
    if level == "adaptive":
        return "Adaptive"
    return f"{level[0].upper()}{level[1:]}" if level else "Unknown"


def _format_config_value_name(value: str) -> str:
    if value == "xhigh":
        return "Extra High"
    return f"{value[0].upper()}{value[1:]}" if value else "Unknown"


def _build_select_config_option(
    *,
    option_id: str,
    name: str,
    description: str,
    current_value: str,
    values: Sequence[str],
    category: str | None = None,
) -> dict[str, object]:
    option: dict[str, object] = {
        "type": "select",
        "id": option_id,
        "name": name,
        "description": description,
        "currentValue": current_value,
        "options": [
            {"value": value, "name": _format_config_value_name(value)}
            for value in values
        ],
    }
    if category is not None:
        option["category"] = category
    return option


def _session_row(row: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _build_session_presentation(
    row: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    merged = _session_row(row)
    if overrides is not None:
        merged.update(overrides)
    available_level_ids = list(_THINKING_LEVELS)
    current_mode_id = _normalize_optional_string(merged.get("thinkingLevel")) or "adaptive"
    if current_mode_id not in available_level_ids:
        available_level_ids.append(current_mode_id)

    modes = {
        "currentModeId": current_mode_id,
        "availableModes": [
            {
                "id": level,
                "name": _format_thinking_level_name(level),
                **(
                    {"description": "Use the Gateway session default thought level."}
                    if level == "adaptive"
                    else {}
                ),
            }
            for level in available_level_ids
        ],
    }
    config_options = [
        _build_select_config_option(
            option_id="thought_level",
            name="Thought level",
            category="thought_level",
            description=(
                "Controls how much deliberate reasoning OpenClaw requests from "
                "the Gateway model."
            ),
            current_value=current_mode_id,
            values=available_level_ids,
        ),
        _build_select_config_option(
            option_id="fast_mode",
            name="Fast mode",
            description="Controls whether OpenAI sessions use the Gateway fast-mode profile.",
            current_value="on" if merged.get("fastMode") is True else "off",
            values=("off", "on"),
        ),
        _build_select_config_option(
            option_id="verbose_level",
            name="Tool verbosity",
            description=(
                "Controls how much tool progress and output detail OpenClaw "
                "keeps enabled for the session."
            ),
            current_value=_normalize_optional_string(merged.get("verboseLevel")) or "off",
            values=("off", "on", "full"),
        ),
        _build_select_config_option(
            option_id="trace_level",
            name="Plugin trace",
            description="Controls whether plugin-owned trace lines are shown for the session.",
            current_value=_normalize_optional_string(merged.get("traceLevel")) or "off",
            values=("off", "on"),
        ),
        _build_select_config_option(
            option_id="reasoning_level",
            name="Reasoning stream",
            description=(
                "Controls whether reasoning-capable models emit reasoning text "
                "for the session."
            ),
            current_value=_normalize_optional_string(merged.get("reasoningLevel")) or "off",
            values=("off", "on", "stream"),
        ),
        _build_select_config_option(
            option_id="response_usage",
            name="Usage detail",
            description=(
                "Controls how much usage information OpenClaw attaches to "
                "responses for the session."
            ),
            current_value=_normalize_optional_string(merged.get("responseUsage")) or "off",
            values=("off", "tokens", "full"),
        ),
        _build_select_config_option(
            option_id="elevated_level",
            name="Elevated actions",
            description=(
                "Controls how aggressively the session allows elevated execution behavior."
            ),
            current_value=_normalize_optional_string(merged.get("elevatedLevel")) or "off",
            values=("off", "on", "ask", "full"),
        ),
    ]
    return {"configOptions": config_options, "modes": modes}


def _format_updated_at(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    timestamp = datetime.fromtimestamp(float(value) / 1000, tz=UTC)
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _build_session_metadata(
    *,
    row: Mapping[str, Any] | None,
    session_key: str,
) -> dict[str, object]:
    record = _session_row(row)
    title = (
        _normalize_optional_string(record.get("derivedTitle"))
        or _normalize_optional_string(record.get("displayName"))
        or _normalize_optional_string(record.get("label"))
        or session_key
    )
    return {
        "title": title,
        "updatedAt": _format_updated_at(record.get("updatedAt")),
    }


def _build_session_usage_snapshot(row: Mapping[str, Any] | None) -> dict[str, int] | None:
    if row is None or row.get("totalTokensFresh") is not True:
        return None
    total_tokens = row.get("totalTokens")
    context_tokens = row.get("contextTokens")
    if (
        isinstance(total_tokens, bool)
        or isinstance(context_tokens, bool)
        or not isinstance(total_tokens, int | float)
        or not isinstance(context_tokens, int | float)
        or context_tokens <= 0
    ):
        return None
    size = max(0, int(context_tokens))
    used = max(0, min(int(total_tokens), size))
    return {"size": size, "used": used}


def _extract_replay_chunks(message: Mapping[str, Any]) -> list[dict[str, object]]:
    role = message.get("role") if isinstance(message.get("role"), str) else ""
    if role not in {"user", "assistant"}:
        return []
    content = message.get("content")
    if isinstance(content, str):
        if not content:
            return []
        return [
            {
                "sessionUpdate": (
                    "user_message_chunk" if role == "user" else "agent_message_chunk"
                ),
                "text": content,
            }
        ]
    if not isinstance(content, list):
        return []
    chunks: list[dict[str, object]] = []
    for block in content:
        if not isinstance(block, Mapping):
            continue
        block_type = block.get("type")
        if block_type == "text" and isinstance(block.get("text"), str) and block.get("text"):
            chunks.append(
                {
                    "sessionUpdate": (
                        "user_message_chunk" if role == "user" else "agent_message_chunk"
                    ),
                    "text": block["text"],
                }
            )
            continue
        thinking = block.get("thinking")
        if (
            role == "assistant"
            and block_type == "thinking"
            and isinstance(thinking, str)
            and thinking
        ):
            chunks.append({"sessionUpdate": "agent_thought_chunk", "text": thinking})
    return chunks


class AcpGatewayAgent:
    def __init__(
        self,
        connection: AcpConnection,
        gateway: AcpGatewayClient,
        *,
        session_store: InMemoryAcpSessionStore | None = None,
        **opts: object,
    ) -> None:
        self._connection = connection
        self._gateway = gateway
        self._session_store = session_store or default_acp_session_store
        self._opts = opts
        self._pending_prompts: dict[str, _PendingPrompt] = {}
        self._disconnect_reason: str | None = None
        rate_limit = opts.get("session_create_rate_limit") or opts.get("sessionCreateRateLimit")
        rate_limit_config = rate_limit if isinstance(rate_limit, Mapping) else None
        self._session_create_rate_limit_max = _read_positive_int(
            rate_limit_config,
            "maxRequests",
            _SESSION_CREATE_RATE_LIMIT_DEFAULT_MAX_REQUESTS,
        )
        self._session_create_rate_limit_window_ms = max(
            1_000,
            _read_positive_int(
                rate_limit_config,
                "windowMs",
                _SESSION_CREATE_RATE_LIMIT_DEFAULT_WINDOW_MS,
            ),
        )
        self._session_create_window_started_at = int(time.monotonic() * 1000)
        self._session_create_window_count = 0

    async def initialize(self, _params: Mapping[str, object]) -> dict[str, object]:
        return {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "agentCapabilities": {
                "loadSession": True,
                "promptCapabilities": {
                    "image": True,
                    "audio": False,
                    "embeddedContext": True,
                },
                "mcpCapabilities": {
                    "http": False,
                    "sse": False,
                },
                "sessionCapabilities": {"list": {}},
            },
            "agentInfo": dict(ACP_AGENT_INFO),
            "authMethods": [],
        }

    async def newSession(self, params: Mapping[str, object]) -> dict[str, object]:  # noqa: N802
        return await self.new_session(params)

    async def new_session(self, params: Mapping[str, object]) -> dict[str, object]:
        self._assert_supported_session_setup(params.get("mcpServers"))
        self._enforce_session_create_rate_limit("newSession")
        meta = parse_session_meta(params.get("_meta"))
        session_key = await resolve_session_key(
            meta=meta,
            fallback_key="acp:pending",
            gateway=self._gateway,
            opts=self._opts,
        )
        cwd = str(params.get("cwd") or "")
        session = self._session_store.create_session(session_key=session_key, cwd=cwd)
        session_id = str(session["sessionId"])
        if session_key == "acp:pending":
            session_key = f"acp:{session_id}"
            session["sessionKey"] = session_key
        snapshot = await self._get_session_snapshot(session_key)
        await self._send_session_snapshot_update(session_id, snapshot, include_controls=False)
        await self._send_available_commands(session_id)
        return {
            "sessionId": session_id,
            "configOptions": snapshot["configOptions"],
            "modes": snapshot["modes"],
        }

    async def loadSession(self, params: Mapping[str, object]) -> dict[str, object]:  # noqa: N802
        return await self.load_session(params)

    async def load_session(self, params: Mapping[str, object]) -> dict[str, object]:
        self._assert_supported_session_setup(params.get("mcpServers"))
        session_id = str(params.get("sessionId") or "")
        if not self._session_store.has_session(session_id):
            self._enforce_session_create_rate_limit("loadSession")
        meta = parse_session_meta(params.get("_meta"))
        session_key = await resolve_session_key(
            meta=meta,
            fallback_key=session_id,
            gateway=self._gateway,
            opts=self._opts,
        )
        cwd = str(params.get("cwd") or "")
        session = self._session_store.create_session(
            session_id=session_id,
            session_key=session_key,
            cwd=cwd,
        )
        snapshot = await self._get_session_snapshot(session_key)
        transcript = await self._get_session_transcript(session_key)
        await self._replay_session_transcript(str(session["sessionId"]), transcript)
        await self._send_session_snapshot_update(
            str(session["sessionId"]),
            snapshot,
            include_controls=False,
        )
        await self._send_available_commands(str(session["sessionId"]))
        return {
            "configOptions": snapshot["configOptions"],
            "modes": snapshot["modes"],
        }

    async def prompt(self, params: Mapping[str, object]) -> dict[str, object]:
        session_id = str(params.get("sessionId") or "")
        session = self._session_store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        if session.get("activeRunId") or session.get("abort"):
            self._session_store.cancel_active_run(session_id)

        run_id = str(uuid.uuid4())
        request_params = build_prompt_send_request(
            session=session,
            prompt_request=params,
            run_id=run_id,
            opts=self._opts,
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, object]] = loop.create_future()
        pending = _PendingPrompt(
            session_id=session_id,
            session_key=str(session.get("sessionKey") or ""),
            run_id=run_id,
            future=future,
        )
        self._pending_prompts[session_id] = pending
        self._session_store.set_active_run(session_id, run_id, lambda: None)
        try:
            await self._gateway.request("chat.send", request_params)
            pending.send_accepted = True
        except Exception as exc:
            has_provenance = (
                "systemInputProvenance" in request_params
                or "systemProvenanceReceipt" in request_params
            )
            if has_provenance and _is_admin_scope_provenance_rejection(exc):
                retry_params = {
                    key: value
                    for key, value in request_params.items()
                    if key not in {"systemInputProvenance", "systemProvenanceReceipt"}
                }
                try:
                    await self._gateway.request("chat.send", retry_params)
                    pending.send_accepted = True
                except Exception:
                    self._pending_prompts.pop(session_id, None)
                    self._session_store.clear_active_run(session_id)
                    raise
                return await future
            self._pending_prompts.pop(session_id, None)
            self._session_store.clear_active_run(session_id)
            raise
        return await future

    def handleGatewayDisconnect(self, reason: str) -> None:  # noqa: N802
        self.handle_gateway_disconnect(reason)

    def handle_gateway_disconnect(self, reason: str) -> None:
        self._disconnect_reason = reason

    async def handleGatewayReconnect(self) -> None:  # noqa: N802
        await self.handle_gateway_reconnect()

    async def handle_gateway_reconnect(self) -> None:
        self._disconnect_reason = None
        for pending in list(self._pending_prompts.values()):
            if not pending.send_accepted:
                continue
            try:
                result = await self._gateway.request(
                    "agent.wait",
                    {"runId": pending.run_id, "timeoutMs": 0},
                )
            except Exception:
                continue
            if result.get("status") == "ok":
                await self._finish_prompt(pending, "end_turn")

    async def cancel(self, params: Mapping[str, object]) -> None:
        session_id = str(params.get("sessionId") or "")
        session = self._session_store.get_session(session_id)
        if session is None:
            return
        active_run_id = session.get("activeRunId")
        pending = self._pending_prompts.get(session_id)
        if isinstance(active_run_id, str):
            scoped_run_id = active_run_id
        elif pending is not None:
            scoped_run_id = pending.run_id
        else:
            scoped_run_id = None
        self._session_store.cancel_active_run(session_id)
        if scoped_run_id is not None:
            try:
                await self._gateway.request(
                    "chat.abort",
                    {"sessionKey": str(session.get("sessionKey") or ""), "runId": scoped_run_id},
                )
            except Exception:
                pass
        if pending is not None and not pending.future.done():
            self._pending_prompts.pop(session_id, None)
            pending.future.set_result({"stopReason": "cancelled"})

    async def setSessionMode(self, params: Mapping[str, object]) -> dict[str, object]:  # noqa: N802
        return await self.set_session_mode(params)

    async def set_session_mode(self, params: Mapping[str, object]) -> dict[str, object]:
        session_id = str(params.get("sessionId") or "")
        session = self._session_store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        mode_id = params.get("modeId")
        if not isinstance(mode_id, str) or not mode_id:
            return {}
        session_key = str(session.get("sessionKey") or "")
        await self._gateway.request(
            "sessions.patch",
            {"key": session_key, "thinkingLevel": mode_id},
        )
        snapshot = await self._get_session_snapshot(
            session_key,
            overrides={"thinkingLevel": mode_id},
        )
        await self._send_session_snapshot_update(session_id, snapshot, include_controls=True)
        return {}

    async def setSessionConfigOption(  # noqa: N802
        self,
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self.set_session_config_option(params)

    async def set_session_config_option(
        self,
        params: Mapping[str, object],
    ) -> dict[str, object]:
        session_id = str(params.get("sessionId") or "")
        session = self._session_store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        config_id = str(params.get("configId") or "")
        value = params.get("value")
        patch_info = self._resolve_session_config_patch(config_id, value)
        session_key = str(session.get("sessionKey") or "")
        await self._gateway.request("sessions.patch", {"key": session_key, **patch_info["patch"]})
        snapshot = await self._get_session_snapshot(
            session_key,
            overrides=patch_info["overrides"],
        )
        await self._send_session_snapshot_update(session_id, snapshot, include_controls=True)
        return {"configOptions": snapshot["configOptions"]}

    async def handleGatewayEvent(self, event: Mapping[str, object]) -> None:  # noqa: N802
        await self.handle_gateway_event(event)

    async def handle_gateway_event(self, event: Mapping[str, object]) -> None:
        if event.get("event") == "agent":
            await self._handle_agent_event(event)
            return
        if event.get("event") != "chat":
            return
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            return
        session_key = payload.get("sessionKey")
        state = payload.get("state")
        run_id = payload.get("runId")
        if not isinstance(session_key, str) or not isinstance(state, str):
            return
        pending = self._find_pending_by_session_key(
            session_key,
            run_id if isinstance(run_id, str) else None,
        )
        if pending is None:
            return
        message = payload.get("message")
        if isinstance(message, Mapping) and state in {"delta", "final"}:
            await self._handle_delta_event(pending, message)
            if state == "delta":
                return
        if state == "final":
            raw_stop_reason = payload.get("stopReason")
            stop_reason = "max_tokens" if raw_stop_reason == "max_tokens" else "end_turn"
            await self._finish_prompt(pending, stop_reason)
            return
        if state == "aborted":
            await self._finish_prompt(pending, "cancelled")
            return
        if state == "error":
            error_kind = payload.get("errorKind")
            stop_reason = "refusal" if error_kind == "refusal" else "end_turn"
            await self._finish_prompt(pending, stop_reason)

    async def _handle_agent_event(self, event: Mapping[str, object]) -> None:
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            return
        if payload.get("stream") != "tool":
            return
        session_key = payload.get("sessionKey")
        run_id = payload.get("runId")
        data = payload.get("data")
        if not isinstance(session_key, str) or not isinstance(data, Mapping):
            return
        pending = self._find_pending_by_session_key(
            session_key,
            run_id if isinstance(run_id, str) else None,
        )
        if pending is None:
            return
        phase = data.get("phase")
        tool_call_id = data.get("toolCallId")
        if not isinstance(phase, str) or not isinstance(tool_call_id, str) or not tool_call_id:
            return
        if phase == "start":
            if tool_call_id in pending.tool_calls:
                return
            name = data.get("name") if isinstance(data.get("name"), str) else None
            args = data.get("args") if isinstance(data.get("args"), Mapping) else None
            raw_input = dict(args) if args is not None else None
            locations = extract_tool_call_locations(raw_input)
            pending.tool_calls[tool_call_id] = {
                "locations": locations,
            }
            await self._session_update(
                {
                    "sessionId": pending.session_id,
                    "update": {
                        "sessionUpdate": "tool_call",
                        "toolCallId": tool_call_id,
                        "title": format_tool_title(name, raw_input),
                        "status": "in_progress",
                        "rawInput": raw_input,
                        "kind": infer_tool_kind(name),
                        "locations": locations,
                    },
                }
            )
            return
        if phase == "update":
            tool_state = pending.tool_calls.get(tool_call_id, {})
            partial_result = data.get("partialResult")
            await self._session_update(
                {
                    "sessionId": pending.session_id,
                    "update": {
                        "sessionUpdate": "tool_call_update",
                        "toolCallId": tool_call_id,
                        "status": "in_progress",
                        "rawOutput": partial_result,
                        "content": extract_tool_call_content(partial_result),
                        "locations": extract_tool_call_locations(
                            tool_state.get("locations"),
                            partial_result,
                        ),
                    },
                }
            )
            return
        if phase == "result":
            tool_state = pending.tool_calls.pop(tool_call_id, {})
            result = data.get("result")
            await self._session_update(
                {
                    "sessionId": pending.session_id,
                    "update": {
                        "sessionUpdate": "tool_call_update",
                        "toolCallId": tool_call_id,
                        "status": "failed" if data.get("isError") else "completed",
                        "rawOutput": result,
                        "content": extract_tool_call_content(result),
                        "locations": extract_tool_call_locations(
                            tool_state.get("locations"),
                            result,
                        ),
                    },
                }
            )

    def _assert_supported_session_setup(self, mcp_servers: object) -> None:
        if not isinstance(mcp_servers, Sequence) or isinstance(mcp_servers, str | bytes):
            return
        if len(mcp_servers) == 0:
            return
        raise ValueError(
            "ACP bridge mode does not support per-session MCP servers. Configure MCP "
            "on the OpenClaw gateway or agent instead."
        )

    def _enforce_session_create_rate_limit(self, method: str) -> None:
        now_ms = int(time.monotonic() * 1000)
        elapsed_ms = now_ms - self._session_create_window_started_at
        if elapsed_ms >= self._session_create_rate_limit_window_ms:
            self._session_create_window_started_at = now_ms
            self._session_create_window_count = 0
            elapsed_ms = 0
        if self._session_create_window_count >= self._session_create_rate_limit_max:
            retry_after_ms = max(1, self._session_create_rate_limit_window_ms - elapsed_ms)
            retry_after_seconds = (retry_after_ms + 999) // 1000
            raise RuntimeError(
                f"ACP session creation rate limit exceeded for {method}; "
                f"retry after {retry_after_seconds}s."
            )
        self._session_create_window_count += 1

    def _resolve_session_config_patch(
        self,
        config_id: str,
        value: object,
    ) -> dict[str, dict[str, object]]:
        if not isinstance(value, str):
            raise ValueError(
                "ACP bridge does not support non-string session config option "
                f'values for "{config_id}".'
            )
        match config_id:
            case "thought_level":
                return {
                    "patch": {"thinkingLevel": value},
                    "overrides": {"thinkingLevel": value},
                }
            case "fast_mode":
                enabled = value == "on"
                return {"patch": {"fastMode": enabled}, "overrides": {"fastMode": enabled}}
            case "verbose_level":
                return {"patch": {"verboseLevel": value}, "overrides": {"verboseLevel": value}}
            case "trace_level":
                return {"patch": {"traceLevel": value}, "overrides": {"traceLevel": value}}
            case "reasoning_level":
                return {
                    "patch": {"reasoningLevel": value},
                    "overrides": {"reasoningLevel": value},
                }
            case "response_usage":
                return {"patch": {"responseUsage": value}, "overrides": {"responseUsage": value}}
            case "elevated_level":
                return {"patch": {"elevatedLevel": value}, "overrides": {"elevatedLevel": value}}
            case _:
                raise ValueError(
                    f'ACP bridge mode does not support session config option "{config_id}".'
                )

    def _find_pending_by_session_key(
        self,
        session_key: str,
        run_id: str | None = None,
    ) -> _PendingPrompt | None:
        for pending in self._pending_prompts.values():
            if pending.session_key != session_key:
                continue
            if run_id is not None and pending.run_id != run_id:
                continue
            return pending
        return None

    async def _handle_delta_event(
        self,
        pending: _PendingPrompt,
        message: Mapping[str, object],
    ) -> None:
        content = message.get("content")
        if not isinstance(content, list):
            return
        thought_parts: list[str] = []
        text_parts: list[str] = []
        for block in content:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "thinking" and isinstance(block.get("thinking"), str):
                thought_parts.append(str(block["thinking"]))
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text_parts.append(str(block["text"]))
        full_thought = "\n".join(thought_parts).rstrip()
        if full_thought and len(full_thought) > pending.sent_thought_length:
            new_thought = full_thought[pending.sent_thought_length :]
            pending.sent_thought_length = len(full_thought)
            await self._session_update(
                {
                    "sessionId": pending.session_id,
                    "update": {
                        "sessionUpdate": "agent_thought_chunk",
                        "content": {"type": "text", "text": new_thought},
                    },
                }
            )
        full_text = "\n".join(text_parts).rstrip()
        if full_text and len(full_text) > pending.sent_text_length:
            new_text = full_text[pending.sent_text_length :]
            pending.sent_text_length = len(full_text)
            await self._session_update(
                {
                    "sessionId": pending.session_id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": new_text},
                    },
                }
            )

    async def _finish_prompt(self, pending: _PendingPrompt, stop_reason: str) -> None:
        self._pending_prompts.pop(pending.session_id, None)
        self._session_store.clear_active_run(pending.session_id)
        try:
            snapshot = await self._get_session_snapshot(pending.session_key)
            await self._send_session_snapshot_update(
                pending.session_id,
                snapshot,
                include_controls=False,
            )
        except Exception:
            pass
        if not pending.future.done():
            pending.future.set_result({"stopReason": stop_reason})

    async def _get_session_snapshot(
        self,
        session_key: str,
        overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        try:
            row = await self._get_gateway_session_row(session_key)
        except Exception:  # noqa: BLE001 - bridge snapshot fallback mirrors OpenClaw.
            row = None
        snapshot = _build_session_presentation(row, overrides)
        snapshot["metadata"] = _build_session_metadata(row=row, session_key=session_key)
        usage = _build_session_usage_snapshot(row)
        if usage is not None:
            snapshot["usage"] = usage
        return snapshot

    async def _get_gateway_session_row(self, session_key: str) -> Mapping[str, Any] | None:
        result = await self._gateway.request(
            "sessions.list",
            {"limit": 200, "search": session_key, "includeDerivedTitles": True},
        )
        sessions = result.get("sessions")
        if not isinstance(sessions, list):
            return None
        for entry in sessions:
            if isinstance(entry, Mapping) and entry.get("key") == session_key:
                return entry
        return None

    async def _get_session_transcript(
        self,
        session_key: str,
    ) -> list[Mapping[str, Any]]:
        try:
            result = await self._gateway.request(
                "sessions.get",
                {"key": session_key, "limit": ACP_LOAD_SESSION_REPLAY_LIMIT},
            )
        except Exception:  # noqa: BLE001 - loadSession falls back to an empty transcript.
            return []
        messages = result.get("messages")
        if not isinstance(messages, list):
            return []
        return [message for message in messages if isinstance(message, Mapping)]

    async def _replay_session_transcript(
        self,
        session_id: str,
        transcript: Sequence[Mapping[str, Any]],
    ) -> None:
        for message in transcript:
            for chunk in _extract_replay_chunks(message):
                await self._session_update(
                    {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": chunk["sessionUpdate"],
                            "content": {"type": "text", "text": chunk["text"]},
                        },
                    }
                )

    async def _send_session_snapshot_update(
        self,
        session_id: str,
        snapshot: Mapping[str, object],
        *,
        include_controls: bool,
    ) -> None:
        if include_controls:
            modes = snapshot.get("modes")
            if isinstance(modes, Mapping):
                await self._session_update(
                    {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "current_mode_update",
                            "currentModeId": modes.get("currentModeId"),
                        },
                    }
                )
            await self._session_update(
                {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "config_option_update",
                        "configOptions": snapshot.get("configOptions"),
                    },
                }
            )
        metadata = snapshot.get("metadata")
        if isinstance(metadata, Mapping):
            await self._session_update(
                {
                    "sessionId": session_id,
                    "update": {"sessionUpdate": "session_info_update", **dict(metadata)},
                }
            )
        usage = snapshot.get("usage")
        if isinstance(usage, Mapping):
            await self._session_update(
                {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "usage_update",
                        "used": usage.get("used"),
                        "size": usage.get("size"),
                        "_meta": {
                            "source": "gateway-session-store",
                            "approximate": True,
                        },
                    },
                }
            )

    async def _send_available_commands(self, session_id: str) -> None:
        await self._session_update(
            {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "available_commands_update",
                    "availableCommands": get_available_commands(),
                },
            }
        )

    async def _session_update(self, payload: dict[str, object]) -> None:
        await self._connection.session_update(payload)
