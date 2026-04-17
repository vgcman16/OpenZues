from __future__ import annotations

from typing import Any

from openzues.services.gateway_identity import GatewayIdentityService
from openzues.services.gateway_node_registry import GatewayNodeRegistry, KnownNode

_NODE_CLIENT_MODES = {"mobile"}
_NODE_PLATFORMS = {"android", "ios", "ipados", "watchos"}


class GatewaySystemPresenceService:
    def __init__(
        self,
        registry: GatewayNodeRegistry,
        *,
        gateway_identity_service: GatewayIdentityService,
    ) -> None:
        self._registry = registry
        self._gateway_identity_service = gateway_identity_service

    def build_snapshot(self, *, now_ms: int) -> dict[str, Any]:
        identity = self._gateway_identity_service.load()
        entries: list[dict[str, Any]] = [
            {
                "deviceId": identity.id,
                "instanceId": identity.id,
                "mode": "backend",
                "reason": "self",
                "roles": ["operator"],
                "scopes": [],
                "tags": ["gateway", "self"],
                "ts": now_ms,
            }
        ]
        for node in self._registry.list_known_nodes():
            if not node.connected:
                continue
            entries.append(_presence_entry(node))
        return {
            "entries": sorted(entries, key=_presence_entry_sort_key),
        }


def _presence_entry(node: KnownNode) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "deviceId": node.node_id,
        "instanceId": node.client_id or node.node_id,
        "mode": _presence_mode(node),
        "reason": _presence_reason(node),
        "roles": _presence_roles(node),
        "scopes": [],
        "ts": node.connected_at_ms or 0,
    }
    if node.display_name:
        entry["host"] = node.display_name
    if node.platform:
        entry["platform"] = node.platform
    if entry["mode"] == "node":
        if node.remote_ip:
            entry["ip"] = node.remote_ip
        if node.version:
            entry["version"] = node.version
        if node.device_family:
            entry["deviceFamily"] = node.device_family
        if node.model_identifier:
            entry["modelIdentifier"] = node.model_identifier
    return entry


def _presence_mode(node: KnownNode) -> str:
    client_mode = str(node.client_mode or "").strip().lower()
    platform = str(node.platform or "").strip().lower()
    if client_mode in _NODE_CLIENT_MODES:
        return "node"
    if platform in _NODE_PLATFORMS:
        return "node"
    if node.device_family or node.model_identifier:
        return "node"
    return "backend"


def _presence_reason(node: KnownNode) -> str:
    if _presence_mode(node) == "node":
        return "node-connected"
    return "connect"


def _presence_roles(node: KnownNode) -> list[str]:
    if _presence_mode(node) == "node":
        return ["node"]
    return ["operator"]


def _presence_entry_sort_key(entry: dict[str, Any]) -> tuple[int, str, str]:
    if entry.get("reason") == "self":
        return (0, "", str(entry.get("deviceId") or ""))
    host = str(entry.get("host") or entry.get("deviceId") or "").strip().lower()
    return (1, host, str(entry.get("deviceId") or ""))
