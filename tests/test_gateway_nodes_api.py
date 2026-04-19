from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.schemas import DashboardView
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.gateway_node_methods import GatewayNodeMethodService
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.gateway_node_service import GatewayNodeService
from openzues.services.gateway_skill_clawhub import GatewaySkillClawHubService
from openzues.services.gateway_skill_install import GatewaySkillInstallService
from openzues.services.gateway_tts_runtime import (
    GatewayTtsRuntimeService,
    GatewayTtsSynthesisResult,
)
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.hub import BroadcastHub
from openzues.services.manager import InstanceRuntime
from openzues.services.session_keys import build_launch_session_key, resolve_thread_session_keys
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


class _FakeOpsMeshService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []
        self.deleted_task_ids: list[int] = []

    async def run_task_blueprint_now(self, task_id: int, *, trigger: str = "manual") -> object:
        self.calls.append((task_id, trigger))
        return SimpleNamespace(id=52)

    async def delete_task_blueprint(self, task_id: int) -> None:
        self.deleted_task_ids.append(task_id)

    async def list_notification_route_views(self) -> list[object]:
        return []

    async def handle_mission_event(self, event_type: str, event: dict[str, object]) -> None:
        del event_type, event

    async def close(self) -> None:
        return None


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


def test_create_app_wires_managed_node_talk_mode_snapshot_only_on_fresh_connect(
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
        name="Managed Talk Mode Node",
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
            "talk.mode",
            {"enabled": True, "phase": "listening"},
        )
        assert set_result == {
            "enabled": True,
            "phase": "listening",
        }

        runtime.connected = True
        client.portal.call(client.app.state.gateway_node_service.sync)
        client.portal.call(client.app.state.gateway_node_service.sync)
        runtime.connected = False
        client.portal.call(client.app.state.gateway_node_service.sync)
        runtime.connected = True
        client.portal.call(client.app.state.gateway_node_service.sync)

    talk_mode_events = [entry for entry in sent_events if entry["event"] == "talk.mode"]

    assert talk_mode_events == [
        {
            "node_id": "7",
            "event": "talk.mode",
            "payload": {
                "enabled": True,
                "phase": "listening",
            },
        },
        {
            "node_id": "7",
            "event": "talk.mode",
            "payload": {
                "enabled": True,
                "phase": "listening",
            },
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


def test_gateway_node_method_call_endpoint_supports_talk_mode(tmp_path) -> None:
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
                "method": "talk.mode",
                "params": {"enabled": True, "phase": "listening"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "phase": "listening",
    }


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
    assert status_payload["providerStates"] == [
        {
            "id": "elevenlabs",
            "label": "ElevenLabs",
            "available": False,
            "selected": False,
        },
        {
            "id": "microsoft",
            "label": "Microsoft",
            "available": True,
            "selected": False,
        },
        {
            "id": "minimax",
            "label": "MiniMax",
            "available": False,
            "selected": False,
        },
        {
            "id": "openai",
            "label": "OpenAI",
            "available": False,
            "selected": False,
        },
    ]
    assert "prefsPath" in status_payload

    assert providers_response.status_code == 200
    assert providers_response.json() == {
        "providers": ["elevenlabs", "microsoft", "minimax", "openai"],
        "active": None,
    }


def test_gateway_node_method_call_endpoint_supports_local_tts_pref_mutations(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        enable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.enable", "params": {}},
        )
        provider_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.setProvider", "params": {"provider": "edge"}},
        )

    reloaded_app = create_app(app_settings)
    with TestClient(reloaded_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.status", "params": {}},
        )
        providers_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.providers", "params": {}},
        )

    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True
    assert enable_response.json()["auto"] == "on"
    assert provider_response.status_code == 200
    assert provider_response.json()["provider"] == "microsoft"
    assert status_response.status_code == 200
    assert status_response.json()["enabled"] is True
    assert status_response.json()["provider"] == "microsoft"
    assert providers_response.status_code == 200
    assert providers_response.json() == {
        "providers": ["elevenlabs", "microsoft", "minimax", "openai"],
        "active": "microsoft",
    }


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
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            tts_runtime_service=GatewayTtsRuntimeService(enabled=False),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "talk.speak", "params": {"text": "Hello from talk mode."}},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Talk synthesis runtime not wired in OpenZues yet"


def test_gateway_node_method_call_endpoint_supports_talk_speak_when_runtime_is_wired(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    synthesized_path = tmp_path / "spoken.wav"
    synthesized_bytes = b"RIFFtalk-api"
    synthesized_path.write_bytes(synthesized_bytes)
    observed: dict[str, object] = {}

    def fake_convert(
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        observed.update(
            {
                "text": text,
                "channel": channel,
                "provider": provider,
                "model_id": model_id,
                "voice_id": voice_id,
            }
        )
        return GatewayTtsSynthesisResult(
            audio_path=str(synthesized_path),
            provider="microsoft",
            output_format="wav",
            voice_compatible=True,
        )

    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            tts_runtime_service=GatewayTtsRuntimeService(
                data_dir=tmp_path / "data",
                convert_runner=fake_convert,
            ),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "talk.speak",
                "params": {
                    "text": "Hello from talk mode.",
                    "provider": "edge",
                    "voiceId": "Microsoft Zira Desktop",
                    "outputFormat": "wav",
                    "rateWpm": 180,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "audioBase64": base64.b64encode(synthesized_bytes).decode("ascii"),
        "provider": "microsoft",
        "outputFormat": "wav",
        "voiceCompatible": True,
        "mimeType": "audio/wav",
        "fileExtension": ".wav",
    }
    assert observed == {
        "text": "Hello from talk mode.",
        "channel": None,
        "provider": "microsoft",
        "model_id": None,
        "voice_id": "Microsoft Zira Desktop",
    }


def test_gateway_node_method_call_endpoint_supports_tts_convert_when_runtime_is_wired(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    synthesized_path = tmp_path / "converted.wav"
    synthesized_path.write_bytes(b"RIFFconverted-wave")
    observed: dict[str, object] = {}

    def fake_convert(
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        observed.update(
            {
                "text": text,
                "channel": channel,
                "provider": provider,
                "model_id": model_id,
                "voice_id": voice_id,
            }
        )
        return GatewayTtsSynthesisResult(
            audio_path=str(synthesized_path),
            provider="microsoft",
            output_format="wav",
            voice_compatible=True,
        )

    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            tts_runtime_service=GatewayTtsRuntimeService(
                data_dir=tmp_path / "data",
                convert_runner=fake_convert,
            ),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "tts.convert",
                "params": {
                    "text": "Hello from API TTS",
                    "channel": "assistant",
                    "provider": "edge",
                    "modelId": "ignored-local-model",
                    "voiceId": "Microsoft Zira Desktop",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "audioPath": str(synthesized_path),
        "provider": "microsoft",
        "outputFormat": "wav",
        "voiceCompatible": True,
    }
    assert observed == {
        "text": "Hello from API TTS",
        "channel": "assistant",
        "provider": "microsoft",
        "model_id": "ignored-local-model",
        "voice_id": "Microsoft Zira Desktop",
    }


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


def test_gateway_node_method_call_endpoint_supports_tools_effective_with_bootstrap_toolsets(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_bootstrap(
                setup_mode="local",
                setup_flow="quickstart",
                route_binding_mode="saved_lane",
                preferred_instance_id=None,
                preferred_project_id=None,
                team_id=None,
                operator_id=None,
                task_blueprint_id=None,
                default_cwd=str(tmp_path),
                bootstrap_roles=[],
                bootstrap_scopes=[],
                model="gpt-5.4",
                max_turns=4,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=["messaging", "clarify"],
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "tools.effective",
                "params": {
                    "sessionKey": build_launch_session_key(
                        mode="saved_lane",
                        preferred_instance_id=None,
                        task_id=None,
                        project_id=None,
                        operator_id=None,
                    ),
                    "agentId": "main",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["agentId"] == "main"
    assert payload["profile"] == "messaging"
    assert len(payload["groups"]) == 1
    assert payload["groups"][0]["id"] == "core"
    assert [tool["id"] for tool in payload["groups"][0]["tools"]] == [
        "messaging",
        "clarify",
    ]


def test_gateway_node_method_call_endpoint_supports_chat_history() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-history-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Need the latest parity checkpoint.",
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The status bridge is landed and verified.",
                session_key="openzues:thread:demo",
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.history",
                "params": {"sessionKey": "openzues:thread:demo", "limit": 2},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "sessionKey": "openzues:thread:demo",
        "sessionId": None,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the latest parity checkpoint."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The status bridge is landed and verified."}],
            },
        ],
        "thinkingLevel": None,
        "fastMode": None,
        "verboseLevel": None,
    }


def test_gateway_node_method_call_endpoint_supports_chat_send() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "thinking": "low",
                    "timeoutMs": 30_000,
                    "idempotencyKey": "run-chat-send-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {"runId": "run-chat-send-1", "status": "ok"}
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


def test_gateway_node_method_call_endpoint_supports_sessions_send() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-send-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "status",
                    "thinking": "low",
                    "timeoutMs": 30_000,
                    "idempotencyKey": "run-session-send-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {"runId": "run-session-send-1", "status": "ok"}
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


def test_gateway_node_method_call_endpoint_sessions_steer_interrupts_tracked_runtime(
    tmp_path,
    monkeypatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        
        async def fake_interrupt_turn(instance_id: int, thread_id: str) -> dict[str, object]:
            return {"ok": True, "instanceId": instance_id, "threadId": thread_id}

        monkeypatch.setattr(client.app.state.manager, "interrupt_turn", fake_interrupt_turn)
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "status",
                    "idempotencyKey": "run-session-send-1",
                },
            },
        )
        assert send_response.status_code == 200
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Steer Loop",
                objective="Interrupt then continue the live control chat thread.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-steer-1",
                session_key="openzues:thread:demo",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.steer",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "redirect",
                    "idempotencyKey": "run-session-steer-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {"runId": "run-session-steer-1", "status": "ok"}
    assert [message["role"] for message in messages[-4:]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[-2]["content"] == "redirect"


def test_gateway_node_method_call_endpoint_sessions_abort_interrupts_tracked_runtime(
    tmp_path,
    monkeypatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-abort-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        
        async def fake_interrupt_turn(instance_id: int, thread_id: str) -> dict[str, object]:
            return {"ok": True, "instanceId": instance_id, "threadId": thread_id}

        monkeypatch.setattr(client.app.state.manager, "interrupt_turn", fake_interrupt_turn)
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "status",
                    "idempotencyKey": "run-session-send-1",
                },
            },
        )
        assert send_response.status_code == 200
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Abort Loop",
                objective="Interrupt the live control chat thread.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-abort-1",
                session_key="openzues:thread:demo",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.abort",
                "params": {
                    "key": "openzues:thread:demo",
                    "runId": "run-session-send-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "abortedRunId": "run-session-send-1",
        "status": "aborted",
    }


