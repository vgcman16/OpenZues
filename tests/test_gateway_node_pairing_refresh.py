from __future__ import annotations

import pytest

from openzues.services.gateway_node_pairing import GatewayNodePairingService


class _FakePairingDatabase:
    def __init__(self) -> None:
        self._request_ids_by_node_id: dict[str, str] = {}
        self._rows_by_request_id: dict[str, dict[str, object]] = {}
        self._paired_rows_by_node_id: dict[str, dict[str, object]] = {}

    async def list_gateway_node_pairing_requests(self) -> list[dict[str, object]]:
        rows = sorted(
            self._rows_by_request_id.values(),
            key=lambda row: (-int(row["requested_at_ms"]), str(row["request_id"])),
        )
        return [dict(row) for row in rows]

    async def upsert_gateway_node_pairing_request(
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
        requested_at_ms: int,
        request_id: str,
    ) -> tuple[dict[str, object], bool]:
        persisted_request_id = self._request_ids_by_node_id.get(node_id, request_id)
        created = persisted_request_id == request_id and persisted_request_id not in self._rows_by_request_id
        existing = self._rows_by_request_id.get(persisted_request_id, {})
        row = {
            "request_id": persisted_request_id,
            "node_id": node_id,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps),
            "commands": list(commands),
            "remote_ip": remote_ip,
            "silent": bool(silent),
            "requested_at_ms": requested_at_ms,
            "created_at": existing.get("created_at"),
            "updated_at": existing.get("updated_at"),
        }
        self._request_ids_by_node_id[node_id] = persisted_request_id
        self._rows_by_request_id[persisted_request_id] = row
        return dict(row), created

    async def get_gateway_node_paired_node(self, node_id: str) -> dict[str, object] | None:
        row = self._paired_rows_by_node_id.get(node_id)
        return dict(row) if row is not None else None

    async def upsert_gateway_node_paired_node(
        self,
        *,
        node_id: str,
        token: str,
        display_name: str | None,
        platform: str | None,
        version: str | None,
        core_version: str | None,
        ui_version: str | None,
        device_family: str | None,
        model_identifier: str | None,
        caps: list[str],
        commands: list[str],
        permissions: dict[str, bool] | None,
        remote_ip: str | None,
        created_at_ms: int,
        approved_at_ms: int,
        last_connected_at_ms: int | None,
    ) -> dict[str, object]:
        row = {
            "node_id": node_id,
            "token": token,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps),
            "commands": list(commands),
            "permissions": permissions,
            "remote_ip": remote_ip,
            "created_at_ms": created_at_ms,
            "approved_at_ms": approved_at_ms,
            "last_connected_at_ms": last_connected_at_ms,
        }
        self._paired_rows_by_node_id[node_id] = row
        return dict(row)

    def seed_paired_node(
        self,
        *,
        node_id: str,
        token: str = "token-1",
        display_name: str | None = "Paired Node",
        platform: str | None = "ios",
        version: str | None = None,
        core_version: str | None = None,
        ui_version: str | None = None,
        device_family: str | None = None,
        model_identifier: str | None = None,
        caps: list[object] | None = None,
        commands: list[object] | None = None,
        permissions: dict[str, bool] | None = None,
        remote_ip: str | None = None,
        created_at_ms: int = 1_000,
        approved_at_ms: int = 2_000,
        last_connected_at_ms: int | None = 3_000,
    ) -> None:
        self._paired_rows_by_node_id[node_id] = {
            "node_id": node_id,
            "token": token,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps or []),
            "commands": list(commands or []),
            "permissions": permissions,
            "remote_ip": remote_ip,
            "created_at_ms": created_at_ms,
            "approved_at_ms": approved_at_ms,
            "last_connected_at_ms": last_connected_at_ms,
        }


