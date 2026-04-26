from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import uuid4

if TYPE_CHECKING:
    from openzues.database import Database

_NODE_SYSTEM_RUN_COMMANDS = ("system.run.prepare", "system.run")
# Keep these literals local so pairing tests can import this module without
# pulling the schema-heavy gateway method policy dependency tree at runtime.
PAIRING_GATEWAY_METHOD_SCOPE = "operator.pairing"
WRITE_GATEWAY_METHOD_SCOPE = "operator.write"
ADMIN_GATEWAY_METHOD_SCOPE = "operator.admin"


@dataclass(frozen=True, slots=True)
class GatewayNodePairingRequest:
    request_id: str
    node_id: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    remote_ip: str | None = None
    silent: bool | None = None
    ts: int = 0


@dataclass(frozen=True, slots=True)
class GatewayPairedNode:
    node_id: str
    token: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    permissions: dict[str, bool] | None = None
    remote_ip: str | None = None
    created_at_ms: int = 0
    approved_at_ms: int = 0
    last_connected_at_ms: int | None = None


@dataclass(frozen=True, slots=True)
class GatewayDeviceAuthToken:
    device_id: str
    role: str
    token: str
    scopes: tuple[str, ...] = ()
    created_at_ms: int = 0
    rotated_at_ms: int | None = None
    revoked_at_ms: int | None = None
    last_used_at_ms: int | None = None