def test_gateway_node_method_call_endpoint_publishes_sessions_changed_after_sessions_abort(
    tmp_path,
    monkeypatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-abort-event-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-abort-event-1",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)

        async def fake_interrupt_turn(instance_id: int, thread_id: str) -> dict[str, object]:
            return {"ok": True, "instanceId": instance_id, "threadId": thread_id}

        monkeypatch.setattr(client.app.state.manager, "interrupt_turn", fake_interrupt_turn)
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": session_key,
                    "message": "status",
                    "idempotencyKey": "run-session-send-1",
                },
            },
        )
        assert send_response.status_code == 200
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Abort Event Loop",
                objective="Interrupt the live control chat thread.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-abort-event-1",
                session_key=session_key,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.abort",
                "params": {
                    "key": session_key,
                    "runId": "run-session-send-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "abortedRunId": "run-session-send-1",
        "status": "aborted",
    }
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    abort_events = [
        event
        for event in sessions_changed
        if isinstance(event.get("payload"), dict) and event["payload"].get("reason") == "abort"
    ]
    assert len(abort_events) == 1
    assert abort_events[0] == {
        "type": "gateway_event",
        "event": "sessions.changed",
        "payload": {
            "sessionKey": session_key,
            "reason": "abort",
            "ts": abort_events[0]["payload"]["ts"],
            "updatedAt": abort_events[0]["payload"]["updatedAt"],
            "sessionId": "thread-abort-event-1",
            "kind": "thread",
            "subject": "Interrupt the live control chat thread.",
            "displayName": "OpenZues Control Chat Thread",
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "contextTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "space": None,
        },
        "createdAt": abort_events[0]["createdAt"],
    }
    assert isinstance(abort_events[0]["createdAt"], str)
    assert isinstance(abort_events[0]["payload"]["ts"], int)
    assert isinstance(abort_events[0]["payload"]["updatedAt"], int)


def test_gateway_node_method_call_endpoint_publishes_session_message_events_after_sessions_send(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-message-event-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-session-message-1",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Session Message Loop",
                objective="Inspect gateway transcript parity.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-session-message-1",
                session_key=session_key,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": session_key,
                    "message": "status",
                    "idempotencyKey": "run-session-message-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {"runId": "run-session-message-1", "status": "ok"}
    session_message_events = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "session.message"
    ]
    assert len(session_message_events) == 2

    user_events = [
        event
        for event in session_message_events
        if isinstance(event.get("payload"), dict)
        and isinstance(event["payload"].get("message"), dict)
        and event["payload"]["message"].get("role") == "user"
    ]
    assert len(user_events) == 1
    assert user_events[0]["type"] == "gateway_event"
    assert user_events[0]["event"] == "session.message"
    user_payload = user_events[0]["payload"]
    assert user_payload["sessionKey"] == session_key
    assert user_payload["messageId"] == "1"
    assert user_payload["messageSeq"] == 1
    assert user_payload["sessionId"] == "thread-session-message-1"
    assert user_payload["kind"] == "thread"
    assert user_payload["subject"] == "Inspect gateway transcript parity."
    assert user_payload["displayName"] == "OpenZues Control Chat Thread"
    assert user_payload["modelProvider"] == "openai"
    assert user_payload["model"] == "gpt-5.4"
    assert user_payload["message"] == {
        "id": "1",
        "role": "user",
        "content": [{"type": "text", "text": "status"}],
    }
    assert isinstance(user_events[0]["createdAt"], str)
    assert isinstance(user_payload["updatedAt"], int)

    assistant_events = [
        event
        for event in session_message_events
        if isinstance(event.get("payload"), dict)
        and isinstance(event["payload"].get("message"), dict)
        and event["payload"]["message"].get("role") == "assistant"
    ]
    assert len(assistant_events) == 1
    assistant_payload = assistant_events[0]["payload"]
    assert assistant_payload["sessionKey"] == session_key
    assert assistant_payload["messageId"] == "2"
    assert assistant_payload["messageSeq"] == 2
    assert assistant_payload["sessionId"] == "thread-session-message-1"
    assert assistant_payload["kind"] == "thread"
    assert assistant_payload["subject"] == "Inspect gateway transcript parity."
    assert assistant_payload["displayName"] == "OpenZues Control Chat Thread"
    assert assistant_payload["modelProvider"] == "openai"
    assert assistant_payload["model"] == "gpt-5.4"
    assert assistant_payload["message"]["id"] == "2"
    assert assistant_payload["message"]["role"] == "assistant"
    assert isinstance(assistant_payload["message"]["content"], list)
    assert assistant_payload["message"]["content"]
    assert isinstance(assistant_events[0]["createdAt"], str)
    assert isinstance(assistant_payload["updatedAt"], int)