@pytest.mark.asyncio
async def test_pair_request_refresh_preserves_silent_when_omitted() -> None:
    service = GatewayNodePairingService(_FakePairingDatabase())

    created = await service.request(
        node_id="pair-node-silent-refresh",
        display_name="Silent Refresh Node",
        platform="ios",
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        remote_ip=None,
        silent=True,
        now_ms=1_000,
    )
    refreshed = await service.request(
        node_id="pair-node-silent-refresh",
        display_name="Silent Refresh Node v2",
        platform=None,
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        remote_ip=None,
        silent=None,
        now_ms=2_000,
    )
    listed = await service.list_pending()

    request_id = created["request"]["requestId"]
    assert refreshed == {
        "status": "pending",
        "request": {
            "requestId": request_id,
            "nodeId": "pair-node-silent-refresh",
            "displayName": "Silent Refresh Node v2",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "silent": True,
            "ts": 2_000,
        },
        "created": False,
    }
    assert listed == [
        {
            "requestId": request_id,
            "nodeId": "pair-node-silent-refresh",
            "displayName": "Silent Refresh Node v2",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "silent": True,
            "ts": 2_000,
            "requiredApproveScopes": ["operator.pairing"],
        }
    ]


@pytest.mark.asyncio
async def test_pair_request_refresh_clears_silent_when_false() -> None:
    service = GatewayNodePairingService(_FakePairingDatabase())

    created = await service.request(
        node_id="pair-node-silent-clear",
        display_name="Silent Clear Node",
        platform="ios",
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        remote_ip=None,
        silent=True,
        now_ms=1_000,
    )
    refreshed = await service.request(
        node_id="pair-node-silent-clear",
        display_name=None,
        platform=None,
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        remote_ip=None,
        silent=False,
        now_ms=2_000,
    )
    listed = await service.list_pending()

    request_id = created["request"]["requestId"]
    assert refreshed == {
        "status": "pending",
        "request": {
            "requestId": request_id,
            "nodeId": "pair-node-silent-clear",
            "displayName": "Silent Clear Node",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "ts": 2_000,
        },
        "created": False,
    }
    assert listed == [
        {
            "requestId": request_id,
            "nodeId": "pair-node-silent-clear",
            "displayName": "Silent Clear Node",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "ts": 2_000,
            "requiredApproveScopes": ["operator.pairing"],
        }
    ]


@pytest.mark.asyncio
async def test_pair_request_normalizes_caps_and_commands_lists() -> None:
    service = GatewayNodePairingService(_FakePairingDatabase())

    created = await service.request(
        node_id="pair-node-normalized",
        display_name="Normalized Node",
        platform="ios",
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=[" voice ", "", "voice", "canvas "],
        commands=[" system.run ", "system.run", " canvas.present ", " "],
        remote_ip=None,
        silent=True,
        now_ms=1_000,
    )
    listed = await service.list_pending()

    assert created["request"]["caps"] == ["voice", "canvas"]
    assert created["request"]["commands"] == ["system.run", "canvas.present"]
    assert listed == [
        {
            "requestId": created["request"]["requestId"],
            "nodeId": "pair-node-normalized",
            "displayName": "Normalized Node",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": ["voice", "canvas"],
            "commands": ["system.run", "canvas.present"],
            "remoteIp": None,
            "silent": True,
            "ts": 1_000,
            "requiredApproveScopes": ["operator.pairing", "operator.admin"],
        }
    ]


@pytest.mark.asyncio
async def test_get_paired_node_normalizes_dirty_stored_caps_and_commands() -> None:
    database = _FakePairingDatabase()
    database.seed_paired_node(
        node_id="pair-node-dirty",
        caps=[" voice ", "voice", "", "canvas "],
        commands=[" system.run ", "system.run", "", " canvas.present "],
    )
    service = GatewayNodePairingService(database)

    node = await service.get_paired_node("pair-node-dirty")

    assert node is not None
    assert node.caps == ("voice", "canvas")
    assert node.commands == ("system.run", "canvas.present")


@pytest.mark.asyncio
async def test_update_paired_node_metadata_normalizes_caps_and_commands_lists() -> None:
    database = _FakePairingDatabase()
    database.seed_paired_node(
        node_id="pair-node-update-normalized",
        caps=["voice"],
        commands=["system.which"],
    )
    service = GatewayNodePairingService(database)

    updated = await service.update_paired_node_metadata(
        "pair-node-update-normalized",
        caps=[" canvas ", "canvas", "", "voice "],
        commands=[" system.run ", "system.run", " system.which "],
    )

    assert updated is not None
    assert updated.caps == ("canvas", "voice")
    assert updated.commands == ("system.run", "system.which")
    stored = await database.get_gateway_node_paired_node("pair-node-update-normalized")
    assert stored is not None
    assert stored["caps"] == ["canvas", "voice"]
    assert stored["commands"] == ["system.run", "system.which"]
