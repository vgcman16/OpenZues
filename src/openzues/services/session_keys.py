from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from openzues.schemas import ConversationTargetView, LaunchRouteBindingMode

SessionKeyShape = Literal["missing", "agent", "legacy_or_alias", "malformed_agent"]
DEFAULT_AGENT_ID = "main"
DEFAULT_MAIN_KEY = "main"
DEFAULT_ACCOUNT_ID = "default"

_VALID_AGENT_SESSION_KEY_RE = re.compile(
    r"^agent:(?P<agent_id>[a-z0-9][a-z0-9_-]{0,63}):(?P<rest>.+)$",
    re.IGNORECASE,
)
_VALID_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
_CRON_RUN_SESSION_KEY_RE = re.compile(r"^cron:[^:]+:run:[^:]+$", re.IGNORECASE)
_INVALID_AGENT_ID_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
_LEADING_DASH_RE = re.compile(r"^-+")
_TRAILING_DASH_RE = re.compile(r"-+$")
_THREAD_SESSION_MARKER = ":thread:"
_BLOCKED_OBJECT_KEYS = frozenset({"__proto__", "constructor", "prototype"})
_RUN_LOOKUP_CACHE_LIMIT = 256
_RUN_LOOKUP_MISS_TTL_MS = 1_000


@dataclass(frozen=True, slots=True)
class ParsedThreadSessionSuffix:
    base_session_key: str | None
    thread_id: str | None


@dataclass(frozen=True, slots=True)
class ParsedAgentSessionKey:
    agent_id: str
    rest: str


@dataclass(frozen=True, slots=True)
class ResolvedThreadSessionKeys:
    session_key: str
    parent_session_key: str | None


@dataclass(frozen=True, slots=True)
class RunLookupCacheEntry:
    session_key: str | None
    expires_at_ms: float | None


_resolved_session_key_by_run_id: dict[str, RunLookupCacheEntry] = {}


def build_launch_session_key(
    *,
    mode: LaunchRouteBindingMode,
    preferred_instance_id: int | None,
    task_id: int | None,
    project_id: int | None,
    operator_id: int | None,
    conversation_target: ConversationTargetView | None = None,
) -> str:
    parts = ["launch", f"mode:{mode}"]
    if task_id is not None:
        parts.append(f"task:{task_id}")
    if project_id is not None:
        parts.append(f"project:{project_id}")
    if operator_id is not None:
        parts.append(f"operator:{operator_id}")
    if mode in {"task_lane", "saved_lane"} and preferred_instance_id is not None:
        parts.append(f"lane:{preferred_instance_id}")
    if conversation_target is not None:
        channel = _normalize_token(conversation_target.channel)
        if channel:
            parts.append(f"channel:{channel}")
            account_id = normalize_optional_account_id(conversation_target.account_id)
            if account_id:
                parts.append(f"account:{account_id}")
            peer_id = _normalize_token(conversation_target.peer_id)
            peer_kind = _normalize_token(str(conversation_target.peer_kind or ""))
            if peer_kind and peer_id:
                parts.append(f"peer:{peer_kind}:{peer_id}")
    return ":".join(parts)