def test_gateway_node_method_call_endpoint_publishes_phase_message_changed_after_sessions_send(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-message-phase-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-message-phase-1",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Message Phase Loop",
                objective="Track transcript-phase session changes.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-message-phase-1",
                session_key=session_key,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": session_key,
                    "message": "status",
                    "idempotencyKey": "run-message-phase-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {"runId": "run-message-phase-1", "status": "ok"}
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    message_phase_events = [
        event
        for event in sessions_changed
        if isinstance(event.get("payload"), dict) and event["payload"].get("phase") == "message"
    ]
    assert len(message_phase_events) == 2

    first_payload = message_phase_events[0]["payload"]
    assert first_payload == {
        "sessionKey": session_key,
        "phase": "message",
        "ts": first_payload["ts"],
        "messageId": "1",
        "messageSeq": 1,
        "updatedAt": first_payload["updatedAt"],
        "sessionId": "thread-message-phase-1",
        "kind": "thread",
        "subject": "Track transcript-phase session changes.",
        "displayName": "OpenZues Control Chat Thread",
        "systemSent": None,
        "abortedLastRun": None,
        "thinkingLevel": None,
        "verboseLevel": None,
        "inputTokens": None,
        "outputTokens": None,
        "totalTokens": None,
        "contextTokens": None,
        "modelProvider": "openai",
        "model": "gpt-5.4",
        "space": None,
    }
    assert isinstance(first_payload["ts"], int)
    assert isinstance(first_payload["updatedAt"], int)

    second_payload = message_phase_events[1]["payload"]
    assert second_payload["sessionKey"] == session_key
    assert second_payload["phase"] == "message"
    assert second_payload["messageId"] == "2"
    assert second_payload["messageSeq"] == 2
    assert second_payload["sessionId"] == "thread-message-phase-1"
    assert second_payload["kind"] == "thread"
    assert second_payload["subject"] == "Track transcript-phase session changes."
    assert second_payload["displayName"] == "OpenZues Control Chat Thread"
    assert second_payload["modelProvider"] == "openai"
    assert second_payload["model"] == "gpt-5.4"
    assert isinstance(second_payload["ts"], int)
    assert isinstance(second_payload["updatedAt"], int)


def test_gateway_node_method_call_endpoint_sessions_usage_returns_bounded_summary() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        main_session_key = build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        )
        session_key = resolve_thread_session_keys(
            base_session_key=main_session_key,
            thread_id="thread-usage-api",
        ).session_key
        asyncio.run(
            database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"label": "Parity Usage API Session"},
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Summarize the usage totals through the gateway API.",
                session_key=session_key,
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The gateway usage summary is ready.",
                session_key=session_key,
            )
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="Usage parity API summary",
                objective="Summarize the current API usage seam.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-api",
                session_key=session_key,
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                total_tokens=1200,
                output_tokens=220,
                reasoning_tokens=90,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.usage",
                "params": {
                    "key": session_key,
                    "startDate": "2026-04-01",
                    "endDate": "2026-04-18",
                    "mode": "specific",
                    "utcOffset": "UTC-5",
                    "limit": 50,
                    "includeContextWeight": False,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["startDate"] == "2026-04-01"
    assert payload["endDate"] == "2026-04-18"
    assert payload["totals"]["totalTokens"] == 1200
    assert payload["aggregates"]["messages"] == {
        "total": 2,
        "user": 1,
        "assistant": 1,
        "toolCalls": 0,
        "toolResults": 0,
        "errors": 0,
    }
    assert len(payload["sessions"]) == 1
    session_payload = payload["sessions"][0]
    assert session_payload["key"] == session_key
    assert session_payload["label"] == "Parity Usage API Session"
    assert session_payload["sessionId"] == "thread-usage-api"
    assert session_payload["modelProvider"] == "openai"
    assert session_payload["model"] == "gpt-5.4"
    assert session_payload["usage"]["totalTokens"] == 1200
    assert session_payload["usage"]["output"] == 220


def test_gateway_node_method_call_endpoint_sessions_reset_clears_transcript() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-reset-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-reset-api",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"label": "Parity Reset Session"},
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Please clear this API transcript.",
                session_key=session_key,
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The API transcript is still present before reset.",
                session_key=session_key,
            )
        )
        other_session_key = resolve_thread_session_keys(
            base_session_key=main_session_key,
            thread_id="thread-other-api",
        ).session_key
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="Noise from another API session.",
                session_key=other_session_key,
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.reset",
                "params": {
                    "key": session_key,
                    "reason": "reset",
                },
            },
        )
        history_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.history",
                "params": {"sessionKey": session_key, "limit": 10},
            },
        )
        messages_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.get",
                "params": {"sessionKey": session_key, "limit": 10},
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["key"] == session_key
    assert payload["entry"]["key"] == session_key
    assert payload["entry"]["kind"] == "thread"
    assert payload["entry"]["sessionId"] == "thread-reset-api"
    assert payload["entry"]["label"] == "Parity Reset Session"
    assert isinstance(payload["entry"]["updatedAt"], int)
    assert payload["entry"]["updatedAt"] > 0

    assert history_response.status_code == 200
    assert history_response.json()["messages"] == []

    assert messages_response.status_code == 200
    assert messages_response.json() == {"messages": []}

    assert list_response.status_code == 200
    assert [session["key"] for session in list_response.json()["sessions"]] == [
        main_session_key,
        session_key,
    ]

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    reset_events = [
        event
        for event in sessions_changed
        if isinstance(event.get("payload"), dict)
        and event["payload"].get("sessionKey") == session_key
        and isinstance(event["payload"].get("reason"), str)
    ]
    assert [event["payload"]["reason"] for event in reset_events] == ["reset"]


def test_gateway_node_method_call_endpoint_sessions_delete_removes_metadata_session() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-delete-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-delete-api",
    ).session_key
    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-other-api",
    ).session_key
    archive_dir = app_settings.db_path.parent / "gateway-session-archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stale_archive = archive_dir / "other-session-deleted-20260301T000000Z.jsonl"
    recent_archive = archive_dir / "other-session-deleted-20260417T000000Z.jsonl"
    ignored_file = archive_dir / "readme.txt"
    stale_archive.write_text("stale\n", encoding="utf-8")
    recent_archive.write_text("recent\n", encoding="utf-8")
    ignored_file.write_text("ignore\n", encoding="utf-8")

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"label": "Parity Delete Session"},
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Please delete this API transcript.",
                session_key=session_key,
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The API transcript is still present before delete.",
                session_key=session_key,
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="Noise from another API session.",
                session_key=other_session_key,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.delete",
                "params": {"key": session_key},
            },
        )
        history_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.history",
                "params": {"sessionKey": session_key, "limit": 10},
            },
        )
        messages_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.get",
                "params": {"sessionKey": session_key, "limit": 10},
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )
        resolve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "sessions.resolve", "params": {"key": session_key}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["key"] == session_key
    assert payload["deleted"] is True
    assert len(payload["archived"]) == 1
    archived_path = Path(payload["archived"][0])
    assert archived_path.exists()
    archived_lines = archived_path.read_text(encoding="utf-8").splitlines()
    assert len(archived_lines) == 2
    archived_records = [json.loads(line) for line in archived_lines]
    assert [record["role"] for record in archived_records] == ["user", "assistant"]
    assert all(record["sessionKey"] == session_key for record in archived_records)
    assert all(record["reason"] == "deleted" for record in archived_records)
    assert not stale_archive.exists()
    assert recent_archive.exists()
    assert ignored_file.exists()

    assert history_response.status_code == 200
    assert history_response.json()["messages"] == []

    assert messages_response.status_code == 200
    assert messages_response.json() == {"messages": []}

    assert list_response.status_code == 200
    assert [session["key"] for session in list_response.json()["sessions"]] == [main_session_key]

    assert resolve_response.status_code == 400
    assert resolve_response.json()["detail"] == "unknown session key"

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    delete_events = [
        event
        for event in sessions_changed
        if isinstance(event.get("payload"), dict)
        and event["payload"].get("sessionKey") == session_key
        and isinstance(event["payload"].get("reason"), str)
    ]
    assert [event["payload"]["reason"] for event in delete_events] == ["delete"]


def test_gateway_node_method_call_endpoint_sessions_compact_fails_explicitly_when_unwired() -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compact-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                    "maxLines": 200,
                },
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "sessions.compact is unavailable until control chat compaction is wired"
    )


def test_sessions_compaction_restore_api_is_explicitly_unavailable(
) -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-restore-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.compaction.restore",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": "checkpoint-001",
                },
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "sessions.compaction.restore is unavailable until control chat compaction restore is wired"
    )


def test_gateway_node_method_call_endpoint_sessions_compaction_list_fails_explicitly_when_unwired(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-list-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.compaction.list",
                "params": {"key": "openzues:thread:demo"},
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "sessions.compaction.list is unavailable until control chat compaction "
        "checkpoints are wired"
    )


def test_gateway_node_method_call_endpoint_sessions_compaction_get_fails_explicitly_when_unwired(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-get-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.compaction.get",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": "checkpoint-001",
                },
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "sessions.compaction.get is unavailable until control chat compaction checkpoints are wired"
    )


def test_gateway_node_method_call_endpoint_sessions_compaction_branch_fails_explicitly_when_unwired(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-branch-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.compaction.branch",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": "checkpoint-001",
                },
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "sessions.compaction.branch is unavailable until control chat compaction branching is wired"
    )