class GatewayNodePairingService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def request(
        self,
        *,
        node_id: str,
        display_name: str | None,
        platform: str | None,
        version: str | None,
        core_version: str | None,
        ui_version: str | None,
        device_family: str | None,
        model_identifier: str | None,
        caps: list[str] | None,
        commands: list[str] | None,
        remote_ip: str | None,
        silent: bool | None,
        now_ms: int,
    ) -> dict[str, object]:
        existing = await self.database.list_gateway_node_pairing_requests()
        existing_row = next((row for row in existing if row["node_id"] == node_id), None)
        existing_request = (
            _request_from_row(existing_row) if existing_row is not None else None
        )
        persisted_silent: bool | None
        if existing_request is None:
            persisted_silent = True if silent is True else None
            resolved_display_name = display_name
            resolved_platform = platform
            resolved_version = version
            resolved_core_version = core_version
            resolved_ui_version = ui_version
            resolved_device_family = device_family
            resolved_model_identifier = model_identifier
            resolved_caps = _string_list(caps)
            resolved_commands = _string_list(commands)
            resolved_remote_ip = remote_ip
        else:
            persisted_silent = bool(existing_request.silent) and bool(silent)
            resolved_display_name = (
                display_name if display_name is not None else existing_request.display_name
            )
            resolved_platform = platform if platform is not None else existing_request.platform
            resolved_version = version if version is not None else existing_request.version
            resolved_core_version = (
                core_version if core_version is not None else existing_request.core_version
            )
            resolved_ui_version = (
                ui_version if ui_version is not None else existing_request.ui_version
            )
            resolved_device_family = (
                device_family
                if device_family is not None
                else existing_request.device_family
            )
            resolved_model_identifier = (
                model_identifier
                if model_identifier is not None
                else existing_request.model_identifier
            )
            resolved_caps = (
                _string_list(caps) if caps is not None else list(existing_request.caps)
            )
            resolved_commands = (
                _string_list(commands)
                if commands is not None
                else list(existing_request.commands)
            )
            resolved_remote_ip = (
                remote_ip if remote_ip is not None else existing_request.remote_ip
            )
            if silent is None:
                persisted_silent = existing_request.silent
            elif silent:
                persisted_silent = True
            else:
                persisted_silent = None

        row, created = await self.database.upsert_gateway_node_pairing_request(
            request_id=str(uuid4()),
            node_id=node_id,
            display_name=resolved_display_name,
            platform=resolved_platform,
            version=resolved_version,
            core_version=resolved_core_version,
            ui_version=resolved_ui_version,
            device_family=resolved_device_family,
            model_identifier=resolved_model_identifier,
            caps=resolved_caps,
            commands=resolved_commands,
            remote_ip=resolved_remote_ip,
            silent=persisted_silent,
            requested_at_ms=now_ms,
        )
        request = _request_from_row(row)
        return {
            "status": "pending",
            "request": _request_payload(request),
            "created": created,
        }

    async def list_pending(self) -> list[dict[str, object]]:
        rows = await self.database.list_gateway_node_pairing_requests()
        return [_pending_payload(_request_from_row(row)) for row in rows]

    async def reject(self, request_id: str) -> dict[str, str] | None:
        row = await self.database.delete_gateway_node_pairing_request(request_id)
        if row is None:
            return None
        request = _request_from_row(row)
        return {
            "requestId": request.request_id,
            "nodeId": request.node_id,
        }

    async def list_paired(self) -> list[dict[str, object]]:
        rows = await self.database.list_gateway_node_paired_nodes()
        return [_paired_list_payload(_paired_node_from_row(row)) for row in rows]

    async def list_paired_nodes(self) -> list[GatewayPairedNode]:
        rows = await self.database.list_gateway_node_paired_nodes()
        return [_paired_node_from_row(row) for row in rows]

    async def get_paired_node(self, node_id: str) -> GatewayPairedNode | None:
        row = await self.database.get_gateway_node_paired_node(node_id)
        return _paired_node_from_row(row) if row is not None else None

    async def update_paired_node_metadata(
        self,
        node_id: str,
        *,
        display_name: str | None = None,
        platform: str | None = None,
        version: str | None = None,
        core_version: str | None = None,
        ui_version: str | None = None,
        device_family: str | None = None,
        model_identifier: str | None = None,
        caps: list[str] | None = None,
        commands: list[str] | None = None,
        permissions: dict[str, bool] | None = None,
        remote_ip: str | None = None,
        last_connected_at_ms: int | None = None,
    ) -> GatewayPairedNode | None:
        existing_row = await self.database.get_gateway_node_paired_node(node_id)
        if existing_row is None:
            return None
        existing = _paired_node_from_row(existing_row)
        resolved_display_name = (
            display_name if display_name is not None else existing.display_name
        )
        resolved_platform = platform if platform is not None else existing.platform
        resolved_version = version if version is not None else existing.version
        resolved_core_version = (
            core_version if core_version is not None else existing.core_version
        )
        resolved_ui_version = ui_version if ui_version is not None else existing.ui_version
        resolved_device_family = (
            device_family if device_family is not None else existing.device_family
        )
        resolved_model_identifier = (
            model_identifier if model_identifier is not None else existing.model_identifier
        )
        resolved_caps = _string_list(caps) if caps is not None else list(existing.caps)
        resolved_commands = (
            _string_list(commands) if commands is not None else list(existing.commands)
        )
        resolved_permissions = permissions if permissions is not None else existing.permissions
        resolved_remote_ip = remote_ip if remote_ip is not None else existing.remote_ip
        resolved_last_connected_at_ms = (
            last_connected_at_ms
            if last_connected_at_ms is not None
            else existing.last_connected_at_ms
        )
        if (
            resolved_display_name == existing.display_name
            and resolved_platform == existing.platform
            and resolved_version == existing.version
            and resolved_core_version == existing.core_version
            and resolved_ui_version == existing.ui_version
            and resolved_device_family == existing.device_family
            and resolved_model_identifier == existing.model_identifier
            and resolved_caps == list(existing.caps)
            and resolved_commands == list(existing.commands)
            and resolved_permissions == existing.permissions
            and resolved_remote_ip == existing.remote_ip
            and resolved_last_connected_at_ms == existing.last_connected_at_ms
        ):
            return existing
        updated_row = await self.database.upsert_gateway_node_paired_node(
            node_id=existing.node_id,
            token=existing.token,
            display_name=resolved_display_name,
            platform=resolved_platform,
            version=resolved_version,
            core_version=resolved_core_version,
            ui_version=resolved_ui_version,
            device_family=resolved_device_family,
            model_identifier=resolved_model_identifier,
            caps=resolved_caps,
            commands=resolved_commands,
            permissions=resolved_permissions,
            remote_ip=resolved_remote_ip,
            created_at_ms=existing.created_at_ms,
            approved_at_ms=existing.approved_at_ms,
            last_connected_at_ms=resolved_last_connected_at_ms,
        )
        return _paired_node_from_row(updated_row)

    async def approve(
        self,
        request_id: str,
        *,
        caller_scopes: tuple[str, ...] | None,
        now_ms: int,
    ) -> dict[str, object] | dict[str, str] | None:
        request_row = await self.database.get_gateway_node_pairing_request(request_id)
        if request_row is None:
            return None
        request = _request_from_row(request_row)
        missing_scope = _missing_scope(
            required_scopes=_required_approve_scopes(request.commands),
            caller_scopes=caller_scopes,
        )
        if missing_scope is not None:
            forbidden: dict[str, object] = {
                "status": "forbidden",
                "missingScope": missing_scope,
            }
            return forbidden
        existing = await self.database.get_gateway_node_paired_node(request.node_id)
        created_at_ms = (
            cast(int, existing["created_at_ms"]) if existing is not None else now_ms
        )
        paired_row = await self.database.upsert_gateway_node_paired_node(
            node_id=request.node_id,
            token=secrets.token_urlsafe(32),
            display_name=request.display_name,
            platform=request.platform,
            version=request.version,
            core_version=request.core_version,
            ui_version=request.ui_version,
            device_family=request.device_family,
            model_identifier=request.model_identifier,
            caps=list(request.caps),
            commands=list(request.commands),
            permissions=None,
            remote_ip=request.remote_ip,
            created_at_ms=created_at_ms,
            approved_at_ms=now_ms,
            last_connected_at_ms=None,
        )
        await self.database.delete_gateway_node_pairing_request(request_id)
        paired = _paired_node_from_row(paired_row)
        approved_result: dict[str, object] = {
            "requestId": request_id,
            "node": _paired_detail_payload(paired),
        }
        return approved_result

    async def verify(self, node_id: str, token: str) -> dict[str, object]:
        paired_row = await self.database.get_gateway_node_paired_node(node_id)
        if paired_row is None:
            return {"ok": False}
        paired = _paired_node_from_row(paired_row)
        if not token.strip() or not paired.token.strip():
            return {"ok": False}
        if not hmac.compare_digest(token, paired.token):
            return {"ok": False}
        return {
            "ok": True,
            "node": _paired_detail_payload(paired),
        }

    async def remove(self, node_id: str) -> dict[str, str] | None:
        paired_row = await self.database.delete_gateway_node_paired_node(node_id)
        if paired_row is None:
            return None
        paired = _paired_node_from_row(paired_row)
        return {"deviceId": paired.node_id}

    async def list_device_token_summaries(self, device_id: str) -> list[dict[str, object]]:
        normalized_device_id = _normalize_device_id(device_id)
        if normalized_device_id is None:
            return []
        rows = await self.database.list_gateway_node_device_tokens(normalized_device_id)
        return [_device_token_summary_payload(_device_token_from_row(row)) for row in rows]

    async def rotate_device_token(
        self,
        *,
        device_id: str,
        role: str,
        scopes: list[str] | None,
        now_ms: int,
    ) -> GatewayDeviceAuthToken | None:
        normalized_device_id = _normalize_device_id(device_id)
        normalized_role = _normalize_role(role)
        if normalized_device_id is None or normalized_role is None:
            return None
        paired_node = await self.database.get_gateway_node_paired_node(normalized_device_id)
        if paired_node is None:
            return None
        existing_row = await self.database.get_gateway_node_device_token(
            normalized_device_id,
            normalized_role,
        )
        existing = _device_token_from_row(existing_row) if existing_row is not None else None
        resolved_scopes = _string_list(scopes)
        row = await self.database.upsert_gateway_node_device_token(
            device_id=normalized_device_id,
            role=normalized_role,
            token=secrets.token_urlsafe(32),
            scopes=resolved_scopes,
            created_at_ms=existing.created_at_ms if existing is not None else now_ms,
            rotated_at_ms=now_ms,
            revoked_at_ms=None,
            last_used_at_ms=existing.last_used_at_ms if existing is not None else None,
        )
        return _device_token_from_row(row)

    async def revoke_device_token(
        self,
        *,
        device_id: str,
        role: str,
        now_ms: int,
    ) -> GatewayDeviceAuthToken | None:
        normalized_device_id = _normalize_device_id(device_id)
        normalized_role = _normalize_role(role)
        if normalized_device_id is None or normalized_role is None:
            return None
        paired_node = await self.database.get_gateway_node_paired_node(normalized_device_id)
        if paired_node is None:
            return None
        row = await self.database.revoke_gateway_node_device_token(
            device_id=normalized_device_id,
            role=normalized_role,
            revoked_at_ms=now_ms,
        )
        return _device_token_from_row(row) if row is not None else None

    async def rename(self, node_id: str, display_name: str) -> dict[str, str] | None:
        trimmed = display_name.strip()
        if not trimmed:
            raise ValueError("displayName required")
        paired_row = await self.database.update_gateway_node_paired_node_display_name(
            node_id,
            trimmed,
        )
        if paired_row is None:
            return None
        paired = _paired_node_from_row(paired_row)
        return {
            "nodeId": paired.node_id,
            "displayName": paired.display_name or trimmed,
        }


