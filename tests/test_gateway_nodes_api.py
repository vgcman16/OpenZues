from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.gateway_node_service import GatewayNodeService
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.manager import InstanceRuntime
from openzues.settings import Settings


@pytest.fixture(autouse=True)
def _reset_external_catalogs() -> None:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    yield
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)


@pytest.fixture(autouse=True)
def _disable_control_plane_background_services(monkeypatch: pytest.MonkeyPatch) -> None:
    def _acquire_as_observer(self, *, metadata=None) -> bool:
        self.acquired = False
        self.owner_pid = None
        self.metadata = dict(metadata or {})
        return False

    monkeypatch.setattr(
        "openzues.services.control_plane.ControlPlaneLease.acquire",
        _acquire_as_observer,
    )


class _AutoReplyNodeConnection:
    def __init__(self, registry: GatewayNodeRegistry, conn_id: str) -> None:
        self.registry = registry
        self.conn_id = conn_id

    def send_gateway_event(self, event: str, payload: object) -> None:
        if event != "node.invoke.request" or not isinstance(payload, dict):
            return
        request_id = str(payload.get("id") or "")
        node_id = str(payload.get("nodeId") or "")
        if not request_id or not node_id:
            return
        asyncio.get_running_loop().call_soon(
            lambda: self.registry.handle_invoke_result(
                request_id=request_id,
                node_id=node_id,
                ok=True,
                payload={"status": "done"},
                payload_json='{"status":"done"}',
                error=None,
            )
        )


class _FakeManager:
    def __init__(self, instances: list[SimpleNamespace]) -> None:
        self._instances = instances

    async def list_views(self) -> list[SimpleNamespace]:
        return self._instances


def _register_known_live_node(
    registry: GatewayNodeRegistry,
    *,
    conn_id: str,
    node_id: str,
    client_id: str,
    display_name: str,
    platform: str,
    client_mode: str = "desktop",
    path_env: str | None = None,
    commands: tuple[str, ...] = (),
    connected_at_ms: int = 0,
) -> None:
    registry.remember(
        KnownNode(
            node_id=node_id,
            display_name=display_name,
            platform=platform,
            client_id=client_id,
            client_mode=client_mode,
            path_env=path_env,
            commands=commands,
            paired=True,
            connected=False,
        )
    )
    registry.register(
        _AutoReplyNodeConnection(registry, conn_id),
        GatewayNodeConnect(
            client_id=client_id,
            device_id=node_id,
            client_mode=client_mode,
            display_name=display_name,
            platform=platform,
            path_env=path_env,
            commands=commands,
        ),
        connected_at_ms=connected_at_ms,
    )


def _allow_mutating_api_requests(client: TestClient) -> None:
    client.app.state.control_plane_role = "leader"
    client.app.state.control_plane_owner_pid = None