def normalize_main_key(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or DEFAULT_MAIN_KEY


def _normalize_token(value: str | None) -> str:
    return str(value or "").strip().lower()


def _canonicalize_account_id(value: str) -> str:
    normalized = value.lower()
    if _VALID_AGENT_ID_RE.fullmatch(value):
        return normalized
    sanitized = _INVALID_AGENT_ID_CHARS_RE.sub("-", normalized)
    sanitized = _LEADING_DASH_RE.sub("", sanitized)
    sanitized = _TRAILING_DASH_RE.sub("", sanitized)
    return sanitized[:64]


def _normalize_optional_account_id(value: str | None) -> str | None:
    trimmed = str(value or "").strip()
    if not trimmed:
        return None
    normalized = _canonicalize_account_id(trimmed)
    if not normalized:
        return None
    if normalized in _BLOCKED_OBJECT_KEYS:
        return None
    return normalized


def normalize_account_id(value: str | None) -> str:
    return _normalize_optional_account_id(value) or DEFAULT_ACCOUNT_ID


def normalize_optional_account_id(value: str | None) -> str | None:
    return _normalize_optional_account_id(value)


def normalize_agent_id(value: str | None) -> str:
    trimmed = str(value or "").strip()
    if not trimmed:
        return DEFAULT_AGENT_ID
    normalized = trimmed.lower()
    if _VALID_AGENT_ID_RE.fullmatch(trimmed):
        return normalized
    sanitized = _INVALID_AGENT_ID_CHARS_RE.sub("-", normalized)
    sanitized = _LEADING_DASH_RE.sub("", sanitized)
    sanitized = _TRAILING_DASH_RE.sub("", sanitized)
    sanitized = sanitized[:64]
    return sanitized or DEFAULT_AGENT_ID


def is_valid_agent_id(value: str | None) -> bool:
    trimmed = str(value or "").strip()
    return bool(trimmed) and _VALID_AGENT_ID_RE.fullmatch(trimmed) is not None


def sanitize_agent_id(value: str | None) -> str:
    return normalize_agent_id(value)


def parse_agent_session_key(session_key: str | None) -> ParsedAgentSessionKey | None:
    raw = str(session_key or "").strip().lower()
    if not raw:
        return None
    match = _VALID_AGENT_SESSION_KEY_RE.fullmatch(raw)
    if match is None:
        return None
    return ParsedAgentSessionKey(
        agent_id=normalize_agent_id(match.group("agent_id")),
        rest=match.group("rest"),
    )


def _parse_agent_session_key_like_openclaw(
    session_key: str | None,
) -> ParsedAgentSessionKey | None:
    raw = str(session_key or "").strip().lower()
    if not raw:
        return None
    parts = [part for part in raw.split(":") if part]
    if len(parts) < 3 or parts[0] != "agent":
        return None
    agent_id = str(parts[1]).strip()
    rest = ":".join(parts[2:]).strip()
    if not agent_id or not rest:
        return None
    return ParsedAgentSessionKey(agent_id=agent_id, rest=rest)


def is_cron_run_session_key(session_key: str | None) -> bool:
    parsed = _parse_agent_session_key_like_openclaw(session_key)
    if parsed is None:
        return False
    return _CRON_RUN_SESSION_KEY_RE.fullmatch(parsed.rest) is not None


def is_cron_session_key(session_key: str | None) -> bool:
    parsed = _parse_agent_session_key_like_openclaw(session_key)
    if parsed is None:
        return False
    return parsed.rest.startswith("cron:")


def is_subagent_session_key(session_key: str | None) -> bool:
    raw = str(session_key or "").strip()
    if not raw:
        return False
    if raw.lower().startswith("subagent:"):
        return True
    parsed = _parse_agent_session_key_like_openclaw(raw)
    return parsed is not None and parsed.rest.startswith("subagent:")


def get_subagent_depth(session_key: str | None) -> int:
    raw = str(session_key or "").strip().lower()
    if not raw:
        return 0
    return raw.count(":subagent:")


def is_acp_session_key(session_key: str | None) -> bool:
    raw = str(session_key or "").strip()
    if not raw:
        return False
    if raw.lower().startswith("acp:"):
        return True
    parsed = _parse_agent_session_key_like_openclaw(raw)
    return parsed is not None and parsed.rest.startswith("acp:")


def scoped_heartbeat_wake_options(
    session_key: str,
    wake_options: dict[str, Any],
) -> dict[str, Any]:
    if _parse_agent_session_key_like_openclaw(session_key) is None:
        return wake_options
    return {**wake_options, "session_key": session_key}


def build_agent_main_session_key(*, agent_id: str, main_key: str | None = None) -> str:
    return f"agent:{normalize_agent_id(agent_id)}:{normalize_main_key(main_key)}"


def _resolve_linked_peer_id(
    *,
    identity_links: dict[str, list[str]] | None,
    channel: str,
    peer_id: str,
) -> str | None:
    if not identity_links:
        return None
    raw_peer_id = str(peer_id or "").strip()
    if not raw_peer_id:
        return None
    candidates = set[str]()
    normalized_peer_id = _normalize_token(raw_peer_id)
    if normalized_peer_id:
        candidates.add(normalized_peer_id)
    normalized_channel = _normalize_token(channel)
    if normalized_channel:
        scoped_candidate = _normalize_token(f"{normalized_channel}:{raw_peer_id}")
        if scoped_candidate:
            candidates.add(scoped_candidate)
    if not candidates:
        return None
    for canonical_name, ids in identity_links.items():
        canonical = str(canonical_name or "").strip()
        if not canonical or not isinstance(ids, list):
            continue
        for linked_id in ids:
            if _normalize_token(linked_id) in candidates:
                return canonical
    return None


def build_agent_peer_session_key(
    *,
    agent_id: str,
    channel: str,
    account_id: str | None = None,
    peer_kind: Literal["direct", "group", "channel"] = "direct",
    peer_id: str | None = None,
    identity_links: dict[str, list[str]] | None = None,
    dm_scope: Literal["main", "per-peer", "per-channel-peer", "per-account-channel-peer"] = "main",
    main_key: str | None = None,
) -> str:
    if peer_kind == "direct":
        resolved_peer_id = str(peer_id or "").strip()
        linked_peer_id = (
            None
            if dm_scope == "main"
            else _resolve_linked_peer_id(
                identity_links=identity_links,
                channel=channel,
                peer_id=resolved_peer_id,
            )
        )
        if linked_peer_id:
            resolved_peer_id = linked_peer_id
        normalized_peer_id = _normalize_token(resolved_peer_id)
        normalized_agent_id = normalize_agent_id(agent_id)
        if dm_scope == "per-account-channel-peer" and normalized_peer_id:
            return (
                f"agent:{normalized_agent_id}:{_normalize_token(channel) or 'unknown'}:"
                f"{normalize_account_id(account_id)}:direct:{normalized_peer_id}"
            )
        if dm_scope == "per-channel-peer" and normalized_peer_id:
            return (
                f"agent:{normalized_agent_id}:{_normalize_token(channel) or 'unknown'}:"
                f"direct:{normalized_peer_id}"
            )
        if dm_scope == "per-peer" and normalized_peer_id:
            return f"agent:{normalized_agent_id}:direct:{normalized_peer_id}"
        return build_agent_main_session_key(agent_id=agent_id, main_key=main_key)
    return (
        f"agent:{normalize_agent_id(agent_id)}:{_normalize_token(channel) or 'unknown'}:"
        f"{peer_kind}:{_normalize_token(peer_id) or 'unknown'}"
    )


def build_agent_session_key(
    *,
    agent_id: str,
    channel: str,
    account_id: str | None = None,
    peer_kind: Literal["direct", "group", "channel"] | None = None,
    peer_id: str | None = None,
    dm_scope: Literal["main", "per-peer", "per-channel-peer", "per-account-channel-peer"] = "main",
    identity_links: dict[str, list[str]] | None = None,
) -> str:
    normalized_peer_kind = peer_kind or "direct"
    normalized_peer_id = _normalize_token(peer_id) or "unknown" if peer_id is not None else None
    return build_agent_peer_session_key(
        agent_id=agent_id,
        channel=_normalize_token(channel) or "unknown",
        account_id=account_id,
        peer_kind=normalized_peer_kind,
        peer_id=normalized_peer_id,
        dm_scope=dm_scope,
        identity_links=identity_links,
        main_key=DEFAULT_MAIN_KEY,
    )


def build_group_history_key(
    *,
    channel: str,
    account_id: str | None,
    peer_kind: Literal["group", "channel"],
    peer_id: str,
) -> str:
    return (
        f"{_normalize_token(channel) or 'unknown'}:{normalize_account_id(account_id)}:"
        f"{peer_kind}:{_normalize_token(peer_id) or 'unknown'}"
    )


def to_agent_request_session_key(store_key: str | None) -> str | None:
    raw = str(store_key or "").strip()
    if not raw:
        return None
    parsed = _parse_agent_session_key_like_openclaw(raw)
    return parsed.rest if parsed is not None else raw


def to_agent_store_session_key(
    *,
    agent_id: str,
    request_key: str | None,
    main_key: str | None = None,
) -> str:
    raw = str(request_key or "").strip()
    lowered = raw.lower()
    if not raw or lowered == DEFAULT_MAIN_KEY:
        return build_agent_main_session_key(agent_id=agent_id, main_key=main_key)
    parsed = parse_agent_session_key(raw)
    if parsed is not None:
        return f"agent:{parsed.agent_id}:{parsed.rest}"
    if lowered.startswith("agent:"):
        return lowered
    return f"agent:{normalize_agent_id(agent_id)}:{lowered}"


def resolve_agent_id_from_session_key(session_key: str | None) -> str:
    parsed = _parse_agent_session_key_like_openclaw(session_key)
    if parsed is None:
        return DEFAULT_AGENT_ID
    return normalize_agent_id(parsed.agent_id)


def canonicalize_session_key(session_key: str | None) -> str | None:
    raw = str(session_key or "").strip()
    if not raw:
        return None
    if raw.lower() == DEFAULT_MAIN_KEY:
        return build_agent_main_session_key(agent_id=DEFAULT_AGENT_ID)
    parsed = parse_agent_session_key(raw)
    if parsed is not None:
        return f"agent:{parsed.agent_id}:{parsed.rest}"
    return raw.lower()


def session_key_lookup_aliases(session_key: str | None) -> tuple[str, ...]:
    canonical = canonicalize_session_key(session_key)
    if canonical is None:
        return ()
    if canonical == f"agent:{DEFAULT_AGENT_ID}:{DEFAULT_MAIN_KEY}":
        return (canonical, DEFAULT_MAIN_KEY)
    return (canonical,)


def parse_thread_session_suffix(session_key: str | None) -> ParsedThreadSessionSuffix:
    raw = str(session_key or "").strip()
    if not raw:
        return ParsedThreadSessionSuffix(base_session_key=None, thread_id=None)
    marker_index = raw.lower().rfind(_THREAD_SESSION_MARKER)
    base_session_key = raw if marker_index == -1 else raw[:marker_index]
    thread_id_raw = (
        None if marker_index == -1 else raw[marker_index + len(_THREAD_SESSION_MARKER) :]
    )
    thread_id = str(thread_id_raw or "").strip() or None
    return ParsedThreadSessionSuffix(
        base_session_key=base_session_key,
        thread_id=thread_id,
    )


def resolve_thread_parent_session_key(session_key: str | None) -> str | None:
    parsed = parse_thread_session_suffix(session_key)
    if not parsed.thread_id:
        return None
    return str(parsed.base_session_key or "").strip() or None


def resolve_thread_session_keys(
    *,
    base_session_key: str,
    thread_id: str | None,
    parent_session_key: str | None = None,
    use_suffix: bool = True,
    normalize_thread_id: Callable[[str], str] | None = None,
) -> ResolvedThreadSessionKeys:
    raw_thread_id = str(thread_id or "").strip()
    if not raw_thread_id:
        return ResolvedThreadSessionKeys(
            session_key=base_session_key,
            parent_session_key=None,
        )
    normalized_thread_id = (
        normalize_thread_id(raw_thread_id)
        if normalize_thread_id is not None
        else raw_thread_id.lower()
    )
    session_key = (
        f"{base_session_key}{_THREAD_SESSION_MARKER}{normalized_thread_id}"
        if use_suffix
        else base_session_key
    )
    return ResolvedThreadSessionKeys(
        session_key=session_key,
        parent_session_key=parent_session_key,
    )


def classify_session_key_shape(session_key: str | None) -> SessionKeyShape:
    raw = str(session_key or "").strip()
    if not raw:
        return "missing"
    if _VALID_AGENT_SESSION_KEY_RE.match(raw):
        return "agent"
    return "malformed_agent" if raw.lower().startswith("agent:") else "legacy_or_alias"


def _current_run_lookup_time_ms() -> float:
    return time.monotonic() * 1000


def _set_resolved_session_key_for_run_cache(
    run_id: str,
    session_key: str | None,
    *,
    now_ms: float,
) -> None:
    if not run_id:
        return
    if (
        run_id not in _resolved_session_key_by_run_id
        and len(_resolved_session_key_by_run_id) >= _RUN_LOOKUP_CACHE_LIMIT
    ):
        oldest_run_id = next(iter(_resolved_session_key_by_run_id), None)
        if oldest_run_id is not None:
            _resolved_session_key_by_run_id.pop(oldest_run_id, None)
    _resolved_session_key_by_run_id[run_id] = RunLookupCacheEntry(
        session_key=session_key,
        expires_at_ms=now_ms + _RUN_LOOKUP_MISS_TTL_MS if session_key is None else None,
    )


async def resolve_session_key_for_run(
    run_id: str | None,
    *,
    database: Any,
    instance_id: int | None = None,
    now_ms: Callable[[], float] | None = None,
) -> str | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    get_now_ms = now_ms or _current_run_lookup_time_ms
    current_now_ms = get_now_ms()
    cached_lookup = _resolved_session_key_by_run_id.get(normalized_run_id)
    if cached_lookup is not None:
        if cached_lookup.session_key is not None:
            return cached_lookup.session_key
        if (cached_lookup.expires_at_ms or 0) > current_now_ms:
            return None
        _resolved_session_key_by_run_id.pop(normalized_run_id, None)
    mission = await database.get_latest_mission_by_run_id(
        normalized_run_id,
        instance_id=instance_id,
        require_session_key=True,
    )
    if mission is not None:
        stored_session_key = canonicalize_session_key(mission.get("session_key")) or str(
            mission.get("session_key") or ""
        ).strip()
        if stored_session_key:
            request_session_key = (
                to_agent_request_session_key(stored_session_key) or stored_session_key
            )
            _set_resolved_session_key_for_run_cache(
                normalized_run_id,
                request_session_key,
                now_ms=current_now_ms,
            )
            return request_session_key
    _set_resolved_session_key_for_run_cache(normalized_run_id, None, now_ms=current_now_ms)
    return None


def reset_resolved_session_key_for_run_cache_for_test() -> None:
    _resolved_session_key_by_run_id.clear()