def _request_from_row(row: dict[str, object]) -> GatewayNodePairingRequest:
    silent = bool(row["silent"]) if row.get("silent") else None
    return GatewayNodePairingRequest(
        request_id=str(row["request_id"]),
        node_id=str(row["node_id"]),
        display_name=_optional_string(row.get("display_name")),
        platform=_optional_string(row.get("platform")),
        version=_optional_string(row.get("version")),
        core_version=_optional_string(row.get("core_version")),
        ui_version=_optional_string(row.get("ui_version")),
        device_family=_optional_string(row.get("device_family")),
        model_identifier=_optional_string(row.get("model_identifier")),
        caps=tuple(_string_list(row.get("caps"))),
        commands=tuple(_string_list(row.get("commands"))),
        remote_ip=_optional_string(row.get("remote_ip")),
        silent=silent,
        ts=cast(int, row["requested_at_ms"]),
    )


def _paired_node_from_row(row: dict[str, object]) -> GatewayPairedNode:
    permissions = row.get("permissions")
    return GatewayPairedNode(
        node_id=str(row["node_id"]),
        token=str(row["token"]),
        display_name=_optional_string(row.get("display_name")),
        platform=_optional_string(row.get("platform")),
        version=_optional_string(row.get("version")),
        core_version=_optional_string(row.get("core_version")),
        ui_version=_optional_string(row.get("ui_version")),
        device_family=_optional_string(row.get("device_family")),
        model_identifier=_optional_string(row.get("model_identifier")),
        caps=tuple(_string_list(row.get("caps"))),
        commands=tuple(_string_list(row.get("commands"))),
        permissions=permissions if isinstance(permissions, dict) else None,
        remote_ip=_optional_string(row.get("remote_ip")),
        created_at_ms=cast(int, row["created_at_ms"]),
        approved_at_ms=cast(int, row["approved_at_ms"]),
        last_connected_at_ms=cast(int | None, row.get("last_connected_at_ms")),
    )