def test_gateway_node_method_call_endpoint_sessions_preview_returns_current_session_items() -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-preview-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Ship parity.",
                mission_id=None,
                session_key=session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Preview ready.",
                mission_id=None,
                session_key=session_key,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.preview",
                "params": {
                    "keys": [session_key, "openzues:thread:missing"],
                    "limit": 12,
                    "maxChars": 240,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["ts"], int)
    assert payload["previews"] == [
        {
            "key": session_key,
            "status": "ok",
            "items": [
                {"role": "user", "text": "Ship parity."},
                {"role": "assistant", "text": "Preview ready."},
            ],
        },
        {
            "key": "openzues:thread:missing",
            "status": "missing",
            "items": [],
        },
    ]


def test_sessions_messages_subscribe_api_returns_stateless_ack_without_connection_context() -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-messages-subscribe-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.messages.subscribe",
                "params": {"key": "  MAIN  "},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": False, "key": "agent:main:main"}


def test_sessions_messages_subscribe_api_acknowledges_client_scoped_subscription() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-messages-subscribe-client-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            headers={"X-OpenZues-Client-Id": "client-1"},
            json={
                "method": "sessions.messages.subscribe",
                "params": {"key": "  MAIN  "},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": True, "key": "agent:main:main"}


def test_sessions_messages_unsubscribe_api_returns_stateless_ack_without_connection_context() -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-messages-unsubscribe-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.messages.unsubscribe",
                "params": {"key": "  MAIN  "},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": False, "key": "agent:main:main"}


def test_sessions_subscribe_api_returns_stateless_ack_without_connection_context() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-subscribe-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "sessions.subscribe", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": False}


def test_sessions_messages_subscribe_api_filters_websocket_delivery_by_client_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-message-websocket-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = "openzues:thread:demo"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Session Message Subscription Loop",
                objective="Inspect websocket session message subscription parity.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-session-message-subscription-1",
                session_key=session_key,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )

        with client.websocket_connect("/ws?clientId=client-message") as websocket:
            subscribe_response = client.post(
                "/api/gateway/node-methods/call",
                headers={"X-OpenZues-Client-Id": "client-message"},
                json={
                    "method": "sessions.messages.subscribe",
                    "params": {"key": session_key},
                },
            )
            send_response = client.post(
                "/api/gateway/node-methods/call",
                json={
                    "method": "sessions.send",
                    "params": {
                        "key": session_key,
                        "message": "status",
                        "idempotencyKey": "run-session-message-subscription-1",
                    },
                },
            )
            event = websocket.receive_json()

    assert subscribe_response.status_code == 200
    assert subscribe_response.json() == {"subscribed": True, "key": session_key}
    assert send_response.status_code == 200
    assert send_response.json() == {"runId": "run-session-message-subscription-1", "status": "ok"}
    assert event["type"] == "gateway_event"
    assert event["event"] == "session.message"
    assert event["payload"]["sessionKey"] == session_key


def test_sessions_subscribe_api_acknowledges_client_scoped_subscription() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-subscribe-client-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            headers={"X-OpenZues-Client-Id": "client-1"},
            json={"method": "sessions.subscribe", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": True}


def test_sessions_subscribe_api_filters_websocket_delivery_by_client_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-changed-websocket-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-subscribe-websocket-delete",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"label": "Parity Subscribe Session"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Delete this transcript after subscribing.",
                session_key=session_key,
            )
        )

        with client.websocket_connect("/ws?clientId=client-session") as websocket:
            subscribe_response = client.post(
                "/api/gateway/node-methods/call",
                headers={"X-OpenZues-Client-Id": "client-session"},
                json={"method": "sessions.subscribe", "params": {}},
            )
            delete_response = client.post(
                "/api/gateway/node-methods/call",
                json={"method": "sessions.delete", "params": {"key": session_key}},
            )
            event = websocket.receive_json()

    assert subscribe_response.status_code == 200
    assert subscribe_response.json() == {"subscribed": True}
    assert delete_response.status_code == 200
    delete_payload = delete_response.json()
    assert delete_payload["ok"] is True
    assert delete_payload["key"] == session_key
    assert delete_payload["deleted"] is True
    assert len(delete_payload["archived"]) == 1
    archived_path = Path(delete_payload["archived"][0])
    assert archived_path.exists()
    assert event["type"] == "gateway_event"
    assert event["event"] == "sessions.changed"
    assert event["payload"]["sessionKey"] == session_key
    assert event["payload"]["reason"] == "delete"


def test_sessions_unsubscribe_api_returns_stateless_ack_without_connection_context() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-unsubscribe-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "sessions.unsubscribe", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"subscribed": False}


def test_sessions_create_api_registers_session_and_sends_initial_message() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-create-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    app = create_app(app_settings, hub=hub)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    created_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-created-api",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.create",
                "params": {
                    "key": created_session_key,
                    "label": "Parity Session",
                    "model": "gpt-5.4-mini",
                    "parentSessionKey": main_session_key,
                    "message": "Ship parity.",
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )
        history_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.history",
                "params": {"sessionKey": created_session_key, "limit": 5},
            },
        )
        resolve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"key": created_session_key},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["key"] == created_session_key
    assert payload["sessionId"] == "thread-created-api"
    assert payload["runStarted"] is True
    assert payload["status"] == "ok"
    assert isinstance(payload["runId"], str)
    assert payload["entry"]["key"] == created_session_key
    assert payload["entry"]["kind"] == "thread"
    assert payload["entry"]["displayName"] == "OpenZues Control Chat Thread"
    assert payload["entry"]["sessionId"] == "thread-created-api"
    assert payload["entry"]["modelProvider"] == "openai"
    assert payload["entry"]["model"] == "gpt-5.4-mini"
    assert payload["entry"]["label"] == "Parity Session"
    assert payload["entry"]["parentSessionKey"] == main_session_key
    assert isinstance(payload["entry"]["updatedAt"], int)
    assert payload["entry"]["updatedAt"] > 0

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert [session["key"] for session in list_payload["sessions"]] == [
        main_session_key,
        created_session_key,
    ]

    assert history_response.status_code == 200
    history_messages = history_response.json()["messages"]
    assert history_messages[0] == {
        "role": "user",
        "content": [{"type": "text", "text": "Ship parity."}],
    }
    assert history_messages[1]["role"] == "assistant"
    assert isinstance(history_messages[1]["content"], list)
    assert history_messages[1]["content"]
    assert history_messages[1]["content"][0]["type"] == "text"
    assert isinstance(history_messages[1]["content"][0]["text"], str)
    assert history_messages[1]["content"][0]["text"]

    assert resolve_response.status_code == 200
    assert resolve_response.json() == {"ok": True, "key": created_session_key}

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    create_send_events = [
        event
        for event in sessions_changed
        if isinstance(event.get("payload"), dict)
        and event["payload"].get("sessionKey") == created_session_key
        and isinstance(event["payload"].get("reason"), str)
    ]
    assert [event["payload"]["reason"] for event in create_send_events] == ["create", "send"]


def test_sessions_patch_api_persists_current_session_metadata_and_surfaces_it() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-patch-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Patch the live control chat session.",
                session_key=current_session_key,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.patch",
                "params": {
                    "key": current_session_key,
                    "label": "Parity Session",
                    "thinkingLevel": "low",
                    "fastMode": True,
                    "verboseLevel": "high",
                    "responseUsage": "tokens",
                    "model": "gpt-5.4-mini",
                },
            },
        )
        sessions_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )
        history_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.history",
                "params": {"sessionKey": current_session_key, "limit": 5},
            },
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["path"] == str(app_settings.db_path)
    assert response.json()["key"] == current_session_key
    assert response.json()["resolved"] == {"modelProvider": "openai", "model": "gpt-5.4-mini"}
    assert response.json()["entry"]["label"] == "Parity Session"
    assert response.json()["entry"]["thinkingLevel"] == "low"
    assert response.json()["entry"]["fastMode"] is True
    assert response.json()["entry"]["verboseLevel"] == "high"
    assert response.json()["entry"]["responseUsage"] == "tokens"
    assert response.json()["entry"]["model"] == "gpt-5.4-mini"

    assert sessions_response.status_code == 200
    assert sessions_response.json()["sessions"] == [
        {
            "key": current_session_key,
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": sessions_response.json()["sessions"][0]["updatedAt"],
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": "low",
            "fastMode": True,
            "verboseLevel": "high",
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4-mini",
            "contextTokens": None,
            "label": "Parity Session",
            "responseUsage": "tokens",
        }
    ]

    assert history_response.status_code == 200
    assert history_response.json()["thinkingLevel"] == "low"
    assert history_response.json()["fastMode"] is True
    assert history_response.json()["verboseLevel"] == "high"


