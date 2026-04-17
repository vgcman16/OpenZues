from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from openzues.database import Database
from openzues.services.gateway_method_policy import (
    ADMIN_GATEWAY_METHOD_SCOPE,
    PAIRING_GATEWAY_METHOD_SCOPE,
    WRITE_GATEWAY_METHOD_SCOPE,
)

_NODE_SYSTEM_RUN_COMMANDS = ("system.run.prepare", "system.run")


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
        caps: list[str],
        commands: list[str],
        remote_ip: str | None,
        silent: bool | None,
        now_ms: int,
    ) -> dict[str, object]:
        existing = await self.database.list_gateway_node_pairing_requests()
        existing_request = next((row for row in existing if row["node_id"] == node_id), None)
        persisted_silent: bool | None
        if existing_request is None:
            persisted_silent = True if silent is True else None
        else:
            persisted_silent = bool(existing_request["silent"]) and bool(silent)

        row, created = await self.database.upsert_gateway_node_pairing_request(
            request_id=str(uuid4()),
            node_id=node_id,
            display_name=display_name,
            platform=platform,
            version=version,
            core_version=core_version,
            ui_version=ui_version,
            device_family=device_family,
            model_identifier=model_identifier,
            caps=caps,
            commands=commands,
            remote_ip=remote_ip,
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
        "remoteIp": request.remote_ip,
        "ts": request.ts,
        "requiredApproveScopes": list(_required_approve_scopes(request.commands)),
    }
    if request.commands:
        payload["commands"] = list(request.commands)
    return payload


def _paired_list_payload(node: GatewayPairedNode) -> dict[str, object]:
    return {
        "nodeId": node.node_id,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
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
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": node.created_at_ms,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.last_connected_at_ms,
    }


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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