def test_gateway_node_endpoints_surface_known_nodes_and_pending_actions(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-node-1",
        node_id="node-1",
        client_id="live-node-1",
        display_name="Node Lane",
        platform="desktop",
        path_env=str(tmp_path),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        queued = client.app.state.gateway_node_service.registry.enqueue_pending_action(
            node_id="node-1",
            command="screen.snapshot",
            params_json='{"mode":"full"}',
            idempotency_key="idem-node-1",
        )

        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/node-1")

        client.app.state.gateway_node_service.registry.unregister("conn-node-1")

        offline_nodes_response = client.get("/api/gateway/nodes")
        pending_response = client.get("/api/gateway/nodes/node-1/pending-actions")
        ack_response = client.post(
            "/api/gateway/nodes/node-1/pending-actions/ack",
            json={"ids": [queued.id]},
        )
        pending_after_ack_response = client.get(
            "/api/gateway/nodes/node-1/pending-actions"
        )

    assert nodes_response.status_code == 200
    nodes_payload = nodes_response.json()
    assert nodes_payload["node_count"] == 1
    assert nodes_payload["connected_count"] == 1
    assert nodes_payload["paired_count"] == 1
    assert nodes_payload["nodes"][0]["node_id"] == "node-1"
    assert nodes_payload["nodes"][0]["connected"] is True

    assert node_response.status_code == 200
    node_payload = node_response.json()
    assert node_payload["node_id"] == "node-1"
    assert node_payload["display_name"] == "Node Lane"
    assert node_payload["connected"] is True
    assert node_payload["paired"] is True

    assert offline_nodes_response.status_code == 200
    offline_nodes_payload = offline_nodes_response.json()
    assert offline_nodes_payload["connected_count"] == 0
    assert offline_nodes_payload["nodes"][0]["connected"] is False

    assert pending_response.status_code == 200
    assert pending_response.json() == {
        "nodeId": "node-1",
        "actions": [
                {
                    "id": queued.id,
                    "command": "screen.snapshot",
                    "paramsJSON": '{"mode":"full"}',
                    "enqueuedAtMs": queued.enqueued_at_ms,
                }
            ],
        }

    assert ack_response.status_code == 200
    assert ack_response.json() == {
        "nodeId": "node-1",
        "ackedIds": [queued.id],
        "remainingCount": 0,
    }

    assert pending_after_ack_response.status_code == 200
    assert pending_after_ack_response.json() == {
        "nodeId": "node-1",
        "actions": [],
    }


def test_gateway_node_endpoints_return_404_for_unknown_node(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        node_response = client.get("/api/gateway/nodes/missing-node")
        pending_response = client.get("/api/gateway/nodes/missing-node/pending-actions")
        ack_response = client.post(
            "/api/gateway/nodes/missing-node/pending-actions/ack",
            json={"ids": ["pending-1"]},
        )

    assert node_response.status_code == 404
    assert pending_response.status_code == 404
    assert ack_response.status_code == 404


def test_gateway_node_pending_work_endpoints_surface_drain_and_enqueue_contract(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-pending-node-1",
        node_id="pending-node-1",
        client_id="pending-live-node-1",
        display_name="Pending Node Lane",
        platform="desktop",
        path_env=str(tmp_path),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        initial_response = client.get("/api/gateway/nodes/pending-node-1/pending-work")
        enqueue_response = client.post(
            "/api/gateway/nodes/pending-node-1/pending-work",
            json={
                "type": "location.request",
                "priority": "high",
                "expiresInMs": 5_000,
                "payload": {"reason": "gps"},
            },
        )
        after_enqueue_response = client.get("/api/gateway/nodes/pending-node-1/pending-work")

    assert initial_response.status_code == 200
    assert initial_response.json() == {
        "nodeId": "pending-node-1",
        "revision": 0,
        "items": [
            {
                "id": "baseline-status",
                "type": "status.request",
                "priority": "default",
                "createdAtMs": initial_response.json()["items"][0]["createdAtMs"],
                "expiresAtMs": None,
                "payload": None,
            }
        ],
        "hasMore": False,
    }

    assert enqueue_response.status_code == 200
    enqueue_payload = enqueue_response.json()
    assert enqueue_payload["nodeId"] == "pending-node-1"
    assert enqueue_payload["revision"] == 1
    assert enqueue_payload["queued"]["type"] == "location.request"
    assert enqueue_payload["queued"]["priority"] == "high"
    assert enqueue_payload["queued"]["payload"] == {"reason": "gps"}
    assert enqueue_payload["wakeTriggered"] is False

    assert after_enqueue_response.status_code == 200
    assert after_enqueue_response.json() == {
        "nodeId": "pending-node-1",
        "revision": 1,
        "items": [
            {
                "id": enqueue_payload["queued"]["id"],
                "type": "location.request",
                "priority": "high",
                "createdAtMs": enqueue_payload["queued"]["createdAtMs"],
                "expiresAtMs": enqueue_payload["queued"]["expiresAtMs"],
                "payload": {"reason": "gps"},
            },
            {
                "id": "baseline-status",
                "type": "status.request",
                "priority": "default",
                "createdAtMs": after_enqueue_response.json()["items"][1]["createdAtMs"],
                "expiresAtMs": None,
                "payload": None,
            },
        ],
        "hasMore": False,
    }


def test_gateway_node_pending_work_endpoint_can_request_wake_for_managed_lane(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    manager = app.state.manager
    manager.instances[7] = InstanceRuntime(
        instance_id=7,
        name="Managed Pending Node",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
    )

    async def fake_connect_instance(instance_id: int) -> InstanceRuntime:
        assert instance_id == 7
        runtime = manager.instances[instance_id]
        runtime.connected = True
        return runtime

    monkeypatch.setattr(manager, "connect_instance", fake_connect_instance)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        enqueue_response = client.post(
            "/api/gateway/nodes/7/pending-work",
            json={
                "type": "location.request",
                "priority": "high",
                "expiresInMs": 5_000,
                "wake": True,
            },
        )

    assert enqueue_response.status_code == 200
    enqueue_payload = enqueue_response.json()
    assert enqueue_payload["nodeId"] == "7"
    assert enqueue_payload["queued"]["type"] == "location.request"
    assert enqueue_payload["wakeTriggered"] is True


def test_managed_node_sync_emits_voicewake_snapshot_only_on_fresh_connect(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = SimpleNamespace(
        id=7,
        name="Managed Lane",
        transport="desktop",
        cwd=str(tmp_path),
        connected=True,
        last_event_at="2026-04-16T22:00:00Z",
    )
    voicewake_service = GatewayVoiceWakeService(tmp_path)
    voicewake_service.set_triggers(["zues", "builder"], now_ms=123)
    service = GatewayNodeService(
        _FakeManager([instance]),
        voicewake_service=voicewake_service,
    )
    sent_events: list[dict[str, object | None]] = []
    original_send_event = service.registry.send_event

    def spy_send_event(node_id: str, event: str, payload: object | None = None) -> bool:
        sent_events.append({"node_id": node_id, "event": event, "payload": payload})
        return original_send_event(node_id, event, payload)

    monkeypatch.setattr(service.registry, "send_event", spy_send_event)

    asyncio.run(service.sync())
    asyncio.run(service.sync())
    instance.connected = False
    asyncio.run(service.sync())
    instance.connected = True
    asyncio.run(service.sync())

    assert sent_events == [
        {
            "node_id": "7",
            "event": "voicewake.changed",
            "payload": {"triggers": ["zues", "builder"]},
        },
        {
            "node_id": "7",
            "event": "voicewake.changed",
            "payload": {"triggers": ["zues", "builder"]},
        },
    ]


def test_create_app_wires_managed_node_voicewake_snapshot_only_on_fresh_connect(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    manager = app.state.manager
    manager.instances[7] = InstanceRuntime(
        instance_id=7,
        name="Managed Voicewake Node",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
    )
    runtime = manager.instances[7]
    with TestClient(app, client=("testclient", 50000)) as client:
        sent_events: list[dict[str, object | None]] = []
        original_send_event = client.app.state.gateway_node_service.registry.send_event

        def spy_send_event(
            node_id: str,
            event: str,
            payload: object | None = None,
        ) -> bool:
            sent_events.append({"node_id": node_id, "event": event, "payload": payload})
            return original_send_event(node_id, event, payload)

        monkeypatch.setattr(
            client.app.state.gateway_node_service.registry,
            "send_event",
            spy_send_event,
        )

        set_result = client.portal.call(
            client.app.state.gateway_node_method_service.call,
            "voicewake.set",
            {"triggers": ["zues", "builder"]},
        )
        assert set_result == {"triggers": ["zues", "builder"]}

        runtime.connected = True
        client.portal.call(client.app.state.gateway_node_service.sync)
        client.portal.call(client.app.state.gateway_node_service.sync)
        runtime.connected = False
        client.portal.call(client.app.state.gateway_node_service.sync)
        runtime.connected = True
        client.portal.call(client.app.state.gateway_node_service.sync)

    assert sent_events == [
        {
            "node_id": "7",
            "event": "voicewake.changed",
            "payload": {"triggers": ["zues", "builder"]},
        },
        {
            "node_id": "7",
            "event": "voicewake.changed",
            "payload": {"triggers": ["zues", "builder"]},
        },
    ]


def test_gateway_node_method_call_endpoint_surfaces_operator_method_payloads(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-method-node-1",
        node_id="method-node-1",
        client_id="method-live-node-1",
        display_name="Method Node Lane",
        platform="desktop",
        path_env=str(tmp_path),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.list", "params": {}},
        )
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )
        describe_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.describe", "params": {"nodeId": "method-node-1"}},
        )
        enqueue_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pending.enqueue",
                "params": {
                    "nodeId": "method-node-1",
                    "type": "location.request",
                    "priority": "high",
                },
            },
        )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert isinstance(list_payload["ts"], int)
    assert list_payload["nodes"] == [
        {
            "nodeId": "method-node-1",
            "displayName": "Method Node Lane",
            "platform": "desktop",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "clientId": "method-live-node-1",
            "clientMode": "desktop",
            "remoteIp": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "pathEnv": str(tmp_path),
            "caps": [],
            "commands": [],
            "permissions": None,
            "paired": True,
            "connected": True,
            "connectedAtMs": 0,
            "approvedAtMs": None,
        }
    ]

    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [],
        "paired": [
            {
                "nodeId": "method-node-1",
                "displayName": "Method Node Lane",
                "platform": "desktop",
                "version": None,
                "coreVersion": None,
                "uiVersion": None,
                "remoteIp": None,
                "permissions": None,
                "createdAtMs": None,
                "approvedAtMs": None,
                "lastConnectedAtMs": 0,
            }
        ],
    }

    assert describe_response.status_code == 200
    describe_payload = describe_response.json()
    assert isinstance(describe_payload["ts"], int)
    assert describe_payload["nodeId"] == "method-node-1"
    assert describe_payload["displayName"] == "Method Node Lane"
    assert describe_payload["connected"] is True
    assert describe_payload["paired"] is True

    assert enqueue_response.status_code == 200
    enqueue_payload = enqueue_response.json()
    assert enqueue_payload["nodeId"] == "method-node-1"
    assert enqueue_payload["revision"] == 1
    assert enqueue_payload["queued"]["type"] == "location.request"
    assert enqueue_payload["queued"]["priority"] == "high"
    assert enqueue_payload["wakeTriggered"] is False


def test_remote_gateway_node_method_call_requires_api_key(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_remote_gateway_node_pair_approve_threads_operator_gateway_scopes(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    local_app = create_app(app_settings)

    with TestClient(local_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-remote-scope",
                    "displayName": "Scoped Remote Node",
                    "platform": "linux",
                    "commands": ["system.run"],
                },
            },
        )
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Operator",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        owner_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Owner",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert request_response.status_code == 200
    assert operator_response.status_code == 200
    assert owner_response.status_code == 200

    request_id = request_response.json()["request"]["requestId"]
    operator_api_key = operator_response.json()["api_key"]
    owner_api_key = owner_response.json()["api_key"]

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        operator_approve_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {operator_api_key}"},
            json={
                "method": "node.pair.approve",
                "params": {"requestId": request_id},
            },
        )
        owner_approve_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "node.pair.approve",
                "params": {"requestId": request_id},
            },
        )

    assert operator_approve_response.status_code == 400
    assert "missing scope: operator.admin" in operator_approve_response.json()["detail"]

    assert owner_approve_response.status_code == 200
    owner_payload = owner_approve_response.json()
    assert owner_payload["node"] == {
        "nodeId": "pair-node-remote-scope",
        "token": owner_payload["node"]["token"],
        "displayName": "Scoped Remote Node",
        "platform": "linux",
        "version": None,
        "coreVersion": None,
        "uiVersion": None,
        "remoteIp": None,
        "permissions": None,
        "createdAtMs": owner_payload["node"]["createdAtMs"],
        "approvedAtMs": owner_payload["node"]["approvedAtMs"],
        "lastConnectedAtMs": None,
    }
    assert isinstance(owner_payload["node"]["token"], str)
    assert len(owner_payload["node"]["token"]) == 43