def test_gateway_node_method_call_endpoint_sessions_usage_timeseries_returns_bounded_points() -> (
    None
):
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-timeseries-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        main_session_key = build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        )
        session_key = resolve_thread_session_keys(
            base_session_key=main_session_key,
            thread_id="thread-usage-timeseries-api",
        ).session_key
        first_mission_id = asyncio.run(
            database.create_mission(
                name="Usage timeseries API first slice",
                objective="Record the first API usage point.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-timeseries-api",
                session_key=session_key,
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                first_mission_id,
                total_tokens=300,
                output_tokens=80,
            )
        )
        second_mission_id = asyncio.run(
            database.create_mission(
                name="Usage timeseries API second slice",
                objective="Record the second API usage point.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-timeseries-api",
                session_key=session_key,
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                second_mission_id,
                total_tokens=700,
                output_tokens=180,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.usage.timeseries",
                "params": {"key": session_key},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessionId"] == "thread-usage-timeseries-api"
    assert len(payload["points"]) == 2
    assert payload["points"][0]["input"] == 220
    assert payload["points"][0]["output"] == 80
    assert payload["points"][0]["totalTokens"] == 300
    assert payload["points"][0]["cumulativeTokens"] == 300
    assert payload["points"][1]["input"] == 520
    assert payload["points"][1]["output"] == 180
    assert payload["points"][1]["totalTokens"] == 700
    assert payload["points"][1]["cumulativeTokens"] == 1000


def test_gateway_node_method_call_endpoint_sessions_usage_logs_returns_bounded_entries() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-logs-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        main_session_key = build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        )
        session_key = resolve_thread_session_keys(
            base_session_key=main_session_key,
            thread_id="thread-usage-logs-api",
        ).session_key
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Please show the API usage logs.",
                session_key=session_key,
            )
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="Usage log API slice",
                objective="Link the API reply back to bounded mission usage.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-logs-api",
                session_key=session_key,
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                total_tokens=640,
                output_tokens=160,
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="Here is the bounded API usage log entry.",
                mission_id=mission_id,
                session_key=session_key,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.usage.logs",
                "params": {"key": session_key, "limit": 200},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessionId"] == "thread-usage-logs-api"
    assert payload["entries"] == [
        {
            "timestamp": payload["entries"][0]["timestamp"],
            "role": "user",
            "content": "Please show the API usage logs.",
        },
        {
            "timestamp": payload["entries"][1]["timestamp"],
            "role": "assistant",
            "content": "Here is the bounded API usage log entry.",
            "tokens": 640,
        },
    ]


def test_gateway_node_method_call_endpoint_chat_abort_interrupts_tracked_runtime(
    tmp_path,
    monkeypatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-abort-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        
        async def fake_interrupt_turn(instance_id: int, thread_id: str) -> dict[str, object]:
            return {"ok": True, "instanceId": instance_id, "threadId": thread_id}

        monkeypatch.setattr(client.app.state.manager, "interrupt_turn", fake_interrupt_turn)
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "idempotencyKey": "run-chat-send-1",
                },
            },
        )
        assert send_response.status_code == 200
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Chat Abort Loop",
                objective="Interrupt the live control chat thread.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-chat-abort-1",
                session_key="openzues:thread:demo",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "chat.abort",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "runId": "run-chat-send-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": True,
        "runIds": ["run-chat-send-1"],
    }


