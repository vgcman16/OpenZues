from __future__ import annotations

import math
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
    ) -> dict[str, Any]:
        normalized_label = (
            _parse_session_label(label) if _string_or_none(label) is not None else None
        )
        normalized_limit = _normalize_positive_numeric_filter(limit)
        normalized_active_minutes = _normalize_positive_numeric_filter(active_minutes)
        normalized_spawned_by = _string_or_none(spawned_by)
        normalized_agent_id = _normalize_lookup_token(agent_id)
        normalized_search = _string_or_none(search)
        if normalized_agent_id is not None and normalized_agent_id != "main":
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
                resolved_session.current_session_key,
                label=normalized_label,
                spawned_by=normalized_spawned_by,
            ):
                return
            sessions.append(
                await self._snapshot_session_payload(
                    session=resolved_session,
                    include_derived_titles=include_derived_titles,
                    include_last_message=include_last_message,
                    now_ms=now_ms,
                )
            )

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
            "responseUsage",
            "reasoningLevel",
            "elevatedLevel",
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
        ):
            value = _string_or_none(session_payload.get(field))
            if value is not None:
                payload[field] = value
        fast_mode = _bool_or_none(session_payload.get("fastMode"))
        if fast_mode is not None:
            payload["fastMode"] = fast_mode
        spawn_depth = _int_or_none(session_payload.get("spawnDepth"))
        if spawn_depth is not None:
            payload["spawnDepth"] = spawn_depth
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

        session = await self._session_for_message(message_row)
        session_payload = await self._session_payload(session=session, now_ms=now_ms)
        message_id = _string_or_none(message_row.get("id"))
        message_seq = await self._message_sequence(message_row)
        payload: dict[str, Any] = {
            "sessionKey": session.current_session_key,
            "message": _message_payload(
                role=role,
                text=str(message_row.get("content") or ""),
                message_id=message_id,
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
        if normalized_agent_id is not None and normalized_agent_id != "main":
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
            session.current_session_key,
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
        model_override = _string_or_none(metadata.get("model"))
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
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai" if (model_override or session.model) else None,
            "model": model_override or session.model,
            "contextTokens": None,
        }
        fast_mode = _bool_or_none(metadata.get("fastMode"))
        if fast_mode is not None:
            payload["fastMode"] = fast_mode
        if latest_owner_session_key is not None:
            payload["spawnedBy"] = latest_owner_session_key
            payload["parentSessionKey"] = latest_owner_session_key
        for field in (
            "label",
            "responseUsage",
            "reasoningLevel",
            "elevatedLevel",
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
                resolved_session.current_session_key,
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
            if not _metadata_matches_spawned_by(metadata, spawned_by=spawned_by):
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
        session_key: str,
        *,
        label: str | None,
        spawned_by: str | None,
    ) -> bool:
        if label is None and spawned_by is None:
            return True
        metadata = await self._session_metadata(session_key)
        if label is not None and _string_or_none(metadata.get("label")) != label:
            return False
        if not _metadata_matches_spawned_by(metadata, spawned_by=spawned_by):
            return False
        return True

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
            return False
        return parsed_session_key.agent_id == agent_id


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
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": role,
        "content": [{"type": "text", "text": text}],
    }
    if message_id is not None:
        payload["id"] = message_id
    return payload


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