def test_gateway_node_pair_request_endpoint_persists_pending_requests_across_restart(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    first_app = create_app(app_settings)
    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-persisted",
                    "displayName": "Persistent Node",
                    "platform": "macos",
                    "commands": ["system.run"],
                    "remoteIp": "10.0.0.8",
                },
            },
        )

    assert request_response.status_code == 200
    request_payload = request_response.json()
    request_id = request_payload["request"]["requestId"]
    request_ts = request_payload["request"]["ts"]

    restarted_app = create_app(app_settings)
    with TestClient(restarted_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [
            {
                "requestId": request_id,
                "nodeId": "pair-node-persisted",
                "displayName": "Persistent Node",
                "platform": "macos",
                "version": None,
                "coreVersion": None,
                "uiVersion": None,
                "remoteIp": "10.0.0.8",
                "ts": request_ts,
                "commands": ["system.run"],
                "requiredApproveScopes": ["operator.pairing", "operator.admin"],
            }
        ],
        "paired": [],
    }


def test_gateway_node_pair_reject_endpoint_removes_pending_request(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-reject",
                    "displayName": "Reject Me",
                    "platform": "ios",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        reject_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.reject", "params": {"requestId": request_id}},
        )
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert reject_response.status_code == 200
    assert reject_response.json() == {
        "requestId": request_id,
        "nodeId": "pair-node-reject",
    }
    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [],
        "paired": [],
    }