def _device_token_from_row(row: dict[str, object]) -> GatewayDeviceAuthToken:
    return GatewayDeviceAuthToken(
        device_id=str(row["device_id"]),
        role=str(row["role"]),
        token=str(row["token"]),
        scopes=tuple(_string_list(row.get("scopes"))),
        created_at_ms=cast(int, row["created_at_ms"]),
        rotated_at_ms=cast(int | None, row.get("rotated_at_ms")),
        revoked_at_ms=cast(int | None, row.get("revoked_at_ms")),
        last_used_at_ms=cast(int | None, row.get("last_used_at_ms")),
    )


def _request_payload(request: GatewayNodePairingRequest) -> dict[str, object]:
    payload: dict[str, object] = {
        "requestId": request.request_id,
        "nodeId": request.node_id,
        "displayName": request.display_name,
        "platform": request.platform,
        "version": request.version,
        "coreVersion": request.core_version,
        "uiVersion": request.ui_version,
        "deviceFamily": request.device_family,
        "modelIdentifier": request.model_identifier,
        "caps": list(request.caps),
        "commands": list(request.commands),
        "remoteIp": request.remote_ip,
        "ts": request.ts,
    }
    if request.silent is not None:
        payload["silent"] = request.silent
    return payload


def _pending_payload(request: GatewayNodePairingRequest) -> dict[str, object]:
    payload: dict[str, object] = {
        "requestId": request.request_id,
        "nodeId": request.node_id,
        "displayName": request.display_name,
        "platform": request.platform,
        "version": request.version,
        "coreVersion": request.core_version,
        "uiVersion": request.ui_version,
        "deviceFamily": request.device_family,
        "modelIdentifier": request.model_identifier,
        "caps": list(request.caps),
        "commands": list(request.commands),
        "remoteIp": request.remote_ip,
        "ts": request.ts,
        "requiredApproveScopes": list(_required_approve_scopes(request.commands)),
    }
    if request.silent is not None:
        payload["silent"] = request.silent
    return payload


