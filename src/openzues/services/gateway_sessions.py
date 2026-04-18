from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

from openzues.database import Database
from openzues.services.session_keys import (
    build_launch_session_key,
    canonicalize_session_key,
    parse_thread_session_suffix,
)

_CONTROL_CHAT_PATH = "/api/control-chat"
_DEFAULT_MODEL = "gpt-5.4"


@dataclass(frozen=True, slots=True)
class _CurrentControlChatSession:
    main_session_key: str
    current_session_key: str
    current_session_id: str | None
    current_mission: dict[str, Any] | None
    model: str


class GatewaySessionsService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def build_snapshot(
        self,
        *,
        include_global: bool,
        include_unknown: bool,
        limit: int | None,
        now_ms: int,
    ) -> dict[str, Any]:
        del include_unknown

        sessions: list[dict[str, Any]] = []
        session = await self._current_control_chat_session()
        current_session_canonical = canonicalize_session_key(session.current_session_key)
        is_global_session = session.current_session_key == session.main_session_key
        current_session_payload = await self._session_payload(
            session=session,
            now_ms=now_ms,
        )
        if include_global or not is_global_session:
            sessions.append(current_session_payload)

        seen_session_keys = {
            current_session_canonical
            if current_session_canonical is not None
            else session.current_session_key.lower()
        }
        metadata_rows = await self._database.list_gateway_session_metadata_rows()
        for row in metadata_rows:
            session_key = _string_or_none(row.get("session_key"))
            if session_key is None:
                continue
            canonical_key = canonicalize_session_key(session_key) or session_key.lower()
            if canonical_key in seen_session_keys:
                continue
            known_session = await self._session_for_key(session_key, default_session=session)
            if (
                not include_global
                and known_session.current_session_key == known_session.main_session_key
            ):
                continue
            sessions.append(await self._session_payload(session=known_session, now_ms=now_ms))
            seen_session_keys.add(canonical_key)
            if limit is not None and len(sessions) >= limit:
                break

        if limit is not None:
            sessions = sessions[:limit]

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
            "inputTokens": session_payload["inputTokens"],
            "outputTokens": session_payload["outputTokens"],
            "totalTokens": session_payload["totalTokens"],
            "contextTokens": session_payload["contextTokens"],
            "modelProvider": session_payload["modelProvider"],
            "model": session_payload["model"],
            "space": session_payload["space"],
        }
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
            "inputTokens": session_payload["inputTokens"],
            "outputTokens": session_payload["outputTokens"],
            "totalTokens": session_payload["totalTokens"],
            "contextTokens": session_payload["contextTokens"],
            "modelProvider": session_payload["modelProvider"],
            "model": session_payload["model"],
            "space": session_payload["space"],
        }
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
        del include_global, include_unknown

        session = await self._current_control_chat_session()
        if label is not None or spawned_by is not None:
            matched_session_key = await self._metadata_lookup_session_key(
                label=label,
                spawned_by=spawned_by,
            )
            if matched_session_key is None:
                if label is not None:
                    raise ValueError("unknown session label")
                raise ValueError("unknown spawnedBy")
            session = await self._session_for_key(matched_session_key, default_session=session)
        if agent_id is not None and agent_id != "main":
            raise ValueError(f'unknown agent id "{agent_id}"')
        if key is not None:
            matched_session = await self._known_session_for_lookup(key, default_session=session)
            if matched_session is None:
                raise ValueError("unknown session key")
            session = matched_session
        if session_id is not None and session_id != session.current_session_id:
            raise ValueError("unknown sessionId")

        return {"ok": True, "key": session.current_session_key}

    async def _session_payload(
        self,
        *,
        session: _CurrentControlChatSession,
        now_ms: int,
    ) -> dict[str, Any]:
        is_global_session = session.current_session_key == session.main_session_key
        metadata = await self._session_metadata(session.current_session_key)
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
                "OpenZues Control Chat" if is_global_session else "OpenZues Control Chat Thread"
            ),
            "surface": "control-chat",
            "subject": (
                _string_or_none(session.current_mission.get("objective"))
                if session.current_mission is not None
                else None
            )
            or "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": updated_at_ms,
            "sessionId": session.current_session_id,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": _string_or_none(metadata.get("thinkingLevel")),
            "verboseLevel": _string_or_none(metadata.get("verboseLevel")),
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
            value = _string_or_none(metadata.get(field))
            if value is not None:
                payload[field] = value
        spawn_depth = _int_or_none(metadata.get("spawnDepth"))
        if spawn_depth is not None:
            payload["spawnDepth"] = spawn_depth
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
            parsed_session_key = parse_thread_session_suffix(stored_session_key)
            return _CurrentControlChatSession(
                main_session_key=_string_or_none(parsed_session_key.base_session_key)
                or session.main_session_key,
                current_session_key=stored_session_key,
                current_session_id=_string_or_none(mission.get("thread_id") if mission else None)
                or _string_or_none(parsed_session_key.thread_id),
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
        parsed_session_key = parse_thread_session_suffix(session_key)
        return _CurrentControlChatSession(
            main_session_key=_string_or_none(parsed_session_key.base_session_key)
            or default_session.main_session_key,
            current_session_key=session_key,
            current_session_id=_string_or_none(mission.get("thread_id") if mission else None)
            or _string_or_none(parsed_session_key.thread_id),
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

    async def _metadata_lookup_session_key(
        self,
        *,
        label: str | None,
        spawned_by: str | None,
    ) -> str | None:
        rows = await self._database.list_gateway_session_metadata_rows()
        for row in rows:
            session_key = _string_or_none(row.get("session_key"))
            metadata = row.get("metadata")
            if session_key is None or not isinstance(metadata, dict):
                continue
            if label is not None and _string_or_none(metadata.get("label")) != label:
                continue
            if spawned_by is not None and _string_or_none(metadata.get("spawnedBy")) != spawned_by:
                continue
            return session_key
        return None


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