def test_gateway_node_pair_approve_verify_and_rename_persist_across_restart(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    first_app = create_app(app_settings)
    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-approved",
                    "displayName": "Approve Me",
                    "platform": "windows",
                    "commands": ["system.run"],
                    "remoteIp": "10.0.0.10",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )

    assert approve_response.status_code == 200
    approve_payload = approve_response.json()
    token = approve_payload["node"]["token"]
    approved_at_ms = approve_payload["node"]["approvedAtMs"]
    created_at_ms = approve_payload["node"]["createdAtMs"]

    restarted_app = create_app(app_settings)
    with TestClient(restarted_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        verify_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.verify",
                "params": {"nodeId": "pair-node-approved", "token": token},
            },
        )
        rename_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.rename",
                "params": {"nodeId": "pair-node-approved", "displayName": "Approved Node"},
            },
        )
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert verify_response.status_code == 200
    assert verify_response.json() == {
        "ok": True,
        "node": {
            "nodeId": "pair-node-approved",
            "token": token,
            "displayName": "Approve Me",
            "platform": "windows",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "remoteIp": "10.0.0.10",
            "permissions": None,
            "createdAtMs": created_at_ms,
            "approvedAtMs": approved_at_ms,
            "lastConnectedAtMs": None,
        },
    }
    assert rename_response.status_code == 200
    assert rename_response.json() == {
        "nodeId": "pair-node-approved",
        "displayName": "Approved Node",
    }
    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [],
        "paired": [
            {
                "nodeId": "pair-node-approved",
                "displayName": "Approved Node",
                "platform": "windows",
                "version": None,
                "coreVersion": None,
                "uiVersion": None,
                "remoteIp": "10.0.0.10",
                "permissions": None,
                "createdAtMs": created_at_ms,
                "approvedAtMs": approved_at_ms,
                "lastConnectedAtMs": None,
            }
        ],
    }


def test_gateway_nodes_endpoints_include_persisted_approved_nodes_after_restart(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    first_app = create_app(app_settings)
    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-catalog",
                    "displayName": "Catalog Node",
                    "platform": "linux",
                    "version": "1.0.0",
                    "coreVersion": "2.0.0",
                    "uiVersion": "3.0.0",
                    "deviceFamily": "server",
                    "modelIdentifier": "vm-standard",
                    "caps": ["shell"],
                    "commands": ["system.run"],
                    "remoteIp": "10.0.0.12",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )

    assert approve_response.status_code == 200
    approved_at_ms = approve_response.json()["node"]["approvedAtMs"]

    restarted_app = create_app(app_settings)
    with TestClient(restarted_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/pair-node-catalog")

    assert nodes_response.status_code == 200
    assert nodes_response.json() == {
        "headline": "Gateway known node catalog is visible",
        "summary": (
            "1 known node(s) are visible; 0 currently connected and 1 saved in the lane "
            "roster."
        ),
        "node_count": 1,
        "connected_count": 0,
        "paired_count": 1,
        "nodes": [
            {
                "node_id": "pair-node-catalog",
                "display_name": "Catalog Node",
                "platform": "linux",
                "version": "1.0.0",
                "core_version": "2.0.0",
                "ui_version": "3.0.0",
                "client_id": None,
                "client_mode": None,
                "remote_ip": "10.0.0.12",
                "device_family": "server",
                "model_identifier": "vm-standard",
                "path_env": None,
                "caps": ["shell"],
                "commands": ["system.run"],
                "permissions": None,
                "paired": True,
                "connected": False,
                "connected_at_ms": None,
                "approved_at_ms": approved_at_ms,
            }
        ],
    }
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "pair-node-catalog",
        "display_name": "Catalog Node",
        "platform": "linux",
        "version": "1.0.0",
        "core_version": "2.0.0",
        "ui_version": "3.0.0",
        "client_id": None,
        "client_mode": None,
        "remote_ip": "10.0.0.12",
        "device_family": "server",
        "model_identifier": "vm-standard",
        "path_env": None,
        "caps": ["shell"],
        "commands": ["system.run"],
        "permissions": None,
        "paired": True,
        "connected": False,
        "connected_at_ms": None,
        "approved_at_ms": approved_at_ms,
    }


