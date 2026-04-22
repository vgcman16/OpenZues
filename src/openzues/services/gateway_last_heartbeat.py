from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from openzues.database import Database
from openzues.services.gateway_node_registry import GatewayNodeRegistry

_RAW_HEARTBEAT_STRING_FIELDS = (
    "to",
    "accountId",
    "preview",
    "reason",
    "channel",
)
_RAW_HEARTBEAT_TOP_LEVEL_FIELDS = frozenset(
    (
        "ts",
        "status",
        "to",
        "accountId",
        "preview",
        "durationMs",
        "hasMedia",
        "reason",
        "channel",
        "silent",
        "indicatorType",
    )
)
_RAW_HEARTBEAT_RESERVED_FIELDS = frozenset(("nodeId", "payload", "payloadJSON"))


class GatewayLastHeartbeatService:
    def __init__(
        self,
        database: Database,
        *,
        registry: GatewayNodeRegistry,
    ) -> None:
        self._database = database
        self._registry = registry

    async def build_snapshot(self) -> dict[str, Any]:
        event = await self._database.get_latest_node_event(event_name="heartbeat")
        if event is None:
            return {"heartbeat": None}
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return {"heartbeat": None}
        heartbeat_payload = payload.get("payload")
        payload_json = payload.get("payloadJSON")
        if heartbeat_payload is None and isinstance(payload_json, str):
            try:
                heartbeat_payload = json.loads(payload_json)
            except json.JSONDecodeError:
                heartbeat_payload = None
        if heartbeat_payload is None:
            heartbeat_payload = _extract_flat_heartbeat_payload(payload)
        if payload_json is None and heartbeat_payload is not None:
            payload_json = json.dumps(heartbeat_payload)
        node_id = str(payload.get("nodeId") or "").strip()
        heartbeat: dict[str, Any] = {
            "nodeId": node_id,
            "event": "heartbeat",
            "payload": heartbeat_payload,
            "payloadJSON": payload_json,
            "createdAt": event.get("created_at"),
        }
        _promote_openclaw_heartbeat_fields(
            heartbeat,
            heartbeat_payload,
            created_at=event.get("created_at"),
        )
        known_node = self._registry.describe_known_node(node_id) if node_id else None
        if known_node is not None:
            if known_node.display_name:
                heartbeat["displayName"] = known_node.display_name
            if known_node.platform:
                heartbeat["platform"] = known_node.platform
        return {"heartbeat": heartbeat}


def _promote_openclaw_heartbeat_fields(
    heartbeat: dict[str, Any],
    raw_payload: object,
    *,
    created_at: object,
) -> None:
    if not isinstance(raw_payload, dict):
        return

    promoted = False
    if (ts := _optional_number(raw_payload.get("ts"))) is not None:
        heartbeat["ts"] = ts
        promoted = True

    status = _optional_non_empty_string(raw_payload.get("status"))
    if status is not None:
        heartbeat["status"] = status
        promoted = True

    if (duration_ms := _optional_number(raw_payload.get("durationMs"))) is not None:
        heartbeat["durationMs"] = duration_ms
        promoted = True

    for field in _RAW_HEARTBEAT_STRING_FIELDS:
        if (value := _optional_non_empty_string(raw_payload.get(field))) is not None:
            heartbeat[field] = value
            promoted = True

    for field in ("hasMedia", "silent"):
        value = raw_payload.get(field)
        if isinstance(value, bool):
            heartbeat[field] = value
            promoted = True

    indicator_type = _optional_non_empty_string(raw_payload.get("indicatorType"))
    if indicator_type is None and status is not None:
        indicator_type = _resolve_indicator_type(status)
    if indicator_type is not None:
        heartbeat["indicatorType"] = indicator_type
        promoted = True

    if promoted and "ts" not in heartbeat:
        if (derived_ts := _timestamp_ms_from_isoformat(created_at)) is not None:
            heartbeat["ts"] = derived_ts


def _extract_flat_heartbeat_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not any(field in payload for field in _RAW_HEARTBEAT_TOP_LEVEL_FIELDS):
        return None
    flattened = {
        key: value
        for key, value in payload.items()
        if key not in _RAW_HEARTBEAT_RESERVED_FIELDS
    }
    return flattened or None


def _optional_non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _optional_number(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    return None


def _timestamp_ms_from_isoformat(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _resolve_indicator_type(status: str) -> str | None:
    normalized = status.strip().lower()
    if normalized in {"ok-empty", "ok-token"}:
        return "ok"
    if normalized == "sent":
        return "alert"
    if normalized == "failed":
        return "error"
    return None