def test_gateway_node_method_call_endpoint_supports_cron_list() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-list-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        scheduled_id = asyncio.run(
            database.create_task_blueprint(
                name="Archive Sweep",
                summary="Keep the release lane tidy.",
                project_id=None,
                instance_id=None,
                cadence_minutes=120,
                enabled=False,
                payload={
                    "objective_template": "Archive the old release artifacts.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        asyncio.run(
            database.update_task_blueprint_payload(
                scheduled_id,
                last_launched_at="2026-04-18T03:00:00Z",
                last_status="failed",
                last_result_summary="Archive webhook target was unavailable.",
            )
        )
        asyncio.run(
            database.create_task_blueprint(
                name="Manual Repair",
                summary="Manual-only work should not appear in cron.list.",
                project_id=None,
                instance_id=None,
                cadence_minutes=None,
                enabled=True,
                payload={
                    "objective_template": "Repair the queue drift.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.list",
                "params": {
                    "enabled": "disabled",
                    "query": "archive",
                    "limit": 10,
                    "sortBy": "updatedAtMs",
                    "sortDir": "desc",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["jobs"][0]["id"] == f"task-blueprint:{scheduled_id}"
    assert payload["jobs"][0]["name"] == "Archive Sweep"
    assert payload["jobs"][0]["enabled"] is False
    assert payload["jobs"][0]["schedule"] == {"kind": "every", "everyMs": 7_200_000}
    assert payload["jobs"][0]["state"]["lastRunStatus"] == "error"
    assert payload["jobs"][0]["state"]["lastStatus"] == "error"
    assert payload["jobs"][0]["state"]["lastError"] == "Archive webhook target was unavailable."


def test_gateway_node_method_call_endpoint_supports_cron_status() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-status-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        enabled_id = asyncio.run(
            database.create_task_blueprint(
                name="Wake Status",
                summary="Track the next scheduler wake.",
                project_id=None,
                instance_id=None,
                cadence_minutes=15,
                enabled=True,
                payload={
                    "objective_template": "Track the next scheduler wake.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        asyncio.run(
            database.update_task_blueprint_payload(
                enabled_id,
                last_launched_at="2026-04-18T03:00:00Z",
                last_status="completed",
                last_result_summary="Wake status heartbeat completed.",
            )
        )
        asyncio.run(
            database.create_task_blueprint(
                name="Disabled Sweep",
                summary="Still counts as a stored cadence job.",
                project_id=None,
                instance_id=None,
                cadence_minutes=120,
                enabled=False,
                payload={
                    "objective_template": "Sweep disabled backlog.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "cron.status", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "storePath": str(app_settings.db_path),
        "jobs": 2,
        "nextWakeAtMs": int(datetime(2026, 4, 18, 3, 15, tzinfo=UTC).timestamp() * 1000),
    }


def test_gateway_node_method_call_endpoint_supports_cron_runs_scope_all() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-runs-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        ship_task_id = asyncio.run(
            database.create_task_blueprint(
                name="Nightly Ship",
                summary="Ship the next verified slice.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified slice.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        archive_task_id = asyncio.run(
            database.create_task_blueprint(
                name="Archive Sweep",
                summary="Sweep the release lane.",
                project_id=None,
                instance_id=None,
                cadence_minutes=30,
                enabled=True,
                payload={
                    "objective_template": "Sweep the release lane.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        ship_mission_id = asyncio.run(
            database.create_mission(
                name="Nightly Ship Run",
                objective="Ship the next verified slice.",
                status="completed",
                instance_id=7,
                project_id=None,
                task_blueprint_id=ship_task_id,
                thread_id="thread-ship-ok",
                session_key="launch:mode:workspace_affinity",
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                ship_mission_id,
                last_checkpoint="Nightly ship landed.",
            )
        )
        archive_mission_id = asyncio.run(
            database.create_mission(
                name="Archive Sweep Run",
                objective="Sweep the release lane.",
                status="failed",
                instance_id=7,
                project_id=None,
                task_blueprint_id=archive_task_id,
                thread_id="thread-archive-error",
                session_key="launch:mode:workspace_affinity",
                conversation_target=None,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
            )
        )
        asyncio.run(
            database.update_mission(
                archive_mission_id,
                last_error="Archive webhook target was unavailable.",
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.runs",
                "params": {
                    "scope": "all",
                    "statuses": ["ok"],
                    "query": "nightly",
                    "limit": 10,
                    "sortDir": "desc",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["offset"] == 0
    assert payload["limit"] == 10
    assert payload["hasMore"] is False
    assert payload["nextOffset"] is None
    entry = payload["entries"][0]
    assert entry["jobId"] == f"task-blueprint:{ship_task_id}"
    assert entry["jobName"] == "Nightly Ship"
    assert entry["status"] == "ok"
    assert entry["summary"] == "Nightly ship landed."
    assert entry["deliveryStatus"] == "not-requested"


def test_gateway_node_method_call_endpoint_supports_cron_run_force() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-run-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    fake_ops_mesh = _FakeOpsMeshService()
    app = create_app(app_settings, ops_mesh_service=fake_ops_mesh)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="Nightly Ship",
                summary="Ship the next verified slice.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified slice.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.run",
                "params": {"id": f"task-blueprint:{task_id}", "mode": "force"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "enqueued": True, "runId": "mission:52"}
    assert fake_ops_mesh.calls == [(task_id, "gateway-cron:force")]


def test_gateway_node_method_call_endpoint_supports_cron_remove() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-remove-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="Nightly Ship",
                summary="Ship the next verified slice.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified slice.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                    "enabled": True,
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.remove",
                "params": {"id": f"task-blueprint:{task_id}"},
            },
        )
        remaining = asyncio.run(database.get_task_blueprint(task_id))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "removed": True}
    assert remaining is None


def test_gateway_node_method_call_endpoint_supports_cron_add() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "cron.add",
                "params": {
                    "name": "Nightly Ship",
                    "description": "Ship the next verified slice.",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Ship the next verified slice.",
                        "model": "gpt-5.4",
                    },
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.list",
                "params": {"includeDisabled": True},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert str(payload["id"]).startswith("task-blueprint:")
    assert payload["name"] == "Nightly Ship"
    assert payload["description"] == "Ship the next verified slice."
    assert payload["schedule"] == {"kind": "every", "everyMs": 3_600_000}
    assert payload["sessionTarget"] == "main"
    assert payload["wakeMode"] == "now"
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Ship the next verified slice.",
        "model": "gpt-5.4",
    }
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == payload["id"]
    assert jobs[0]["name"] == "Nightly Ship"


def test_gateway_node_method_call_endpoint_supports_cron_update() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="Nightly Ship",
                summary="Ship the next verified slice.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified slice.",
                    "conversation_target": None,
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                    "completion_marker": None,
                    "cwd": None,
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": None,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "toolsets": [],
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": f"task-blueprint:{task_id}",
                    "patch": {
                        "name": "Nightly Repair",
                        "description": "Repair the next verified slice.",
                        "enabled": False,
                        "schedule": {"kind": "every", "everyMs": 7_200_000},
                        "payload": {
                            "message": "Repair the next verified slice.",
                            "model": "gpt-5.4-mini",
                        },
                    },
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.list",
                "params": {"includeDisabled": True},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == f"task-blueprint:{task_id}"
    assert payload["name"] == "Nightly Repair"
    assert payload["description"] == "Repair the next verified slice."
    assert payload["enabled"] is False
    assert payload["schedule"] == {"kind": "every", "everyMs": 7_200_000}
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Repair the next verified slice.",
        "model": "gpt-5.4-mini",
    }
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["id"] == payload["id"]
    assert jobs[0]["name"] == "Nightly Repair"
    assert jobs[0]["enabled"] is False


def test_gateway_node_method_call_endpoint_supports_wake_now_and_next_heartbeat(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        now_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                },
            },
        )
        messages_after_now = asyncio.run(client.app.state.database.list_control_chat_messages())
        queued_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Check the queued parity nudge on the next heartbeat.",
                },
            },
        )
        messages_before_tick = asyncio.run(client.app.state.database.list_control_chat_messages())
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        messages_after_tick = asyncio.run(client.app.state.database.list_control_chat_messages())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert now_response.status_code == 200
    assert now_response.json() == {"ok": True}
    assert [message["content"] for message in messages_after_now if message["role"] == "user"] == [
        "Resume parity from the latest checkpoint."
    ]

    assert queued_response.status_code == 200
    assert queued_response.json() == {"ok": True}
    assert [
        message["content"] for message in messages_before_tick if message["role"] == "user"
    ] == ["Resume parity from the latest checkpoint."]

    assert acted is True
    assert [
        message["content"] for message in messages_after_tick if message["role"] == "user"
    ] == [
        "Resume parity from the latest checkpoint.",
        "Check the queued parity nudge on the next heartbeat.",
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_supports_agents_files_list_and_get(
    tmp_path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / ".codex").mkdir(parents=True, exist_ok=True)
    (workspace_root / "AGENTS.md").write_text("Top-level instructions.\n", encoding="utf-8")
    (workspace_root / ".codex" / "AGENTS.md").write_text(
        "Codex instructions.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_root)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "agents.files.list", "params": {"agentId": "main"}},
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.get",
                "params": {"agentId": "main", "name": "AGENTS.md"},
            },
        )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["agentId"] == "main"
    assert list_payload["workspace"] == str(workspace_root)
    files_by_name = {entry["name"]: entry for entry in list_payload["files"]}
    assert files_by_name["AGENTS.md"]["missing"] is False
    assert files_by_name[".codex/AGENTS.md"]["missing"] is False

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["agentId"] == "main"
    assert get_payload["workspace"] == str(workspace_root)
    assert get_payload["file"]["name"] == "AGENTS.md"
    assert get_payload["file"]["missing"] is False
    assert get_payload["file"]["content"] == "Top-level instructions.\n"


def test_gateway_node_method_call_endpoint_supports_agents_files_set(
    tmp_path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.set",
                "params": {
                    "agentId": "main",
                    "name": ".codex/AGENTS.md",
                    "content": "Codex instructions.\n",
                },
            },
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.get",
                "params": {"agentId": "main", "name": ".codex/AGENTS.md"},
            },
        )

    written_path = workspace_root / ".codex" / "AGENTS.md"
    assert set_response.status_code == 200
    set_payload = set_response.json()
    assert set_payload["ok"] is True
    assert set_payload["agentId"] == "main"
    assert set_payload["workspace"] == str(workspace_root)
    assert set_payload["file"]["name"] == ".codex/AGENTS.md"
    assert set_payload["file"]["path"] == str(written_path)
    assert set_payload["file"]["missing"] is False
    assert set_payload["file"]["content"] == "Codex instructions.\n"
    assert written_path.read_text(encoding="utf-8") == "Codex instructions.\n"

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["file"]["name"] == ".codex/AGENTS.md"
    assert get_payload["file"]["missing"] is False
    assert get_payload["file"]["content"] == "Codex instructions.\n"


def test_gateway_node_method_call_endpoint_supports_agents_list_and_agent_identity_get(
    tmp_path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workspace_root)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "agents.list", "params": {}},
        )
        identity_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.identity.get",
                "params": {"sessionKey": "launch:mode:workspace_affinity"},
            },
        )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["defaultId"] == "main"
    assert list_payload["mainKey"] == "main"
    assert list_payload["scope"] == "global"
    assert list_payload["agents"] == [
        {
            "id": "main",
            "name": "OpenZues",
            "identity": {
                "name": "OpenZues",
                "avatar": "/static/favicon.svg",
                "avatarUrl": "/static/favicon.svg",
                "emoji": None,
            },
            "workspace": str(workspace_root),
            "model": {"primary": "gpt-5.4"},
        }
    ]

    assert identity_response.status_code == 200
    assert identity_response.json() == {
        "agentId": "main",
        "name": "OpenZues",
        "avatar": "/static/favicon.svg",
        "emoji": None,
    }


def test_gateway_node_method_call_endpoint_supports_sessions_list() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["defaults"]["mainSessionKey"] == "launch:mode:workspace_affinity"
    assert payload["sessions"] == [
        {
            "key": "launch:mode:workspace_affinity",
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][0]["updatedAt"],
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "contextTokens": None,
        }
    ]
    assert isinstance(payload["ts"], int)
    assert isinstance(payload["sessions"][0]["updatedAt"], int)
    assert payload["sessions"][0]["updatedAt"] > 0


def test_gateway_node_method_call_endpoint_sessions_list_includes_metadata_sessions() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-metadata-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=thread_session_key,
                metadata={
                    "label": "Parity Worker",
                    "spawnedBy": "parity-conductor",
                    "model": "gpt-5.4-mini",
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["sessions"] == [
        {
            "key": main_session_key,
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][0]["updatedAt"],
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "contextTokens": None,
        },
        {
            "key": thread_session_key,
            "kind": "thread",
            "displayName": "OpenZues Control Chat Thread",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][1]["updatedAt"],
            "sessionId": "thread-parity",
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4-mini",
            "contextTokens": None,
            "label": "Parity Worker",
            "spawnedBy": "parity-conductor",
        },
    ]
    assert isinstance(payload["sessions"][1]["updatedAt"], int)
    assert payload["sessions"][1]["updatedAt"] > 0


def test_gateway_node_method_call_endpoint_sessions_list_hides_unknown_session_unless_requested(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-unknown-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key="unknown",
                metadata={"label": "Unknown Session"},
            )
        )
        hidden_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )
        visible_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": True, "limit": 10},
            },
        )

    assert hidden_response.status_code == 200
    assert [session["key"] for session in hidden_response.json()["sessions"]] == [main_session_key]
    assert visible_response.status_code == 200
    assert [session["key"] for session in visible_response.json()["sessions"]] == [
        main_session_key,
        "unknown",
    ]


def test_gateway_node_method_call_endpoint_sessions_list_supports_label_and_spawned_by_filters(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-filters-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    parity_worker_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity-worker",
    ).session_key
    other_worker_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-other-worker",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=parity_worker_key,
                metadata={
                    "label": "Parity Worker",
                    "spawnedBy": "parity-conductor",
                },
            )
        )
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=other_worker_key,
                metadata={
                    "label": "Other Worker",
                    "spawnedBy": "other-conductor",
                },
            )
        )
        label_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "label": "Parity Worker",
                },
            },
        )
        spawned_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": True,
                    "limit": 10,
                    "spawnedBy": "parity-conductor",
                },
            },
        )

    assert label_response.status_code == 200
    assert [session["key"] for session in label_response.json()["sessions"]] == [parity_worker_key]
    assert spawned_response.status_code == 200
    assert [session["key"] for session in spawned_response.json()["sessions"]] == [
        parity_worker_key
    ]


def test_gateway_node_method_call_endpoint_sessions_list_supports_agent_id_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-agent-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-filter",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=thread_session_key,
                metadata={"label": "Agent Filter Worker"},
            )
        )
        allowed_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "agentId": "main",
                },
            },
        )
        rejected_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "agentId": "other-agent",
                },
            },
        )

    assert allowed_response.status_code == 200
    assert [session["key"] for session in allowed_response.json()["sessions"]] == [
        main_session_key,
        thread_session_key,
    ]
    assert rejected_response.status_code == 400
    assert rejected_response.json()["detail"] == 'unknown agent id "other-agent"'


def test_gateway_node_method_call_endpoint_sessions_list_supports_active_minutes_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-active-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    stale_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-stale-active-filter",
    ).session_key
    reference_time = datetime.now(UTC)
    stale_updated_at = (reference_time - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=stale_session_key,
                metadata={"label": "Stale Worker"},
            )
        )
        with sqlite3.connect(app_settings.db_path) as db:
            db.execute(
                "UPDATE gateway_session_metadata SET updated_at = ? WHERE session_key = ?",
                (stale_updated_at, stale_session_key),
            )
            db.commit()
        tight_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "activeMinutes": 5,
                },
            },
        )
        wide_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "activeMinutes": 30,
                },
            },
        )

    assert tight_response.status_code == 200
    assert [session["key"] for session in tight_response.json()["sessions"]] == [main_session_key]
    assert wide_response.status_code == 200
    assert [session["key"] for session in wide_response.json()["sessions"]] == [
        main_session_key,
        stale_session_key,
    ]


def test_gateway_node_method_call_endpoint_sessions_list_supports_search_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-search-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    target_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-search-target",
    ).session_key
    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-search-other",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=target_session_key,
                metadata={"label": "Parity Search Worker"},
            )
        )
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=other_session_key,
                metadata={"label": "Background Worker"},
            )
        )
        label_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "search": "parity",
                },
            },
        )
        key_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "limit": 10,
                    "search": "thread-search-other",
                },
            },
        )

    assert label_response.status_code == 200
    assert [session["key"] for session in label_response.json()["sessions"]] == [target_session_key]
    assert key_response.status_code == 200
    assert [session["key"] for session in key_response.json()["sessions"]] == [other_session_key]


def test_gateway_node_method_call_endpoint_sessions_list_supports_include_last_message_preview(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-last-message-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    preview_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-last-message-preview",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=preview_session_key,
                metadata={"label": "Preview Worker"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="First preview message.",
                session_key=preview_session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Latest preview message.",
                session_key=preview_session_key,
            )
        )
        hidden_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": False,
                    "includeUnknown": False,
                    "includeLastMessage": False,
                    "label": "Preview Worker",
                    "limit": 10,
                },
            },
        )
        visible_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": False,
                    "includeUnknown": False,
                    "includeLastMessage": True,
                    "label": "Preview Worker",
                    "limit": 10,
                },
            },
        )

    assert hidden_response.status_code == 200
    assert [session["key"] for session in hidden_response.json()["sessions"]] == [
        preview_session_key
    ]
    assert "lastMessagePreview" not in hidden_response.json()["sessions"][0]
    assert visible_response.status_code == 200
    assert [session["key"] for session in visible_response.json()["sessions"]] == [
        preview_session_key
    ]
    assert visible_response.json()["sessions"][0]["lastMessagePreview"] == "Latest preview message."


def test_gateway_node_method_call_endpoint_sessions_list_supports_include_derived_titles() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-derived-title-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    preview_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-derived-title",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=preview_session_key,
                metadata={"label": "Preview Worker"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="First derived title message.",
                session_key=preview_session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Latest preview message.",
                session_key=preview_session_key,
            )
        )
        hidden_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": False,
                    "includeUnknown": False,
                    "includeDerivedTitles": False,
                    "label": "Preview Worker",
                    "limit": 10,
                },
            },
        )
        visible_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": False,
                    "includeUnknown": False,
                    "includeDerivedTitles": True,
                    "label": "Preview Worker",
                    "limit": 10,
                },
            },
        )

    assert hidden_response.status_code == 200
    assert [session["key"] for session in hidden_response.json()["sessions"]] == [
        preview_session_key
    ]
    assert "derivedTitle" not in hidden_response.json()["sessions"][0]
    assert visible_response.status_code == 200
    assert [session["key"] for session in visible_response.json()["sessions"]] == [
        preview_session_key
    ]
    assert visible_response.json()["sessions"][0]["derivedTitle"] == "First derived title message."


def test_gateway_node_method_call_endpoint_supports_sessions_get() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-get-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Need the control-chat transcript.",
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The bounded session transcript is ready.",
                session_key="openzues:thread:demo",
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.get",
                "params": {"sessionKey": "openzues:thread:demo", "limit": 2},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the control-chat transcript."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The bounded session transcript is ready."}],
            },
        ]
    }


def test_gateway_node_method_call_endpoint_filters_sessions_get_by_session_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-get-filtered-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.append_control_chat_message(
                role="user",
                content="Need the thread transcript.",
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="The thread transcript is ready.",
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="Noise from another session.",
                session_key="openzues:thread:other",
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.get",
                "params": {"sessionKey": "openzues:thread:demo", "limit": 5},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the thread transcript."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The thread transcript is ready."}],
            },
        ]
    }


def test_gateway_node_method_call_endpoint_supports_sessions_resolve() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
                "method": "sessions.resolve",
                "params": {"agentId": "main"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": "launch:mode:workspace_affinity"}


def test_gateway_node_method_call_endpoint_supports_sessions_resolve_by_label() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-label-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=current_session_key,
                metadata={"label": "Parity Session"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"label": "Parity Session"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": current_session_key}


def test_gateway_node_method_call_endpoint_supports_sessions_resolve_by_spawned_by() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-spawned-by-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=current_session_key,
                metadata={"spawnedBy": "parity-conductor"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"spawnedBy": "parity-conductor"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": current_session_key}


def test_gateway_node_method_call_endpoint_hides_current_session_label_when_global_is_excluded(
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-label-excludes-global-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=current_session_key,
                metadata={"label": "Parity Session"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"label": "Parity Session", "includeGlobal": False},
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown session label"


def test_gateway_node_method_call_endpoint_supports_sessions_resolve_by_metadata_known_spawned_by(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-metadata-spawned-by-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=thread_session_key,
                metadata={"spawnedBy": "parity-conductor"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"spawnedBy": "parity-conductor"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": thread_session_key}


def test_gateway_node_method_call_endpoint_supports_sessions_resolve_by_session_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-session-id-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-session-id-api",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=thread_session_key,
                metadata={"label": "Session Id API"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"sessionId": "thread-session-id-api"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": thread_session_key}


def test_gateway_node_method_call_endpoint_hides_global_session_id_when_global_is_excluded(
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-session-id-excludes-global-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_mission(
                name="Global Session Id",
                objective="Prove global sessionId visibility filtering.",
                status="completed",
                instance_id=9,
                project_id=None,
                thread_id="global-session-id-parity-api",
                session_key=current_session_key,
                cwd="C:/workspace",
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                task_blueprint_id=None,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {
                    "sessionId": "global-session-id-parity-api",
                    "includeGlobal": False,
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown sessionId"


def test_gateway_node_method_call_endpoint_supports_sessions_resolve_by_transcript_only_session_id(
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-transcript-session-id-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity",
        thread_id="thread-transcript-session-id-api",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Transcript-only session evidence.",
                session_key=session_key,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"sessionId": "thread-transcript-session-id-api"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "key": session_key}


def test_gateway_node_method_call_endpoint_sessions_resolve_by_key_respects_spawned_by_filter(
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-key-spawned-by-filter-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    visible_parent_key = "agent:main:subagent:visible-parent"
    hidden_parent_key = "agent:main:subagent:hidden-parent"
    child_key = "agent:main:subagent:shared-child-key-filter"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=visible_parent_key,
                metadata={"spawnedBy": "agent:main:main"},
            )
        )
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=hidden_parent_key,
                metadata={"spawnedBy": "agent:main:main"},
            )
        )
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=child_key,
                metadata={"spawnedBy": hidden_parent_key},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"key": child_key, "spawnedBy": visible_parent_key},
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown session key"


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


def test_gateway_node_method_call_endpoint_supports_status() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-status-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        gateway_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "status", "params": {}},
        )
        api_response = client.get("/api/status")

    assert gateway_response.status_code == 200
    assert api_response.status_code == 200
    gateway_payload = gateway_response.json()
    api_payload = api_response.json()
    if "gateway_capability" in gateway_payload and "gateway_capability" in api_payload:
        gateway_payload["gateway_capability"].pop("checked_at", None)
        api_payload["gateway_capability"].pop("checked_at", None)
    assert gateway_payload == api_payload


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


def test_gateway_node_method_call_endpoint_supports_local_skills_update(
    tmp_path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "skills-update-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: skills-update-test
description: skills update api test
platforms:
  - windows
metadata:
  skillKey: skills-update
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
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.update",
                "params": {
                    "skillKey": "skills-update",
                    "enabled": False,
                    "apiKey": "abc\r\ndef",
                    "env": {
                        " OPENZUES_TOKEN ": "  ready  ",
                        "REMOVE_ME": "   ",
                    },
                },
            },
        )
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.status", "params": {}},
        )

    assert update_response.status_code == 200
    assert update_response.json() == {
        "ok": True,
        "skillKey": "skills-update",
        "config": {
            "enabled": False,
            "apiKey": "abcdef",
            "env": {"OPENZUES_TOKEN": "ready"},
        },
    }
    assert status_response.status_code == 200
    assert status_response.json()["skills"] == [
        {
            "name": "skills-update-test",
            "description": "skills update api test",
            "source": "codex-home",
            "bundled": True,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "skills-update",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": True,
            "blockedByAllowlist": False,
            "eligible": False,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


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


def test_gateway_node_method_call_endpoint_surfaces_skills_install_unavailable(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            skill_clawhub_service=GatewaySkillClawHubService(resolve_launcher=False),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        install_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.install",
                "params": {"source": "clawhub", "slug": "openclaw/example"},
            },
        )

    assert install_response.status_code == 503
    assert (
        install_response.json()["detail"]
        == "ClawHub CLI is not available on the gateway host."
    )


def test_gateway_node_method_call_endpoint_supports_gateway_skill_installer_mode(
    tmp_path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / ".codex-home"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "skills-install-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: skills-install-test
description: skills install api test
platforms:
  - windows
metadata:
  skillKey: skills-install
  requires:
    bins:
      - missing-bin
  install:
    - id: node
      kind: node
      label: Install skills-install-test
      package: demo-skill
      bins:
        - missing-bin
---
Body
""",
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        shim_path = bin_dir / "missing-bin.cmd"
        shim_path.write_text("@echo off\r\necho installed\r\n", encoding="utf-8")
        return (0, "installed", "")

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_install_service=GatewaySkillInstallService(command_runner=fake_command_runner),
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        install_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.install",
                "params": {
                    "name": "skills-install-test",
                    "installId": "node",
                    "timeoutMs": 45_000,
                },
            },
        )
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.status", "params": {}},
        )

    assert install_response.status_code == 200
    assert install_response.json() == {
        "ok": True,
        "name": "skills-install-test",
        "skillKey": "skills-install",
        "installId": "node",
        "kind": "node",
        "label": "Install skills-install-test",
        "bins": ["missing-bin"],
        "command": ["npm", "install", "-g", "demo-skill"],
        "cwd": str(skill_path.parent),
    }
    assert observed == {
        "argv": ("npm", "install", "-g", "demo-skill"),
        "cwd": str(skill_path.parent),
        "timeout_ms": 45_000,
    }
    assert status_response.status_code == 200
    assert status_response.json()["skills"] == [
        {
            "name": "skills-install-test",
            "description": "skills install api test",
            "source": "codex-home",
            "bundled": True,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "skills-install",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": ["missing-bin"],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [
                {
                    "id": "node",
                    "kind": "node",
                    "label": "Install skills-install-test",
                    "bins": ["missing-bin"],
                }
            ],
        }
    ]


def test_gateway_node_method_call_endpoint_supports_clawhub_skills_install_mode(
    tmp_path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        skill_path = tmp_path / "skills" / "demo-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(
            """---
name: demo-skill
description: installed from clawhub api
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
            encoding="utf-8",
        )
        return (0, "installed", "")

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_clawhub_service=GatewaySkillClawHubService(
            launcher=("clawhub",),
            command_runner=fake_command_runner,
        ),
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        install_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.install",
                "params": {
                    "source": "clawhub",
                    "slug": "demo-skill",
                    "version": "1.2.3",
                    "force": True,
                },
            },
        )
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.status", "params": {}},
        )

    assert install_response.status_code == 200
    assert install_response.json() == {
        "ok": True,
        "source": "clawhub",
        "action": "install",
        "slug": "demo-skill",
        "version": "1.2.3",
        "force": True,
        "command": [
            "clawhub",
            "install",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.3",
            "--force",
        ],
        "workspaceDir": str(tmp_path),
        "skillsDir": str(tmp_path / "skills"),
    }
    assert observed == {
        "argv": (
            "clawhub",
            "install",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.3",
            "--force",
        ),
        "cwd": str(tmp_path),
        "timeout_ms": None,
    }
    assert status_response.status_code == 200
    assert status_response.json()["skills"] == [
        {
            "name": "demo-skill",
            "description": "installed from clawhub api",
            "source": "workspace",
            "bundled": False,
            "filePath": str(tmp_path / "skills" / "demo-skill" / "SKILL.md"),
            "baseDir": str(tmp_path / "skills" / "demo-skill"),
            "skillKey": "demo-skill",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


def test_gateway_node_method_call_endpoint_supports_clawhub_skills_update_mode(
    tmp_path,
    monkeypatch,
) -> None:
    codex_home = tmp_path / ".codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = tmp_path / "skills" / "demo-skill" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: demo-skill
description: before clawhub update api
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        skill_path.write_text(
            """---
name: demo-skill
description: updated from clawhub api
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
            encoding="utf-8",
        )
        return (0, "updated", "")

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_clawhub_service=GatewaySkillClawHubService(
            launcher=("clawhub",),
            command_runner=fake_command_runner,
        ),
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "skills.update",
                "params": {
                    "source": "clawhub",
                    "slug": "demo-skill",
                    "version": "1.2.4",
                    "force": True,
                },
            },
        )
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "skills.status", "params": {}},
        )

    assert update_response.status_code == 200
    assert update_response.json() == {
        "ok": True,
        "source": "clawhub",
        "action": "update",
        "slug": "demo-skill",
        "version": "1.2.4",
        "force": True,
        "all": False,
        "command": [
            "clawhub",
            "update",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.4",
            "--force",
        ],
        "workspaceDir": str(tmp_path),
        "skillsDir": str(tmp_path / "skills"),
    }
    assert observed == {
        "argv": (
            "clawhub",
            "update",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.4",
            "--force",
        ),
        "cwd": str(tmp_path),
        "timeout_ms": None,
    }
    assert status_response.status_code == 200
    assert status_response.json()["skills"] == [
        {
            "name": "demo-skill",
            "description": "updated from clawhub api",
            "source": "workspace",
            "bundled": False,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "demo-skill",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


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
