from __future__ import annotations

import copy
import math
import re
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

_NATIVE_HOOK_RELAY_EVENTS = {
    "pre_tool_use",
    "post_tool_use",
    "permission_request",
    "before_agent_finalize",
}
_NATIVE_HOOK_RELAY_PROVIDERS = {"codex"}
_DEFAULT_RELAY_TTL_MS = 30 * 60 * 1000
_MAX_JSON_DEPTH = 64
_MAX_JSON_NODES = 20_000
_MAX_JSON_STRING_LENGTH = 1_000_000
_MAX_JSON_TOTAL_STRING_LENGTH = 4_000_000
_RELAY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")


@dataclass(frozen=True)
class GatewayNativeHookRelayRegistration:
    relay_id: str
    provider: str
    session_id: str
    run_id: str
    allowed_events: tuple[str, ...]
    expires_at_ms: int
    agent_id: str | None = None
    session_key: str | None = None


class GatewayNativeHookRelayService:
    def __init__(self, *, now_ms: Callable[[], int] | None = None) -> None:
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))
        self._registrations: dict[str, GatewayNativeHookRelayRegistration] = {}
        self._invocations: list[dict[str, object]] = []

    @property
    def invocations(self) -> list[dict[str, object]]:
        return [copy.deepcopy(invocation) for invocation in self._invocations]

    def register(
        self,
        *,
        provider: str,
        relay_id: str,
        session_id: str,
        run_id: str,
        allowed_events: Iterable[str] | None = None,
        ttl_ms: int | None = None,
        agent_id: str | None = None,
        session_key: str | None = None,
    ) -> GatewayNativeHookRelayRegistration:
        normalized_provider = _read_native_hook_provider(provider)
        normalized_relay_id = _read_native_hook_relay_id(relay_id)
        normalized_events = _normalize_allowed_events(allowed_events)
        registration = GatewayNativeHookRelayRegistration(
            relay_id=normalized_relay_id,
            provider=normalized_provider,
            session_id=_read_non_empty_string(session_id, "sessionId"),
            run_id=_read_non_empty_string(run_id, "runId"),
            allowed_events=normalized_events,
            expires_at_ms=self._now_ms() + _normalize_positive_integer(
                ttl_ms,
                _DEFAULT_RELAY_TTL_MS,
            ),
            agent_id=_optional_non_empty_string(agent_id),
            session_key=_optional_non_empty_string(session_key),
        )
        self._registrations[normalized_relay_id] = registration
        self._invocations = [
            invocation
            for invocation in self._invocations
            if invocation.get("relayId") != normalized_relay_id
        ]
        return registration

    async def invoke(
        self,
        *,
        provider: object,
        relay_id: object,
        event: object,
        raw_payload: object,
    ) -> dict[str, object]:
        normalized_provider = _read_native_hook_provider(provider)
        normalized_relay_id = _read_non_empty_string(relay_id, "relayId")
        normalized_event = _read_native_hook_event(event)
        registration = self._registrations.get(normalized_relay_id)
        if registration is None:
            self._prune_expired()
            raise ValueError("native hook relay not found")
        if self._now_ms() > registration.expires_at_ms:
            self._registrations.pop(normalized_relay_id, None)
            self._invocations = [
                invocation
                for invocation in self._invocations
                if invocation.get("relayId") != normalized_relay_id
            ]
            raise ValueError("native hook relay expired")
        if registration.provider != normalized_provider:
            raise ValueError("native hook relay provider mismatch")
        if normalized_event not in registration.allowed_events:
            raise ValueError("native hook relay event not allowed")
        if not _is_json_value(raw_payload):
            raise ValueError("native hook relay payload must be JSON-compatible")

        normalized_payload = copy.deepcopy(raw_payload)
        invocation = _normalize_native_hook_invocation(
            registration,
            event=normalized_event,
            raw_payload=normalized_payload,
            received_at=_format_ms_as_iso(self._now_ms()),
        )
        self._invocations.append(invocation)
        return {"stdout": "", "stderr": "", "exitCode": 0}

    def _prune_expired(self) -> None:
        timestamp_ms = self._now_ms()
        expired = {
            relay_id
            for relay_id, registration in self._registrations.items()
            if timestamp_ms > registration.expires_at_ms
        }
        for relay_id in expired:
            self._registrations.pop(relay_id, None)


def _normalize_native_hook_invocation(
    registration: GatewayNativeHookRelayRegistration,
    *,
    event: str,
    raw_payload: object,
    received_at: str,
) -> dict[str, object]:
    payload = raw_payload if isinstance(raw_payload, Mapping) else {}
    invocation: dict[str, object] = {
        "provider": registration.provider,
        "relayId": registration.relay_id,
        "event": event,
    }
    for source_key, target_key in (
        ("hook_event_name", "nativeEventName"),
        ("cwd", "cwd"),
        ("model", "model"),
        ("turn_id", "turnId"),
        ("transcript_path", "transcriptPath"),
        ("permission_mode", "permissionMode"),
        ("last_assistant_message", "lastAssistantMessage"),
        ("tool_name", "toolName"),
        ("tool_use_id", "toolUseId"),
    ):
        value = payload.get(source_key)
        if isinstance(value, str) and value:
            invocation[target_key] = value
    stop_hook_active = payload.get("stop_hook_active")
    if isinstance(stop_hook_active, bool):
        invocation["stopHookActive"] = stop_hook_active
    if registration.agent_id is not None:
        invocation["agentId"] = registration.agent_id
    invocation["sessionId"] = registration.session_id
    if registration.session_key is not None:
        invocation["sessionKey"] = registration.session_key
    invocation["runId"] = registration.run_id
    invocation["rawPayload"] = raw_payload
    invocation["receivedAt"] = received_at
    return invocation


def _read_native_hook_provider(value: object) -> str:
    if value in _NATIVE_HOOK_RELAY_PROVIDERS:
        return str(value)
    raise ValueError("unsupported native hook relay provider")


def _read_native_hook_event(value: object) -> str:
    if value in _NATIVE_HOOK_RELAY_EVENTS:
        return str(value)
    raise ValueError("unsupported native hook relay event")


def _read_native_hook_relay_id(value: object) -> str:
    relay_id = _read_non_empty_string(value, "relayId")
    if not _RELAY_ID_PATTERN.fullmatch(relay_id):
        raise ValueError("native hook relay id must be non-empty, compact, and URL-safe")
    return relay_id


def _read_non_empty_string(value: object, name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"native hook relay {name} is required")


def _optional_non_empty_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_allowed_events(value: Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return tuple(sorted(_NATIVE_HOOK_RELAY_EVENTS))
    events = tuple(_read_native_hook_event(event) for event in value)
    return events or tuple(sorted(_NATIVE_HOOK_RELAY_EVENTS))


def _normalize_positive_integer(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float) and math.isfinite(float(value)) and value > 0:
        return math.floor(float(value))
    return default


def _is_json_value(value: object) -> bool:
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    total_string_length = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_JSON_NODES or depth > _MAX_JSON_DEPTH:
            return False
        if current is None or isinstance(current, bool):
            continue
        if isinstance(current, str):
            if len(current) > _MAX_JSON_STRING_LENGTH:
                return False
            total_string_length += len(current)
            if total_string_length > _MAX_JSON_TOTAL_STRING_LENGTH:
                return False
            continue
        if isinstance(current, int | float):
            if isinstance(current, bool) or not math.isfinite(float(current)):
                return False
            continue
        if isinstance(current, list | tuple):
            stack.extend((item, depth + 1) for item in current)
            continue
        if isinstance(current, Mapping):
            for key, item in current.items():
                if not isinstance(key, str):
                    return False
                stack.append((item, depth + 1))
            continue
        return False
    return True


def _format_ms_as_iso(value: int) -> str:
    return (
        datetime.fromtimestamp(value / 1000, tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
