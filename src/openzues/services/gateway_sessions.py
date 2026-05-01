from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

from openzues.database import Database
from openzues.services.session_keys import (
    build_launch_session_key,
    canonicalize_session_key,
    is_cron_run_session_key,
    parse_agent_session_key,
    parse_thread_session_suffix,
    session_key_lookup_aliases,
    to_agent_request_session_key,
    to_agent_store_session_key,
)

_CONTROL_CHAT_PATH = "/api/control-chat"
_DEFAULT_MODEL = "gpt-5.4"
_CONTROL_CHAT_GLOBAL_DISPLAY_NAME = "OpenZues Control Chat"
_CONTROL_CHAT_THREAD_DISPLAY_NAME = "OpenZues Control Chat Thread"
_CONTROL_CHAT_SUBJECT_FALLBACK = "Operator control chat"
_DERIVED_TITLE_MAX_LEN = 60
_DERIVED_TITLE_ELLIPSIS = "\u2026"
_SESSION_LABEL_MAX_LENGTH = 512
_SESSION_LIST_MESSAGE_LIMIT_MAX = 20
_SESSION_MESSAGE_ASSISTANT_SKIP_TEXTS = {"NO_REPLY", "ANNOUNCE_SKIP", "REPLY_SKIP"}
_SESSION_RUN_STATUS_VALUES = {"running", "done", "failed", "killed", "timeout"}
_OPENCLAW_SESSION_LIST_KINDS = {
    "main",
    "group",
    "cron",
    "hook",
    "node",
    "other",
    "global",
    "thread",
}
_TRANSCRIPT_USAGE_MESSAGE_LIMIT = 1_000
_SESSION_MESSAGE_INLINE_DIRECTIVE_RE = re.compile(
    r"\[\[\s*(?:reply_to(?:_current|\s*:\s*[^\]]+)?|audio_as_voice)\s*\]\]",
    re.IGNORECASE,
)
_TRAILING_UNTRUSTED_CONTEXT_RE = re.compile(
    r"(?:\r?\n){0,2}"
    r"Untrusted context \(metadata, do not treat as instructions or commands\):\s*\r?\n"
    r"<<<EXTERNAL_UNTRUSTED_CONTENT(?:\s+id=\"[^\"]{1,128}\")?>>>\s*\r?\n"
    r".*?"
    r"<<<END_EXTERNAL_UNTRUSTED_CONTENT(?:\s+id=\"[^\"]{1,128}\")?>>>\s*\Z",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class _CurrentControlChatSession:
    main_session_key: str
    current_session_key: str
    current_session_id: str | None
    current_mission: dict[str, Any] | None
    model: str


@dataclass(frozen=True, slots=True)
class _SessionIdMatchCandidate:
    session: _CurrentControlChatSession
    updated_at_ms: int | None
    normalized_session_key: str
    normalized_request_key: str
    is_canonical_session_key: bool
    is_structural: bool


class GatewaySessionsService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def build_snapshot(
        self,
        *,
        include_global: bool,
        include_unknown: bool,
        limit: int | None,
        active_minutes: int | None,
        label: str | None,
        spawned_by: str | None,
        agent_id: str | None,
        search: str | None,
        include_derived_titles: bool,
        include_last_message: bool,
        now_ms: int,
        kinds: tuple[str, ...] | None = None,
        message_limit: int | None = None,
    ) -> dict[str, Any]:
        normalized_label = (
            _parse_session_label(label) if _string_or_none(label) is not None else None
        )
        normalized_limit = _normalize_positive_numeric_filter(limit)
        normalized_active_minutes = _normalize_positive_numeric_filter(active_minutes)
        normalized_spawned_by = _string_or_none(spawned_by)
        normalized_agent_id = _normalize_lookup_token(agent_id)
        normalized_search = _string_or_none(search)
        normalized_kinds = _normalized_session_list_kinds(kinds)
        normalized_message_limit = _normalize_session_list_message_limit(message_limit)
        if normalized_agent_id is not None and not await self._agent_exists(
            normalized_agent_id
        ):
            raise ValueError(f'unknown agent id "{normalized_agent_id}"')
        sessions: list[dict[str, Any]] = []
        session = await self._current_control_chat_session()
        seen_session_keys: set[str] = set()

        async def append_snapshot_session(
            candidate_session_key: str | None,
            *,
            known_session: _CurrentControlChatSession | None = None,
        ) -> None:
            raw_session_key = _string_or_none(candidate_session_key)
            if raw_session_key is None or is_cron_run_session_key(raw_session_key):
                return
            canonical_key = canonicalize_session_key(raw_session_key) or raw_session_key.lower()
            if canonical_key in seen_session_keys:
                return
            seen_session_keys.add(canonical_key)
            resolved_session = known_session or await self._session_for_key(
                raw_session_key,
                default_session=session,
            )
            if not self._session_matches_visibility(
                resolved_session,
                include_global=include_global,
                include_unknown=include_unknown,
            ):
                return
            if not self._session_matches_agent(
                resolved_session.current_session_key,
                agent_id=normalized_agent_id,
            ):
                return
            if not await self._session_matches_filters(
                resolved_session,
                label=normalized_label,
                spawned_by=normalized_spawned_by,
            ):
                return
            session_payload = await self._snapshot_session_payload(
                session=resolved_session,
                include_derived_titles=include_derived_titles,
                include_last_message=include_last_message,
                now_ms=now_ms,
                message_limit=normalized_message_limit,
            )
            if not _session_payload_matches_kinds(session_payload, normalized_kinds):
                return
            sessions.append(session_payload)

        await append_snapshot_session(session.current_session_key, known_session=session)

        metadata_rows = await self._database.list_gateway_session_metadata_rows()
        for row in metadata_rows:
            await append_snapshot_session(_string_or_none(row.get("session_key")))

        missions = await self._database.list_missions()
        for mission in reversed(missions):
            await append_snapshot_session(_string_or_none(mission.get("session_key")))

        transcript_session_keys = await self._database.list_control_chat_session_keys()
        for transcript_session_key in transcript_session_keys:
            await append_snapshot_session(transcript_session_key)

        if normalized_active_minutes is not None:
            cutoff = now_ms - normalized_active_minutes * 60_000
            sessions = [
                session_payload
                for session_payload in sessions
                if _int_or_none(session_payload.get("updatedAt")) is not None
                and int(session_payload["updatedAt"]) >= cutoff
            ]

        if normalized_search is not None:
            normalized_search = normalized_search.lower()
            sessions = [
                session_payload
                for session_payload in sessions
                if any(
                    isinstance(field, str) and normalized_search in field.lower()
                    for field in (
                        session_payload.get("displayName"),
                        session_payload.get("label"),
                        session_payload.get("subject"),
                        session_payload.get("sessionId"),
                        session_payload.get("key"),
                    )
                )
            ]

        sessions.sort(key=_snapshot_sort_key)

        if normalized_limit is not None:
            sessions = sessions[:normalized_limit]

        return {
            "ts": now_ms,
            "path": _CONTROL_CHAT_PATH,
            "count": len(sessions),
            "defaults": {
                "modelProvider": "openai",
                "model": session.model,
                "contextTokens": None,
                "mainSessionKey": session.main_session_key,
            },
            "sessions": sessions,
        }

    async def _snapshot_session_payload(
        self,
        *,
        session: _CurrentControlChatSession,
        include_derived_titles: bool,
        include_last_message: bool,
        now_ms: int,
        message_limit: int,
    ) -> dict[str, Any]:
        payload = await self._session_payload(session=session, now_ms=now_ms)
        if include_last_message:
            last_message_preview = await self._last_message_preview(session.current_session_key)
            if last_message_preview is not None:
                payload["lastMessagePreview"] = last_message_preview
        if include_derived_titles:
            derived_title = _derive_session_title(
                payload,
                first_user_message=await self._first_user_message(session.current_session_key),
            )
            if derived_title is not None:
                payload["derivedTitle"] = derived_title
        if message_limit > 0:
            payload["messages"] = await self._session_list_messages(
                session.current_session_key,
                limit=message_limit,
            )
        return payload

    async def current_session_key(self) -> str:
        session = await self._current_control_chat_session()
        return session.current_session_key

    async def main_session_key(self) -> str:
        session = await self._current_control_chat_session()
        return session.main_session_key

    async def build_current_session_payload(self, *, now_ms: int) -> dict[str, Any]:
        session = await self._current_control_chat_session()
        return await self._session_payload(session=session, now_ms=now_ms)

    async def build_session_payload_for_key(
        self,
        *,
        session_key: str,
        now_ms: int,
    ) -> dict[str, Any] | None:
        session = await self._current_control_chat_session()
        known_session = await self._known_session_for_lookup(
            session_key,
            default_session=session,
            agent_id=None,
        )
        if known_session is None:
            return None
        return await self._session_payload(session=known_session, now_ms=now_ms)

    async def build_changed_event_payload(
        self,
        *,
        session_key: str,
        reason: str,
        now_ms: int,
        compacted: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sessionKey": session_key,
            "reason": reason,
            "ts": now_ms,
        }
        if compacted is not None:
            payload["compacted"] = compacted

        session_payload = await self.build_session_payload_for_key(
            session_key=session_key,
            now_ms=now_ms,
        )
        if session_payload is None:
            return payload

        payload.update(
            {
                "updatedAt": session_payload["updatedAt"],
                "sessionId": session_payload["sessionId"],
                "kind": session_payload["kind"],
                "subject": session_payload["subject"],
                "displayName": session_payload["displayName"],
                "systemSent": session_payload["systemSent"],
                "abortedLastRun": session_payload["abortedLastRun"],
                "thinkingLevel": session_payload["thinkingLevel"],
                "verboseLevel": session_payload["verboseLevel"],
                "traceLevel": session_payload["traceLevel"],
                "inputTokens": session_payload["inputTokens"],
                "outputTokens": session_payload["outputTokens"],
                "totalTokens": session_payload["totalTokens"],
                "contextTokens": session_payload["contextTokens"],
                "modelProvider": session_payload["modelProvider"],
                "model": session_payload["model"],
                "space": session_payload["space"],
            }
        )
        for field in (
            "label",
            "displayName",
            "chatType",
            "channel",
            "groupId",
            "groupChannel",
            "responseUsage",
            "reasoningLevel",
            "elevatedLevel",
            "ttsAuto",
            "authProfileOverride",
            "authProfileOverrideSource",
            "queueMode",
            "queueDrop",
            "execHost",
            "execSecurity",
            "execAsk",
            "execNode",
            "spawnedBy",
            "spawnedWorkspaceDir",
            "subagentRole",
            "subagentControlScope",
            "sendPolicy",
            "groupActivation",
            "parentSessionKey",
            "lastChannel",
            "lastTo",
            "lastAccountId",
        ):
            value = _string_or_none(session_payload.get(field))
            if value is not None:
                payload[field] = value
        fast_mode = _bool_or_none(session_payload.get("fastMode"))
        if fast_mode is not None:
            payload["fastMode"] = fast_mode
        forked_from_parent = _bool_or_none(session_payload.get("forkedFromParent"))
        if forked_from_parent is not None:
            payload["forkedFromParent"] = forked_from_parent
        spawn_depth = _int_or_none(session_payload.get("spawnDepth"))
        if spawn_depth is not None:
            payload["spawnDepth"] = spawn_depth
        last_thread_id = _route_thread_id_or_none(session_payload.get("lastThreadId"))
        if last_thread_id is not None:
            payload["lastThreadId"] = last_thread_id
        delivery_context = _delivery_context_or_none(session_payload.get("deliveryContext"))
        if delivery_context is not None:
            payload["deliveryContext"] = delivery_context
        status = _session_run_status_or_none(session_payload.get("status"))
        if status is not None:
            payload["status"] = status
        for field in ("startedAt", "endedAt", "runtimeMs"):
            lifecycle_value = _session_lifecycle_int_or_none(session_payload.get(field))
            if lifecycle_value is not None:
                payload[field] = lifecycle_value
        total_tokens_fresh = _bool_or_none(session_payload.get("totalTokensFresh"))
        if total_tokens_fresh is not None:
            payload["totalTokensFresh"] = total_tokens_fresh
        estimated_cost_usd = _float_or_none(session_payload.get("estimatedCostUsd"))
        if estimated_cost_usd is not None:
            payload["estimatedCostUsd"] = estimated_cost_usd
        compaction_checkpoint_count = _int_or_none(
            session_payload.get("compactionCheckpointCount")
        )
        if compaction_checkpoint_count is not None:
            payload["compactionCheckpointCount"] = compaction_checkpoint_count
        latest_compaction_checkpoint = session_payload.get("latestCompactionCheckpoint")
        if isinstance(latest_compaction_checkpoint, dict):
            payload["latestCompactionCheckpoint"] = latest_compaction_checkpoint
        child_sessions = _session_child_sessions_or_none(session_payload)
        if child_sessions is not None:
            payload["childSessions"] = child_sessions
        return payload

    async def build_message_event_payload(
        self,
        *,
        message_row: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any] | None:
        role = _string_or_none(message_row.get("role"))
        if role not in {"user", "assistant"}:
            return None
        message_text = _session_message_display_text(str(message_row.get("content") or ""))
        if _is_suppressed_assistant_session_message(role=role, text=message_text):
            return None

        session = await self._session_for_message(message_row)
        session_payload = await self._session_payload(session=session, now_ms=now_ms)
        message_id = _string_or_none(message_row.get("id"))
        message_seq = await self._message_sequence(message_row)
        parent_id = _message_parent_id(message_row.get("metadata_json"))
        payload: dict[str, Any] = {
            "sessionKey": session.current_session_key,
            "message": _message_payload(
                role=role,
                text=message_text,
                message_id=message_id,
                message_seq=message_seq,
                parent_id=parent_id,
            ),
            "updatedAt": session_payload["updatedAt"],
            "sessionId": session_payload["sessionId"],
            "kind": session_payload["kind"],
            "subject": session_payload["subject"],
            "displayName": session_payload["displayName"],
            "systemSent": session_payload["systemSent"],
            "abortedLastRun": session_payload["abortedLastRun"],
            "thinkingLevel": session_payload["thinkingLevel"],
            "verboseLevel": session_payload["verboseLevel"],
            "traceLevel": session_payload["traceLevel"],
            "inputTokens": session_payload["inputTokens"],
            "outputTokens": session_payload["outputTokens"],
            "totalTokens": session_payload["totalTokens"],
            "contextTokens": session_payload["contextTokens"],
            "modelProvider": session_payload["modelProvider"],
            "model": session_payload["model"],
            "space": session_payload["space"],
        }
        _apply_session_event_metadata(payload, session_payload)
        _apply_live_usage_metadata(payload, message_row)
        compaction_checkpoint_count = _int_or_none(
            session_payload.get("compactionCheckpointCount")
        )
        if compaction_checkpoint_count is not None:
            payload["compactionCheckpointCount"] = compaction_checkpoint_count
        latest_compaction_checkpoint = session_payload.get("latestCompactionCheckpoint")
        if isinstance(latest_compaction_checkpoint, dict):
            payload["latestCompactionCheckpoint"] = latest_compaction_checkpoint
        child_sessions = _session_child_sessions_or_none(session_payload)
        if child_sessions is not None:
            payload["childSessions"] = child_sessions
        if message_id is not None:
            payload["messageId"] = message_id
        if message_seq is not None:
            payload["messageSeq"] = message_seq
        return payload

    async def build_message_changed_event_payload(
        self,
        *,
        message_row: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any] | None:
        role = _string_or_none(message_row.get("role"))
        if role not in {"user", "assistant"}:
            return None
        message_text = _session_message_display_text(str(message_row.get("content") or ""))
        if _is_suppressed_assistant_session_message(role=role, text=message_text):
            return None

        session = await self._session_for_message(message_row)
        session_payload = await self._session_payload(session=session, now_ms=now_ms)
        message_id = _string_or_none(message_row.get("id"))
        message_seq = await self._message_sequence(message_row)
        payload: dict[str, Any] = {
            "sessionKey": session.current_session_key,
            "phase": "message",
            "ts": now_ms,
            "updatedAt": session_payload["updatedAt"],
            "sessionId": session_payload["sessionId"],
            "kind": session_payload["kind"],
            "subject": session_payload["subject"],
            "displayName": session_payload["displayName"],
            "systemSent": session_payload["systemSent"],
            "abortedLastRun": session_payload["abortedLastRun"],
            "thinkingLevel": session_payload["thinkingLevel"],
            "verboseLevel": session_payload["verboseLevel"],
            "traceLevel": session_payload["traceLevel"],
            "inputTokens": session_payload["inputTokens"],
            "outputTokens": session_payload["outputTokens"],
            "totalTokens": session_payload["totalTokens"],
            "contextTokens": session_payload["contextTokens"],
            "modelProvider": session_payload["modelProvider"],
            "model": session_payload["model"],
            "space": session_payload["space"],
        }
        _apply_session_event_metadata(payload, session_payload)
        _apply_live_usage_metadata(payload, message_row)
        compaction_checkpoint_count = _int_or_none(
            session_payload.get("compactionCheckpointCount")
        )
        if compaction_checkpoint_count is not None:
            payload["compactionCheckpointCount"] = compaction_checkpoint_count
        latest_compaction_checkpoint = session_payload.get("latestCompactionCheckpoint")
        if isinstance(latest_compaction_checkpoint, dict):
            payload["latestCompactionCheckpoint"] = latest_compaction_checkpoint
        child_sessions = _session_child_sessions_or_none(session_payload)
        if child_sessions is not None:
            payload["childSessions"] = child_sessions
        if message_id is not None:
            payload["messageId"] = message_id
        if message_seq is not None:
            payload["messageSeq"] = message_seq
        return payload

    async def resolve_key(
        self,
        *,
        key: str | None,
        session_id: str | None,
        label: str | None,
        agent_id: str | None,
        spawned_by: str | None,
        include_global: bool,
        include_unknown: bool,
    ) -> dict[str, Any]:
        normalized_key = _string_or_none(key)
        normalized_session_id = _string_or_none(session_id)
        normalized_label = (
            _parse_session_label(label) if _string_or_none(label) is not None else None
        )
        normalized_agent_id = _normalize_lookup_token(agent_id)
        normalized_spawned_by = _string_or_none(spawned_by)
        selection_count = sum(
            value is not None
            for value in (normalized_key, normalized_session_id, normalized_label)
        )
        if selection_count > 1:
            raise ValueError("Provide either key, sessionId, or label (not multiple)")
        if selection_count == 0:
            raise ValueError("Either key, sessionId, or label is required")
        if normalized_agent_id is not None and not await self._agent_exists(
            normalized_agent_id
        ):
            raise ValueError(f'unknown agent id "{normalized_agent_id}"')
        session = await self._current_control_chat_session()
        if (
            normalized_label is not None or normalized_spawned_by is not None
        ) and normalized_key is None and normalized_session_id is None:
            matched_session_keys = await self._metadata_lookup_session_keys(
                label=normalized_label,
                spawned_by=normalized_spawned_by,
                agent_id=normalized_agent_id,
                include_global=include_global,
                include_unknown=include_unknown,
                default_session=session,
            )
            if not matched_session_keys:
                if normalized_label is not None:
                    raise ValueError("unknown session label")
                raise ValueError("unknown spawnedBy")
            if len(matched_session_keys) > 1:
                joined_keys = ", ".join(matched_session_keys)
                if normalized_label is not None:
                    raise ValueError(
                        f"multiple sessions found with label: {normalized_label} ({joined_keys})"
                    )
                raise ValueError(
                    "multiple sessions found with spawnedBy: "
                    f"{normalized_spawned_by} ({joined_keys})"
                )
            session = await self._session_for_key(
                matched_session_keys[0],
                default_session=session,
            )
        if normalized_key is not None:
            matched_session = await self._known_session_for_lookup(
                normalized_key,
                default_session=session,
                agent_id=normalized_agent_id,
            )
            if matched_session is None:
                raise ValueError("unknown session key")
            session = matched_session
        if normalized_session_id is not None:
            matched_session = await self._known_session_for_session_id(
                normalized_session_id,
                default_session=session,
                agent_id=normalized_agent_id,
                spawned_by=normalized_spawned_by,
                include_global=include_global,
                include_unknown=include_unknown,
            )
            if matched_session is None:
                raise ValueError("unknown sessionId")
            if (
                normalized_key is not None or normalized_label is not None
                and matched_session.current_session_key != session.current_session_key
            ):
                raise ValueError("unknown sessionId")
            session = matched_session
        if not await self._session_matches_filters(
            session,
            label=normalized_label,
            spawned_by=normalized_spawned_by,
        ):
            if normalized_key is not None:
                raise ValueError("unknown session key")
            if normalized_session_id is not None:
                raise ValueError("unknown sessionId")
            if normalized_label is not None:
                raise ValueError("unknown session label")
            raise ValueError("unknown spawnedBy")
        if normalized_key is None and not self._session_matches_visibility(
            session,
            include_global=include_global,
            include_unknown=include_unknown,
        ):
            if normalized_session_id is not None:
                raise ValueError("unknown sessionId")
            if normalized_label is not None:
                raise ValueError("unknown session label")
            if normalized_spawned_by is not None:
                raise ValueError("unknown spawnedBy")

        return {"ok": True, "key": session.current_session_key}

    async def _session_payload(
        self,
        *,
        session: _CurrentControlChatSession,
        now_ms: int,
    ) -> dict[str, Any]:
        is_global_session = session.current_session_key == session.main_session_key
        metadata = await self._session_metadata(session.current_session_key)
        latest_owner_session_key = _latest_owner_session_key(
            metadata,
            owner_session_key=session.current_session_key,
        )
        provider_override = _string_or_none(metadata.get("providerOverride"))
        model_id_override = _string_or_none(metadata.get("modelOverride"))
        model_override = _string_or_none(metadata.get("model"))
        transcript_usage = await self._transcript_usage_snapshot(session.current_session_key)
        transcript_model_provider = _string_or_none(transcript_usage.get("modelProvider"))
        transcript_model = _string_or_none(transcript_usage.get("model"))
        resolved_model = model_id_override or model_override or transcript_model or session.model
        resolved_model_provider = (
            provider_override
            if model_id_override is not None and provider_override is not None
            else (
                "openai"
                if model_override is not None
                else transcript_model_provider or ("openai" if resolved_model else None)
            )
        )
        context_tokens = _int_or_none(
            transcript_usage.get("contextTokens")
        ) or _context_tokens_for_model(
            provider=resolved_model_provider,
            model=resolved_model,
        )
        updated_at_ms = await self._updated_at_ms(
            current_mission=session.current_mission,
            current_session_key=session.current_session_key,
            now_ms=now_ms,
        )
        payload: dict[str, Any] = {
            "key": session.current_session_key,
            "kind": "global" if is_global_session else "thread",
            "displayName": (
                _CONTROL_CHAT_GLOBAL_DISPLAY_NAME
                if is_global_session
                else _CONTROL_CHAT_THREAD_DISPLAY_NAME
            ),
            "surface": "control-chat",
            "subject": (
                _string_or_none(session.current_mission.get("objective"))
                if session.current_mission is not None
                else None
            )
            or _CONTROL_CHAT_SUBJECT_FALLBACK,
            "room": None,
            "space": None,
            "updatedAt": updated_at_ms,
            "sessionId": session.current_session_id,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": _string_or_none(metadata.get("thinkingLevel")),
            "verboseLevel": _string_or_none(metadata.get("verboseLevel")),
            "traceLevel": _string_or_none(metadata.get("traceLevel")),
            "inputTokens": _int_or_none(transcript_usage.get("inputTokens")),
            "outputTokens": _int_or_none(transcript_usage.get("outputTokens")),
            "totalTokens": _int_or_none(transcript_usage.get("totalTokens")),
            "modelProvider": resolved_model_provider,
            "model": resolved_model,
            "contextTokens": context_tokens,
        }
        total_tokens_fresh = _bool_or_none(transcript_usage.get("totalTokensFresh"))
        payload["totalTokensFresh"] = (
            total_tokens_fresh if total_tokens_fresh is not None else False
        )
        estimated_cost_usd = _float_or_none(transcript_usage.get("estimatedCostUsd"))
        if estimated_cost_usd is not None:
            payload["estimatedCostUsd"] = estimated_cost_usd
        fast_mode = _bool_or_none(metadata.get("fastMode"))
        if fast_mode is not None:
            payload["fastMode"] = fast_mode
        session_status = _session_run_status_or_none(metadata.get("status"))
        if session_status is not None:
            payload["status"] = session_status
        for field in ("startedAt", "endedAt", "runtimeMs"):
            lifecycle_value = _session_lifecycle_int_or_none(metadata.get(field))
            if lifecycle_value is not None:
                payload[field] = lifecycle_value
        aborted_last_run = _bool_or_none(metadata.get("abortedLastRun"))
        if aborted_last_run is not None:
            payload["abortedLastRun"] = aborted_last_run
        forked_from_parent = _bool_or_none(metadata.get("forkedFromParent"))
        if forked_from_parent is not None:
            payload["forkedFromParent"] = forked_from_parent
        if latest_owner_session_key is not None:
            payload["spawnedBy"] = latest_owner_session_key
            payload["parentSessionKey"] = latest_owner_session_key
        for field in (
            "label",
            "displayName",
            "chatType",
            "channel",
            "groupId",
            "groupChannel",
            "responseUsage",
            "reasoningLevel",
            "elevatedLevel",
            "ttsAuto",
            "authProfileOverride",
            "authProfileOverrideSource",
            "queueMode",
            "queueDrop",
            "execHost",
            "execSecurity",
            "execAsk",
            "execNode",
            "spawnedBy",
            "spawnedWorkspaceDir",
            "subagentRole",
            "subagentControlScope",
            "sendPolicy",
            "groupActivation",
            "parentSessionKey",
            "providerOverride",
            "modelOverride",
            "modelOverrideSource",
            "claudeCliSessionId",
        ):
            if latest_owner_session_key is not None and field in {"spawnedBy", "parentSessionKey"}:
                continue
            value = (
                _canonicalize_owner_session_key(
                    metadata.get(field),
                    owner_session_key=session.current_session_key,
                )
                if field in {"spawnedBy", "parentSessionKey"}
                else _string_or_none(metadata.get(field))
            )
            if value is not None:
                payload[field] = value
        spawn_depth = _int_or_none(metadata.get("spawnDepth"))
        if spawn_depth is not None:
            payload["spawnDepth"] = spawn_depth
        for field in (
            "authProfileOverrideCompactionCount",
            "queueDebounceMs",
            "queueCap",
        ):
            int_value = _int_or_none(metadata.get(field))
            if int_value is not None:
                payload[field] = int_value
        group_activation_needs_system_intro = _bool_or_none(
            metadata.get("groupActivationNeedsSystemIntro")
        )
        if group_activation_needs_system_intro is not None:
            payload["groupActivationNeedsSystemIntro"] = group_activation_needs_system_intro
        cli_session_ids = _string_dict_or_none(metadata.get("cliSessionIds"))
        if cli_session_ids is not None:
            payload["cliSessionIds"] = cli_session_ids
        cli_session_bindings = _nested_string_dict_or_none(metadata.get("cliSessionBindings"))
        if cli_session_bindings is not None:
            payload["cliSessionBindings"] = cli_session_bindings
        delivery_context: dict[str, Any] = {}
        metadata_delivery_context = _delivery_context_or_none(metadata.get("deliveryContext"))
        if metadata_delivery_context is not None:
            delivery_context.update(metadata_delivery_context)
        for field, context_field in (
            ("lastChannel", "channel"),
            ("lastTo", "to"),
            ("lastAccountId", "accountId"),
        ):
            value = _string_or_none(metadata.get(field))
            if value is not None:
                payload[field] = value
                delivery_context[context_field] = value
        last_thread_id = _route_thread_id_or_none(metadata.get("lastThreadId"))
        if last_thread_id is not None:
            payload["lastThreadId"] = last_thread_id
            delivery_context["threadId"] = last_thread_id
        origin = metadata.get("origin")
        if isinstance(origin, dict):
            origin_provider = _string_or_none(origin.get("provider"))
            if origin_provider is not None and "channel" not in delivery_context:
                payload["lastChannel"] = origin_provider
                delivery_context["channel"] = origin_provider
            origin_account_id = _string_or_none(origin.get("accountId"))
            if origin_account_id is not None and "accountId" not in delivery_context:
                payload["lastAccountId"] = origin_account_id
                delivery_context["accountId"] = origin_account_id
            origin_thread_id = _route_thread_id_or_none(origin.get("threadId"))
            if origin_thread_id is not None and "threadId" not in delivery_context:
                payload["lastThreadId"] = origin_thread_id
                delivery_context["threadId"] = origin_thread_id
        if delivery_context:
            payload["deliveryContext"] = delivery_context
        child_sessions = await self._child_session_keys(session.current_session_key)
        if child_sessions:
            payload["childSessions"] = child_sessions
        compaction_checkpoint_count = (
            await self._database.count_control_chat_compaction_checkpoints(
                session_key=session.current_session_key
            )
        )
        if compaction_checkpoint_count > 0:
            payload["compactionCheckpointCount"] = compaction_checkpoint_count
            latest_checkpoint = await self._database.list_control_chat_compaction_checkpoints(
                session_key=session.current_session_key,
                limit=1,
            )
            if latest_checkpoint:
                payload["latestCompactionCheckpoint"] = latest_checkpoint[0]
        return payload

    async def _updated_at_ms(
        self,
        *,
        current_mission: dict[str, Any] | None,
        current_session_key: str,
        now_ms: int,
    ) -> int:
        updated_at_ms = _iso8601_to_timestamp_ms(
            current_mission.get("updated_at") if current_mission is not None else None
        )
        metadata_row = await self._database.get_gateway_session_metadata(current_session_key)
        metadata_updated_at_ms = _iso8601_to_timestamp_ms(
            metadata_row.get("updated_at") if metadata_row is not None else None
        )
        if updated_at_ms is not None and metadata_updated_at_ms is not None:
            return max(updated_at_ms, metadata_updated_at_ms)
        if updated_at_ms is not None:
            return updated_at_ms
        if metadata_updated_at_ms is not None:
            return metadata_updated_at_ms

        latest_messages = await self._database.list_control_chat_messages(
            limit=1,
            session_key=current_session_key,
        )
        if latest_messages:
            message_updated_at_ms = _iso8601_to_timestamp_ms(latest_messages[-1].get("created_at"))
            if message_updated_at_ms is not None:
                if metadata_updated_at_ms is not None:
                    return max(message_updated_at_ms, metadata_updated_at_ms)
                return message_updated_at_ms
        return now_ms

    async def _current_control_chat_session(self) -> _CurrentControlChatSession:
        gateway = await self._database.get_gateway_bootstrap()
        main_session_key = _main_session_key_from_gateway(gateway)
        latest_thread_mission = await (
            self._database.get_latest_thread_child_mission_by_parent_session_key(
                main_session_key,
                require_thread=True,
            )
        )
        latest_main_mission = await self._database.get_latest_mission_by_session_key(
            main_session_key,
            require_thread=False,
        )
        current_mission = latest_thread_mission or latest_main_mission
        current_session_key = _string_or_none(
            current_mission.get("session_key") if current_mission is not None else None
        ) or main_session_key
        current_session_id = (
            _string_or_none(current_mission.get("thread_id"))
            if current_mission is not None
            else None
        )
        model = (
            _string_or_none(current_mission.get("model") if current_mission is not None else None)
            or _string_or_none(gateway.get("model") if gateway is not None else None)
            or _DEFAULT_MODEL
        )
        return _CurrentControlChatSession(
            main_session_key=main_session_key,
            current_session_key=current_session_key,
            current_session_id=current_session_id,
            current_mission=current_mission,
            model=model,
        )

    async def _session_for_message(
        self,
        message_row: dict[str, Any],
    ) -> _CurrentControlChatSession:
        session = await self._current_control_chat_session()
        stored_session_key = _string_or_none(message_row.get("session_key"))
        if stored_session_key is not None:
            mission = await self._database.get_latest_mission_by_session_key(
                stored_session_key,
                require_thread=False,
            )
            main_session_key, parsed_thread_id = _resolved_stored_session_scope(
                stored_session_key,
                fallback_main_session_key=session.main_session_key,
            )
            return _CurrentControlChatSession(
                main_session_key=main_session_key,
                current_session_key=stored_session_key,
                current_session_id=_string_or_none(mission.get("thread_id") if mission else None)
                or parsed_thread_id,
                current_mission=mission,
                model=_string_or_none(mission.get("model") if mission else None) or session.model,
            )
        raw_mission_id = message_row.get("mission_id")
        if isinstance(raw_mission_id, bool) or not isinstance(raw_mission_id, int):
            return session
        mission = await self._database.get_mission(raw_mission_id)
        if mission is None:
            return session
        return _CurrentControlChatSession(
            main_session_key=session.main_session_key,
            current_session_key=_string_or_none(mission.get("session_key"))
            or session.current_session_key,
            current_session_id=_string_or_none(mission.get("thread_id"))
            or session.current_session_id,
            current_mission=mission,
            model=_string_or_none(mission.get("model")) or session.model,
        )

    async def _last_message_preview(self, session_key: str) -> str | None:
        latest_messages = await self._database.list_control_chat_messages(
            limit=1,
            session_key=session_key,
        )
        if not latest_messages:
            return None
        return _string_or_none(latest_messages[-1].get("content"))

    async def _first_user_message(self, session_key: str) -> str | None:
        first_message = await self._database.get_first_control_chat_message(
            session_key=session_key,
            role="user",
        )
        if first_message is None:
            return None
        return _string_or_none(first_message.get("content"))

    async def _session_list_messages(
        self,
        session_key: str,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        messages = await self._database.list_control_chat_messages(
            limit=limit,
            session_key=session_key,
        )
        projected: list[dict[str, Any]] = []
        for message in messages:
            role = _string_or_none(message.get("role"))
            if role not in {"user", "assistant"}:
                continue
            text = _session_message_display_text(str(message.get("content") or ""))
            if _is_suppressed_assistant_session_message(role=role, text=text):
                continue
            projected.append(
                _message_payload(
                    role=role,
                    text=text,
                    message_id=_message_id_text(message.get("id")),
                    message_seq=await self._message_sequence(message),
                    parent_id=_message_parent_id(message.get("metadata_json")),
                )
            )
        return projected

    async def _transcript_usage_snapshot(self, session_key: str) -> dict[str, Any]:
        messages = await self._database.list_control_chat_messages(
            limit=_TRANSCRIPT_USAGE_MESSAGE_LIMIT,
            session_key=session_key,
        )
        snapshot: dict[str, Any] = {}
        input_tokens = 0
        output_tokens = 0
        cache_read = 0
        cache_write = 0
        saw_input_tokens = False
        saw_output_tokens = False
        latest_prompt_tokens: int | None = None
        estimated_cost_usd = 0.0
        saw_cost = False

        for message in messages:
            if _string_or_none(message.get("role")) != "assistant":
                continue
            usage = _json_object_or_none(message.get("usage_json"))
            cost = _json_object_or_none(message.get("cost_json"))
            provider = _string_or_none(message.get("model_provider")) or _string_or_none(
                usage.get("provider") if usage is not None else None
            )
            model = _string_or_none(message.get("model")) or _string_or_none(
                usage.get("model") if usage is not None else None
            )
            is_delivery_mirror = provider == "openclaw" and model == "delivery-mirror"

            input_value = _first_int_value(
                usage,
                ("input", "inputTokens", "input_tokens", "promptTokens", "prompt_tokens"),
            )
            output_value = _first_int_value(
                usage,
                (
                    "output",
                    "outputTokens",
                    "output_tokens",
                    "completionTokens",
                    "completion_tokens",
                ),
            )
            cache_read_value = _first_int_value(
                usage,
                ("cacheRead", "cache_read", "cache_read_input_tokens", "cached_tokens"),
            )
            cache_write_value = _first_int_value(
                usage,
                ("cacheWrite", "cache_write", "cache_creation_input_tokens"),
            )
            cost_value = _usage_cost_usd(usage=usage, cost=cost)
            has_meaningful_usage = any(
                value is not None and value > 0
                for value in (
                    input_value,
                    output_value,
                    cache_read_value,
                    cache_write_value,
                )
            ) or (cost_value is not None and cost_value > 0)
            if is_delivery_mirror and not has_meaningful_usage:
                continue

            if provider is not None and not is_delivery_mirror:
                snapshot["modelProvider"] = provider
            if model is not None and not is_delivery_mirror:
                snapshot["model"] = model
            if input_value is not None:
                input_tokens += input_value
                saw_input_tokens = True
            if output_value is not None:
                output_tokens += output_value
                saw_output_tokens = True
            if cache_read_value is not None:
                cache_read += cache_read_value
            if cache_write_value is not None:
                cache_write += cache_write_value

            prompt_tokens = (
                (input_value or 0)
                + (cache_read_value or 0)
                + (cache_write_value or 0)
            )
            if prompt_tokens > 0:
                latest_prompt_tokens = prompt_tokens
            if cost_value is not None:
                estimated_cost_usd += cost_value
                saw_cost = True

        if saw_input_tokens:
            snapshot["inputTokens"] = input_tokens
        if saw_output_tokens:
            snapshot["outputTokens"] = output_tokens
        if latest_prompt_tokens is not None:
            snapshot["totalTokens"] = latest_prompt_tokens
            snapshot["totalTokensFresh"] = True
        if saw_cost:
            snapshot["estimatedCostUsd"] = estimated_cost_usd
        context_tokens = _context_tokens_for_model(
            provider=_string_or_none(snapshot.get("modelProvider")),
            model=_string_or_none(snapshot.get("model")),
        )
        if context_tokens is not None:
            snapshot["contextTokens"] = context_tokens
        return snapshot

    async def _message_sequence(self, message_row: dict[str, Any]) -> int | None:
        stored_session_key = _string_or_none(message_row.get("session_key"))
        message_id = _int_or_none(message_row.get("id"))
        if stored_session_key is None or message_id is None:
            return None
        count = await self._database.count_control_chat_messages(
            session_key=stored_session_key,
            up_to_id=message_id,
        )
        return count or None

    async def _session_for_key(
        self,
        session_key: str,
        *,
        default_session: _CurrentControlChatSession,
    ) -> _CurrentControlChatSession:
        mission = await self._database.get_latest_mission_by_session_key(
            session_key,
            require_thread=False,
        )
        main_session_key, parsed_thread_id = _resolved_stored_session_scope(
            session_key,
            fallback_main_session_key=default_session.main_session_key,
        )
        return _CurrentControlChatSession(
            main_session_key=main_session_key,
            current_session_key=session_key,
            current_session_id=_string_or_none(mission.get("thread_id") if mission else None)
            or parsed_thread_id,
            current_mission=mission,
            model=_string_or_none(mission.get("model") if mission else None)
            or default_session.model,
        )

    async def _known_session_for_lookup(
        self,
        session_key: str,
        *,
        default_session: _CurrentControlChatSession,
        agent_id: str | None,
    ) -> _CurrentControlChatSession | None:
        requested_canonical = canonicalize_session_key(session_key)
        current_canonical = canonicalize_session_key(default_session.current_session_key)
        if requested_canonical is not None and requested_canonical == current_canonical:
            return default_session

        direct_match = await self._known_session_for_lookup_candidate(
            session_key,
            default_session=default_session,
        )
        if direct_match is not None:
            return direct_match

        agent_store_lookup_key = _scoped_agent_store_lookup_key(session_key, agent_id=agent_id)
        agent_store_canonical = canonicalize_session_key(agent_store_lookup_key)
        if (
            agent_store_lookup_key is not None
            and (
                requested_canonical is None
                or requested_canonical != agent_store_canonical
            )
        ):
            if agent_store_canonical is not None and agent_store_canonical == current_canonical:
                return default_session
            scoped_match = await self._known_session_for_lookup_candidate(
                agent_store_lookup_key,
                default_session=default_session,
            )
            if scoped_match is not None:
                return scoped_match

        agent_store_lookup_key = _default_agent_store_lookup_key(session_key)
        agent_store_canonical = canonicalize_session_key(agent_store_lookup_key)
        if (
            agent_store_lookup_key is None
            or requested_canonical is not None
            and requested_canonical == agent_store_canonical
        ):
            return None
        if agent_store_canonical is not None and agent_store_canonical == current_canonical:
            return default_session
        return await self._known_session_for_lookup_candidate(
            agent_store_lookup_key,
            default_session=default_session,
        )

    async def _known_session_for_lookup_candidate(
        self,
        session_key: str,
        *,
        default_session: _CurrentControlChatSession,
    ) -> _CurrentControlChatSession | None:
        metadata_row = await self._database.get_gateway_session_metadata(session_key)
        if metadata_row is not None:
            stored_session_key = _string_or_none(metadata_row.get("session_key")) or session_key
            return await self._session_for_key(stored_session_key, default_session=default_session)

        mission = await self._database.get_latest_mission_by_session_key(
            session_key,
            require_thread=False,
        )
        if mission is not None:
            stored_session_key = _string_or_none(mission.get("session_key")) or session_key
            return await self._session_for_key(stored_session_key, default_session=default_session)

        message_count = await self._database.count_control_chat_messages(session_key=session_key)
        if message_count > 0:
            return await self._session_for_key(session_key, default_session=default_session)

        return None

    async def _session_metadata(self, session_key: str) -> dict[str, Any]:
        row = await self._database.get_gateway_session_metadata(session_key)
        if row is None:
            return {}
        metadata = row.get("metadata")
        return metadata if isinstance(metadata, dict) else {}

    async def _child_session_keys(self, session_key: str) -> list[str]:
        rows = await self._database.list_gateway_session_metadata_rows()
        child_session_keys: list[str] = []
        seen_session_keys: set[str] = set()
        for row in rows:
            child_session_key = _string_or_none(row.get("session_key"))
            metadata = row.get("metadata")
            if (
                child_session_key is None
                or child_session_key == session_key
                or not isinstance(metadata, dict)
            ):
                continue
            latest_owner_session_key = _latest_owner_session_key(
                metadata,
                owner_session_key=child_session_key,
            )
            if latest_owner_session_key is not None:
                if not _session_keys_match(latest_owner_session_key, session_key):
                    continue
            elif not _metadata_matches_spawned_by(metadata, spawned_by=session_key):
                continue
            dedupe_key = canonicalize_session_key(child_session_key) or child_session_key.lower()
            if dedupe_key in seen_session_keys:
                continue
            seen_session_keys.add(dedupe_key)
            child_session_keys.append(child_session_key)
        return child_session_keys

    async def _known_session_for_session_id(
        self,
        session_id: str,
        *,
        default_session: _CurrentControlChatSession,
        agent_id: str | None,
        spawned_by: str | None,
        include_global: bool,
        include_unknown: bool,
    ) -> _CurrentControlChatSession | None:
        matches = await self._session_id_match_candidates(
            session_id,
            default_session=default_session,
            agent_id=agent_id,
            spawned_by=spawned_by,
            include_global=include_global,
            include_unknown=include_unknown,
        )
        if not matches:
            return None

        canonical_matches = _collapse_session_id_alias_matches(matches)
        if len(canonical_matches) == 1:
            return canonical_matches[0].session

        structural_matches = [match for match in canonical_matches if match.is_structural]
        selected_structural_match = _select_unique_freshest_session_id_match(structural_matches)
        if selected_structural_match is not None:
            return selected_structural_match.session
        if len(structural_matches) > 1:
            return None

        selected_canonical_match = _select_unique_freshest_session_id_match(canonical_matches)
        if selected_canonical_match is not None:
            return selected_canonical_match.session
        return None

    async def _session_id_match_candidates(
        self,
        session_id: str,
        *,
        default_session: _CurrentControlChatSession,
        agent_id: str | None,
        spawned_by: str | None,
        include_global: bool,
        include_unknown: bool,
    ) -> list[_SessionIdMatchCandidate]:
        normalized_session_id = _normalize_lookup_token(session_id)
        if normalized_session_id is None:
            return []

        seen_session_keys: set[str] = set()
        matches: list[_SessionIdMatchCandidate] = []

        async def append_candidate(
            session_key: str | None,
            *,
            known_session: _CurrentControlChatSession | None = None,
        ) -> None:
            raw_session_key = _string_or_none(session_key)
            if raw_session_key is None or raw_session_key in seen_session_keys:
                return
            seen_session_keys.add(raw_session_key)
            resolved_session = known_session or await self._session_for_key(
                raw_session_key,
                default_session=default_session,
            )
            if not self._session_matches_visibility(
                resolved_session,
                include_global=include_global,
                include_unknown=include_unknown,
            ):
                return
            if not self._session_matches_agent(
                resolved_session.current_session_key,
                agent_id=agent_id,
            ):
                return
            if not await self._session_matches_filters(
                resolved_session,
                label=None,
                spawned_by=spawned_by,
            ):
                return
            if not _session_id_selector_matches(
                session=resolved_session,
                normalized_session_id=normalized_session_id,
            ):
                return
            matches.append(
                _build_session_id_match_candidate(
                    session=resolved_session,
                    updated_at_ms=await self._session_updated_at_ms_or_none(
                        session=resolved_session
                    ),
                    normalized_session_id=normalized_session_id,
                )
            )

        await append_candidate(
            default_session.current_session_key,
            known_session=default_session,
        )

        metadata_rows = await self._database.list_gateway_session_metadata_rows()
        for row in metadata_rows:
            await append_candidate(_string_or_none(row.get("session_key")))

        missions = await self._database.list_missions()
        for mission in missions:
            await append_candidate(_string_or_none(mission.get("session_key")))

        transcript_session_keys = await self._database.list_control_chat_session_keys()
        for transcript_session_key in transcript_session_keys:
            await append_candidate(transcript_session_key)

        return matches

    async def _session_updated_at_ms_or_none(
        self,
        *,
        session: _CurrentControlChatSession,
    ) -> int | None:
        mission_updated_at_ms = _iso8601_to_timestamp_ms(
            session.current_mission.get("updated_at")
            if session.current_mission is not None
            else None
        )
        metadata_row = await self._database.get_gateway_session_metadata(
            session.current_session_key
        )
        metadata_updated_at_ms = _iso8601_to_timestamp_ms(
            metadata_row.get("updated_at") if metadata_row is not None else None
        )
        if mission_updated_at_ms is not None and metadata_updated_at_ms is not None:
            return max(mission_updated_at_ms, metadata_updated_at_ms)
        if mission_updated_at_ms is not None:
            return mission_updated_at_ms
        if metadata_updated_at_ms is not None:
            return metadata_updated_at_ms

        latest_messages = await self._database.list_control_chat_messages(
            limit=1,
            session_key=session.current_session_key,
        )
        if not latest_messages:
            return None
        return _iso8601_to_timestamp_ms(latest_messages[-1].get("created_at"))

    async def _metadata_lookup_session_keys(
        self,
        *,
        label: str | None,
        spawned_by: str | None,
        agent_id: str | None,
        include_global: bool,
        include_unknown: bool,
        default_session: _CurrentControlChatSession,
    ) -> list[str]:
        rows = await self._database.list_gateway_session_metadata_rows()
        matched_session_keys: list[str] = []
        seen_session_keys: set[str] = set()
        for row in rows:
            session_key = _string_or_none(row.get("session_key"))
            metadata = row.get("metadata")
            if session_key is None or not isinstance(metadata, dict):
                continue
            if label is not None and _string_or_none(metadata.get("label")) != label:
                continue
            resolved_session = await self._session_for_key(
                session_key,
                default_session=default_session,
            )
            if not self._session_matches_visibility(
                resolved_session,
                include_global=include_global,
                include_unknown=include_unknown,
            ):
                continue
            if not self._session_matches_agent(
                resolved_session.current_session_key,
                agent_id=agent_id,
            ):
                continue
            if not _session_matches_filter_values(
                session=resolved_session,
                metadata=metadata,
                label=label,
                spawned_by=spawned_by,
            ):
                continue
            dedupe_key = (
                canonicalize_session_key(resolved_session.current_session_key)
                or resolved_session.current_session_key.lower()
            )
            if dedupe_key in seen_session_keys:
                continue
            seen_session_keys.add(dedupe_key)
            matched_session_keys.append(resolved_session.current_session_key)
        return matched_session_keys

    async def _session_matches_filters(
        self,
        session: _CurrentControlChatSession,
        *,
        label: str | None,
        spawned_by: str | None,
    ) -> bool:
        if label is None and spawned_by is None:
            return True
        metadata = await self._session_metadata(session.current_session_key)
        return _session_matches_filter_values(
            session=session,
            metadata=metadata,
            label=label,
            spawned_by=spawned_by,
        )

    def _session_matches_visibility(
        self,
        session: _CurrentControlChatSession,
        *,
        include_global: bool,
        include_unknown: bool,
    ) -> bool:
        if not include_global and session.current_session_key == session.main_session_key:
            return False
        if not include_unknown and session.current_session_key == "unknown":
            return False
        return True

    def _session_matches_agent(self, session_key: str, *, agent_id: str | None) -> bool:
        if agent_id is None:
            return True
        parsed_session_key = parse_agent_session_key(session_key)
        if parsed_session_key is None:
            return agent_id == "main"
        return parsed_session_key.agent_id == agent_id

    async def _agent_exists(self, agent_id: str) -> bool:
        if agent_id == "main":
            return True
        return await self._database.get_gateway_agent(agent_id) is not None


def _main_session_key_from_gateway(gateway: dict[str, Any] | None) -> str:
    route_binding_mode = _route_binding_mode(gateway)
    task_id = _int_or_none(gateway.get("task_blueprint_id") if gateway is not None else None)
    project_id = _int_or_none(gateway.get("preferred_project_id") if gateway is not None else None)
    operator_id = _int_or_none(gateway.get("operator_id") if gateway is not None else None)
    return build_launch_session_key(
        mode=route_binding_mode,
        preferred_instance_id=None,
        task_id=task_id,
        project_id=project_id,
        operator_id=operator_id,
    )


def _route_binding_mode(
    gateway: dict[str, Any] | None,
) -> Literal["task_lane", "saved_lane", "workspace_affinity"]:
    if gateway is None:
        return "workspace_affinity"
    route_binding_mode = str(gateway.get("route_binding_mode") or "").strip().lower()
    if route_binding_mode in {"task_lane", "saved_lane", "workspace_affinity"}:
        return cast(Literal["task_lane", "saved_lane", "workspace_affinity"], route_binding_mode)
    setup_mode = str(gateway.get("setup_mode") or "local")
    return "workspace_affinity" if setup_mode == "remote" else "saved_lane"


def _derive_session_title(
    session_payload: dict[str, Any],
    *,
    first_user_message: str | None,
) -> str | None:
    display_name = _normalized_title_value(session_payload.get("displayName"))
    if display_name not in {
        None,
        _CONTROL_CHAT_GLOBAL_DISPLAY_NAME,
        _CONTROL_CHAT_THREAD_DISPLAY_NAME,
    }:
        return display_name

    subject = _normalized_title_value(session_payload.get("subject"))
    if subject not in {None, _CONTROL_CHAT_SUBJECT_FALLBACK}:
        return subject

    if first_user_message is not None:
        return _truncate_title(first_user_message, _DERIVED_TITLE_MAX_LEN)

    session_id = _string_or_none(session_payload.get("sessionId"))
    if session_id is None:
        return None
    return _format_session_id_prefix(
        session_id,
        updated_at_ms=_int_or_none(session_payload.get("updatedAt")),
    )


def _normalized_title_value(value: object) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    return " ".join(text.split())


def _format_session_id_prefix(session_id: str, *, updated_at_ms: int | None) -> str:
    prefix = session_id[:8]
    if updated_at_ms is not None and updated_at_ms > 0:
        updated_at = datetime.fromtimestamp(updated_at_ms / 1000, tz=UTC).date().isoformat()
        return f"{prefix} ({updated_at})"
    return prefix


def _truncate_title(text: str, max_len: int) -> str:
    normalized = _normalized_title_value(text)
    if normalized is None or len(normalized) <= max_len:
        return normalized or ""
    cut = normalized[: max_len - len(_DERIVED_TITLE_ELLIPSIS)]
    last_space = cut.rfind(" ")
    if last_space > max_len * 0.6:
        return cut[:last_space] + _DERIVED_TITLE_ELLIPSIS
    return cut + _DERIVED_TITLE_ELLIPSIS


def _string_or_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _session_lifecycle_int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    number = _int_or_none(value)
    if number is None or number < 0:
        return None
    return number


def _session_run_status_or_none(value: object) -> str | None:
    status = _string_or_none(value)
    if status in _SESSION_RUN_STATUS_VALUES:
        return status
    return None


def _route_thread_id_or_none(value: object) -> int | str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _string_or_none(value)
    return None


def _delivery_context_or_none(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    delivery_context: dict[str, Any] = {}
    for field in ("channel", "to", "accountId"):
        field_value = _string_or_none(value.get(field))
        if field_value is not None:
            delivery_context[field] = field_value
    thread_id = _route_thread_id_or_none(value.get("threadId"))
    if thread_id is not None:
        delivery_context["threadId"] = thread_id
    return delivery_context or None


def _string_dict_or_none(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, str] = {}
    for key, item in value.items():
        key_text = _string_or_none(key)
        item_text = _string_or_none(item)
        if key_text is not None and item_text is not None:
            normalized[key_text] = item_text
    return normalized or None


def _nested_string_dict_or_none(value: object) -> dict[str, dict[str, str]] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, dict[str, str]] = {}
    for key, item in value.items():
        key_text = _string_or_none(key)
        item_value = _string_dict_or_none(item)
        if key_text is not None and item_value:
            normalized[key_text] = item_value
    return normalized or None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) else None


def _bool_or_none(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _normalize_positive_numeric_filter(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return None
    return max(1, math.floor(numeric_value))


def _normalize_session_list_message_limit(value: int | None) -> int:
    if value is None:
        return 0
    return min(max(value, 0), _SESSION_LIST_MESSAGE_LIMIT_MAX)


def _normalized_session_list_kinds(values: tuple[str, ...] | None) -> set[str] | None:
    if not values:
        return None
    normalized = {
        value.strip().lower()
        for value in values
        if value.strip().lower() in _OPENCLAW_SESSION_LIST_KINDS
    }
    return normalized or None


def _session_payload_matches_kinds(
    session_payload: dict[str, Any],
    normalized_kinds: set[str] | None,
) -> bool:
    if normalized_kinds is None:
        return True
    return bool(_session_payload_kind_aliases(session_payload) & normalized_kinds)


def _session_payload_kind_aliases(session_payload: dict[str, Any]) -> set[str]:
    key = _string_or_none(session_payload.get("key")) or ""
    kind = (_string_or_none(session_payload.get("kind")) or "").lower()
    aliases = {kind} if kind else set()
    if kind == "global":
        aliases.add("main")
    if kind == "thread":
        aliases.add("other")
    if key.startswith("cron:"):
        aliases.add("cron")
    if key.startswith("hook:"):
        aliases.add("hook")
    if key.startswith("node-") or key.startswith("node:"):
        aliases.add("node")
    if kind == "group" or ":group:" in key or ":channel:" in key:
        aliases.add("group")
    return aliases


def _message_id_text(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    return _string_or_none(value)


def _message_parent_id(metadata_value: object) -> str | None:
    metadata = _json_object_or_none(metadata_value)
    if metadata is None:
        return None
    return _message_id_text(metadata.get("parentId"))


def _snapshot_sort_key(session_payload: dict[str, Any]) -> tuple[int, str]:
    updated_at = _int_or_none(session_payload.get("updatedAt"))
    return (
        -(updated_at if updated_at is not None else -1),
        _string_or_none(session_payload.get("key")) or "",
    )


def _iso8601_to_timestamp_ms(value: object) -> int | None:
    text = _string_or_none(value)
    if text is None:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def _message_payload(
    *,
    role: str,
    text: str,
    message_id: str | None,
    message_seq: int | None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": role,
        "content": [{"type": "text", "text": text}],
    }
    if message_id is not None:
        payload["id"] = message_id
    if parent_id is not None:
        payload["parentId"] = parent_id
    openclaw_meta: dict[str, str | int] = {}
    if message_id is not None:
        openclaw_meta["id"] = message_id
    if message_seq is not None:
        openclaw_meta["seq"] = message_seq
    if openclaw_meta:
        payload["__openclaw"] = openclaw_meta
    return payload


def _session_message_display_text(text: str) -> str:
    stripped = _TRAILING_UNTRUSTED_CONTEXT_RE.sub("", text)
    if stripped != text:
        text = stripped.rstrip()
    return _SESSION_MESSAGE_INLINE_DIRECTIVE_RE.sub("", text)


def _is_suppressed_assistant_session_message(*, role: str, text: str) -> bool:
    return role == "assistant" and text.strip().upper() in _SESSION_MESSAGE_ASSISTANT_SKIP_TEXTS


def _apply_session_event_metadata(
    payload: dict[str, Any],
    session_payload: dict[str, Any],
) -> None:
    for field in (
        "label",
        "responseUsage",
        "reasoningLevel",
        "elevatedLevel",
        "execHost",
        "execSecurity",
        "execAsk",
        "execNode",
        "fastMode",
        "spawnedBy",
        "spawnedWorkspaceDir",
        "forkedFromParent",
        "spawnDepth",
        "subagentRole",
        "subagentControlScope",
        "sendPolicy",
        "groupActivation",
        "parentSessionKey",
        "lastChannel",
        "lastTo",
        "lastAccountId",
        "lastThreadId",
        "deliveryContext",
        "status",
        "startedAt",
        "endedAt",
        "runtimeMs",
    ):
        if field in session_payload:
            payload[field] = session_payload[field]


def _usage_cost_usd(
    *,
    usage: dict[str, Any] | None,
    cost: dict[str, Any] | None,
) -> float | None:
    estimated_cost = _first_float_value(cost, ("total", "estimatedCostUsd", "usd"))
    if estimated_cost is not None:
        return estimated_cost
    if usage is None:
        return None
    nested_cost = usage.get("cost")
    return _first_float_value(
        nested_cost if isinstance(nested_cost, dict) else None,
        ("total", "estimatedCostUsd", "usd"),
    )


def _context_tokens_for_model(
    *,
    provider: str | None,
    model: str | None,
) -> int | None:
    normalized_provider = str(provider or "").strip().lower()
    normalized_model = str(model or "").strip().lower()
    if normalized_provider == "anthropic" and "claude-sonnet-4" in normalized_model:
        return 1_048_576
    return None


def _apply_live_usage_metadata(
    payload: dict[str, Any],
    message_row: dict[str, Any],
) -> None:
    usage = _json_object_or_none(message_row.get("usage_json"))
    cost = _json_object_or_none(message_row.get("cost_json"))
    if usage is None and cost is None:
        return

    input_tokens = _first_int_value(
        usage,
        ("input", "inputTokens", "prompt", "promptTokens"),
    )
    output_tokens = _first_int_value(
        usage,
        ("output", "outputTokens", "completion", "completionTokens"),
    )
    total_tokens = _first_int_value(usage, ("totalTokens", "total", "total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    estimated_cost = _usage_cost_usd(usage=usage, cost=cost)

    if input_tokens is not None:
        payload["inputTokens"] = input_tokens
    if output_tokens is not None:
        payload["outputTokens"] = output_tokens
    if total_tokens is not None:
        payload["totalTokens"] = total_tokens
        payload["totalTokensFresh"] = True
    if estimated_cost is not None:
        payload["estimatedCostUsd"] = estimated_cost


def _json_object_or_none(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _first_int_value(
    payload: dict[str, Any] | None,
    keys: tuple[str, ...],
) -> int | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and math.isfinite(value):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return None


def _first_float_value(
    payload: dict[str, Any] | None,
    keys: tuple[str, ...],
) -> float | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            number = float(value)
        elif isinstance(value, str):
            try:
                number = float(value)
            except ValueError:
                continue
        else:
            continue
        if math.isfinite(number):
            return number
    return None


def _normalize_lookup_token(value: object) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    return text.lower()


def _parse_session_label(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid label: must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("invalid label: empty")
    if len(trimmed) > _SESSION_LABEL_MAX_LENGTH:
        raise ValueError(f"invalid label: too long (max {_SESSION_LABEL_MAX_LENGTH})")
    return trimmed


def _metadata_matches_spawned_by(
    metadata: dict[str, Any],
    *,
    spawned_by: str | None,
) -> bool:
    if spawned_by is None:
        return True
    latest_owner_session_key = _latest_owner_session_key(metadata)
    if latest_owner_session_key is not None:
        return _session_keys_match(latest_owner_session_key, spawned_by)
    return (
        _session_keys_match(metadata.get("spawnedBy"), spawned_by)
        or _session_keys_match(metadata.get("parentSessionKey"), spawned_by)
    )


def _session_matches_filter_values(
    *,
    session: _CurrentControlChatSession,
    metadata: dict[str, Any],
    label: str | None,
    spawned_by: str | None,
) -> bool:
    if label is not None and _string_or_none(metadata.get("label")) != label:
        return False
    if spawned_by is None:
        return True
    if session.current_session_key == "unknown":
        return False
    if session.current_session_key == session.main_session_key:
        return False
    return _metadata_matches_spawned_by(metadata, spawned_by=spawned_by)


def _canonicalize_owner_session_key(
    value: object,
    *,
    owner_session_key: str | None,
) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered.startswith("agent:"):
        return canonicalize_session_key(text) or lowered
    owner_agent_session = parse_agent_session_key(owner_session_key)
    if owner_agent_session is not None:
        prefixed = f"agent:{owner_agent_session.agent_id}:{text}"
        canonical_prefixed = canonicalize_session_key(prefixed)
        if canonical_prefixed is not None:
            return canonical_prefixed
    return canonicalize_session_key(text) or lowered


def _latest_owner_session_key(
    metadata: dict[str, Any],
    *,
    owner_session_key: str | None = None,
) -> str | None:
    return _canonicalize_owner_session_key(
        metadata.get("controllerSessionKey"),
        owner_session_key=owner_session_key,
    ) or _canonicalize_owner_session_key(
        metadata.get("requesterSessionKey"),
        owner_session_key=owner_session_key,
    )


def _session_child_sessions_or_none(session_payload: dict[str, Any]) -> list[str] | None:
    child_sessions = session_payload.get("childSessions")
    if not isinstance(child_sessions, list):
        return None
    normalized_child_sessions: list[str] = []
    seen_child_sessions: set[str] = set()
    for child_session in child_sessions:
        normalized_child_session = _string_or_none(child_session)
        if normalized_child_session is None or normalized_child_session in seen_child_sessions:
            continue
        seen_child_sessions.add(normalized_child_session)
        normalized_child_sessions.append(normalized_child_session)
    return normalized_child_sessions or None


def _session_key_match_candidates(value: object) -> set[str]:
    text = _string_or_none(value)
    if text is None:
        return set()
    candidates = {
        canonicalize_session_key(text) or text.lower(),
    }
    for alias in session_key_lookup_aliases(text):
        normalized_alias = canonicalize_session_key(alias) or alias.lower()
        candidates.add(normalized_alias)
    if parse_agent_session_key(text) is not None:
        request_key = _string_or_none(to_agent_request_session_key(text))
        if request_key is not None:
            candidates.add(request_key.lower())
    return candidates


def _session_keys_match(left: object, right: object) -> bool:
    left_candidates = _session_key_match_candidates(left)
    if not left_candidates:
        return False
    right_candidates = _session_key_match_candidates(right)
    if not right_candidates:
        return False
    return bool(left_candidates.intersection(right_candidates))


def _default_agent_store_lookup_key(value: object) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"global", "unknown"}:
        return lowered
    return _string_or_none(to_agent_store_session_key(agent_id="main", request_key=text))


def _scoped_agent_store_lookup_key(value: object, *, agent_id: str | None) -> str | None:
    text = _string_or_none(value)
    if text is None or agent_id is None or agent_id == "main":
        return None
    lowered = text.lower()
    if lowered in {"global", "unknown"}:
        return None
    return _string_or_none(to_agent_store_session_key(agent_id=agent_id, request_key=text))


def _session_id_selector_matches(
    *,
    session: _CurrentControlChatSession,
    normalized_session_id: str,
) -> bool:
    if _normalize_lookup_token(session.current_session_id) == normalized_session_id:
        return True
    if any(
        _normalize_lookup_token(alias) == normalized_session_id
        for alias in session_key_lookup_aliases(session.current_session_key)
    ):
        return True
    request_key = to_agent_request_session_key(session.current_session_key)
    return _normalize_lookup_token(request_key) == normalized_session_id


def _build_session_id_match_candidate(
    *,
    session: _CurrentControlChatSession,
    updated_at_ms: int | None,
    normalized_session_id: str,
) -> _SessionIdMatchCandidate:
    raw_session_key = session.current_session_key.strip()
    normalized_session_key = canonicalize_session_key(raw_session_key) or raw_session_key.lower()
    request_session_key = to_agent_request_session_key(raw_session_key) or raw_session_key
    normalized_request_key = request_session_key.strip().lower()
    return _SessionIdMatchCandidate(
        session=session,
        updated_at_ms=updated_at_ms,
        normalized_session_key=normalized_session_key,
        normalized_request_key=normalized_request_key,
        is_canonical_session_key=raw_session_key == normalized_session_key,
        is_structural=(
            normalized_session_key.endswith(f":{normalized_session_id}")
            or normalized_request_key == normalized_session_id
            or normalized_request_key.endswith(f":{normalized_session_id}")
        ),
    )


def _collapse_session_id_alias_matches(
    matches: list[_SessionIdMatchCandidate],
) -> list[_SessionIdMatchCandidate]:
    grouped: dict[str, list[_SessionIdMatchCandidate]] = {}
    for match in matches:
        grouped.setdefault(match.normalized_request_key, []).append(match)
    collapsed: list[_SessionIdMatchCandidate] = []
    for group in grouped.values():
        if len(group) == 1:
            collapsed.append(group[0])
            continue
        collapsed.append(
            sorted(
                group,
                key=lambda match: (
                    -_updated_at_sort_value(match.updated_at_ms),
                    0 if match.is_canonical_session_key else 1,
                    match.normalized_session_key,
                ),
            )[0]
        )
    return collapsed


def _select_unique_freshest_session_id_match(
    matches: list[_SessionIdMatchCandidate],
) -> _SessionIdMatchCandidate | None:
    if len(matches) == 1:
        return matches[0]
    sorted_matches = sorted(
        matches,
        key=lambda match: -_updated_at_sort_value(match.updated_at_ms),
    )
    freshest = sorted_matches[0]
    second_freshest = sorted_matches[1]
    if _updated_at_sort_value(freshest.updated_at_ms) > _updated_at_sort_value(
        second_freshest.updated_at_ms
    ):
        return freshest
    return None


def _updated_at_sort_value(value: int | None) -> int:
    return value if value is not None else 0


def _resolved_stored_session_scope(
    session_key: str,
    *,
    fallback_main_session_key: str,
) -> tuple[str, str | None]:
    parsed_session_key = parse_thread_session_suffix(session_key)
    parsed_thread_id = _string_or_none(parsed_session_key.thread_id)
    if parsed_thread_id is None:
        return fallback_main_session_key, None
    return (
        _string_or_none(parsed_session_key.base_session_key) or fallback_main_session_key,
        parsed_thread_id,
    )
