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

    async def get_gateway_node_pairing_request(
        self, request_id: str
    ) -> dict[str, object] | None:
        row = self._rows_by_request_id.get(request_id)
        return dict(row) if row is not None else None

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
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        remote_ip: str | None,
        silent: bool | None,
        requested_at_ms: int,
        request_id: str,
        public_key: str | None = None,
    ) -> tuple[dict[str, object], bool]:
        persisted_request_id = self._request_ids_by_node_id.get(node_id, request_id)
        created = (
            persisted_request_id == request_id
            and persisted_request_id not in self._rows_by_request_id
        )
        existing = self._rows_by_request_id.get(persisted_request_id, {})
        row = {
            "request_id": persisted_request_id,
            "node_id": node_id,
            "public_key": public_key,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps),
            "commands": list(commands),
            "roles": list(roles or []),
            "scopes": list(scopes or []),
            "remote_ip": remote_ip,
            "silent": bool(silent),
            "requested_at_ms": requested_at_ms,
            "created_at": existing.get("created_at"),
            "updated_at": existing.get("updated_at"),
        }
        self._request_ids_by_node_id[node_id] = persisted_request_id
        self._rows_by_request_id[persisted_request_id] = row
        return dict(row), created

    async def delete_gateway_node_pairing_request(
        self, request_id: str
    ) -> dict[str, object] | None:
        row = self._rows_by_request_id.pop(request_id, None)
        if row is None:
            return None
        self._request_ids_by_node_id.pop(str(row["node_id"]), None)
        return dict(row)

    async def get_gateway_node_paired_node(self, node_id: str) -> dict[str, object] | None:
        row = self._paired_rows_by_node_id.get(node_id)
        return dict(row) if row is not None else None

    async def list_gateway_node_paired_nodes(self) -> list[dict[str, object]]:
        rows = sorted(
            self._paired_rows_by_node_id.values(),
            key=lambda row: (-int(row["approved_at_ms"]), str(row["node_id"])),
        )
        return [dict(row) for row in rows]

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
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        bins: list[str],
        permissions: dict[str, bool] | None,
        remote_ip: str | None,
        created_at_ms: int,
        approved_at_ms: int,
        last_connected_at_ms: int | None,
        public_key: str | None = None,
    ) -> dict[str, object]:
        row = {
            "node_id": node_id,
            "token": token,
            "public_key": public_key,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps),
            "commands": list(commands),
            "roles": list(roles or []),
            "scopes": list(scopes or []),
            "bins": list(bins),
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
        public_key: str | None = None,
        display_name: str | None = "Paired Node",
        platform: str | None = "ios",
        version: str | None = None,
        core_version: str | None = None,
        ui_version: str | None = None,
        device_family: str | None = None,
        model_identifier: str | None = None,
        caps: list[object] | None = None,
        commands: list[object] | None = None,
        roles: list[object] | None = None,
        scopes: list[object] | None = None,
        bins: list[object] | None = None,
        permissions: dict[str, bool] | None = None,
        remote_ip: str | None = None,
        created_at_ms: int = 1_000,
        approved_at_ms: int = 2_000,
        last_connected_at_ms: int | None = 3_000,
    ) -> None:
        self._paired_rows_by_node_id[node_id] = {
            "node_id": node_id,
            "token": token,
            "public_key": public_key,
            "display_name": display_name,
            "platform": platform,
            "version": version,
            "core_version": core_version,
            "ui_version": ui_version,
            "device_family": device_family,
            "model_identifier": model_identifier,
            "caps": list(caps or []),
            "commands": list(commands or []),
            "roles": list(roles or []),
            "scopes": list(scopes or []),
            "bins": list(bins or []),
            "permissions": permissions,
            "remote_ip": remote_ip,
            "created_at_ms": created_at_ms,
            "approved_at_ms": approved_at_ms,
            "last_connected_at_ms": last_connected_at_ms,
        }


@pytest.mark.asyncio
async def test_pair_request_preserves_public_key_through_refresh_list_and_approval() -> None:
    database = _FakePairingDatabase()
    service = GatewayNodePairingService(database)

    created = await service.request(
        node_id="pair-node-public-key",
        public_key=" pending-public-key-1 ",
        display_name="Public Key Node",
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
        node_id="pair-node-public-key",
        public_key=None,
        display_name="Public Key Node v2",
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
    approved = await service.approve(
        str(created["request"]["requestId"]),
        caller_scopes=("operator.pairing",),
        now_ms=3_000,
    )
    paired = await service.list_paired_nodes()

    request_id = created["request"]["requestId"]
    assert created["request"]["publicKey"] == "pending-public-key-1"
    assert refreshed["request"]["publicKey"] == "pending-public-key-1"
    assert listed[0]["publicKey"] == "pending-public-key-1"
    assert approved == {
        "requestId": request_id,
        "node": {
            "nodeId": "pair-node-public-key",
            "publicKey": "pending-public-key-1",
            "token": approved["node"]["token"],
            "displayName": "Public Key Node v2",
            "platform": "ios",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "permissions": None,
            "createdAtMs": 3_000,
            "approvedAtMs": 3_000,
            "lastConnectedAtMs": None,
        },
    }
    assert paired[0].public_key == "pending-public-key-1"


@pytest.mark.asyncio
async def test_pair_request_same_approval_snapshot_preserves_original_ts() -> None:
    service = GatewayNodePairingService(_FakePairingDatabase())

    created = await service.request(
        node_id="pair-node-queue-stable",
        public_key="public-key-queue-stable",
        display_name="Queue Stable Node",
        platform="ios",
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        role="operator",
        roles=None,
        scopes=["operator.read"],
        remote_ip="10.0.0.1",
        silent=True,
        now_ms=1_000,
    )
    refreshed = await service.request(
        node_id="pair-node-queue-stable",
        public_key="public-key-queue-stable",
        display_name="Queue Stable Node Updated",
        platform=None,
        version=None,
        core_version=None,
        ui_version=None,
        device_family=None,
        model_identifier=None,
        caps=None,
        commands=None,
        role="operator",
        roles=None,
        scopes=["operator.read"],
        remote_ip="10.0.0.2",
        silent=True,
        now_ms=2_000,
    )
    listed = await service.list_pending()

    assert refreshed["created"] is False
    assert refreshed["request"]["requestId"] == created["request"]["requestId"]
    assert refreshed["request"]["displayName"] == "Queue Stable Node Updated"
    assert refreshed["request"]["remoteIp"] == "10.0.0.2"
    assert refreshed["request"]["ts"] == 1_000
    assert listed[0]["ts"] == 1_000


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
            "ts": 1_000,
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
            "ts": 1_000,
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
            "ts": 1_000,
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
            "ts": 1_000,
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
