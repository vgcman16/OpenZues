from __future__ import annotations

import os
import platform
import socket
import sys
import tomllib
from functools import lru_cache
from pathlib import Path
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
        entries: list[dict[str, Any]] = [_self_presence_entry(identity.id, now_ms=now_ms)]
        for node in self._registry.list_known_nodes():
            if not node.connected:
                continue
            entries.append(_presence_entry(node))
        return {
            "entries": sorted(entries, key=_presence_entry_sort_key),
        }


def _self_presence_entry(device_id: str, *, now_ms: int) -> dict[str, Any]:
    host = _self_host()
    ip = _self_ip(host)
    version = _package_version()
    platform_value = _self_platform()
    device_family = _self_device_family()
    model_identifier = _self_model_identifier()
    entry: dict[str, Any] = {
        "deviceId": device_id,
        "instanceId": device_id,
        "mode": "backend",
        "reason": "self",
        "roles": ["operator"],
        "scopes": [],
        "tags": ["gateway", "self"],
        "ts": now_ms,
    }
    if host is not None:
        entry["host"] = host
    if ip is not None:
        entry["ip"] = ip
    if version is not None:
        entry["version"] = version
    if platform_value is not None:
        entry["platform"] = platform_value
    if device_family is not None:
        entry["deviceFamily"] = device_family
    if model_identifier is not None:
        entry["modelIdentifier"] = model_identifier
    text = _self_presence_text(
        host=host,
        ip=ip,
        version=version,
        mode=str(entry["mode"]),
        reason=str(entry["reason"]),
    )
    if text is not None:
        entry["text"] = text
    return entry


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


def _self_host() -> str | None:
    host = socket.gethostname().strip()
    return host or None


def _self_ip(host: str | None) -> str | None:
    lookup_host = host or _self_host()
    if lookup_host is None:
        return None
    try:
        addresses = socket.getaddrinfo(
            lookup_host,
            None,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return lookup_host
    for _, _, _, _, sockaddr in addresses:
        address = str(sockaddr[0]).strip()
        if address and not address.startswith("127."):
            return address
    return lookup_host


@lru_cache(maxsize=1)
def _package_version() -> str | None:
    resolved = _first_non_empty_string(
        os.environ.get("OPENZUES_VERSION"),
        _runtime_package_version(),
        os.environ.get("OPENZUES_SERVICE_VERSION"),
        os.environ.get("npm_package_version"),
    )
    if resolved is not None:
        return resolved

    from importlib import metadata

    try:
        version = metadata.version("openzues").strip()
        if version:
            return version
    except metadata.PackageNotFoundError:
        pass

    pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = pyproject.get("project")
    if not isinstance(project, dict):
        return None
    version = str(project.get("version") or "").strip()
    return version or None


def _runtime_package_version() -> str | None:
    from openzues import __version__

    return _first_non_empty_string(__version__)


def _first_non_empty_string(*values: object) -> str | None:
    for value in values:
        if not isinstance(value, str):
            continue
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


def _self_platform() -> str | None:
    release = platform.release().strip()
    if sys.platform == "darwin":
        mac_version = platform.mac_ver()[0].strip() or release
        return f"macos {mac_version}".strip()
    if sys.platform.startswith("win"):
        return f"windows {release}".strip()
    return f"{sys.platform} {release}".strip()


def _self_device_family() -> str | None:
    if sys.platform == "darwin":
        return "Mac"
    if sys.platform.startswith("win"):
        return "Windows"
    if sys.platform.startswith("linux"):
        return "Linux"
    platform_name = sys.platform.strip()
    return platform_name or None


def _self_model_identifier() -> str | None:
    identifier = platform.machine().strip()
    return identifier or None


def _self_presence_text(
    *,
    host: str | None,
    ip: str | None,
    version: str | None,
    mode: str,
    reason: str,
) -> str | None:
    host_label = host or None
    if host_label is None:
        return None
    subject = f"Gateway: {host_label}"
    if ip:
        subject = f"{subject} ({ip})"
    parts = [subject]
    if version:
        parts.append(f"app {version}")
    parts.append(f"mode {mode}")
    parts.append(f"reason {reason}")
    return " \u00b7 ".join(parts)
