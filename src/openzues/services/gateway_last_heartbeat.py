from __future__ import annotations

import json
from typing import Any

from openzues.database import Database
from openzues.services.gateway_node_registry import GatewayNodeRegistry


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
        known_node = self._registry.describe_known_node(node_id) if node_id else None
        if known_node is not None:
            if known_node.display_name:
                heartbeat["displayName"] = known_node.display_name
            if known_node.platform:
                heartbeat["platform"] = known_node.platform
        return {"heartbeat": heartbeat}
