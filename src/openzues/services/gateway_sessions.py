from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, cast

from openzues.database import Database
from openzues.services.session_keys import build_launch_session_key

_CONTROL_CHAT_PATH = "/api/control-chat"
_DEFAULT_MODEL = "gpt-5.4"


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
        model = (
            _string_or_none(current_mission.get("model") if current_mission is not None else None)
            or _string_or_none(gateway.get("model") if gateway is not None else None)
            or _DEFAULT_MODEL
        )
        is_global_session = current_session_key == main_session_key
        updated_at_ms = await self._updated_at_ms(current_mission=current_mission, now_ms=now_ms)

        sessions: list[dict[str, Any]] = []
        if include_global or not is_global_session:
            sessions.append(
                {
                    "key": current_session_key,
                    "kind": "global" if is_global_session else "thread",
                    "displayName": (
                        "OpenZues Control Chat"
                        if is_global_session
                        else "OpenZues Control Chat Thread"
                    ),
                    "surface": "control-chat",
                    "subject": (
                        _string_or_none(current_mission.get("objective"))
                        if current_mission is not None
                        else None
                    )
                    or "Operator control chat",
                    "room": None,
                    "space": None,
                    "updatedAt": updated_at_ms,
                    "sessionId": (
                        _string_or_none(current_mission.get("thread_id"))
                        if current_mission is not None
                        else None
                    ),
                    "systemSent": None,
                    "abortedLastRun": None,
                    "thinkingLevel": None,
                    "verboseLevel": None,
                    "inputTokens": None,
                    "outputTokens": None,
                    "totalTokens": None,
                    "modelProvider": "openai" if model else None,
                    "model": model,
                    "contextTokens": None,
                }
            )

        if limit is not None:
            sessions = sessions[:limit]

        return {
            "ts": now_ms,
            "path": _CONTROL_CHAT_PATH,
            "count": len(sessions),
            "defaults": {
                "model": model,
                "contextTokens": None,
                "mainSessionKey": main_session_key,
            },
            "sessions": sessions,
        }

    async def _updated_at_ms(
        self,
        *,
        current_mission: dict[str, Any] | None,
        now_ms: int,
    ) -> int:
        updated_at_ms = _iso8601_to_timestamp_ms(
            current_mission.get("updated_at") if current_mission is not None else None
        )
        if updated_at_ms is not None:
            return updated_at_ms

        latest_messages = await self._database.list_control_chat_messages(limit=1)
        if latest_messages:
            message_updated_at_ms = _iso8601_to_timestamp_ms(latest_messages[-1].get("created_at"))
            if message_updated_at_ms is not None:
                return message_updated_at_ms
        return now_ms


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