def test_gateway_node_method_call_endpoint_rejects_node_only_and_unknown_methods(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        pull_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pending.pull", "params": {}},
        )
        unknown_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.missing", "params": {}},
        )

    assert pull_response.status_code == 400
    assert "requires a connected device identity" in pull_response.json()["detail"]
    assert unknown_response.status_code == 400
    assert "unsupported method" in unknown_response.json()["detail"]


def test_gateway_node_method_call_endpoint_supports_node_invoke(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-node-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            platform="windows",
            commands=("system.run",),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.invoke",
                "params": {
                    "nodeId": "node-1",
                    "command": "system.run",
                    "params": {"command": "whoami"},
                    "timeoutMs": 250,
                    "idempotencyKey": "idem-system-run",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "nodeId": "node-1",
        "command": "system.run",
        "payload": {"status": "done"},
        "payloadJSON": '{"status":"done"}',
    }


def test_gateway_node_method_call_endpoint_supports_voicewake_get_and_set(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "voicewake.get", "params": {}},
        )
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "voicewake.set",
                "params": {"triggers": ["  zues  ", "", "builder  "]},
            },
        )
        after_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "voicewake.get", "params": {}},
        )

    assert get_response.status_code == 200
    assert get_response.json() == {"triggers": ["openclaw", "claude", "computer"]}
    assert set_response.status_code == 200
    assert set_response.json() == {"triggers": ["zues", "builder"]}
    assert after_response.status_code == 200
    assert after_response.json() == {"triggers": ["zues", "builder"]}


def test_gateway_node_method_call_endpoint_supports_gateway_identity_get(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "gateway.identity.get", "params": {}},
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "gateway.identity.get", "params": {}},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_response.json()["id"].startswith("gateway-")
    assert len(first_response.json()["publicKey"]) > 20
    assert (tmp_path / "data" / "settings" / "gateway-identity.json").exists()


def test_gateway_node_method_call_endpoint_supports_health(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        gateway_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "health", "params": {}},
        )
        api_response = client.get("/api/health")

    assert gateway_response.status_code == 200
    assert api_response.status_code == 200
    assert gateway_response.json() == {
        "status": api_response.json()["status"],
        "controlPlane": api_response.json()["control_plane"],
        "ownerPid": api_response.json()["owner_pid"],
        "lockPath": api_response.json()["lock_path"],
        "runtimeUpdate": api_response.json()["runtime_update"],
    }


def test_gateway_node_method_call_endpoint_supports_talk_config(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "talk.config", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"config": {}}


def test_gateway_node_method_call_endpoint_talk_config_enforces_secret_scope(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    bootstrap_app = create_app(app_settings)
    with TestClient(bootstrap_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Operator",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        owner_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Owner",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert operator_response.status_code == 200
    assert owner_response.status_code == 200

    operator_api_key = operator_response.json()["api_key"]
    owner_api_key = owner_response.json()["api_key"]

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        operator_talk_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {operator_api_key}"},
            json={
                "method": "talk.config",
                "params": {"includeSecrets": True},
            },
        )
        owner_talk_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "talk.config",
                "params": {"includeSecrets": True},
            },
        )

    assert operator_talk_response.status_code == 400
    assert "missing scope: operator.talk.secrets" in operator_talk_response.json()["detail"]
    assert owner_talk_response.status_code == 200
    assert owner_talk_response.json() == {"config": {}}


def test_gateway_node_method_call_endpoint_supports_tts_status_and_providers(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.status", "params": {}},
        )
        providers_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.providers", "params": {}},
        )

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["enabled"] is False
    assert status_payload["auto"] == "off"
    assert status_payload["provider"] is None
    assert status_payload["fallbackProvider"] is None
    assert status_payload["fallbackProviders"] == []
    assert status_payload["providerStates"] == []
    assert "prefsPath" in status_payload

    assert providers_response.status_code == 200
    assert providers_response.json() == {
        "providers": [],
        "active": None,
    }


def test_gateway_node_method_call_endpoint_tts_enable_fails_as_explicitly_unavailable(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.enable", "params": {}},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "TTS runtime not wired in OpenZues yet"


def test_gateway_node_method_call_endpoint_supports_models_list(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "models.list", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {
                "id": "gpt-5.4",
                "name": "gpt-5.4",
                "provider": "openai",
                "isDefault": True,
            },
            {
                "id": "gpt-5.4-mini",
                "name": "gpt-5.4-mini",
                "provider": "openai",
            },
        ]
    }


def test_gateway_node_method_call_endpoint_talk_speak_fails_as_explicitly_unavailable(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "talk.speak", "params": {"text": "Hello from talk mode."}},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Talk synthesis runtime not wired in OpenZues yet"


def test_gateway_node_method_call_endpoint_supports_config_schema_and_lookup(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        schema_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema", "params": {}},
        )
        lookup_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "assistantName"}},
        )

    assert schema_response.status_code == 200
    assert schema_response.json()["version"] == "openzues-control-ui-bootstrap-v1"
    assert schema_response.json()["schema"]["properties"]["assistantName"]["type"] == "string"

    assert lookup_response.status_code == 200
    assert lookup_response.json() == {
        "path": "assistantName",
        "schema": {
            "type": "string",
            "title": "Assistant Name",
        },
        "hint": {"label": "Assistant Name"},
        "hintPath": "assistantName",
        "children": [],
    }


def test_gateway_node_method_call_endpoint_config_schema_lookup_rejects_unknown_path(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "notReal"}},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "config schema path not found"


def test_gateway_node_method_call_endpoint_supports_tools_catalog(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tools.catalog", "params": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agentId"] == "openzues"
    assert payload["profiles"] == [
        {"id": "minimal", "label": "Minimal"},
        {"id": "coding", "label": "Coding"},
        {"id": "messaging", "label": "Messaging"},
        {"id": "full", "label": "Full"},
    ]
    group = payload["groups"][0]
    assert group["id"] == "openzues-toolsets"
    assert group["label"] == "OpenZues Toolsets"
    assert any(tool["id"] == "tts" for tool in group["tools"])


def test_gateway_node_method_call_endpoint_tools_effective_is_explicitly_unavailable(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "tools.effective",
                "params": {"sessionKey": "openzues:thread:demo"},
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Effective tool inventory is not wired in OpenZues yet"


def test_gateway_node_method_call_endpoint_supports_config_get(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        gateway_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.get", "params": {}},
        )
        api_response = client.get("/__openclaw/control-ui-config.json")

    assert gateway_response.status_code == 200
    assert api_response.status_code == 200
    assert gateway_response.json() == api_response.json()


def test_gateway_node_method_call_endpoint_supports_commands_list(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "commands.list", "params": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["commands"]
    assert any(command["name"] == "status" for command in payload["commands"])
    assert any(command["name"] == "browser.open" for command in payload["commands"])


def test_gateway_node_method_call_endpoint_commands_list_rejects_unknown_agent(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "commands.list",
                "params": {"agentId": "other-agent"},
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == 'unknown agent id "other-agent"'


def test_gateway_node_method_call_endpoint_supports_channels_status(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/completed"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                    "summary": "slack workspace-bot channel deploy-room",
                },
                "enabled": True,
            },
        )
        gateway_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "channels.status", "params": {}},
        )
        dashboard_response = client.get("/api/dashboard")

    assert route_response.status_code == 200
    assert gateway_response.status_code == 200
    assert dashboard_response.status_code == 200
    payload = gateway_response.json()
    dashboard_routes = dashboard_response.json()["ops_mesh"]["notification_routes"]
    assert payload["routes"] == dashboard_routes
    assert payload["routeCount"] == len(dashboard_routes)
    assert payload["enabledCount"] == sum(1 for route in dashboard_routes if route["enabled"])
    assert payload["conversationTargetCount"] == sum(
        1 for route in dashboard_routes if route["conversation_target"] is not None
    )


def test_gateway_node_method_call_endpoint_supports_system_presence(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-system-presence-node-1"),
        GatewayNodeConnect(
            client_id="mobile-node-1",
            device_id="node-1",
            client_mode="mobile",
            display_name="Builder Phone",
            platform="ios",
            version="1.2.3",
            device_family="iphone",
            model_identifier="iphone15,3",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1_700_000_000_000 - 5_000,
    )
    registry.remember(
        KnownNode(
            node_id="offline-node",
            display_name="Offline Node",
            platform="ios",
            client_id="offline-node",
            client_mode="mobile",
            paired=True,
            connected=False,
        )
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "system-presence", "params": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "entries" in payload
    assert isinstance(payload["entries"], list)
    assert len(payload["entries"]) == 2
    self_entry = next(
        entry for entry in payload["entries"] if entry.get("reason") == "self"
    )
    assert self_entry["deviceId"].startswith("gateway-")
    assert self_entry["instanceId"] == self_entry["deviceId"]
    assert self_entry["mode"] == "backend"
    assert self_entry["roles"] == ["operator"]
    node_entry = next(
        entry for entry in payload["entries"] if entry.get("deviceId") == "node-1"
    )
    assert node_entry == {
        "deviceId": "node-1",
        "instanceId": "mobile-node-1",
        "host": "Builder Phone",
        "ip": "10.0.0.5",
        "version": "1.2.3",
        "platform": "ios",
        "deviceFamily": "iphone",
        "modelIdentifier": "iphone15,3",
        "mode": "node",
        "reason": "node-connected",
        "ts": 1_699_999_995_000,
        "roles": ["node"],
        "scopes": [],
    }
    assert not any(entry.get("deviceId") == "offline-node" for entry in payload["entries"])
    assert (tmp_path / "data" / "settings" / "gateway-identity.json").exists()


def test_gateway_node_method_call_endpoint_supports_skills_bins(tmp_path, monkeypatch) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    skill_path = codex_home / "skills" / "skills-bins-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: skills-bins-test
description: skills bins api test
metadata:
  requires:
    bins:
      - git
  install:
    - bins:
        - uv
---
Body
""",
        encoding="utf-8",
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.bins", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"bins": ["git", "uv"]}


def test_gateway_node_method_call_endpoint_supports_skills_status(tmp_path, monkeypatch) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "skills-status-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: skills-status-test
description: skills status api test
platforms:
  - windows
metadata:
  skillKey: skills-status
  requires:
    bins:
      - missing-bin
  install:
    - id: node
      kind: node
      label: Install skills-status-test
      bins:
        - missing-bin
---
Body
""",
        encoding="utf-8",
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.status", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "workspaceDir": str(tmp_path),
        "managedSkillsDir": str(codex_home / "skills"),
        "skills": [
            {
                "name": "skills-status-test",
                "description": "skills status api test",
                "source": "codex-home",
                "bundled": True,
                "filePath": str(skill_path),
                "baseDir": str(skill_path.parent),
                "skillKey": "skills-status",
                "primaryEnv": None,
                "emoji": None,
                "homepage": None,
                "always": False,
                "disabled": False,
                "blockedByAllowlist": False,
                "eligible": False,
                "requirements": {
                    "bins": ["missing-bin"],
                    "env": [],
                    "config": [],
                    "os": ["windows"],
                },
                "missing": {
                    "bins": ["missing-bin"],
                    "env": [],
                    "config": [],
                    "os": [],
                },
                "configChecks": [],
                "install": [
                    {
                        "id": "node",
                        "kind": "node",
                        "label": "Install skills-status-test",
                        "bins": ["missing-bin"],
                    }
                ],
            }
        ],
    }


def test_gateway_node_method_call_endpoint_supports_skills_search_and_detail(
    tmp_path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "skills-search-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: Skills Search Test
description: GitHub workflow search detail api test
version: 1.2.3
platforms:
  - windows
metadata:
  systems:
    - codex
---
Body
""",
        encoding="utf-8",
    )
    os.utime(skill_path, (1_700_000_000, 1_700_000_000))
    slug = "local/codex-home/skills-search-test"
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        search_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.search",
                "params": {"query": "github", "limit": 10},
            },
        )
        detail_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.detail", "params": {"slug": slug}},
        )

    assert search_response.status_code == 200
    assert search_response.json() == {
        "results": [
            {
                "score": 1.0,
                "slug": slug,
                "displayName": "Skills Search Test",
                "summary": "GitHub workflow search detail api test",
                "version": "1.2.3",
                "updatedAt": 1_700_000_000,
            }
        ]
    }
    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "skill": {
            "slug": slug,
            "displayName": "Skills Search Test",
            "summary": "GitHub workflow search detail api test",
            "createdAt": 1_700_000_000,
            "updatedAt": 1_700_000_000,
        },
        "latestVersion": {
            "version": "1.2.3",
            "createdAt": 1_700_000_000,
        },
        "metadata": {
            "os": ["windows"],
            "systems": ["codex"],
        },
        "owner": {
            "handle": "local",
            "displayName": "Local Skill Catalog",
            "image": None,
        },
    }


def test_gateway_node_method_call_endpoint_surfaces_skills_install_update_unavailable(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        install_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.install",
                "params": {"source": "clawhub", "slug": "openclaw/example"},
            },
        )
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.update",
                "params": {"skillKey": "example-skill", "enabled": True},
            },
        )

    assert install_response.status_code == 503
    assert (
        install_response.json()["detail"]
        == "ClawHub skill install is not wired in OpenZues yet"
    )
    assert update_response.status_code == 503
    assert update_response.json()["detail"] == "Skill config patching is not wired in OpenZues yet"


def test_gateway_node_scoped_method_call_endpoint_surfaces_node_role_methods(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-node-role-1"),
        GatewayNodeConnect(
            client_id="live-node-role-1",
            device_id="node-role-1",
            platform="ios",
            commands=("canvas.present",),
        ),
    )
    queued = registry.enqueue_pending_action(
        node_id="node-role-1",
        command="canvas.present",
        params_json='{"screen":"main"}',
        idempotency_key="idem-node-role",
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        pull_response = client.post(
            "/api/gateway/nodes/node-role-1/method-call",
            json={"method": "node.pending.pull", "params": {}},
        )
        ack_response = client.post(
            "/api/gateway/nodes/node-role-1/method-call",
            json={"method": "node.pending.ack", "params": {"ids": [queued.id]}},
        )
        unavailable_response = client.post(
            "/api/gateway/nodes/node-role-1/method-call",
            json={
                "method": "node.canvas.capability.refresh",
                "params": {},
            },
        )

    assert pull_response.status_code == 200
    assert pull_response.json() == {
        "nodeId": "node-role-1",
        "actions": [
            {
                "id": queued.id,
                "command": "canvas.present",
                "paramsJSON": '{"screen":"main"}',
                "enqueuedAtMs": queued.enqueued_at_ms,
            }
        ],
    }
    assert ack_response.status_code == 200
    assert ack_response.json() == {
        "nodeId": "node-role-1",
        "ackedIds": [queued.id],
        "remainingCount": 0,
    }
    assert unavailable_response.status_code == 503
    assert "canvas host unavailable" in unavailable_response.json()["detail"]


def test_remote_node_scoped_method_call_requires_node_token(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/nodes/node-role-remote-1/method-call",
            json={"method": "node.pending.pull", "params": {}},
        )

    assert response.status_code == 401
    assert "node token" in response.json()["detail"]


def test_remote_node_scoped_method_call_requires_matching_pairing_token(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-node-role-remote-1"),
        GatewayNodeConnect(
            client_id="live-node-role-remote-1",
            device_id="node-role-remote-1",
            platform="ios",
            commands=("canvas.present",),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "node-role-remote-1",
                    "displayName": "Remote Node Role",
                    "platform": "ios",
                },
            },
        )
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.approve",
                "params": {"requestId": request_response.json()["request"]["requestId"]},
            },
        )

    assert request_response.status_code == 200
    assert approve_response.status_code == 200

    token = approve_response.json()["node"]["token"]
    queued = registry.enqueue_pending_action(
        node_id="node-role-remote-1",
        command="canvas.present",
        params_json='{"screen":"main"}',
        idempotency_key="idem-node-role-remote",
    )

    with TestClient(app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        invalid_token_response = client.post(
            "/api/gateway/nodes/node-role-remote-1/method-call",
            headers={"Authorization": "Bearer not-the-right-token"},
            json={"method": "node.pending.pull", "params": {}},
        )
        valid_token_response = client.post(
            "/api/gateway/nodes/node-role-remote-1/method-call",
            headers={"Authorization": f"Bearer {token}"},
            json={"method": "node.pending.pull", "params": {}},
        )

    assert invalid_token_response.status_code == 401
    assert "Unknown node token." == invalid_token_response.json()["detail"]

    assert valid_token_response.status_code == 200
    assert valid_token_response.json() == {
        "nodeId": "node-role-remote-1",
        "actions": [
            {
                "id": queued.id,
                "command": "canvas.present",
                "paramsJSON": '{"screen":"main"}',
                "enqueuedAtMs": queued.enqueued_at_ms,
            }
        ],
    }


def test_remote_node_event_endpoint_records_event(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    first_app = create_app(app_settings)

    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "node-event-remote-1",
                    "displayName": "Remote Event Node",
                    "platform": "ios",
                },
            },
        )
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.approve",
                "params": {"requestId": request_response.json()["request"]["requestId"]},
            },
        )

    assert request_response.status_code == 200
    assert approve_response.status_code == 200
    token = approve_response.json()["node"]["token"]

    remote_app = create_app(app_settings)
    registry = remote_app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-node-event-remote-1"),
        GatewayNodeConnect(
            client_id="live-node-event-remote-1",
            device_id="node-event-remote-1",
            platform="ios",
        ),
    )

    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/nodes/node-event-remote-1/method-call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "method": "node.event",
                "params": {
                    "event": "heartbeat",
                    "payload": {"ok": True, "source": "remote-node"},
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    database = Database(app_settings.db_path)
    asyncio.run(database.initialize())
    events = asyncio.run(database.list_events())
    assert len(events) == 1
    assert events[0]["method"] == "node.event"
    assert events[0]["payload"]["nodeId"] == "node-event-remote-1"
    assert events[0]["payload"]["event"] == "heartbeat"
    assert events[0]["payload"]["payload"] == {
        "ok": True,
        "source": "remote-node",
    }


def test_last_heartbeat_endpoint_returns_latest_recorded_heartbeat(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-last-heartbeat-node-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            client_mode="mobile",
            display_name="Builder Phone",
            platform="ios",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1_700_000_000_000 - 5_000,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        event_response = client.post(
            "/api/gateway/nodes/node-1/method-call",
            json={
                "method": "node.event",
                "params": {
                    "event": "heartbeat",
                    "payload": {"ok": True, "source": "api-node"},
                },
            },
        )
        heartbeat_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "last-heartbeat", "params": {}},
        )

    assert event_response.status_code == 200
    assert heartbeat_response.status_code == 200
    assert heartbeat_response.json() == {
        "heartbeat": {
            "nodeId": "node-1",
            "displayName": "Builder Phone",
            "platform": "ios",
            "event": "heartbeat",
            "payload": {"ok": True, "source": "api-node"},
            "payloadJSON": '{"ok": true, "source": "api-node"}',
            "createdAt": heartbeat_response.json()["heartbeat"]["createdAt"],
        }
    }
    assert isinstance(heartbeat_response.json()["heartbeat"]["createdAt"], str)


def test_last_heartbeat_endpoint_returns_none_without_recorded_heartbeat(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "last-heartbeat", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"heartbeat": None}


def test_remote_node_canvas_capability_refresh_returns_scoped_host_url(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    first_app = create_app(app_settings)

    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "node-canvas-remote-1",
                    "displayName": "Remote Canvas Node",
                    "platform": "ios",
                },
            },
        )
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.approve",
                "params": {"requestId": request_response.json()["request"]["requestId"]},
            },
        )

    assert request_response.status_code == 200
    assert approve_response.status_code == 200
    token = approve_response.json()["node"]["token"]

    remote_app = create_app(app_settings)
    registry = remote_app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-node-canvas-remote-1"),
        GatewayNodeConnect(
            client_id="live-node-canvas-remote-1",
            device_id="node-canvas-remote-1",
            platform="ios",
            canvas_host_url="http://127.0.0.1:18789",
        ),
    )

    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/nodes/node-canvas-remote-1/method-call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "method": "node.canvas.capability.refresh",
                "params": {},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["canvasCapability"], str)
    assert payload["canvasCapabilityExpiresAtMs"] > 0
    assert payload["canvasHostUrl"] == (
        f"http://127.0.0.1:18789/__openclaw__/cap/{payload['canvasCapability']}"
    )