def _paired_list_payload(node: GatewayPairedNode) -> dict[str, object]:
    return {
        "nodeId": node.node_id,
        "token": node.token,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": node.created_at_ms,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.last_connected_at_ms,
    }


def _paired_detail_payload(node: GatewayPairedNode) -> dict[str, object]:
    return {
        "nodeId": node.node_id,
        "token": node.token,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": node.created_at_ms,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.last_connected_at_ms,
    }


def _device_token_summary_payload(token: GatewayDeviceAuthToken) -> dict[str, object]:
    payload: dict[str, object] = {
        "role": token.role,
        "scopes": list(token.scopes),
        "createdAtMs": token.created_at_ms,
        "lastUsedAtMs": token.last_used_at_ms,
    }
    if token.rotated_at_ms is not None:
        payload["rotatedAtMs"] = token.rotated_at_ms
    if token.revoked_at_ms is not None:
        payload["revokedAtMs"] = token.revoked_at_ms
    return payload


def _required_approve_scopes(commands: tuple[str, ...]) -> tuple[str, ...]:
    if any(command in _NODE_SYSTEM_RUN_COMMANDS for command in commands):
        return (PAIRING_GATEWAY_METHOD_SCOPE, ADMIN_GATEWAY_METHOD_SCOPE)
    if commands:
        return (PAIRING_GATEWAY_METHOD_SCOPE, WRITE_GATEWAY_METHOD_SCOPE)
    return (PAIRING_GATEWAY_METHOD_SCOPE,)


def _missing_scope(
    *,
    required_scopes: tuple[str, ...],
    caller_scopes: tuple[str, ...] | None,
) -> str | None:
    if caller_scopes is None:
        return None
    allowed = set(caller_scopes)
    for scope in required_scopes:
        if scope not in allowed:
            return scope
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _normalize_device_id(device_id: str) -> str | None:
    trimmed = device_id.strip()
    return trimmed or None


def _normalize_role(role: str) -> str | None:
    trimmed = role.strip()
    return trimmed or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        trimmed = item.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized
