from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import httpx
import pytest
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database, utcnow
from openzues.schemas import ConversationTargetView, DashboardView
from openzues.services import gateway_config_schema as gateway_config_schema_module
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.gateway_cron import build_gateway_cron_task_blueprint
from openzues.services.gateway_node_methods import GatewayNodeMethodService
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.gateway_node_service import GatewayNodeService
from openzues.services.gateway_sessions import GatewaySessionsService
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


class _BackgroundUnavailableNodeConnection:
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
                ok=False,
                payload=None,
                payload_json=None,
                error={
                    "code": "NODE_BACKGROUND_UNAVAILABLE",
                    "message": (
                        "NODE_BACKGROUND_UNAVAILABLE: canvas/camera/screen commands "
                        "require foreground"
                    ),
                },
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

    async def send_direct_channel_message(self, **_: object) -> dict[str, object]:
        raise AssertionError("send_direct_channel_message should not be called in this fake")

    async def send_direct_channel_poll(self, **_: object) -> dict[str, object]:
        raise AssertionError("send_direct_channel_poll should not be called in this fake")

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
    device_family: str | None = None,
    path_env: str | None = None,
    commands: tuple[str, ...] = (),
    permissions: dict[str, bool] | None = None,
    connected_at_ms: int = 0,
) -> None:
    registry.remember(
        KnownNode(
            node_id=node_id,
            display_name=display_name,
            platform=platform,
            client_id=client_id,
            client_mode=client_mode,
            device_family=device_family,
            path_env=path_env,
            commands=commands,
            permissions=permissions,
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
            device_family=device_family,
            path_env=path_env,
            commands=commands,
            permissions=permissions,
        ),
        connected_at_ms=connected_at_ms,
    )


def _allow_mutating_api_requests(client: TestClient) -> None:
    client.app.state.control_plane_role = "leader"
    client.app.state.control_plane_owner_pid = None


def _wait_for(fetch, predicate, *, timeout_seconds: float = 3.0, interval_seconds: float = 0.05):
    deadline = time.monotonic() + timeout_seconds
    value = fetch()
    while not predicate(value):
        if time.monotonic() >= deadline:
            return value
        time.sleep(interval_seconds)
        value = fetch()
    return value


def _unused_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_test_server(app) -> tuple[str, uvicorn.Server, threading.Thread]:
    port = _unused_tcp_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5.0
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("Uvicorn test server stopped before startup")
        if time.monotonic() >= deadline:
            raise RuntimeError("Timed out waiting for Uvicorn test server startup")
        time.sleep(0.01)
    return f"http://127.0.0.1:{port}", server, thread


def _stop_test_server(server: uvicorn.Server, thread: threading.Thread) -> None:
    server.should_exit = True
    thread.join(timeout=5.0)


def _read_sse_payload(lines: Iterator[str], event_name: str) -> dict[str, Any]:
    current_event: str | None = None
    data_lines: list[str] = []
    for line in lines:
        if line.startswith(":") or line.startswith("retry:"):
            continue
        if not line:
            if current_event == event_name and data_lines:
                payload = json.loads("\n".join(data_lines))
                assert isinstance(payload, dict)
                return payload
            current_event = None
            data_lines = []
            continue
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ").strip()
        elif line.startswith("data: "):
            data_lines.append(line.removeprefix("data: "))
    raise AssertionError(f"SSE event {event_name!r} was not delivered before stream closed")


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


def test_gateway_node_catalog_endpoint_exposes_only_allowlisted_live_commands(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-node-filter",
        node_id="node-filter",
        client_id="live-node-filter",
        display_name="Filtered Phone",
        platform="ios",
        device_family="iPhone",
        commands=("canvas.snapshot", "system.run", "browser.inspect"),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/node-filter")

    assert nodes_response.status_code == 200
    assert nodes_response.json()["nodes"][0]["commands"] == ["canvas.snapshot"]
    assert node_response.status_code == 200
    assert node_response.json()["commands"] == ["canvas.snapshot"]


def test_gateway_node_endpoints_preserve_empty_live_permissions_map(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-node-empty-permissions",
        node_id="node-empty-permissions",
        client_id="live-node-empty-permissions",
        display_name="Runtime Permissions Node",
        platform="android",
        permissions={},
        connected_at_ms=321,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/node-empty-permissions")

    assert nodes_response.status_code == 200
    assert nodes_response.json()["nodes"] == [
        {
            "node_id": "node-empty-permissions",
            "display_name": "Runtime Permissions Node",
            "platform": "android",
            "version": None,
            "core_version": None,
            "ui_version": None,
            "client_id": "live-node-empty-permissions",
            "client_mode": "desktop",
            "remote_ip": None,
            "device_family": None,
            "model_identifier": None,
            "path_env": None,
            "caps": [],
            "commands": [],
            "permissions": {},
            "paired": True,
            "connected": True,
            "connected_at_ms": 321,
            "approved_at_ms": None,
        }
    ]
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "node-empty-permissions",
        "display_name": "Runtime Permissions Node",
        "platform": "android",
        "version": None,
        "core_version": None,
        "ui_version": None,
        "client_id": "live-node-empty-permissions",
        "client_mode": "desktop",
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": None,
        "caps": [],
        "commands": [],
        "permissions": {},
        "paired": True,
        "connected": True,
        "connected_at_ms": 321,
        "approved_at_ms": None,
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


def test_gateway_node_pending_work_endpoint_preserves_explicit_empty_payload_object(
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
        conn_id="conn-pending-empty-payload",
        node_id="pending-empty-payload",
        client_id="pending-empty-payload-live",
        display_name="Pending Empty Payload Node",
        platform="desktop",
        path_env=str(tmp_path),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        enqueue_response = client.post(
            "/api/gateway/nodes/pending-empty-payload/pending-work",
            json={
                "type": "location.request",
                "payload": {},
            },
        )
        drained_response = client.get("/api/gateway/nodes/pending-empty-payload/pending-work")

    assert enqueue_response.status_code == 200
    enqueue_payload = enqueue_response.json()
    assert enqueue_payload["nodeId"] == "pending-empty-payload"
    assert enqueue_payload["queued"]["type"] == "location.request"
    assert enqueue_payload["queued"]["payload"] == {}
    assert enqueue_payload["wakeTriggered"] is False

    assert drained_response.status_code == 200
    assert drained_response.json() == {
        "nodeId": "pending-empty-payload",
        "revision": 1,
        "items": [
            {
                "id": enqueue_payload["queued"]["id"],
                "type": "location.request",
                "priority": "normal",
                "createdAtMs": enqueue_payload["queued"]["createdAtMs"],
                "expiresAtMs": None,
                "payload": {},
            },
            {
                "id": "baseline-status",
                "type": "status.request",
                "priority": "default",
                "createdAtMs": drained_response.json()["items"][1]["createdAtMs"],
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


def test_gateway_node_pending_work_endpoint_waits_for_managed_lane_reconnect_after_wake(
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
    connect_calls = 0

    async def fake_connect_instance(instance_id: int) -> InstanceRuntime:
        nonlocal connect_calls
        assert instance_id == 7
        connect_calls += 1
        runtime = manager.instances[instance_id]
        asyncio.get_running_loop().call_soon(
            lambda: setattr(runtime, "connected", True)
        )
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
    assert connect_calls == 1
    assert app.state.gateway_node_service.registry.get("7") is not None


def test_gateway_node_pending_work_endpoint_keeps_wake_triggered_false_when_managed_wake_fails(
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
        raise RuntimeError("connect failed")

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
    assert enqueue_payload["wakeTriggered"] is False


def test_gateway_node_pending_work_endpoint_reuses_existing_item_without_rewaking(
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
    connect_calls = 0

    async def fake_connect_instance(instance_id: int) -> InstanceRuntime:
        nonlocal connect_calls
        assert instance_id == 7
        connect_calls += 1
        runtime = manager.instances[instance_id]
        runtime.connected = True
        return runtime

    monkeypatch.setattr(manager, "connect_instance", fake_connect_instance)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first_response = client.post(
            "/api/gateway/nodes/7/pending-work",
            json={
                "type": "location.request",
                "priority": "high",
                "expiresInMs": 5_000,
                "payload": {"reason": "gps"},
                "wake": True,
            },
        )
        manager.instances[7].connected = False
        second_response = client.post(
            "/api/gateway/nodes/7/pending-work",
            json={
                "type": "location.request",
                "priority": "default",
                "expiresInMs": 1_000,
                "payload": {"reason": "wifi"},
                "wake": True,
            },
        )
        drained_response = client.get("/api/gateway/nodes/7/pending-work")

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["nodeId"] == "7"
    assert first_payload["revision"] == 1
    assert first_payload["queued"]["type"] == "location.request"
    assert first_payload["queued"]["priority"] == "high"
    assert first_payload["queued"]["payload"] == {"reason": "gps"}
    assert first_payload["wakeTriggered"] is True

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["nodeId"] == "7"
    assert second_payload["revision"] == 1
    assert second_payload["queued"]["id"] == first_payload["queued"]["id"]
    assert second_payload["queued"]["type"] == "location.request"
    assert second_payload["queued"]["priority"] == "high"
    assert second_payload["queued"]["createdAtMs"] == first_payload["queued"]["createdAtMs"]
    assert second_payload["queued"]["expiresAtMs"] == first_payload["queued"]["expiresAtMs"]
    assert second_payload["queued"]["payload"] == {"reason": "gps"}
    assert second_payload["wakeTriggered"] is False
    assert connect_calls == 1

    assert drained_response.status_code == 200
    assert drained_response.json() == {
        "nodeId": "7",
        "revision": 1,
        "items": [
            {
                "id": first_payload["queued"]["id"],
                "type": "location.request",
                "priority": "high",
                "createdAtMs": first_payload["queued"]["createdAtMs"],
                "expiresAtMs": first_payload["queued"]["expiresAtMs"],
                "payload": {"reason": "gps"},
            },
            {
                "id": "baseline-status",
                "type": "status.request",
                "priority": "default",
                "createdAtMs": drained_response.json()["items"][1]["createdAtMs"],
                "expiresAtMs": None,
                "payload": None,
            },
        ],
        "hasMore": False,
    }


def test_gateway_node_method_call_endpoint_keeps_not_connected_boundary_when_managed_wake_fails(
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
        name="Managed Offline Node",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
    )
    app.state.gateway_node_service.registry.remember(
        KnownNode(
            node_id="7",
            display_name="Managed Offline Node",
            platform="stdio",
            client_id="7",
            client_mode="stdio",
            commands=("system.run",),
            paired=True,
            connected=False,
        )
    )

    async def fake_connect_instance(instance_id: int) -> InstanceRuntime:
        assert instance_id == 7
        raise RuntimeError("connect failed")

    monkeypatch.setattr(manager, "connect_instance", fake_connect_instance)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        node_response = client.get("/api/gateway/nodes/7")
        invoke_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.invoke",
                "params": {
                    "nodeId": "7",
                    "command": "system.run",
                    "params": {"command": "whoami"},
                    "idempotencyKey": "idem-managed-offline-node",
                },
            },
        )

    assert node_response.status_code == 200
    assert invoke_response.status_code == 503
    assert invoke_response.json() == {"detail": "node not connected"}


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
        "paired": [],
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


def test_remote_gateway_node_method_call_accepts_x_openclaw_token_header(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    local_app = create_app(app_settings)

    with TestClient(local_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        owner_response = client.post("/api/operators/1/api-key")

    assert owner_response.status_code == 200
    api_key = owner_response.json()["api_key"]
    assert isinstance(api_key, str)
    assert api_key

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            headers={"X-OpenClaw-Token": api_key},
            json={"method": "gateway.identity.get", "params": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert re.fullmatch(r"[0-9a-f]{64}", payload["id"])
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", payload["publicKey"])


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
        "deviceFamily": None,
        "modelIdentifier": None,
        "caps": [],
        "commands": ["system.run"],
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
                    "silent": True,
                },
            },
        )

    assert request_response.status_code == 200
    request_payload = request_response.json()
    request_id = request_payload["request"]["requestId"]
    request_ts = request_payload["request"]["ts"]
    assert request_payload["request"]["silent"] is True

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
                "deviceFamily": None,
                "modelIdentifier": None,
                "caps": [],
                "remoteIp": "10.0.0.8",
                "silent": True,
                "ts": request_ts,
                "commands": ["system.run"],
                "requiredApproveScopes": ["operator.pairing", "operator.admin"],
            }
        ],
        "paired": [],
    }


def test_gateway_node_pair_request_endpoint_refresh_preserves_fields_and_clears_lists(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        created_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-refresh-api",
                    "displayName": "Persistent Node",
                    "platform": "ios",
                    "version": "1.2.3",
                    "coreVersion": "2.0.0",
                    "uiVersion": "3.0.0",
                    "deviceFamily": "iphone",
                    "modelIdentifier": "iphone15,3",
                    "caps": ["voice", "canvas"],
                    "commands": ["canvas.present"],
                    "remoteIp": "10.0.0.8",
                },
            },
        )
        refreshed_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-refresh-api",
                    "commands": ["canvas.present", "system.run"],
                },
            },
        )
        cleared_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "pair-node-refresh-api",
                    "caps": [],
                    "commands": [],
                },
            },
        )
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert created_response.status_code == 200
    request_id = created_response.json()["request"]["requestId"]

    assert refreshed_response.status_code == 200
    assert refreshed_response.json() == {
        "status": "pending",
        "request": {
            "requestId": request_id,
            "nodeId": "pair-node-refresh-api",
            "displayName": "Persistent Node",
            "platform": "ios",
            "version": "1.2.3",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "iphone",
            "modelIdentifier": "iphone15,3",
            "caps": ["voice", "canvas"],
            "commands": ["canvas.present", "system.run"],
            "remoteIp": "10.0.0.8",
            "ts": refreshed_response.json()["request"]["ts"],
        },
        "created": False,
    }
    assert cleared_response.status_code == 200
    assert cleared_response.json() == {
        "status": "pending",
        "request": {
            "requestId": request_id,
            "nodeId": "pair-node-refresh-api",
            "displayName": "Persistent Node",
            "platform": "ios",
            "version": "1.2.3",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "iphone",
            "modelIdentifier": "iphone15,3",
            "caps": [],
            "commands": [],
            "remoteIp": "10.0.0.8",
            "ts": cleared_response.json()["request"]["ts"],
        },
        "created": False,
    }
    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [
            {
                "requestId": request_id,
                "nodeId": "pair-node-refresh-api",
                "displayName": "Persistent Node",
                "platform": "ios",
                "version": "1.2.3",
                "coreVersion": "2.0.0",
                "uiVersion": "3.0.0",
                "deviceFamily": "iphone",
                "modelIdentifier": "iphone15,3",
                "caps": [],
                "commands": [],
                "remoteIp": "10.0.0.8",
                "ts": cleared_response.json()["request"]["ts"],
                "requiredApproveScopes": ["operator.pairing"],
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
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": ["system.run"],
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
                "token": token,
                "displayName": "Approved Node",
                "platform": "windows",
                "version": None,
                "coreVersion": None,
                "uiVersion": None,
                "deviceFamily": None,
                "modelIdentifier": None,
                "caps": [],
                "commands": ["system.run"],
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


def test_managed_gateway_nodes_persist_last_connected_pairing_metadata_across_restart(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    first_app = create_app(app_settings)
    manager = first_app.state.manager
    manager.instances[7] = InstanceRuntime(
        instance_id=7,
        name="Managed Runtime Node",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
        connected=True,
        last_event_at="2026-04-22T15:04:05Z",
    )

    with TestClient(first_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        request_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.pair.request",
                "params": {
                    "nodeId": "7",
                    "displayName": "Pending Managed Node",
                    "platform": "linux",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )
        connected_response = client.get("/api/gateway/nodes/7")

    assert approve_response.status_code == 200
    expected_connected_at_ms = int(
        datetime(2026, 4, 22, 15, 4, 5, tzinfo=UTC).timestamp() * 1000
    )
    assert connected_response.status_code == 200
    assert connected_response.json() == {
        "node_id": "7",
        "display_name": "Managed Runtime Node",
        "platform": "stdio",
        "version": None,
        "core_version": None,
        "ui_version": None,
        "client_id": "7",
        "client_mode": "stdio",
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": str(tmp_path),
        "caps": [],
        "commands": [],
        "permissions": None,
        "paired": True,
        "connected": True,
        "connected_at_ms": expected_connected_at_ms,
        "approved_at_ms": approve_response.json()["node"]["approvedAtMs"],
    }

    restarted_app = create_app(app_settings)
    with TestClient(restarted_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        node_response = client.get("/api/gateway/nodes/7")

    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "7",
        "display_name": "Managed Runtime Node",
        "platform": "stdio",
        "version": None,
        "core_version": None,
        "ui_version": None,
        "client_id": None,
        "client_mode": None,
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": None,
        "caps": [],
        "commands": [],
        "permissions": None,
        "paired": True,
        "connected": False,
        "connected_at_ms": expected_connected_at_ms,
        "approved_at_ms": approve_response.json()["node"]["approvedAtMs"],
    }


def test_gateway_nodes_endpoints_keep_empty_live_command_surface_over_paired_values(
    tmp_path,
) -> None:
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
                    "nodeId": "pair-node-live-empty",
                    "displayName": "Catalog Node",
                    "platform": "linux",
                    "version": "1.0.0",
                    "coreVersion": "2.0.0",
                    "uiVersion": "3.0.0",
                    "deviceFamily": "server",
                    "modelIdentifier": "vm-standard",
                    "caps": ["shell"],
                    "commands": ["system.run"],
                    "remoteIp": "10.0.0.11",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )
        assert approve_response.status_code == 200

        registry = client.app.state.gateway_node_service.registry
        registry.register(
            _AutoReplyNodeConnection(registry, "conn-pair-node-live-empty"),
            GatewayNodeConnect(
                client_id="live-pair-node-live-empty",
                device_id="pair-node-live-empty",
                client_mode="desktop",
                display_name="Catalog Node",
                platform="linux",
                version="1.0.1",
                core_version="2.0.1",
                ui_version="3.0.1",
                device_family="server",
                model_identifier="vm-standard",
                path_env=str(tmp_path),
                caps=(),
                commands=(),
            ),
            remote_ip="10.0.0.12",
            connected_at_ms=321,
        )

        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/pair-node-live-empty")
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert nodes_response.status_code == 200
    nodes_payload = nodes_response.json()
    assert nodes_payload["paired_count"] == 1
    assert nodes_payload["connected_count"] == 1
    assert nodes_payload["nodes"] == [
        {
            "node_id": "pair-node-live-empty",
            "display_name": "Catalog Node",
            "platform": "linux",
            "version": "1.0.1",
            "core_version": "2.0.1",
            "ui_version": "3.0.1",
            "client_id": "live-pair-node-live-empty",
            "client_mode": "desktop",
            "remote_ip": "10.0.0.12",
            "device_family": "server",
            "model_identifier": "vm-standard",
            "path_env": str(tmp_path),
            "caps": [],
            "commands": [],
            "permissions": None,
            "paired": True,
            "connected": True,
            "connected_at_ms": 321,
            "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
        }
    ]
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "pair-node-live-empty",
        "display_name": "Catalog Node",
        "platform": "linux",
        "version": "1.0.1",
        "core_version": "2.0.1",
        "ui_version": "3.0.1",
        "client_id": "live-pair-node-live-empty",
        "client_mode": "desktop",
        "remote_ip": "10.0.0.12",
        "device_family": "server",
        "model_identifier": "vm-standard",
        "path_env": str(tmp_path),
        "caps": [],
        "commands": [],
        "permissions": None,
        "paired": True,
        "connected": True,
        "connected_at_ms": 321,
        "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
    }
    assert pair_list_response.status_code == 200
    assert pair_list_response.json() == {
        "pending": [],
        "paired": [
            {
                "nodeId": "pair-node-live-empty",
                "token": approve_response.json()["node"]["token"],
                "displayName": "Catalog Node",
                "platform": "linux",
                "version": "1.0.1",
                "coreVersion": "2.0.1",
                "uiVersion": "3.0.1",
                "deviceFamily": "server",
                "modelIdentifier": "vm-standard",
                "caps": ["shell"],
                "commands": ["system.run"],
                "remoteIp": "10.0.0.12",
                "permissions": None,
                "createdAtMs": approve_response.json()["node"]["createdAtMs"],
                "approvedAtMs": approve_response.json()["node"]["approvedAtMs"],
                "lastConnectedAtMs": 321,
            }
        ],
    }


def test_gateway_nodes_endpoints_pin_paired_commands_until_repair_request(tmp_path) -> None:
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
                    "nodeId": "pair-node-command-pin",
                    "displayName": "Pinned Node",
                    "platform": "darwin",
                    "commands": ["canvas.snapshot"],
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )
        assert approve_response.status_code == 200

        registry = client.app.state.gateway_node_service.registry
        registry.register(
            _AutoReplyNodeConnection(registry, "conn-pair-node-command-pin"),
            GatewayNodeConnect(
                client_id="live-pair-node-command-pin",
                device_id="pair-node-command-pin",
                client_mode="node",
                display_name="Pinned Node",
                platform="darwin",
                version="1.0.1",
                commands=("canvas.snapshot", "system.run"),
            ),
            connected_at_ms=321,
        )

        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/pair-node-command-pin")

    assert nodes_response.status_code == 200
    nodes_payload = nodes_response.json()
    assert nodes_payload["paired_count"] == 1
    assert nodes_payload["connected_count"] == 1
    assert nodes_payload["nodes"] == [
        {
            "node_id": "pair-node-command-pin",
            "display_name": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "core_version": None,
            "ui_version": None,
            "client_id": "live-pair-node-command-pin",
            "client_mode": "node",
            "remote_ip": None,
            "device_family": None,
            "model_identifier": None,
            "path_env": None,
            "caps": [],
            "commands": ["canvas.snapshot"],
            "permissions": None,
            "paired": True,
            "connected": True,
            "connected_at_ms": 321,
            "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
        }
    ]
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "pair-node-command-pin",
        "display_name": "Pinned Node",
        "platform": "darwin",
        "version": "1.0.1",
        "core_version": None,
        "ui_version": None,
        "client_id": "live-pair-node-command-pin",
        "client_mode": "node",
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": None,
        "caps": [],
        "commands": ["canvas.snapshot"],
        "permissions": None,
        "paired": True,
        "connected": True,
        "connected_at_ms": 321,
        "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
    }


def test_gateway_nodes_endpoints_stage_silent_scope_upgrade_request_for_paired_command_expansion(
    tmp_path,
) -> None:
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
                    "nodeId": "pair-node-scope-upgrade-catalog",
                    "displayName": "Pinned Node",
                    "platform": "darwin",
                    "commands": ["canvas.snapshot"],
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": request_id}},
        )
        assert approve_response.status_code == 200

        registry = client.app.state.gateway_node_service.registry
        registry.register(
            _AutoReplyNodeConnection(registry, "conn-pair-node-scope-upgrade-catalog"),
            GatewayNodeConnect(
                client_id="live-pair-node-scope-upgrade-catalog",
                device_id="pair-node-scope-upgrade-catalog",
                client_mode="node",
                display_name="Pinned Node",
                platform="darwin",
                version="1.0.1",
                commands=("canvas.snapshot", "system.run"),
            ),
            connected_at_ms=321,
        )

        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/pair-node-scope-upgrade-catalog")
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert nodes_response.status_code == 200
    nodes_payload = nodes_response.json()
    assert nodes_payload["nodes"] == [
        {
            "node_id": "pair-node-scope-upgrade-catalog",
            "display_name": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "core_version": None,
            "ui_version": None,
            "client_id": "live-pair-node-scope-upgrade-catalog",
            "client_mode": "node",
            "remote_ip": None,
            "device_family": None,
            "model_identifier": None,
            "path_env": None,
            "caps": [],
            "commands": ["canvas.snapshot"],
            "permissions": None,
            "paired": True,
            "connected": True,
            "connected_at_ms": 321,
            "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
        }
    ]
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "pair-node-scope-upgrade-catalog",
        "display_name": "Pinned Node",
        "platform": "darwin",
        "version": "1.0.1",
        "core_version": None,
        "ui_version": None,
        "client_id": "live-pair-node-scope-upgrade-catalog",
        "client_mode": "node",
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": None,
        "caps": [],
        "commands": ["canvas.snapshot"],
        "permissions": None,
        "paired": True,
        "connected": True,
        "connected_at_ms": 321,
        "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
    }

    assert pair_list_response.status_code == 200
    pair_list_payload = pair_list_response.json()
    pending_request_id = pair_list_payload["pending"][0]["requestId"]
    assert pending_request_id != request_id
    assert pair_list_payload["pending"] == [
        {
            "requestId": pending_request_id,
            "nodeId": "pair-node-scope-upgrade-catalog",
            "displayName": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": ["canvas.snapshot", "system.run"],
            "remoteIp": None,
            "silent": True,
            "ts": pair_list_payload["pending"][0]["ts"],
            "requiredApproveScopes": ["operator.pairing", "operator.admin"],
        }
    ]
    assert pair_list_payload["paired"] == [
        {
            "nodeId": "pair-node-scope-upgrade-catalog",
            "token": approve_response.json()["node"]["token"],
            "displayName": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": ["canvas.snapshot"],
            "remoteIp": None,
            "permissions": None,
            "createdAtMs": approve_response.json()["node"]["createdAtMs"],
            "approvedAtMs": approve_response.json()["node"]["approvedAtMs"],
            "lastConnectedAtMs": 321,
        }
    ]


def test_gateway_nodes_endpoints_stage_silent_upgrade_for_commandless_reconnect(
    tmp_path,
) -> None:
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
                    "nodeId": "pair-node-command-empty",
                    "displayName": "Pinned Node",
                    "platform": "darwin",
                },
            },
        )
        initial_request_id = request_response.json()["request"]["requestId"]
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.approve", "params": {"requestId": initial_request_id}},
        )
        assert approve_response.status_code == 200

        registry = client.app.state.gateway_node_service.registry
        registry.register(
            _AutoReplyNodeConnection(registry, "conn-pair-node-command-empty"),
            GatewayNodeConnect(
                client_id="live-pair-node-command-empty",
                device_id="pair-node-command-empty",
                client_mode="node",
                display_name="Pinned Node",
                platform="darwin",
                version="1.0.1",
                commands=("canvas.snapshot", "system.run"),
            ),
            connected_at_ms=321,
        )

        nodes_response = client.get("/api/gateway/nodes")
        node_response = client.get("/api/gateway/nodes/pair-node-command-empty")
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert nodes_response.status_code == 200
    nodes_payload = nodes_response.json()
    assert nodes_payload["nodes"] == [
        {
            "node_id": "pair-node-command-empty",
            "display_name": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "core_version": None,
            "ui_version": None,
            "client_id": "live-pair-node-command-empty",
            "client_mode": "node",
            "remote_ip": None,
            "device_family": None,
            "model_identifier": None,
            "path_env": None,
            "caps": [],
            "commands": [],
            "permissions": None,
            "paired": True,
            "connected": True,
            "connected_at_ms": 321,
            "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
        }
    ]
    assert node_response.status_code == 200
    assert node_response.json() == {
        "node_id": "pair-node-command-empty",
        "display_name": "Pinned Node",
        "platform": "darwin",
        "version": "1.0.1",
        "core_version": None,
        "ui_version": None,
        "client_id": "live-pair-node-command-empty",
        "client_mode": "node",
        "remote_ip": None,
        "device_family": None,
        "model_identifier": None,
        "path_env": None,
        "caps": [],
        "commands": [],
        "permissions": None,
        "paired": True,
        "connected": True,
        "connected_at_ms": 321,
        "approved_at_ms": nodes_payload["nodes"][0]["approved_at_ms"],
    }

    assert pair_list_response.status_code == 200
    pair_list_payload = pair_list_response.json()
    pending_request_id = pair_list_payload["pending"][0]["requestId"]
    assert pending_request_id != initial_request_id
    assert pair_list_payload["pending"] == [
        {
            "requestId": pending_request_id,
            "nodeId": "pair-node-command-empty",
            "displayName": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": ["canvas.snapshot", "system.run"],
            "remoteIp": None,
            "silent": True,
            "ts": pair_list_payload["pending"][0]["ts"],
            "requiredApproveScopes": ["operator.pairing", "operator.admin"],
        }
    ]
    assert pair_list_payload["paired"] == [
        {
            "nodeId": "pair-node-command-empty",
            "token": approve_response.json()["node"]["token"],
            "displayName": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": [],
            "remoteIp": None,
            "permissions": None,
            "createdAtMs": approve_response.json()["node"]["createdAtMs"],
            "approvedAtMs": approve_response.json()["node"]["approvedAtMs"],
            "lastConnectedAtMs": 321,
        }
    ]


def test_gateway_node_method_call_endpoint_blocks_scope_upgrade_until_repair_request_is_approved(
    tmp_path,
) -> None:
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
                    "nodeId": "pair-node-scope-upgrade-api",
                    "displayName": "Pinned Node",
                    "platform": "darwin",
                    "commands": ["canvas.snapshot"],
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
        assert approve_response.status_code == 200

        registry = client.app.state.gateway_node_service.registry
        registry.register(
            _AutoReplyNodeConnection(registry, "conn-pair-node-scope-upgrade-api"),
            GatewayNodeConnect(
                client_id="live-pair-node-scope-upgrade-api",
                device_id="pair-node-scope-upgrade-api",
                client_mode="node",
                display_name="Pinned Node",
                platform="darwin",
                version="1.0.1",
                commands=("canvas.snapshot", "system.run"),
            ),
            connected_at_ms=321,
        )

        invoke_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.invoke",
                "params": {
                    "nodeId": "pair-node-scope-upgrade-api",
                    "command": "system.run",
                    "params": {"command": "whoami"},
                    "idempotencyKey": "idem-system-run",
                },
            },
        )
        node_response = client.get("/api/gateway/nodes/pair-node-scope-upgrade-api")
        pair_list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "node.pair.list", "params": {}},
        )

    assert pair_list_response.status_code == 200
    pending_request_id = pair_list_response.json()["pending"][0]["requestId"]
    assert invoke_response.status_code == 409
    assert invoke_response.json() == {
        "detail": f"scope upgrade pending approval (requestId: {pending_request_id})"
    }
    assert node_response.status_code == 200
    assert node_response.json()["commands"] == ["canvas.snapshot"]
    assert pair_list_response.json()["pending"] == [
        {
            "requestId": pending_request_id,
            "nodeId": "pair-node-scope-upgrade-api",
            "displayName": "Pinned Node",
            "platform": "darwin",
            "version": "1.0.1",
            "coreVersion": None,
            "uiVersion": None,
            "deviceFamily": None,
            "modelIdentifier": None,
            "caps": [],
            "commands": ["canvas.snapshot", "system.run"],
            "remoteIp": None,
            "silent": True,
            "ts": pair_list_response.json()["pending"][0]["ts"],
            "requiredApproveScopes": ["operator.pairing", "operator.admin"],
        }
    ]


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


def test_gateway_node_call_endpoint_queues_foreground_ios_invoke_pending_actions(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    registry.register(
        _BackgroundUnavailableNodeConnection(registry, "conn-node-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            platform="ios",
            device_family="iphone",
            commands=("canvas.navigate",),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        invoke_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "node.invoke",
                "params": {
                    "nodeId": "node-1",
                    "command": "canvas.navigate",
                    "params": {"url": "http://example.com/"},
                    "idempotencyKey": "idem-queued",
                },
            },
        )
        pending_response = client.get("/api/gateway/nodes/node-1/pending-actions")
        pending_payload = pending_response.json()
        queued_action_id = pending_payload["actions"][0]["id"]
        ack_response = client.post(
            "/api/gateway/nodes/node-1/pending-actions/ack",
            json={"ids": [queued_action_id]},
        )
        empty_response = client.get("/api/gateway/nodes/node-1/pending-actions")

    assert invoke_response.status_code == 503
    assert invoke_response.json() == {
        "detail": "node command queued until iOS returns to foreground"
    }
    assert pending_response.status_code == 200
    assert pending_payload == {
        "nodeId": "node-1",
        "actions": [
            {
                "id": queued_action_id,
                "command": "canvas.navigate",
                "paramsJSON": '{"url": "http://example.com/"}',
                "enqueuedAtMs": pending_payload["actions"][0]["enqueuedAtMs"],
            }
        ],
    }
    assert ack_response.status_code == 200
    assert ack_response.json() == {
        "nodeId": "node-1",
        "ackedIds": [queued_action_id],
        "remainingCount": 0,
    }
    assert empty_response.status_code == 200
    assert empty_response.json() == {
        "nodeId": "node-1",
        "actions": [],
    }


def test_gateway_node_method_call_endpoint_rejects_system_exec_approvals_node_invoke(
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
                "method": "node.invoke",
                "params": {
                    "nodeId": "node-1",
                    "command": "system.execApprovals.list",
                    "params": {"file": "/tmp/policy.json"},
                    "idempotencyKey": "idem-system-exec-approvals",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "node.invoke does not allow system.execApprovals.*; use exec.approvals.node.*"
    )


@pytest.mark.parametrize(
    "proxy_params",
    [
        pytest.param({"method": "POST", "path": "profiles/create/"}, id="create-profile"),
        pytest.param({"method": "POST", "path": " /reset-profile/ "}, id="reset-profile"),
        pytest.param({"method": "DELETE", "path": "profiles/default/"}, id="delete-profile"),
    ],
)
def test_gateway_node_method_call_endpoint_rejects_persistent_browser_proxy_mutations(
    tmp_path,
    proxy_params: dict[str, str],
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
                "method": "node.invoke",
                "params": {
                    "nodeId": "node-1",
                    "command": "browser.proxy",
                    "params": proxy_params,
                    "idempotencyKey": "idem-browser-proxy-mutation",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "node.invoke cannot mutate persistent browser profiles via browser.proxy"
    )


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
    assert get_response.json() == {"triggers": ["openclaw", "claude"]}
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
    assert re.fullmatch(r"[0-9a-f]{64}", first_response.json()["id"])
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", first_response.json()["publicKey"])
    assert len(first_response.json()["publicKey"]) > 20
    identity_path = tmp_path / "data" / "settings" / "gateway-identity.json"
    assert identity_path.exists()
    stored = json.loads(identity_path.read_text(encoding="utf-8"))
    assert stored["version"] == 1
    assert stored["deviceId"] == first_response.json()["id"]
    assert "BEGIN PUBLIC KEY" in stored["publicKeyPem"]
    assert "BEGIN PRIVATE KEY" in stored["privateKeyPem"]


def test_gateway_node_method_call_endpoint_repairs_device_id_with_invalid_private_pem(
    tmp_path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    expected_id = hashlib.sha256(public_key_bytes).hexdigest()
    expected_public_key = base64.urlsafe_b64encode(public_key_bytes).decode("ascii").rstrip("=")
    identity_path = tmp_path / "data" / "settings" / "gateway-identity.json"
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(
        json.dumps(
            {
                "version": 1,
                "deviceId": "stale-device-id",
                "publicKeyPem": public_key_pem,
                "privateKeyPem": "not-a-valid-private-key",
                "createdAtMs": 123,
            },
            indent=2,
        )
        + "\n",
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
            json={"method": "gateway.identity.get", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"id": expected_id, "publicKey": expected_public_key}
    stored = json.loads(identity_path.read_text(encoding="utf-8"))
    assert stored["deviceId"] == expected_id
    assert stored["publicKeyPem"] == public_key_pem
    assert stored["privateKeyPem"] == "not-a-valid-private-key"
    assert stored["createdAtMs"] == 123


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


@pytest.mark.parametrize("provider", ["   ", "not-a-real-provider"])
def test_gateway_node_method_call_endpoint_rejects_blank_or_unknown_tts_provider(
    tmp_path,
    provider: str,
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
                "method": "tts.setProvider",
                "params": {"provider": provider},
            },
        )
        status_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "tts.status", "params": {}},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid provider. Use a registered TTS provider id."
    assert status_response.status_code == 200
    assert status_response.json()["provider"] is None


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


def test_gateway_node_method_call_endpoint_returns_models_auth_status_unavailable_contract(
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
            json={"method": "models.authStatus", "params": {"refresh": True}},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "models.authStatus is unavailable until model auth health runtime is wired"
    }


def test_gateway_node_method_call_endpoint_rejects_unknown_device_token_target(
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
                "method": "device.token.rotate",
                "params": {
                    "deviceId": "device-1",
                    "role": "operator",
                    "scopes": ["operator.read"],
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "device token rotation denied"}


def test_gateway_node_method_call_endpoint_supports_device_pair_lifecycle(tmp_path) -> None:
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
                    "nodeId": "device-api-node",
                    "displayName": "API Device",
                    "platform": "windows",
                    "deviceFamily": "desktop",
                    "remoteIp": "10.0.0.52",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "device.pair.list", "params": {}},
        )
        approve_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "device.pair.approve", "params": {"requestId": request_id}},
        )
        remove_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "device.pair.remove", "params": {"deviceId": "device-api-node"}},
        )

    assert list_response.status_code == 200
    assert list_response.json()["pending"][0]["deviceId"] == "device-api-node"
    assert approve_response.status_code == 200
    approved_device = approve_response.json()["device"]
    assert approved_device["deviceId"] == "device-api-node"
    assert "token" not in approved_device
    assert approved_device["tokens"] == {}
    assert remove_response.status_code == 200
    assert remove_response.json() == {"deviceId": "device-api-node"}


def test_gateway_node_method_call_endpoint_supports_device_token_lifecycle(tmp_path) -> None:
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
                    "nodeId": "device-token-api-node",
                    "displayName": "API Token Device",
                },
            },
        )
        request_id = request_response.json()["request"]["requestId"]
        client.post(
            "/api/gateway/node-methods/call",
            json={"method": "device.pair.approve", "params": {"requestId": request_id}},
        )
        rotate_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "device.token.rotate",
                "params": {
                    "deviceId": "device-token-api-node",
                    "role": "operator",
                    "scopes": ["operator.read"],
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "device.pair.list", "params": {}},
        )
        revoke_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "device.token.revoke",
                "params": {"deviceId": "device-token-api-node", "role": "operator"},
            },
        )

    assert rotate_response.status_code == 200
    rotated = rotate_response.json()
    assert rotated["deviceId"] == "device-token-api-node"
    assert rotated["role"] == "operator"
    assert rotated["scopes"] == ["operator.read"]
    assert isinstance(rotated["token"], str)
    assert list_response.status_code == 200
    assert list_response.json()["paired"][0]["tokens"][0]["role"] == "operator"
    assert revoke_response.status_code == 200
    assert revoke_response.json()["deviceId"] == "device-token-api-node"
    assert revoke_response.json()["role"] == "operator"
    assert isinstance(revoke_response.json()["revokedAtMs"], int)


def test_gateway_node_method_call_endpoint_tracks_plugin_approval_lifecycle(tmp_path) -> None:
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
                "method": "plugin.approval.request",
                "params": {
                    "pluginId": "alpha-plugin",
                    "title": "Install alpha plugin",
                    "description": "Approve installation of the alpha plugin bundle.",
                    "severity": "warning",
                    "toolName": "plugin.install",
                    "toolCallId": "call-1",
                    "agentId": "agent-1",
                    "sessionKey": "session-1",
                    "turnSourceChannel": "slack",
                    "turnSourceTo": "ops",
                    "turnSourceAccountId": "acct-1",
                    "turnSourceThreadId": 42,
                    "timeoutMs": 30_000,
                    "twoPhase": True,
                },
            },
        )
        approval_id = request_response.json()["id"]
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "plugin.approval.list", "params": {}},
        )
        resolve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "plugin.approval.resolve",
                "params": {"id": approval_id, "decision": "allow-always"},
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "plugin.approval.waitDecision", "params": {"id": approval_id}},
        )

    assert request_response.status_code == 200
    assert isinstance(approval_id, str)
    assert approval_id.startswith("plugin:")
    assert request_response.json()["status"] == "accepted"
    assert list_response.status_code == 200
    assert [approval["id"] for approval in list_response.json()["approvals"]] == [approval_id]
    assert resolve_response.status_code == 200
    assert resolve_response.json() == {"ok": True}
    assert wait_response.status_code == 200
    assert wait_response.json()["decision"] == "allow-always"


def test_gateway_node_method_call_endpoint_tracks_exec_approval_lifecycle(tmp_path) -> None:
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
                "method": "exec.approval.request",
                "params": {
                    "id": "exec-api-approval-1",
                    "command": "npm test",
                    "commandArgv": ["npm", "test"],
                    "env": {"CI": "1"},
                    "cwd": "C:/workspace",
                    "host": "gateway",
                    "security": "allowlist",
                    "ask": "on-miss",
                    "agentId": "agent-1",
                    "resolvedPath": "C:/workspace/package.json",
                    "sessionKey": "session-1",
                    "timeoutMs": 30_000,
                    "twoPhase": True,
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approval.list", "params": {}},
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approval.get", "params": {"id": "exec-api-approval-1"}},
        )
        resolve_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "exec.approval.resolve",
                "params": {"id": "exec-api-approval-1", "decision": "allow-always"},
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "exec.approval.waitDecision",
                "params": {"id": "exec-api-approval-1"},
            },
        )

    assert request_response.status_code == 200
    assert request_response.json()["id"] == "exec-api-approval-1"
    assert list_response.status_code == 200
    assert [approval["id"] for approval in list_response.json()["approvals"]] == [
        "exec-api-approval-1"
    ]
    assert get_response.status_code == 200
    assert get_response.json()["allowedDecisions"] == ["allow-once", "allow-always", "deny"]
    assert resolve_response.status_code == 200
    assert resolve_response.json() == {"ok": True}
    assert wait_response.status_code == 200
    assert wait_response.json()["decision"] == "allow-always"


def test_gateway_node_method_call_endpoint_persists_exec_approvals_config(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    file_config = {
        "version": 1,
        "socket": {"path": "C:/tmp/approvals.sock", "token": "secret-token"},
        "defaults": {
            "security": "strict",
            "ask": "manual",
            "askFallback": "deny",
            "autoAllowSkills": True,
        },
    }

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        before_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approvals.get", "params": {}},
        )
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approvals.set", "params": {"file": file_config}},
        )
        after_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approvals.get", "params": {}},
        )
        node_set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "exec.approvals.node.set",
                "params": {"nodeId": "node-1", "file": {"version": 1, "agents": {}}},
            },
        )
        node_get_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "exec.approvals.node.get", "params": {"nodeId": "node-1"}},
        )

    assert before_response.status_code == 200
    assert before_response.json()["exists"] is False
    assert set_response.status_code == 200
    assert set_response.json()["file"]["socket"] == {"path": "C:/tmp/approvals.sock"}
    assert "token" not in set_response.json()["file"]["socket"]
    assert after_response.status_code == 200
    assert after_response.json() == set_response.json()
    assert node_set_response.status_code == 200
    assert node_get_response.status_code == 200
    assert node_get_response.json() == node_set_response.json()


def test_gateway_node_method_call_endpoint_toggles_attention_queue_runtime(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        before_dashboard = client.get("/api/dashboard")
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": False}},
        )
        disabled_dashboard = client.get("/api/dashboard")
        enable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": True}},
        )
        enabled_dashboard = client.get("/api/dashboard")

    assert before_dashboard.status_code == 200
    assert before_dashboard.json()["attention_queue"]["enabled"] is True
    assert disable_response.status_code == 200
    assert disable_response.json() == {"ok": True, "enabled": False}
    assert disabled_dashboard.status_code == 200
    assert disabled_dashboard.json()["attention_queue"]["enabled"] is False
    assert disabled_dashboard.json()["attention_queue"]["headline"] == "Attention queue is manual"
    assert enable_response.status_code == 200
    assert enable_response.json() == {"ok": True, "enabled": True}
    assert enabled_dashboard.status_code == 200
    assert enabled_dashboard.json()["attention_queue"]["enabled"] is True


def test_gateway_node_method_call_endpoint_wake_now_stays_pending_when_heartbeats_are_disabled(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": False}},
        )
        wake_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert disable_response.status_code == 200
    assert disable_response.json() == {"ok": True, "enabled": False}
    assert wake_response.status_code == 200
    assert wake_response.json() == {"ok": True}
    assert [message["content"] for message in messages if message["role"] == "user"] == []
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "now"
    assert wake_requests[0]["text"] == "Resume parity from the latest checkpoint."
    assert wake_requests[0]["status"] == "pending"


def test_attention_queue_tick_drains_multiple_pending_wakes_in_one_pass(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": False}},
        )
        first_wake = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {"mode": "now", "text": "Resume parity from checkpoint A."},
            },
        )
        second_wake = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {"mode": "now", "text": "Resume parity from checkpoint B."},
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert disable_response.status_code == 200
    assert disable_response.json() == {"ok": True, "enabled": False}
    assert first_wake.status_code == 200
    assert second_wake.status_code == 200
    assert acted is True
    assert [message["content"] for message in messages if message["role"] == "user"] == [
        "Resume parity from checkpoint B.",
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["text"] == "Resume parity from checkpoint B."
    assert wake_requests[0]["status"] == "dispatched"


def test_attention_queue_tick_coalesces_duplicate_pending_wakes_in_one_pass(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": False}},
        )
        first_wake = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {"mode": "now", "text": "Resume parity from the latest checkpoint."},
            },
        )
        second_wake = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {"mode": "now", "text": "Resume parity from the latest checkpoint."},
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert disable_response.status_code == 200
    assert disable_response.json() == {"ok": True, "enabled": False}
    assert first_wake.status_code == 200
    assert second_wake.status_code == 200
    assert acted is True
    assert [message["content"] for message in messages if message["role"] == "user"] == [
        "Resume parity from the latest checkpoint."
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["status"] == "dispatched"


def test_attention_queue_tick_collapses_historical_same_target_pending_rows_before_dispatch(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []
    target_session_key = "agent:main:thread:demo"

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(app_settings.db_path) as db:
            db.execute(
                """
                INSERT INTO gateway_wake_requests (
                    mode,
                    text,
                    reason,
                    agent_id,
                    session_key,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    "next-heartbeat",
                    "Resume parity from checkpoint A.",
                    "exec-event",
                    "main",
                    target_session_key,
                    now,
                    now,
                ),
            )
            db.execute(
                """
                INSERT INTO gateway_wake_requests (
                    mode,
                    text,
                    reason,
                    agent_id,
                    session_key,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    "next-heartbeat",
                    "Resume parity from checkpoint B.",
                    "retry",
                    "main",
                    target_session_key,
                    now,
                    now,
                ),
            )
            db.commit()
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert acted is True
    assert submit_calls == [("Resume parity from checkpoint A.", target_session_key)]
    assert len(wake_requests) == 1
    assert wake_requests[0]["text"] == "Resume parity from checkpoint A."
    assert wake_requests[0]["reason"] == "exec-event"
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == target_session_key
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_now_auto_retries_after_submit_error(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[str] = []

    async def flaky_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard, session_key
        submit_calls.append(prompt)
        if len(submit_calls) == 1:
            raise RuntimeError("wake submit boom")
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", flaky_submit)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {"mode": "now", "text": "Resume parity after the wake failure."},
            },
        )
        wake_requests = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_gateway_wake_requests()),
            lambda rows: len(rows) == 1 and rows[0]["status"] == "dispatched",
            timeout_seconds=2.5,
        )
        control_chat_messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert submit_calls == [
        "Resume parity after the wake failure.",
        "Resume parity after the wake failure.",
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["status"] == "dispatched"
    assert [
        message["content"]
        for message in control_chat_messages
        if message["role"] == "user"
    ] == []


def test_attention_queue_reenable_clears_stale_wake_retry_cooldown(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[str] = []

    async def flaky_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard, session_key
        submit_calls.append(prompt)
        if len(submit_calls) == 1:
            raise RuntimeError("wake submit boom")
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr("openzues.services.control_chat.WAKE_RETRY_COOLDOWN_SECONDS", 60.0)
        monkeypatch.setattr("openzues.services.control_chat.time.monotonic", lambda: 100.0)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", flaky_submit)
        
        async def no_op_start_attention_queue(*args, **kwargs) -> None:
            del args, kwargs

        monkeypatch.setattr(
            client.app.state.control_chat_service,
            "start_attention_queue",
            no_op_start_attention_queue,
        )
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": False}},
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity after the wake failure.",
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        with pytest.raises(RuntimeError, match="wake submit boom"):
            asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        enable_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "set-heartbeats", "params": {"enabled": True}},
        )
        refreshed_dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(refreshed_dashboard)
        )
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())
        with client.app.state.control_chat_service._wake_retry_timer_lock:
            if client.app.state.control_chat_service._wake_retry_timer is not None:
                client.app.state.control_chat_service._wake_retry_timer.cancel()
                client.app.state.control_chat_service._wake_retry_timer = None

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert disable_response.status_code == 200
    assert disable_response.json() == {"ok": True, "enabled": False}
    assert enable_response.status_code == 200
    assert enable_response.json() == {"ok": True, "enabled": True}
    assert acted is True
    assert submit_calls == [
        "Resume parity after the wake failure.",
        "Resume parity after the wake failure.",
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["status"] == "dispatched"


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


def test_gateway_node_method_call_endpoint_rejects_rate_wpm_outside_upstream_window(
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
            tts_runtime_service=GatewayTtsRuntimeService(
                data_dir=tmp_path / "data",
                convert_runner=lambda **_: (_ for _ in ()).throw(
                    AssertionError("convert_runner should not be reached for invalid talk.speak")
                ),
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
                    "rateWpm": 350,
                },
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "invalid talk.speak params: rateWpm must resolve to speed between 0.5 and 2.0"
    )


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


def test_gateway_node_method_call_endpoint_normalizes_blank_tts_convert_selectors(
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
                    "channel": "   ",
                    "provider": "   ",
                    "modelId": "   ",
                    "voiceId": "   ",
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
        "channel": None,
        "provider": "microsoft",
        "model_id": None,
        "voice_id": None,
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
        array_lookup_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "localMediaPreviewRoots"}},
        )
        embed_lookup_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "embedSandbox"}},
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
    assert array_lookup_response.status_code == 200
    assert array_lookup_response.json() == {
        "path": "localMediaPreviewRoots",
        "schema": {
            "type": "array",
            "title": "Local Media Preview Roots",
        },
        "hint": {"label": "Local Media Preview Roots"},
        "hintPath": "localMediaPreviewRoots",
        "children": [
            {
                "key": "*",
                "path": "localMediaPreviewRoots.*",
                "type": "string",
                "required": False,
                "hasChildren": False,
                "hint": {"label": "Local Media Preview Root"},
                "hintPath": "localMediaPreviewRoots[]",
            }
        ],
    }
    assert embed_lookup_response.status_code == 200
    assert embed_lookup_response.json() == {
        "path": "embedSandbox",
        "schema": {
            "type": "string",
            "title": "Embed Sandbox",
            "enum": ["strict", "scripts", "trusted"],
        },
        "hint": {"label": "Embed Sandbox"},
        "hintPath": "embedSandbox",
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


def test_gateway_node_method_call_endpoint_config_schema_lookup_rejects_empty_or_dot_only_path(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        for path in ["", ".", "..."]:
            response = client.post(
                "/api/gateway/node-methods/call",
                json={"method": "config.schema.lookup", "params": {"path": path}},
            )

            assert response.status_code == 400
            assert response.json()["detail"] == "config schema path not found"


def test_gateway_node_method_call_endpoint_marks_branch_schema_children(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_root_schema",
        lambda: {
            "type": "object",
            "properties": {
                "parent": {
                    "type": "object",
                    "properties": {
                        "branch": {
                            "title": "Branch Field",
                            "allOf": [
                                {"type": "string"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "token": {"type": "string"},
                                    },
                                },
                            ],
                        }
                    },
                }
            },
        },
    )
    monkeypatch.setattr(gateway_config_schema_module, "_UI_HINTS", {})
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "parent"}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "path": "parent",
        "schema": {
            "type": "object",
        },
        "children": [
            {
                "key": "branch",
                "path": "parent.branch",
                "type": None,
                "required": False,
                "hasChildren": True,
            }
        ],
    }


def test_gateway_node_method_call_endpoint_uses_indexed_tuple_item_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_root_schema",
        lambda: {
            "type": "object",
            "properties": {
                "pair": {
                    "type": "array",
                    "items": [
                        {"type": "string", "title": "First Item"},
                        {"type": "number", "title": "Second Item"},
                    ],
                }
            },
        },
    )
    monkeypatch.setattr(gateway_config_schema_module, "_UI_HINTS", {})
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.schema.lookup", "params": {"path": "pair.1"}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "path": "pair.1",
        "schema": {
            "type": "number",
            "title": "Second Item",
        },
        "children": [],
    }


def test_gateway_node_method_call_endpoint_supports_scoped_plugin_config_lookup(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_root_schema",
        lambda: {
            "type": "object",
            "properties": {
                "$schema": {
                    "type": "string",
                    "title": "Schema URI",
                },
                "plugins": {
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "object",
                            "properties": {
                                "@openclaw/voice-call": {
                                    "type": "object",
                                    "properties": {
                                        "config": {
                                            "type": "object",
                                            "title": "Voice Call Config",
                                            "properties": {
                                                "provider": {
                                                    "type": "string",
                                                    "title": "Provider",
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                },
            },
        },
    )
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_UI_HINTS",
        {
            "$schema": {"label": "Schema URI"},
            "plugins.entries.@openclaw/voice-call.config": {
                "label": "Voice Call Config",
            },
        },
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
            json={
                "method": "config.schema.lookup",
                "params": {"path": "plugins.entries.@openclaw/voice-call.config"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "path": "plugins.entries.@openclaw/voice-call.config",
        "schema": {
            "type": "object",
            "title": "Voice Call Config",
        },
        "hint": {"label": "Voice Call Config"},
        "hintPath": "plugins.entries.@openclaw/voice-call.config",
        "children": [
            {
                "key": "provider",
                "path": "plugins.entries.@openclaw/voice-call.config.provider",
                "type": "string",
                "required": False,
                "hasChildren": False,
            }
        ],
    }


def test_gateway_node_method_call_endpoint_accepts_punctuation_rich_lookup_paths(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_id = "@openclaw/voice-call+beta:v2"
    plugin_path = f"plugins.entries.{plugin_id}.config"
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_root_schema",
        lambda: {
            "type": "object",
            "properties": {
                "plugins": {
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "object",
                            "properties": {
                                plugin_id: {
                                    "type": "object",
                                    "properties": {
                                        "config": {
                                            "type": "object",
                                            "title": "Voice Call Beta Config",
                                            "properties": {
                                                "provider": {
                                                    "type": "string",
                                                    "title": "Provider",
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_UI_HINTS",
        {
            plugin_path: {
                "label": "Voice Call Beta Config",
            },
        },
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
            json={
                "method": "config.schema.lookup",
                "params": {"path": plugin_path},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "path": plugin_path,
        "schema": {
            "type": "object",
            "title": "Voice Call Beta Config",
        },
        "hint": {"label": "Voice Call Beta Config"},
        "hintPath": plugin_path,
        "children": [
            {
                "key": "provider",
                "path": f"{plugin_path}.provider",
                "type": "string",
                "required": False,
                "hasChildren": False,
            }
        ],
    }


def test_gateway_node_method_call_endpoint_accepts_long_valid_lookup_paths(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_segment = "p" * 1100
    long_path = f"{long_segment}.leaf"
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_root_schema",
        lambda: {
            "type": "object",
            "properties": {
                long_segment: {
                    "type": "object",
                    "title": "Long Segment Container",
                    "properties": {
                        "leaf": {
                            "type": "string",
                            "title": "Long Path Leaf",
                        }
                    },
                }
            },
        },
    )
    monkeypatch.setattr(
        gateway_config_schema_module,
        "_UI_HINTS",
        {
            long_path: {
                "label": "Long Path Leaf",
            },
        },
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
            json={
                "method": "config.schema.lookup",
                "params": {"path": long_path},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "path": long_path,
        "schema": {
            "type": "string",
            "title": "Long Path Leaf",
        },
        "hint": {"label": "Long Path Leaf"},
        "hintPath": long_path,
        "children": [],
    }


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


def test_gateway_node_method_call_endpoint_supports_tools_effective_with_empty_toolsets(
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
                toolsets=[],
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
    assert payload["profile"] == "minimal"
    assert payload["groups"] == [
        {
            "id": "core",
            "label": "Built-in tools",
            "source": "core",
            "tools": [],
        }
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
        "traceLevel": None,
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


def test_gateway_node_method_call_endpoint_treats_chat_send_stop_message_as_abort(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                name="Gateway Chat Stop Loop",
                objective="Abort the live control chat thread from chat.send stop text.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-chat-stop-1",
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
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": " /STOP!!! ",
                    "idempotencyKey": "run-chat-send-stop-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": True,
        "runIds": ["run-chat-send-1"],
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert all("/STOP" not in str(message["content"]) for message in messages)


def test_gateway_node_method_call_endpoint_chat_send_stop_message_reports_no_active_run(
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
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "stop please",
                    "idempotencyKey": "run-chat-send-stop-idle-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": False,
        "runIds": [],
    }
    assert messages == []


def test_gateway_node_method_call_endpoint_ignores_blank_chat_send_originating_fields() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-blank-origin-api"
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
                    "originatingChannel": "   ",
                    "originatingTo": "   ",
                    "originatingAccountId": "   ",
                    "originatingThreadId": "   ",
                    "idempotencyKey": "run-chat-send-blank-origin-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-blank-origin-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


def test_gateway_node_method_call_endpoint_preserves_chat_send_originating_fields() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-origin-runtime-api"
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
                    "originatingChannel": "slack",
                    "originatingTo": "C12345",
                    "originatingAccountId": "T999",
                    "originatingThreadId": "1714000000.000100",
                    "idempotencyKey": "run-chat-send-origin-runtime-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-origin-runtime-api-1",
        "status": "ok",
    }
    assert messages[-2]["content"] == "\n".join(
        [
            "[OpenClaw route provenance]",
            "OriginatingChannel: slack",
            "OriginatingTo: C12345",
            "OriginatingAccountId: T999",
            "OriginatingThreadId: 1714000000.000100",
            "",
            "status",
        ]
    )


def test_gateway_node_method_call_endpoint_preserves_chat_send_system_provenance() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-system-runtime-api"
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
                    "systemInputProvenance": {
                        "kind": "internal_system",
                        "originSessionId": "session-123",
                        "sourceSessionKey": "openzues:thread:source",
                        "sourceChannel": "slack",
                        "sourceTool": "gateway",
                    },
                    "systemProvenanceReceipt": "Gateway witness",
                    "idempotencyKey": "run-chat-send-system-runtime-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-system-runtime-api-1",
        "status": "ok",
    }
    assert messages[-2]["content"] == "\n".join(
        [
            "Gateway witness",
            "[OpenClaw input provenance]",
            "Kind: internal_system",
            "originSessionId: session-123",
            "sourceSessionKey: openzues:thread:source",
            "sourceChannel: slack",
            "sourceTool: gateway",
            "",
            "status",
        ]
    )


def test_remote_chat_send_blank_system_receipt_honors_scope_and_omission() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-blank-system-receipt-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        operator_send_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {operator_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemProvenanceReceipt": "   ",
                    "idempotencyKey": "run-chat-send-blank-system-receipt-operator-api-1",
                },
            },
        )
        owner_send_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemProvenanceReceipt": "   ",
                    "idempotencyKey": "run-chat-send-blank-system-receipt-owner-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert operator_send_response.status_code == 400
    assert operator_send_response.json()["detail"] == "system provenance fields require admin scope"
    assert owner_send_response.status_code == 200
    assert owner_send_response.json() == {
        "runId": "run-chat-send-blank-system-receipt-owner-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


def test_remote_chat_send_rejects_null_byte_system_receipt() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-null-system-receipt-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    bootstrap_app = create_app(app_settings)
    with TestClient(bootstrap_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        owner_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Owner",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert owner_response.status_code == 200
    owner_api_key = owner_response.json()["api_key"]

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemProvenanceReceipt": "wit\u0000ness",
                    "idempotencyKey": "run-chat-send-null-system-receipt-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "message must not contain null bytes"


def test_remote_chat_send_blank_message_with_provenance_requires_message_or_attachment() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-empty-provenance-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    bootstrap_app = create_app(app_settings)
    with TestClient(bootstrap_app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        owner_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Owner",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert owner_response.status_code == 200
    owner_api_key = owner_response.json()["api_key"]

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        explicit_origin_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "",
                    "originatingChannel": "slack",
                    "originatingTo": "C12345",
                    "idempotencyKey": "run-chat-send-empty-origin-api-1",
                },
            },
        )
        provenance_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "",
                    "systemInputProvenance": {"kind": "internal_system"},
                    "idempotencyKey": "run-chat-send-empty-provenance-api-1",
                },
            },
        )
        receipt_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "",
                    "systemProvenanceReceipt": "Gateway witness",
                    "idempotencyKey": "run-chat-send-empty-receipt-api-1",
                },
            },
        )

    assert explicit_origin_response.status_code == 400
    assert explicit_origin_response.json()["detail"] == "message or attachment required"
    assert provenance_response.status_code == 400
    assert provenance_response.json()["detail"] == "message or attachment required"
    assert receipt_response.status_code == 400
    assert receipt_response.json()["detail"] == "message or attachment required"


def test_remote_chat_send_invalid_system_input_provenance_honors_scope_and_omission() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-invalid-provenance-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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
        operator_send_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {operator_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemInputProvenance": {"kind": "not-a-real-kind"},
                    "idempotencyKey": "run-chat-send-invalid-provenance-operator-api-1",
                },
            },
        )
        owner_send_response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {owner_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemInputProvenance": {"kind": "not-a-real-kind"},
                    "idempotencyKey": "run-chat-send-invalid-provenance-owner-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert operator_send_response.status_code == 400
    assert operator_send_response.json()["detail"] == "system provenance fields require admin scope"
    assert owner_send_response.status_code == 200
    assert owner_send_response.json() == {
        "runId": "run-chat-send-invalid-provenance-owner-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


@pytest.mark.parametrize(("raw_value",), [("",), (0,), (False,)])
def test_remote_chat_send_falsey_scalar_system_input_provenance_is_omitted_before_scope_gate(
    raw_value: object,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-falsey-provenance-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
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

    assert operator_response.status_code == 200
    operator_api_key = operator_response.json()["api_key"]

    remote_app = create_app(app_settings)
    with TestClient(remote_app, client=("203.0.113.7", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            headers={"Authorization": f"Bearer {operator_api_key}"},
            json={
                "method": "chat.send",
                "params": {
                    "sessionKey": "openzues:thread:demo",
                    "message": "status",
                    "systemInputProvenance": raw_value,
                    "idempotencyKey": "run-chat-send-falsey-provenance-operator-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-falsey-provenance-operator-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_ignores_inert_chat_send_attachments(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-inert-attachments-api"
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
                    "attachments": attachments,
                    "idempotencyKey": "run-chat-send-inert-attachments-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-inert-attachments-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


def _assert_gateway_attachment_was_persisted(
    *,
    app_settings: Settings,
    prompt: str,
    encoded_content: str = "Zm9v",
    extension: str = "png",
) -> None:
    decoded_content = base64.b64decode(encoded_content)
    digest = hashlib.sha256(decoded_content).hexdigest()
    stored_path = (
        app_settings.data_dir / "gateway-attachments" / "inbound" / f"{digest}.{extension}"
    )

    assert stored_path.read_bytes() == decoded_content
    assert f"media://inbound/{digest}" in prompt
    assert f"sha256={digest}" in prompt
    assert "bytes=3" in prompt
    assert str(stored_path) in prompt
    assert encoded_content not in prompt


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                    "content": "Zm9v",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "Zm9v",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_sends_effective_chat_send_attachments_(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-send-effective-attachments-api"
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
                    "attachments": attachments,
                    "idempotencyKey": "run-chat-send-effective-attachments-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-chat-send-effective-attachments-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert "status" in messages[-2]["content"]
    assert "Gateway attachments:" in messages[-2]["content"]
    assert "image/png" in messages[-2]["content"]
    _assert_gateway_attachment_was_persisted(
        app_settings=app_settings,
        prompt=messages[-2]["content"],
    )


@pytest.mark.parametrize(
    ("method", "session_field"),
    [
        ("chat.send", "sessionKey"),
        ("sessions.send", "key"),
        ("sessions.steer", "key"),
    ],
)
def test_gateway_node_method_call_endpoint_requires_message_or_effective_attachment(
    method: str,
    session_field: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-message-or-attachment-required-api"
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
                "method": method,
                "params": {
                    session_field: "openzues:thread:demo",
                    "message": "",
                    "attachments": [
                        {
                            "type": "image",
                            "mimeType": "image/png",
                            "fileName": "preview.png",
                        }
                    ],
                    "idempotencyKey": f"run-{method.replace('.', '-')}-empty-message-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "message or attachment required"


@pytest.mark.parametrize(
    ("method", "session_field"),
    [
        ("chat.send", "sessionKey"),
        ("sessions.send", "key"),
        ("sessions.steer", "key"),
    ],
)
def test_gateway_node_method_call_endpoint_rejects_null_bytes_in_send_message(
    method: str,
    session_field: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-send-null-bytes-api"
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
                "method": method,
                "params": {
                    session_field: "openzues:thread:demo",
                    "message": "sta\u0000tus",
                    "idempotencyKey": f"run-{method.replace('.', '-')}-null-byte-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "message must not contain null bytes"


@pytest.mark.parametrize(
    ("method", "session_field"),
    [
        ("chat.send", "sessionKey"),
        ("sessions.send", "key"),
        ("sessions.steer", "key"),
    ],
)
def test_gateway_node_method_call_endpoint_sanitizes_send_message_before_runtime(
    method: str,
    session_field: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-send-sanitize-api"
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
                "method": method,
                "params": {
                    session_field: "openzues:thread:demo",
                    "message": "Cafe\u0301\u0007",
                    "idempotencyKey": f"run-{method.replace('.', '-')}-sanitize-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": f"run-{method.replace('.', '-')}-sanitize-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "Café"
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


def test_gateway_node_method_call_endpoint_treats_sessions_send_stop_message_as_abort(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                name="Gateway Sessions Send Stop Loop",
                objective="Abort the live control chat thread from sessions.send stop text.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-sessions-send-stop-1",
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
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": " /STOP!!! ",
                    "idempotencyKey": "run-session-send-stop-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": True,
        "runIds": ["run-session-send-1"],
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert all("/STOP" not in str(message["content"]) for message in messages)


def test_gateway_node_method_call_endpoint_sessions_send_stop_message_reports_no_active_run(
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
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "stop please",
                    "idempotencyKey": "run-session-send-stop-idle-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": False,
        "runIds": [],
    }
    assert messages == []


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_ignores_inert_sessions_send_attachments(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-send-inert-attachments-api"
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
                    "attachments": attachments,
                    "idempotencyKey": "run-session-send-inert-attachments-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-send-inert-attachments-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert [message["session_key"] for message in messages[-2:]] == [
        "openzues:thread:demo",
        "openzues:thread:demo",
    ]


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                    "content": "Zm9v",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "Zm9v",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_sends_effective_sessions_send_attachments_(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-send-effective-attachments-api"
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
                    "attachments": attachments,
                    "idempotencyKey": "run-session-send-effective-attachments-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-send-effective-attachments-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert "status" in messages[-2]["content"]
    assert "Gateway attachments:" in messages[-2]["content"]
    assert "image/png" in messages[-2]["content"]
    _assert_gateway_attachment_was_persisted(
        app_settings=app_settings,
        prompt=messages[-2]["content"],
    )


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
    assert response.json() == {
        "runId": "run-session-steer-1",
        "status": "ok",
        "interruptedActiveRun": True,
    }
    assert [message["role"] for message in messages[-4:]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[-2]["content"] == "redirect"


def test_gateway_node_method_call_endpoint_sessions_send_started_ack_attaches_message_seq(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-send-started-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    database = Database(app_settings.db_path)

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "started"}

    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            database=database,
            chat_send_service=fake_chat_send_service,
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Existing transcript line.",
                session_key="openzues:thread:demo",
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "status",
                    "idempotencyKey": "run-session-send-started-api-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-send-started-api-1",
        "status": "started",
        "messageSeq": 2,
    }


def test_gateway_node_method_call_endpoint_sessions_steer_started_ack_attaches_both_flags(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-started-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    database = Database(app_settings.db_path)

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "started"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        del session_key, run_id
        return {"ok": True}

    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            database=database,
            chat_send_service=fake_chat_send_service,
            chat_abort_service=fake_chat_abort_service,
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Existing transcript line.",
                session_key="openzues:thread:demo",
            )
        )
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "status",
                    "idempotencyKey": "run-session-send-started-api-1",
                },
            },
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.steer",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "redirect",
                    "idempotencyKey": "run-session-steer-started-api-1",
                },
            },
        )

    assert send_response.status_code == 200
    assert send_response.json() == {
        "runId": "run-session-send-started-api-1",
        "status": "started",
        "messageSeq": 2,
    }
    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-steer-started-api-1",
        "status": "started",
        "messageSeq": 2,
        "interruptedActiveRun": True,
    }


def test_gateway_node_method_call_endpoint_sessions_steer_without_interrupt_emits_send_reason(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-event-api"
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
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"traceLevel": "verbose"},
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.steer",
                "params": {
                    "key": session_key,
                    "message": "redirect",
                    "idempotencyKey": "run-session-steer-standalone-api-1",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-steer-standalone-api-1",
        "status": "ok",
    }
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event"
        and event.get("event") == "sessions.changed"
        and isinstance(event.get("payload"), dict)
        and isinstance(event["payload"].get("reason"), str)
    ]
    assert len(sessions_changed) == 1
    assert sessions_changed[0]["payload"] == {
        "sessionKey": session_key,
        "reason": "send",
        "ts": sessions_changed[0]["payload"]["ts"],
        "updatedAt": sessions_changed[0]["payload"]["updatedAt"],
        "sessionId": None,
        "kind": "global",
        "subject": "Operator control chat",
        "displayName": "OpenZues Control Chat",
        "systemSent": None,
        "abortedLastRun": None,
        "thinkingLevel": None,
        "verboseLevel": None,
        "traceLevel": "verbose",
        "inputTokens": None,
        "outputTokens": None,
        "totalTokens": None,
        "totalTokensFresh": False,
        "contextTokens": None,
        "modelProvider": "openai",
        "model": "gpt-5.4",
        "space": None,
    }
    assert isinstance(sessions_changed[0]["createdAt"], str)
    assert isinstance(sessions_changed[0]["payload"]["ts"], int)
    assert isinstance(sessions_changed[0]["payload"]["updatedAt"], int)


def test_gateway_node_method_call_endpoint_sessions_steer_stop_message_aborts_without_follow_up(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-stop-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    interrupt_results: list[dict[str, object]] = [
        {"ok": True, "instanceId": 7, "threadId": "thread-steer-stop-1"},
        {"ok": False, "reason": "no_active_turn"},
    ]

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)

        async def fake_interrupt_turn(instance_id: int, thread_id: str) -> dict[str, object]:
            del instance_id, thread_id
            if interrupt_results:
                return interrupt_results.pop(0)
            return {"ok": False, "reason": "no_active_turn"}

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
                name="Gateway Steer Stop Loop",
                objective="Interrupt the live control chat thread without persisting stop text.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-steer-stop-1",
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
                    "message": " /STOP!!! ",
                    "idempotencyKey": "run-session-steer-stop-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": False,
        "runIds": [],
        "interruptedActiveRun": True,
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert messages[-2]["content"] == "status"
    assert all("/STOP" not in str(message["content"]) for message in messages)


def test_gateway_node_method_call_endpoint_sessions_steer_stop_message_reports_idle_abort(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-stop-idle-api"
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
                "method": "sessions.steer",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "stop please",
                    "idempotencyKey": "run-session-steer-stop-idle-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "aborted": False,
        "runIds": [],
    }
    assert messages == []


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_ignores_inert_sessions_steer_attachments(
    tmp_path,
    monkeypatch,
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-inert-attachments-api"
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
                    "idempotencyKey": "run-session-send-steer-inert-api-1",
                },
            },
        )
        assert send_response.status_code == 200
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Steer Inert Attachments Loop",
                objective=(
                    "Interrupt then continue the live control chat thread with inert "
                    "attachments."
                ),
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-steer-inert-1",
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
                    "attachments": attachments,
                    "idempotencyKey": "run-session-steer-inert-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-steer-inert-api-1",
        "status": "ok",
        "interruptedActiveRun": True,
    }
    assert [message["role"] for message in messages[-4:]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[-2]["content"] == "redirect"


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                    "content": "Zm9v",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "Zm9v",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_steers_effective_sessions_attachments_(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-steer-effective-attachments-api"
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
                "method": "sessions.steer",
                "params": {
                    "key": "openzues:thread:demo",
                    "message": "redirect",
                    "attachments": attachments,
                    "idempotencyKey": "run-session-steer-effective-attachments-api-1",
                },
            },
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert response.status_code == 200
    assert response.json() == {
        "runId": "run-session-steer-effective-attachments-api-1",
        "status": "ok",
    }
    assert [message["role"] for message in messages[-2:]] == ["user", "assistant"]
    assert "redirect" in messages[-2]["content"]
    assert "Gateway attachments:" in messages[-2]["content"]
    assert "image/png" in messages[-2]["content"]
    _assert_gateway_attachment_was_persisted(
        app_settings=app_settings,
        prompt=messages[-2]["content"],
    )


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
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "totalTokensFresh": False,
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
        "__openclaw": {"id": "1", "seq": 1},
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


def test_gateway_node_method_call_endpoint_supports_chat_inject_for_subscribed_session(
    tmp_path,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-inject-api"
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
    session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        ),
        thread_id="thread-chat-inject-api",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_mission(
                name="Gateway Chat Inject API Loop",
                objective="Inspect transcript injection API parity.",
                status="active",
                instance_id=7,
                project_id=None,
                thread_id="thread-chat-inject-api",
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

        with client.websocket_connect("/ws?clientId=client-chat-inject") as websocket:
            subscribe_response = client.post(
                "/api/gateway/node-methods/call",
                headers={"X-OpenZues-Client-Id": "client-chat-inject"},
                json={
                    "method": "sessions.messages.subscribe",
                    "params": {"key": session_key},
                },
            )
            response = client.post(
                "/api/gateway/node-methods/call",
                json={
                    "method": "chat.inject",
                    "params": {
                        "sessionKey": session_key,
                        "message": "Injected parity note",
                        "label": "Parity Note",
                    },
                },
            )
            event = websocket.receive_json()

    assert subscribe_response.status_code == 200
    assert subscribe_response.json() == {"subscribed": True, "key": session_key}
    assert response.status_code == 200
    assert response.json() == {"ok": True, "messageId": "1"}
    assert event["type"] == "gateway_event"
    assert event["event"] == "session.message"
    assert event["payload"]["sessionKey"] == session_key
    assert event["payload"]["messageId"] == "1"
    assert event["payload"]["message"]["role"] == "assistant"
    assert event["payload"]["message"]["content"] == [
        {"type": "text", "text": "Injected parity note"}
    ]

    database = Database(app_settings.db_path)
    asyncio.run(database.initialize())
    rows = asyncio.run(database.list_control_chat_messages(limit=10, session_key=session_key))
    assert len(rows) == 1
    assert rows[0]["role"] == "assistant"
    assert rows[0]["content"] == "Injected parity note"
    assert rows[0]["target_label"] == "Parity Note"

    sessions_changed = [
        recorded
        for recorded in hub.published_events
        if recorded.get("type") == "gateway_event" and recorded.get("event") == "sessions.changed"
    ]
    assert len(sessions_changed) == 1
    assert sessions_changed[0]["payload"]["sessionKey"] == session_key
    assert sessions_changed[0]["payload"]["phase"] == "message"


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
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"traceLevel": "debug"},
            )
        )
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
        "traceLevel": "debug",
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
    assert second_payload["traceLevel"] == "debug"
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
    assert {session["key"] for session in list_response.json()["sessions"]} == {
        main_session_key,
        session_key,
        other_session_key,
    }

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
    assert {session["key"] for session in list_response.json()["sessions"]} == {
        main_session_key,
        other_session_key,
    }

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


def test_gateway_node_method_call_endpoint_supports_sessions_compact_and_checkpoint_inventory() -> (
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
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        kept_id = asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                    "maxLines": 2,
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.list",
                "params": {"key": "openzues:thread:demo"},
            },
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.get",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        remaining_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )

    assert compact_response.status_code == 200
    compact_payload = compact_response.json()
    assert compact_payload["ok"] is True
    assert compact_payload["key"] == "openzues:thread:demo"
    assert compact_payload["compacted"] is True
    assert compact_payload["kept"] == 2
    assert compact_payload["archivedCount"] == 2

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["ok"] is True
    assert list_payload["key"] == "openzues:thread:demo"
    assert list_payload["checkpoints"] == [
        {
            "checkpointId": checkpoint_id,
            "sessionKey": "openzues:thread:demo",
            "sessionId": "demo",
            "createdAt": list_payload["checkpoints"][0]["createdAt"],
            "reason": "manual",
            "summary": "Alpha line 1 Alpha line 2 Bravo line 1",
            "firstKeptEntryId": str(kept_id),
            "preCompaction": {
                "sessionId": "demo",
                "entryId": list_payload["checkpoints"][0]["preCompaction"]["entryId"],
            },
            "postCompaction": {
                "sessionId": "demo",
                "entryId": str(kept_id),
            },
        }
    ]

    assert get_response.status_code == 200
    assert get_response.json() == {
        "ok": True,
        "key": "openzues:thread:demo",
        "checkpoint": list_payload["checkpoints"][0],
    }
    assert [message["id"] for message in remaining_messages] == [kept_id]


def test_gateway_node_method_call_endpoint_supports_sessions_compact_summary_without_max_lines(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        third_id = asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Delta line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Echo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.list",
                "params": {"key": "openzues:thread:demo"},
            },
        )
        remaining_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )

    assert compact_response.status_code == 200
    compact_payload = compact_response.json()
    assert compact_payload["ok"] is True
    assert compact_payload["key"] == "openzues:thread:demo"
    assert compact_payload["compacted"] is True
    assert compact_payload["archivedCount"] == 3

    assert [message["role"] for message in remaining_messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert remaining_messages[0]["action_kind"] == "compaction_summary"
    assert remaining_messages[0]["content"] == (
        "Compaction summary of earlier turns:\n"
        "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2"
    )
    assert [message["content"] for message in remaining_messages[1:]] == [
        "Delta line 1",
        "Echo line 1",
    ]

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["ok"] is True
    assert list_payload["key"] == "openzues:thread:demo"
    assert list_payload["checkpoints"] == [
        {
            "checkpointId": checkpoint_id,
            "sessionKey": "openzues:thread:demo",
            "sessionId": "demo",
            "createdAt": list_payload["checkpoints"][0]["createdAt"],
            "reason": "summary",
            "summary": "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2",
            "firstKeptEntryId": str(remaining_messages[0]["id"]),
            "preCompaction": {
                "sessionId": "demo",
                "entryId": str(third_id),
            },
            "postCompaction": {
                "sessionId": "demo",
                "entryId": str(remaining_messages[0]["id"]),
            },
        }
    ]


def test_gateway_node_method_call_endpoint_supports_summary_compaction_restore() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-restore-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Delta line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Echo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Foxtrot line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        restore_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.restore",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        restored_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )

    assert compact_response.status_code == 200
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    assert restore_payload["ok"] is True
    assert restore_payload["key"] == "openzues:thread:demo"
    assert restore_payload["checkpoint"]["checkpointId"] == checkpoint_id
    assert [message["content"] for message in restored_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]


def test_gateway_node_method_call_endpoint_supports_summary_compaction_branch() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-branch-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Delta line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Echo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        branch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.branch",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        branch_key = branch_response.json()["key"]
        source_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )
        branch_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key=branch_key,
            )
        )

    assert compact_response.status_code == 200
    assert branch_response.status_code == 200
    branch_payload = branch_response.json()
    assert branch_payload["ok"] is True
    assert branch_payload["sourceKey"] == "openzues:thread:demo"
    assert branch_payload["checkpoint"]["checkpointId"] == checkpoint_id
    assert [message["content"] for message in source_messages] == [
        "Compaction summary of earlier turns:\n"
        "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]
    assert [message["content"] for message in branch_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]


def test_gateway_node_method_call_endpoint_supports_sessions_compaction_restore() -> None:
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
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key="openzues:thread:demo",
                metadata={"traceLevel": "verbose"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                    "maxLines": 2,
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Delta line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        restore_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.restore",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        checkpoint_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.get",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        restored_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )

    assert compact_response.status_code == 200
    assert restore_response.status_code == 200
    restore_payload = restore_response.json()
    assert restore_payload["ok"] is True
    assert restore_payload["key"] == "openzues:thread:demo"
    assert restore_payload["sessionId"] == restore_payload["entry"]["sessionId"]
    assert restore_payload["checkpoint"] == checkpoint_response.json()["checkpoint"]
    assert restore_payload["entry"]["key"] == "openzues:thread:demo"
    assert restore_payload["entry"]["kind"] == "thread"
    assert restore_payload["entry"]["traceLevel"] == "verbose"
    assert isinstance(restore_payload["entry"]["updatedAt"], int)
    assert [message["content"] for message in restored_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
    ]


def test_sessions_compaction_list_api_returns_empty_inventory_for_unknown_key(
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

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "key": "openzues:thread:demo",
        "checkpoints": [],
    }


def test_gateway_node_method_call_endpoint_sessions_compaction_get_rejects_unknown_checkpoint(
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

    assert response.status_code == 400
    assert response.json()["detail"] == "checkpoint not found: checkpoint-001"


def test_gateway_node_method_call_endpoint_supports_sessions_compaction_branch() -> None:
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
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key="openzues:thread:demo",
                metadata={"label": "Parity Session", "model": "gpt-5.4-mini"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {
                    "key": "openzues:thread:demo",
                    "maxLines": 2,
                },
            },
        )
        checkpoint_id = compact_response.json()["checkpointId"]
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Delta line 1",
                mission_id=None,
                session_key="openzues:thread:demo",
            )
        )
        branch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.branch",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        branch_key = branch_response.json()["key"]
        checkpoint_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compaction.get",
                "params": {
                    "key": "openzues:thread:demo",
                    "checkpointId": checkpoint_id,
                },
            },
        )
        source_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key="openzues:thread:demo",
            )
        )
        branch_messages = asyncio.run(
            client.app.state.database.list_control_chat_messages(
                limit=10,
                session_key=branch_key,
            )
        )

    assert compact_response.status_code == 200
    assert branch_response.status_code == 200
    branch_payload = branch_response.json()
    assert branch_payload["ok"] is True
    assert branch_payload["sourceKey"] == "openzues:thread:demo"
    assert branch_payload["key"] != "openzues:thread:demo"
    assert branch_payload["sessionId"] == branch_payload["entry"]["sessionId"]
    assert branch_payload["checkpoint"] == checkpoint_response.json()["checkpoint"]
    assert branch_payload["entry"]["key"] == branch_payload["key"]
    assert branch_payload["entry"]["kind"] == "thread"
    assert branch_payload["entry"]["label"] == "Parity Session (checkpoint)"
    assert branch_payload["entry"]["parentSessionKey"] == "openzues:thread:demo"
    assert branch_payload["entry"]["model"] == "gpt-5.4-mini"
    assert isinstance(branch_payload["entry"]["updatedAt"], int)
    assert [message["content"] for message in source_messages] == [
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
    ]
    assert [message["content"] for message in branch_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
    ]


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


def test_gateway_node_method_call_endpoint_reports_missing_push_registration(tmp_path) -> None:
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
                "method": "push.test",
                "params": {
                    "nodeId": "ios-node-1",
                    "title": "OpenZues",
                    "body": "Push parity ping.",
                    "environment": "production",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "node ios-node-1 has no APNs registration (connect iOS node first)"
    )


def test_gateway_node_method_call_endpoint_sends_apns_relay_push(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
        apns_relay_base_url="https://relay.example.test",
        apns_relay_timeout_ms=1500,
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-ios-relay-push-1",
        node_id="ios-node-1",
        client_id="live-ios-relay-push-1",
        display_name="iOS Relay Node",
        platform="ios",
    )
    observed: dict[str, object] = {}

    class _FakeRelayResponse:
        status_code = 202
        is_success = True

        def json(self) -> dict[str, object]:
            return {
                "ok": True,
                "status": 200,
                "apnsId": "apns-relay-1",
                "tokenSuffix": "relay123",
            }

    class _FakeRelayClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            observed["timeout"] = timeout
            observed["follow_redirects"] = follow_redirects

        async def __aenter__(self) -> _FakeRelayClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            content: str,
            headers: dict[str, str],
        ) -> _FakeRelayResponse:
            observed["url"] = url
            observed["content"] = content
            observed["headers"] = headers
            return _FakeRelayResponse()

    monkeypatch.setattr("openzues.services.gateway_apns.httpx.AsyncClient", _FakeRelayClient)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        register_response = client.post(
            "/api/gateway/nodes/ios-node-1/method-call",
            json={
                "method": "node.event",
                "params": {
                    "event": "push.apns.register",
                    "payload": {
                        "transport": "relay",
                        "relayHandle": "relay-handle-123",
                        "sendGrant": "relay-send-grant-123",
                        "installationId": "install-123",
                        "topic": "com.openzues.ios",
                        "environment": "production",
                        "distribution": "official",
                        "tokenDebugSuffix": "debug123",
                    },
                },
            },
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "push.test",
                "params": {
                    "nodeId": "ios-node-1",
                    "title": "OpenZues",
                    "body": "Push parity ping.",
                    "environment": "production",
                },
            },
        )

    assert register_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "status": 200,
        "apnsId": "apns-relay-1",
        "reason": None,
        "tokenSuffix": "relay123",
        "topic": "com.openzues.ios",
        "environment": "production",
        "transport": "relay",
    }
    assert observed["timeout"] == 1.5
    assert observed["follow_redirects"] is False
    assert observed["url"] == "https://relay.example.test/v1/push/send"
    body_json = str(observed["content"])
    body = json.loads(body_json)
    assert body == {
        "relayHandle": "relay-handle-123",
        "pushType": "alert",
        "priority": 10,
        "payload": {
            "aps": {
                "alert": {
                    "title": "OpenZues",
                    "body": "Push parity ping.",
                },
                "sound": "default",
            },
            "openclaw": {
                "kind": "push.test",
                "nodeId": "ios-node-1",
                "ts": body["payload"]["openclaw"]["ts"],
            },
        },
    }
    assert isinstance(body["payload"]["openclaw"]["ts"], int)
    headers = observed["headers"]
    assert isinstance(headers, dict)
    assert headers["authorization"] == "Bearer relay-send-grant-123"
    assert headers["content-type"] == "application/json"
    signed_at_ms = int(headers["x-openclaw-gateway-signed-at-ms"])
    signature_payload = "\n".join(
        [
            "openclaw-relay-send-v1",
            headers["x-openclaw-gateway-device-id"],
            str(signed_at_ms),
            body_json,
        ]
    )
    signature = base64.urlsafe_b64decode(
        headers["x-openclaw-gateway-signature"] + "==="
    )
    public_key = base64.urlsafe_b64decode(
        app.state.gateway_identity_service.load().public_key + "==="
    )
    Ed25519PublicKey.from_public_bytes(public_key).verify(
        signature,
        signature_payload.encode("utf-8"),
    )


def test_gateway_node_method_call_endpoint_sends_direct_apns_push(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setenv("OPENCLAW_APNS_TEAM_ID", "TEAM123456")
    monkeypatch.setenv("OPENCLAW_APNS_KEY_ID", "KEY1234567")
    monkeypatch.setenv("OPENCLAW_APNS_PRIVATE_KEY_P8", private_key_pem)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
        apns_timeout_ms=1500,
    )
    app = create_app(app_settings)
    registry = app.state.gateway_node_service.registry
    _register_known_live_node(
        registry,
        conn_id="conn-ios-direct-push-1",
        node_id="ios-node-1",
        client_id="live-ios-direct-push-1",
        display_name="iOS Direct Node",
        platform="ios",
    )
    observed: dict[str, object] = {}

    class _FakeApnsResponse:
        status_code = 200
        is_success = True
        headers = {"apns-id": "apns-direct-1"}
        text = ""

        def json(self) -> dict[str, object]:
            return {}

    class _FakeApnsClient:
        def __init__(
            self,
            *,
            timeout: float,
            follow_redirects: bool,
            http2: bool = False,
        ) -> None:
            observed["timeout"] = timeout
            observed["follow_redirects"] = follow_redirects
            observed["http2"] = http2

        async def __aenter__(self) -> _FakeApnsClient:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            content: str,
            headers: dict[str, str],
        ) -> _FakeApnsResponse:
            observed["url"] = url
            observed["content"] = content
            observed["headers"] = headers
            return _FakeApnsResponse()

    monkeypatch.setattr("openzues.services.gateway_apns.httpx.AsyncClient", _FakeApnsClient)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        register_response = client.post(
            "/api/gateway/nodes/ios-node-1/method-call",
            json={
                "method": "node.event",
                "params": {
                    "event": "push.apns.register",
                    "payload": {
                        "transport": "direct",
                        "token": "c" * 64,
                        "topic": "com.openzues.ios",
                        "environment": "sandbox",
                    },
                },
            },
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "push.test",
                "params": {
                    "nodeId": "ios-node-1",
                    "title": "OpenZues",
                    "body": "Direct push parity ping.",
                    "environment": "production",
                },
            },
        )

    assert register_response.status_code == 200
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "status": 200,
        "apnsId": "apns-direct-1",
        "reason": None,
        "tokenSuffix": "cccccccc",
        "topic": "com.openzues.ios",
        "environment": "production",
        "transport": "direct",
    }
    assert observed["timeout"] == 1.5
    assert observed["follow_redirects"] is False
    assert observed["http2"] is True
    assert observed["url"] == f"https://api.push.apple.com/3/device/{'c' * 64}"
    headers = observed["headers"]
    assert isinstance(headers, dict)
    assert headers["apns-topic"] == "com.openzues.ios"
    assert headers["apns-push-type"] == "alert"
    assert headers["apns-priority"] == "10"
    assert headers["apns-expiration"] == "0"
    assert headers["content-type"] == "application/json"
    assert headers["authorization"].startswith("bearer ")
    jwt_header, jwt_payload, jwt_signature = headers["authorization"][7:].split(".")
    decoded_header = json.loads(base64.urlsafe_b64decode(jwt_header + "==="))
    decoded_payload = json.loads(base64.urlsafe_b64decode(jwt_payload + "==="))
    assert decoded_header == {"alg": "ES256", "kid": "KEY1234567", "typ": "JWT"}
    assert decoded_payload["iss"] == "TEAM123456"
    assert isinstance(decoded_payload["iat"], int)
    assert len(base64.urlsafe_b64decode(jwt_signature + "===")) == 64
    body = json.loads(str(observed["content"]))
    assert body == {
        "aps": {
            "alert": {
                "title": "OpenZues",
                "body": "Direct push parity ping.",
            },
            "sound": "default",
        },
        "openclaw": {
            "kind": "push.test",
            "nodeId": "ios-node-1",
            "ts": body["openclaw"]["ts"],
        },
    }
    assert isinstance(body["openclaw"]["ts"], int)


def test_gateway_node_method_call_endpoint_rejects_connect_as_non_callable_method(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "connect", "params": {}},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "connect is only valid as the first request"


@pytest.mark.parametrize(
    ("method", "params"),
    [
        (
            "web.login.start",
            {
                "force": True,
                "timeoutMs": 30_000,
                "verbose": True,
                "accountId": "telegram-primary",
            },
        ),
        (
            "web.login.wait",
            {
                "timeoutMs": 30_000,
                "accountId": "telegram-primary",
            },
        ),
    ],
)
def test_gateway_node_method_call_endpoint_rejects_web_login_without_provider(
    tmp_path,
    method: str,
    params: dict[str, object],
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
            json={"method": method, "params": params},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "web login provider is not available"


@pytest.mark.parametrize(
    ("method", "params"),
    [
        (
            "web.login.start",
            {
                "force": True,
                "timeoutMs": 30_000,
                "verbose": True,
                "accountId": "   ",
            },
        ),
        (
            "web.login.wait",
            {
                "timeoutMs": 30_000,
                "accountId": "   ",
            },
        ),
    ],
)
def test_gateway_node_method_call_endpoint_allows_blank_web_login_account_id(
    tmp_path,
    method: str,
    params: dict[str, object],
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
            json={"method": method, "params": params},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "web login provider is not available"


def test_gateway_node_method_call_endpoint_allows_blank_logout_account_id(
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
                "method": "channels.logout",
                "params": {
                    "channel": "telegram",
                    "accountId": "   ",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "channel telegram does not support logout"


def test_gateway_node_method_call_endpoint_allows_blank_channels_start_account_id(
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
                "method": "channels.start",
                "params": {
                    "channel": "telegram",
                    "accountId": "   ",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "channel telegram does not support runtime start"


def test_gateway_node_method_call_endpoint_rejects_channels_logout_without_supported_channel(
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
                "method": "channels.logout",
                "params": {
                    "channel": "telegram",
                    "accountId": "primary",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "channel telegram does not support logout"


def test_gateway_node_method_call_endpoint_rejects_invalid_channels_logout_channel(
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
                "method": "channels.logout",
                "params": {
                    "channel": "not-a-real-channel",
                    "accountId": "primary",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid channels.logout channel"


def test_gateway_node_method_call_endpoint_rejects_blank_channels_logout_channel(
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
                "method": "channels.logout",
                "params": {
                    "channel": "   ",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("invalid channels.logout params:")


def test_gateway_node_method_call_endpoint_supports_logs_tail_cursor_follow_up(tmp_path) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    log_path = logs_root / "openzues-test.log"
    log_path.write_text("first line\nsecond line\n", encoding="utf-8")

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "logs.tail",
                "params": {
                    "limit": 1,
                    "maxBytes": 1_000,
                },
            },
        )
        assert first.status_code == 200
        first_payload = first.json()
        assert first_payload["file"] == str(log_path)
        assert first_payload["lines"] == ["second line"]

        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("third line\n")

        second = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "logs.tail",
                "params": {
                    "cursor": first_payload["cursor"],
                    "limit": 10,
                    "maxBytes": 1_000,
                },
            },
        )

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["file"] == str(log_path)
    assert second_payload["lines"] == ["third line"]
    assert second_payload["reset"] is False


def test_gateway_node_method_call_endpoint_supports_update_run(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    restart_calls: list[str] = []

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        runtime_updates = client.app.state.hermes_platform_service.runtime_updates
        assert runtime_updates is not None

        async def fake_restart() -> None:
            restart_calls.append("restart")

        async def fake_safe_boundary() -> bool:
            return False

        runtime_updates._restart_callback = fake_restart
        runtime_updates._is_safe_restart_boundary = fake_safe_boundary
        runtime_updates.repo_root = tmp_path
        runtime_updates.startup_revision = "rev-a"
        runtime_updates._revision_resolver = lambda _repo_root: "rev-b"
        runtime_updates._snapshot.enabled = True
        runtime_updates._snapshot.repo_root = str(tmp_path)
        runtime_updates._snapshot.startup_revision = "rev-a"
        runtime_updates._snapshot.current_revision = "rev-a"
        runtime_updates._snapshot.pending_revision = None
        runtime_updates._snapshot.pending_restart = False
        runtime_updates._snapshot.restart_in_progress = False
        runtime_updates._snapshot.safe_to_restart = False
        runtime_updates._snapshot.last_checked_at = None
        runtime_updates._snapshot.last_restart_at = None
        runtime_updates._snapshot.last_error = None
        runtime_updates._snapshot.auto_restart = True

        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "update.run", "params": {}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["headline"] == "A newer repo revision is waiting for a safe boundary"
    assert payload["pending_restart"] is True
    assert payload["pending_revision"] == "rev-b"
    assert payload["safe_to_restart"] is False
    assert payload["restart_in_progress"] is False
    assert payload["last_checked_at"]
    assert restart_calls == []


def test_gateway_node_method_call_endpoint_update_run_accepts_optional_restart_request_params(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    restart_calls: list[str] = []

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        runtime_updates = client.app.state.hermes_platform_service.runtime_updates
        assert runtime_updates is not None

        async def fake_restart() -> None:
            restart_calls.append("restart")

        async def fake_safe_boundary() -> bool:
            return False

        runtime_updates._restart_callback = fake_restart
        runtime_updates._is_safe_restart_boundary = fake_safe_boundary
        runtime_updates.repo_root = tmp_path
        runtime_updates.startup_revision = "rev-a"
        runtime_updates._revision_resolver = lambda _repo_root: "rev-b"
        runtime_updates._snapshot.enabled = True
        runtime_updates._snapshot.repo_root = str(tmp_path)
        runtime_updates._snapshot.startup_revision = "rev-a"
        runtime_updates._snapshot.current_revision = "rev-a"
        runtime_updates._snapshot.pending_revision = None
        runtime_updates._snapshot.pending_restart = False
        runtime_updates._snapshot.restart_in_progress = False
        runtime_updates._snapshot.safe_to_restart = False
        runtime_updates._snapshot.last_checked_at = None
        runtime_updates._snapshot.last_restart_at = None
        runtime_updates._snapshot.last_error = None
        runtime_updates._snapshot.auto_restart = True

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "update.run",
                "params": {
                    "sessionKey": "agent:main:thread:demo",
                    "deliveryContext": {
                        "channel": "slack",
                        "to": "user:U123",
                        "accountId": "default",
                        "threadId": 1771242986529939,
                    },
                    "note": "Restart after the bounded parity patch.",
                    "restartDelayMs": 0,
                    "timeoutMs": 5_000,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["headline"] == "A newer repo revision is waiting for a safe boundary"
    assert payload["pending_restart"] is True
    assert payload["pending_revision"] == "rev-b"
    assert payload["safe_to_restart"] is False
    assert payload["restart_in_progress"] is False
    assert payload["last_checked_at"]
    assert restart_calls == []


def test_gateway_node_method_call_endpoint_supports_wizard_start_next_completion(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.start",
                "params": {
                    "mode": "remote",
                    "workspace": str(tmp_path),
                },
            },
        )
        assert start.status_code == 200
        start_payload = start.json()
        session_id = start_payload["sessionId"]
        operator_step = start_payload["step"]

        status = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "wizard.status", "params": {"sessionId": session_id}},
        )
        email_step_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": operator_step["id"],
                        "value": "Remote Builder",
                    },
                },
            },
        )
        assert email_step_response.status_code == 200
        email_step_payload = email_step_response.json()
        email_step = email_step_payload["step"]

        team_step_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": email_step["id"],
                        "value": "remote.builder@example.com",
                    },
                },
            },
        )
        assert team_step_response.status_code == 200
        team_step_payload = team_step_response.json()
        team_step = team_step_payload["step"]

        note_step_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": team_step["id"],
                        "value": "Platform Ops",
                    },
                },
            },
        )
        assert note_step_response.status_code == 200
        note_step_payload = note_step_response.json()
        note_step = note_step_payload["step"]

        task_step_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": note_step["id"],
                        "value": True,
                    },
                },
            },
        )
        assert task_step_response.status_code == 200
        task_step_payload = task_step_response.json()
        task_step = task_step_payload["step"]

        next_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": task_step["id"],
                        "value": "Parity Workspace Loop",
                    },
                },
            },
        )
        saved = client.get("/api/setup/wizard")

    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert operator_step == {
        "id": operator_step["id"],
        "field": "operator_name",
        "type": "text",
        "title": "Operator Name",
        "message": "Name the operator who should receive the remote ingress API key.",
        "placeholder": "Remote Builder",
        "executor": "client",
    }
    assert status.status_code == 200
    assert status.json() == {"status": "running"}
    assert email_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": email_step["id"],
            "field": "operator_email",
            "type": "text",
            "title": "Operator Email",
            "message": "Optionally add an email for the remote API key handoff.",
            "placeholder": "builder@example.com",
            "required": False,
            "inputType": "email",
            "executor": "client",
        },
    }
    assert team_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": team_step["id"],
            "field": "team_name",
            "type": "text",
            "title": "Operator Team",
            "message": "Optionally group the remote operator under a team label.",
            "placeholder": "Platform Ops",
            "required": False,
            "executor": "client",
        },
    }
    assert note_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": note_step["id"],
            "field": "remote_lane_note",
            "type": "note",
            "title": "Lane Binding Can Wait",
            "message": (
                "No saved lane is staged yet. Remote setup can still save the workspace, "
                "operator access, and recurring task now, then bind a lane when the first "
                "launch is ready."
            ),
            "executor": "client",
        },
    }
    assert task_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert next_response.status_code == 200
    assert next_response.json() == {"done": True, "status": "done"}
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["mode"] == "remote"
    assert saved_payload["flow"] == "advanced"
    assert saved_payload["operator_name"] == "Remote Builder"
    assert saved_payload["operator_email"] == "remote.builder@example.com"
    assert saved_payload["team_name"] == "Platform Ops"
    assert saved_payload["project_path"] == str(tmp_path)
    assert saved_payload["task_name"] == "Parity Workspace Loop"


def test_onboarding_wizard_http_endpoint_supports_remote_completion(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={
                "mode": "remote",
                "flow": "quickstart",
                "project_path": str(tmp_path),
            },
        )
        assert start.status_code == 200
        start_payload = start.json()
        session_id = start_payload["sessionId"]
        operator_step = start_payload["step"]

        email_step_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": operator_step["id"],
                    "value": "Remote Builder",
                },
            },
        )
        assert email_step_response.status_code == 200
        email_step_payload = email_step_response.json()
        email_step = email_step_payload["step"]

        team_step_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": email_step["id"],
                    "value": "",
                },
            },
        )
        assert team_step_response.status_code == 200
        team_step_payload = team_step_response.json()
        team_step = team_step_payload["step"]

        note_step_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": team_step["id"],
                    "value": "",
                },
            },
        )
        assert note_step_response.status_code == 200
        note_step_payload = note_step_response.json()
        note_step = note_step_payload["step"]

        task_step_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": note_step["id"],
                    "value": True,
                },
            },
        )
        assert task_step_response.status_code == 200
        task_step_payload = task_step_response.json()
        task_step = task_step_payload["step"]

        done = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": task_step["id"],
                    "value": "Remote Guided Loop",
                },
            },
        )
        saved = client.get("/api/setup/wizard")

    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert operator_step == {
        "id": operator_step["id"],
        "field": "operator_name",
        "type": "text",
        "title": "Operator Name",
        "message": "Name the operator who should receive the remote ingress API key.",
        "placeholder": "Remote Builder",
        "executor": "client",
    }
    assert email_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": email_step["id"],
            "field": "operator_email",
            "type": "text",
            "title": "Operator Email",
            "message": "Optionally add an email for the remote API key handoff.",
            "placeholder": "builder@example.com",
            "required": False,
            "inputType": "email",
            "executor": "client",
        },
    }
    assert team_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": team_step["id"],
            "field": "team_name",
            "type": "text",
            "title": "Operator Team",
            "message": "Optionally group the remote operator under a team label.",
            "placeholder": "Platform Ops",
            "required": False,
            "executor": "client",
        },
    }
    assert note_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": note_step["id"],
            "field": "remote_lane_note",
            "type": "note",
            "title": "Lane Binding Can Wait",
            "message": (
                "No saved lane is staged yet. Remote setup can still save the workspace, "
                "operator access, and recurring task now, then bind a lane when the first "
                "launch is ready."
            ),
            "executor": "client",
        },
    }
    assert task_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert done.status_code == 200
    assert done.json() == {"done": True, "status": "done"}
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["mode"] == "remote"
    assert saved_payload["flow"] == "advanced"
    assert saved_payload["operator_name"] == "Remote Builder"
    assert saved_payload["operator_email"] is None
    assert saved_payload["team_name"] is None
    assert saved_payload["project_path"] == str(tmp_path)
    assert saved_payload["task_name"] == "Remote Guided Loop"


def test_onboarding_wizard_http_endpoint_allows_next_without_answer(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={},
        )
        assert start.status_code == 200
        start_payload = start.json()

        current = client.post(
            "/api/onboarding/wizard/next",
            json={"sessionId": start_payload["sessionId"]},
        )

    assert current.status_code == 200
    assert current.json() == {
        "done": False,
        "status": "running",
        "step": {
            "id": start_payload["step"]["id"],
            "field": "mode",
            "type": "select",
            "title": "Setup Mode",
            "message": "Choose how you want the gateway wizard to stage setup.",
            "options": [
                {
                    "value": "local",
                    "label": "Local",
                    "hint": "Use a local control plane and desktop lane.",
                },
                {
                    "value": "remote",
                    "label": "Remote",
                    "hint": "Stage the workspace spine first and bind a lane later.",
                },
            ],
            "initialValue": "local",
            "executor": "client",
        },
    }


def test_onboarding_dashboard_marks_guided_owned_bootstrap_fields(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="onboarding-guided-selection-note"' in html
    for field_name in (
        "project_path",
        "instance_mode",
        "instance_id",
        "instance_name",
        "operator_name",
        "operator_email",
        "team_name",
        "task_name",
    ):
        assert re.search(
            rf'<(?:input|select)[^>]*name="{field_name}"[^>]*data-guided-owned="true"',
            html,
        )


def test_onboarding_wizard_http_endpoint_prompts_for_mode_and_local_flow_from_blank_start(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={},
        )
        assert start.status_code == 200
        start_payload = start.json()
        session_id = start_payload["sessionId"]
        mode_step = start_payload["step"]

        flow_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": mode_step["id"],
                    "value": "local",
                },
            },
        )
        assert flow_response.status_code == 200
        flow_payload = flow_response.json()
        flow_step = flow_payload["step"]

        workspace_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": flow_step["id"],
                    "value": "advanced",
                },
            },
        )
        assert workspace_response.status_code == 200
        workspace_payload = workspace_response.json()
        workspace_step = workspace_payload["step"]

        operator_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": workspace_step["id"],
                    "value": str(tmp_path),
                },
            },
        )
        assert operator_response.status_code == 200
        operator_payload = operator_response.json()
        operator_step = operator_payload["step"]

        task_response = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": operator_step["id"],
                    "value": "Local Builder",
                },
            },
        )
        assert task_response.status_code == 200
        task_payload = task_response.json()
        task_step = task_payload["step"]

        done = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": task_step["id"],
                    "value": "Local Guided Loop",
                },
            },
        )
        saved = client.get("/api/setup/wizard")

    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert mode_step == {
        "id": mode_step["id"],
        "field": "mode",
        "type": "select",
        "title": "Setup Mode",
        "message": "Choose how you want the gateway wizard to stage setup.",
        "options": [
            {
                "value": "local",
                "label": "Local",
                "hint": "Use a local control plane and desktop lane.",
            },
            {
                "value": "remote",
                "label": "Remote",
                "hint": "Stage the workspace spine first and bind a lane later.",
            },
        ],
        "initialValue": "local",
        "executor": "client",
    }
    assert flow_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": flow_step["id"],
            "field": "flow",
            "type": "select",
            "title": "Setup Flow",
            "message": "Choose how deeply to stage the local bootstrap posture.",
            "options": [
                {
                    "value": "quickstart",
                    "label": "QuickStart",
                    "hint": "Reuse the current control plane and tune the rest later.",
                },
                {
                    "value": "advanced",
                    "label": "Advanced",
                    "hint": "Stage the full local control plane posture before bootstrap.",
                },
            ],
            "initialValue": "quickstart",
            "executor": "client",
        },
    }
    assert workspace_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": workspace_step["id"],
            "field": "project_path",
            "type": "text",
            "title": "Workspace",
            "message": "Enter the workspace path to stage for setup.",
            "placeholder": "C:/workspace",
            "executor": "client",
        },
    }
    assert operator_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": operator_step["id"],
            "field": "operator_name",
            "type": "text",
            "title": "Operator Name",
            "message": "Name the operator who should receive the local bootstrap access.",
            "placeholder": "Operator",
            "executor": "client",
        },
    }
    assert task_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert done.status_code == 200
    assert done.json() == {"done": True, "status": "done"}
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["mode"] == "local"
    assert saved_payload["flow"] == "advanced"
    assert saved_payload["project_path"] == str(tmp_path)
    assert saved_payload["operator_name"] == "Local Builder"
    assert saved_payload["task_name"] == "Local Guided Loop"


def test_picker_only_setup_wizard_save_does_not_preseed_guided_mode_step(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        saved = client.put(
            "/api/setup/wizard",
            json={
                "mode": "remote",
                "flow": "advanced",
            },
        )
        start = client.post(
            "/api/onboarding/wizard/start",
            json={},
        )
        current = client.get("/api/setup/wizard")

    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["updated_at"] is None
    assert saved_payload["mode"] == "local"
    assert saved_payload["flow"] == "quickstart"

    assert start.status_code == 200
    start_payload = start.json()
    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert start_payload["step"] == {
        "id": start_payload["step"]["id"],
        "field": "mode",
        "type": "select",
        "title": "Setup Mode",
        "message": "Choose how you want the gateway wizard to stage setup.",
        "options": [
            {
                "value": "local",
                "label": "Local",
                "hint": "Use a local control plane and desktop lane.",
            },
            {
                "value": "remote",
                "label": "Remote",
                "hint": "Stage the workspace spine first and bind a lane later.",
            },
        ],
        "initialValue": "local",
        "executor": "client",
    }

    assert current.status_code == 200
    current_payload = current.json()
    assert current_payload["updated_at"] is None
    assert current_payload["mode"] == "local"
    assert current_payload["flow"] == "quickstart"


def test_gateway_node_method_call_endpoint_supports_local_wizard_completion_from_saved_draft(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        saved_draft = client.put(
            "/api/setup/wizard",
            json={
                "mode": "local",
                "flow": "quickstart",
                "project_path": str(tmp_path),
            },
        )
        assert saved_draft.status_code == 200

        start = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.start",
                "params": {
                    "mode": "local",
                    "workspace": str(tmp_path),
                },
            },
        )
        assert start.status_code == 200
        start_payload = start.json()
        session_id = start_payload["sessionId"]
        operator_step = start_payload["step"]

        task_step_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": operator_step["id"],
                        "value": "Local Builder",
                    },
                },
            },
        )
        assert task_step_response.status_code == 200
        task_step_payload = task_step_response.json()
        task_step = task_step_payload["step"]

        done = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wizard.next",
                "params": {
                    "sessionId": session_id,
                    "answer": {
                        "stepId": task_step["id"],
                        "value": "Local Guided Loop",
                    },
                },
            },
        )
        saved = client.get("/api/setup/wizard")

    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert operator_step == {
        "id": operator_step["id"],
        "field": "operator_name",
        "type": "text",
        "title": "Operator Name",
        "message": "Name the operator who should receive the local bootstrap access.",
        "placeholder": "Operator",
        "executor": "client",
    }
    assert task_step_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": task_step["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert done.status_code == 200
    assert done.json() == {"done": True, "status": "done"}
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["mode"] == "local"
    assert saved_payload["flow"] == "quickstart"
    assert saved_payload["project_path"] == str(tmp_path)
    assert saved_payload["operator_name"] == "Local Builder"
    assert saved_payload["task_name"] == "Local Guided Loop"


def test_onboarding_wizard_start_clears_explicit_blank_optional_remote_identity_fields(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        seeded = client.put(
            "/api/setup/wizard",
            json={
                "mode": "remote",
                "flow": "advanced",
                "project_path": str(tmp_path),
                "operator_name": "Remote Builder",
                "operator_email": "stale@example.com",
                "team_name": "Old Team",
            },
        )
        assert seeded.status_code == 200

        start = client.post(
            "/api/onboarding/wizard/start",
            json={
                "mode": "remote",
                "flow": "advanced",
                "project_path": str(tmp_path),
                "operator_name": "Remote Builder",
                "operator_email": None,
                "team_name": None,
            },
        )
        saved = client.get("/api/setup/wizard")

    assert start.status_code == 200
    start_payload = start.json()
    assert start_payload["done"] is False
    assert start_payload["status"] == "running"
    assert start_payload["step"] == {
        "id": start_payload["step"]["id"],
        "field": "operator_email",
        "type": "text",
        "title": "Operator Email",
        "message": "Optionally add an email for the remote API key handoff.",
        "placeholder": "builder@example.com",
        "required": False,
        "inputType": "email",
        "executor": "client",
    }
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["operator_name"] == "Remote Builder"
    assert saved_payload["operator_email"] is None
    assert saved_payload["team_name"] is None


def test_onboarding_wizard_http_endpoint_cancel_without_persisting_draft(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={},
        )
        assert start.status_code == 200
        session_id = start.json()["sessionId"]

        cancel = client.post(
            "/api/onboarding/wizard/cancel",
            json={"sessionId": session_id},
        )
        saved = client.get("/api/setup/wizard")

    assert cancel.status_code == 200
    assert cancel.json() == {"status": "cancelled", "error": "cancelled"}
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["updated_at"] is None
    assert saved_payload["project_path"] is None
    assert saved_payload["task_name"] is None


def test_onboarding_wizard_http_endpoint_status_reports_running_and_stale_session(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={},
        )
        assert start.status_code == 200
        session_id = start.json()["sessionId"]

        status = client.get(f"/api/onboarding/wizard/status?sessionId={session_id}")
        assert status.status_code == 200

        cancel = client.post(
            "/api/onboarding/wizard/cancel",
            json={"sessionId": session_id},
        )
        stale = client.get(f"/api/onboarding/wizard/status?sessionId={session_id}")

    assert status.json() == {"status": "running"}
    assert cancel.status_code == 200
    assert cancel.json() == {"status": "cancelled", "error": "cancelled"}
    assert stale.status_code == 400
    assert stale.json() == {"detail": "wizard not found"}


def test_onboarding_wizard_http_endpoint_persists_answered_fields_before_cancel(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/onboarding/wizard/start",
            json={
                "mode": "local",
                "flow": "quickstart",
                "project_path": str(tmp_path),
            },
        )
        assert start.status_code == 200
        start_payload = start.json()
        session_id = start_payload["sessionId"]
        operator_step = start_payload["step"]

        next_step = client.post(
            "/api/onboarding/wizard/next",
            json={
                "sessionId": session_id,
                "answer": {
                    "stepId": operator_step["id"],
                    "value": "Local Builder",
                },
            },
        )
        saved_before_cancel = client.get("/api/setup/wizard")
        cancel = client.post(
            "/api/onboarding/wizard/cancel",
            json={"sessionId": session_id},
        )
        saved_after_cancel = client.get("/api/setup/wizard")

    assert next_step.status_code == 200
    next_payload = next_step.json()
    assert next_payload == {
        "done": False,
        "status": "running",
        "step": {
            "id": next_payload["step"]["id"],
            "field": "task_name",
            "type": "text",
            "title": "Task Name",
            "message": "Name the recurring setup task.",
            "executor": "client",
        },
    }
    assert saved_before_cancel.status_code == 200
    before_payload = saved_before_cancel.json()
    assert before_payload["mode"] == "local"
    assert before_payload["flow"] == "quickstart"
    assert before_payload["project_path"] == str(tmp_path)
    assert before_payload["operator_name"] == "Local Builder"
    assert before_payload["task_name"] is None
    assert before_payload["updated_at"] is not None
    assert cancel.status_code == 200
    assert cancel.json() == {"status": "cancelled", "error": "cancelled"}
    assert saved_after_cancel.status_code == 200
    after_payload = saved_after_cancel.json()
    assert after_payload["project_path"] == str(tmp_path)
    assert after_payload["operator_name"] == "Local Builder"
    assert after_payload["task_name"] is None


def test_gateway_node_method_call_endpoint_supports_wizard_cancel_without_persisting_draft(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "wizard.start", "params": {}},
        )
        assert start.status_code == 200
        session_id = start.json()["sessionId"]

        cancel = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "wizard.cancel", "params": {"sessionId": session_id}},
        )
        status_after = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "wizard.status", "params": {"sessionId": session_id}},
        )
        saved = client.get("/api/setup/wizard")

    assert cancel.status_code == 200
    assert cancel.json() == {"status": "cancelled", "error": "cancelled"}
    assert status_after.status_code == 400
    assert status_after.json()["detail"] == "wizard not found"
    assert saved.status_code == 200
    saved_payload = saved.json()
    assert saved_payload["project_path"] is None
    assert saved_payload["task_name"] is None


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


def test_sessions_subscribe_api_delivers_compaction_checkpoint_metadata() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-changed-compaction-websocket-api"
    )
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
        thread_id="thread-subscribe-websocket-compact",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                session_key=session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                session_key=session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                session_key=session_key,
            )
        )

        with client.websocket_connect("/ws?clientId=client-session") as websocket:
            subscribe_response = client.post(
                "/api/gateway/node-methods/call",
                headers={"X-OpenZues-Client-Id": "client-session"},
                json={"method": "sessions.subscribe", "params": {}},
            )
            compact_response = client.post(
                "/api/gateway/node-methods/call",
                json={
                    "method": "sessions.compact",
                    "params": {"key": session_key, "maxLines": 2},
                },
            )
            event = websocket.receive_json()

    assert subscribe_response.status_code == 200
    assert subscribe_response.json() == {"subscribed": True}
    assert compact_response.status_code == 200
    compact_payload = compact_response.json()
    assert compact_payload["ok"] is True
    assert event["type"] == "gateway_event"
    assert event["event"] == "sessions.changed"
    assert event["payload"]["sessionKey"] == session_key
    assert event["payload"]["reason"] == "compact"
    assert event["payload"]["compacted"] is True
    assert event["payload"]["compactionCheckpointCount"] == 1
    assert event["payload"]["latestCompactionCheckpoint"] == {
        "checkpointId": compact_payload["checkpointId"],
        "sessionKey": session_key,
        "sessionId": "thread-subscribe-websocket-compact",
        "createdAt": event["payload"]["latestCompactionCheckpoint"]["createdAt"],
        "reason": "manual",
        "summary": "Alpha line 1 Alpha line 2 Bravo line 1",
        "firstKeptEntryId": event["payload"]["latestCompactionCheckpoint"]["firstKeptEntryId"],
        "preCompaction": {
            "sessionId": "thread-subscribe-websocket-compact",
            "entryId": event["payload"]["latestCompactionCheckpoint"]["preCompaction"]["entryId"],
        },
        "postCompaction": {
            "sessionId": "thread-subscribe-websocket-compact",
            "entryId": event["payload"]["latestCompactionCheckpoint"]["postCompaction"]["entryId"],
        },
    }


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
    assert payload["messageSeq"] == 1
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


def test_sessions_create_api_accepts_persisted_custom_agent_sessions() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-create-custom-agent-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.create_gateway_agent(
                agent_id="builder-prime",
                name="Builder Prime",
                workspace=str(tmp_path / "agents" / "builder-prime"),
                model="gpt-5.4-mini",
                emoji=None,
                avatar=None,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.create",
                "params": {
                    "agentId": "builder-prime",
                    "label": "Builder Prime Session",
                    "message": "Ship the custom-agent API slice.",
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {
                    "includeGlobal": True,
                    "includeUnknown": False,
                    "agentId": "builder-prime",
                    "limit": 10,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    created_key = payload["key"]
    assert created_key.startswith("agent:builder-prime:main:thread:gateway-create-")
    assert payload["ok"] is True
    assert payload["entry"]["key"] == created_key
    assert payload["entry"]["label"] == "Builder Prime Session"
    assert list_response.status_code == 200
    assert [session["key"] for session in list_response.json()["sessions"]] == [created_key]


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
                    "traceLevel": "debug",
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
    assert response.json()["entry"]["traceLevel"] == "debug"
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
            "traceLevel": "debug",
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "totalTokensFresh": False,
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
    assert history_response.json()["traceLevel"] == "debug"


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


def test_gateway_node_method_call_endpoint_usage_cost_returns_bounded_daily_summary() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-usage-cost-api"
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
        first_mission_id = asyncio.run(
            database.create_mission(
                name="Usage cost API first slice",
                objective="Count the first API daily usage total.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-cost-api-1",
                session_key="openzues:thread:usage-cost-api-1",
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
                name="Usage cost API second slice",
                objective="Count the second API daily usage total.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-cost-api-2",
                session_key="openzues:thread:usage-cost-api-2",
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
        out_of_range_mission_id = asyncio.run(
            database.create_mission(
                name="Usage cost API out-of-range slice",
                objective="Stay outside the API date window.",
                status="completed",
                instance_id=7,
                project_id=None,
                thread_id="thread-usage-cost-api-3",
                session_key="openzues:thread:usage-cost-api-3",
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
                out_of_range_mission_id,
                total_tokens=999,
                output_tokens=333,
            )
        )

        with sqlite3.connect(database.path) as conn:
            conn.execute(
                "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
                (
                    "2026-04-15T12:00:00+00:00",
                    "2026-04-15T12:00:00+00:00",
                    first_mission_id,
                ),
            )
            conn.execute(
                "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
                (
                    "2026-04-16T18:30:00+00:00",
                    "2026-04-16T18:30:00+00:00",
                    second_mission_id,
                ),
            )
            conn.execute(
                "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
                (
                    "2026-04-18T08:00:00+00:00",
                    "2026-04-18T08:00:00+00:00",
                    out_of_range_mission_id,
                ),
            )
            conn.commit()

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "usage.cost",
                "params": {
                    "startDate": "2026-04-15",
                    "endDate": "2026-04-16",
                    "mode": "utc",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["days"] == 2
    assert payload["daily"] == [
        {
            "date": "2026-04-15",
            "input": 220,
            "output": 80,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 300,
            "totalCost": 0.0,
            "inputCost": 0.0,
            "outputCost": 0.0,
            "cacheReadCost": 0.0,
            "cacheWriteCost": 0.0,
            "missingCostEntries": 1,
        },
        {
            "date": "2026-04-16",
            "input": 520,
            "output": 180,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 700,
            "totalCost": 0.0,
            "inputCost": 0.0,
            "outputCost": 0.0,
            "cacheReadCost": 0.0,
            "cacheWriteCost": 0.0,
            "missingCostEntries": 1,
        },
    ]
    assert payload["totals"] == {
        "input": 740,
        "output": 260,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 1000,
        "totalCost": 0.0,
        "inputCost": 0.0,
        "outputCost": 0.0,
        "cacheReadCost": 0.0,
        "cacheWriteCost": 0.0,
        "missingCostEntries": 2,
    }


def test_gateway_node_method_call_endpoint_usage_status_returns_provider_inventory() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-usage-status-api"
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
            json={"method": "usage.status", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "updatedAt": response.json()["updatedAt"],
        "providers": [
            {
                "provider": "openai",
                "displayName": "openai",
                "windows": [],
                "plan": None,
                "error": "Quota telemetry is not available in OpenZues yet.",
            }
        ],
    }


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


def test_gateway_node_method_call_endpoint_treats_empty_chat_abort_run_id_as_session_abort(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
                    "runId": "",
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


def test_gateway_node_method_call_endpoint_supports_cron_status_with_one_shot_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-status-at-api"
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
            database.create_task_blueprint(
                name="One Shot",
                summary="Run once at noon UTC.",
                project_id=None,
                instance_id=None,
                cadence_minutes=None,
                enabled=True,
                payload={
                    "objective_template": "Run once at noon UTC.",
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
                    "schedule_kind": "at",
                    "schedule_at": "2026-04-18T12:00:00.000Z",
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
        "jobs": 1,
        "nextWakeAtMs": int(datetime(2026, 4, 18, 12, 0, tzinfo=UTC).timestamp() * 1000),
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


def test_gateway_node_method_call_endpoint_surfaces_delivered_cron_webhook_status() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-runs-delivery-api"
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
        created_task = build_gateway_cron_task_blueprint(
            {
                "name": "Nightly Ship Webhook",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Ship the next verified webhook slice.",
                },
                "delivery": {
                    "mode": "webhook",
                    "to": "https://example.invalid/cron-finished",
                },
            }
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name=created_task.name,
                summary=created_task.summary,
                project_id=created_task.project_id,
                instance_id=created_task.instance_id,
                cadence_minutes=created_task.cadence_minutes,
                enabled=created_task.enabled,
                payload=created_task.model_dump(
                    exclude={
                        "name",
                        "summary",
                        "project_id",
                        "instance_id",
                        "cadence_minutes",
                        "enabled",
                    }
                ),
            )
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="Nightly Ship Webhook Run",
                objective="Ship the next verified webhook slice.",
                status="completed",
                instance_id=7,
                project_id=None,
                task_blueprint_id=task_id,
                thread_id="thread-ship-webhook-ok",
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
                mission_id,
                last_checkpoint="Nightly webhook ship landed.",
            )
        )
        asyncio.run(
            database.create_outbound_delivery(
                route_id=None,
                route_name="Cron webhook for Nightly Ship Webhook",
                route_kind="webhook",
                route_target="https://example.invalid/cron-finished",
                event_type="cron/finished",
                session_key="launch:mode:workspace_affinity",
                conversation_target=None,
                route_scope={
                    "route_name": "Cron webhook for Nightly Ship Webhook",
                    "route_kind": "webhook",
                    "route_target": "https://example.invalid/cron-finished",
                },
                event_payload={
                    "missionId": mission_id,
                    "taskId": task_id,
                    "jobId": f"task-blueprint:{task_id}",
                    "summary": "Nightly webhook ship landed.",
                },
                message_summary="Nightly webhook ship landed.",
                test_delivery=False,
                delivery_state="delivered",
                attempt_count=1,
                delivered_at=utcnow(),
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.runs",
                "params": {
                    "id": f"task-blueprint:{task_id}",
                    "limit": 10,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["entries"][0]["summary"] == "Nightly webhook ship landed."
    assert payload["entries"][0]["deliveryStatus"] == "delivered"


def test_app_ops_mesh_service_delivers_last_channel_cron_failure_to_session_messages() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-last-channel-session-delivery"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        task = asyncio.run(
            client.app.state.ops_mesh_service.create_task_blueprint(
                build_gateway_cron_task_blueprint(
                    {
                        "name": "Last Channel Failure Session Delivery",
                        "enabled": True,
                        "schedule": {"kind": "every", "everyMs": 3_600_000},
                        "sessionTarget": "isolated",
                        "wakeMode": "next-heartbeat",
                        "payload": {
                            "kind": "agentTurn",
                            "message": "Deliver cron failure through the live session key.",
                        },
                        "delivery": {
                            "mode": "announce",
                            "channel": "last",
                        },
                    }
                )
            )
        )
        database = client.app.state.database
        mission_id = asyncio.run(
            database.create_mission(
                name="Last Channel Failure Session Delivery",
                objective="Deliver cron failure through the live session key.",
                status="failed",
                instance_id=task.instance_id or 1,
                project_id=task.project_id,
                task_blueprint_id=task.id,
                thread_id="thread_cron_failure_last_channel_session_delivery",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
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
                toolsets=[],
            )
        )
        session_key = "agent:main:telegram:direct:123:thread:99"
        asyncio.run(
            database.update_mission(
                mission_id,
                last_checkpoint="last-channel session delivery failed",
                last_error="lane timed out",
                last_activity_at=datetime.now(UTC).isoformat(),
                session_key=session_key,
            )
        )

        asyncio.run(
            client.app.state.ops_mesh_service.handle_mission_event(
                "mission/failed",
                {"missionId": mission_id},
            )
        )
        messages = asyncio.run(
            database.list_control_chat_messages(limit=10, session_key=session_key)
        )
        deliveries = asyncio.run(
            client.app.state.ops_mesh_service.list_outbound_delivery_views(limit=10)
        )

    assert [message["content"] for message in messages if message["role"] == "assistant"] == [
        '\u26a0\ufe0f Cron job "Last Channel Failure Session Delivery" failed: lane timed out'
    ]
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "session"
    assert deliveries[0].route_target == session_key
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == session_key


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


def test_gateway_node_method_call_endpoint_supports_cron_remove_for_one_shot_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-remove-at-api"
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
                name="One Shot",
                summary="Run exactly once.",
                project_id=None,
                instance_id=None,
                cadence_minutes=None,
                enabled=True,
                payload={
                    "objective_template": "Run exactly once.",
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
                    "schedule_kind": "at",
                    "schedule_at": "2026-04-18T12:00:00.000Z",
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
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
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
    assert payload["sessionTarget"] == "isolated"
    assert payload["wakeMode"] == "next-heartbeat"
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


def test_gateway_node_method_call_endpoint_supports_cron_add_anchor_ms() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-anchor-api"
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
                    "name": "Anchored Ship",
                    "description": "Ship on the anchored minute boundary.",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000, "anchorMs": 123},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Ship on the anchored minute boundary.",
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
    assert payload["schedule"] == {"kind": "every", "everyMs": 3_600_000, "anchorMs": 123}
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {"kind": "every", "everyMs": 3_600_000, "anchorMs": 123}


def test_gateway_node_method_call_endpoint_supports_cron_add_at_schedule() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-at-api"
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
                    "name": "One Shot",
                    "description": "Run exactly once at noon UTC.",
                    "enabled": True,
                    "schedule": {"kind": "at", "at": "2026-04-18T12:00:00Z"},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run exactly once at noon UTC.",
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
    assert payload["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}


def test_gateway_node_method_call_endpoint_supports_cron_expression_schedule() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-cron-api"
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
                    "name": "Hourly Repair",
                    "enabled": True,
                    "schedule": {
                        "kind": "cron",
                        "expr": "0 * * * *",
                        "tz": "UTC",
                        "staggerMs": 30_000,
                    },
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Repair the hourly parity seam.",
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
    assert response.json()["schedule"] == {
        "kind": "cron",
        "expr": "0 * * * *",
        "tz": "UTC",
        "staggerMs": 30_000,
    }
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {
        "kind": "cron",
        "expr": "0 * * * *",
        "tz": "UTC",
        "staggerMs": 30_000,
    }


def test_gateway_node_method_call_endpoint_routes_main_system_event_cron_run_through_wake_queue(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Wake Main Lane",
                    "description": "Nudge the main lane on the next heartbeat.",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Resume the main lane from cron.",
                    },
                },
            },
        )
        assert add_response.status_code == 200
        job_id = str(add_response.json()["id"])

        run_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.run",
                "params": {"id": job_id, "mode": "force"},
            },
        )
        database = client.app.state.database
        wake_requests = asyncio.run(database.list_gateway_wake_requests())
        events = asyncio.run(database.list_events())
        missions = asyncio.run(database.list_missions())

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["ok"] is True
    assert payload["enqueued"] is True
    assert isinstance(payload["runId"], str)
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["text"] == "Resume the main lane from cron."
    assert wake_requests[0]["status"] == "pending"
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"]["text"] == "Resume the main lane from cron."
    assert missions == []


def test_main_system_event_cron_run_routes_session_key_through_wake_queue() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-run-session-key-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    stored_session_key = "agent:openzues:telegram:direct:123:thread:77"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Wake Main Lane Session Key",
                    "description": (
                        "Nudge the main lane on the next heartbeat with a target session."
                    ),
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "sessionKey": "telegram:direct:123:thread:77",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Resume the main lane from cron.",
                    },
                },
            },
        )
        assert add_response.status_code == 200
        job_id = str(add_response.json()["id"])

        run_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.run",
                "params": {"id": job_id, "mode": "force"},
            },
        )
        database = client.app.state.database
        wake_requests = asyncio.run(database.list_gateway_wake_requests())
        events = asyncio.run(database.list_events())

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["ok"] is True
    assert payload["enqueued"] is True
    assert isinstance(payload["runId"], str)
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["session_key"] == stored_session_key
    assert len(events) == 1
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"]["sessionKey"] == stored_session_key


def test_gateway_node_method_call_endpoint_surfaces_cron_runs_for_main_system_event_wake_jobs(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Wake Main Lane",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Resume the main lane from cron.",
                    },
                },
            },
        )
        assert add_response.status_code == 200
        job_id = str(add_response.json()["id"])

        run_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.run",
                "params": {"id": job_id, "mode": "force"},
            },
        )
        assert run_response.status_code == 200

        runs_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.runs",
                "params": {"id": job_id, "limit": 10},
            },
        )

    assert runs_response.status_code == 200
    payload = runs_response.json()
    assert payload["total"] == 1
    assert payload["entries"][-1]["jobId"] == job_id
    assert payload["entries"][-1]["action"] == "finished"
    assert payload["entries"][-1]["status"] == "ok"
    assert payload["entries"][-1]["summary"] == "Resume the main lane from cron."
    assert payload["entries"][-1]["deliveryStatus"] == "not-requested"


def test_gateway_node_method_call_endpoint_supports_cron_add_isolated_agent_turn_job(
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
                "method": "cron.add",
                "params": {
                    "name": "Isolated Lane",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run the isolated lane from cron.",
                        "model": "gpt-5.4-mini",
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
    assert payload["sessionTarget"] == "isolated"
    assert payload["wakeMode"] == "next-heartbeat"
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Run the isolated lane from cron.",
        "model": "gpt-5.4-mini",
    }
    assert payload["delivery"] == {"mode": "announce"}
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["sessionTarget"] == "isolated"
    assert list_response.json()["jobs"][0]["delivery"] == {"mode": "announce"}


def test_gateway_node_method_call_endpoint_preserves_isolated_agent_turn_none_delivery(
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
                "method": "cron.add",
                "params": {
                    "name": "Isolated Lane No Delivery",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run the isolated lane from cron without announce delivery.",
                    },
                    "delivery": {"mode": "none"},
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
    assert response.json()["delivery"] == {"mode": "none"}
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {"mode": "none"}


def test_gateway_node_method_call_endpoint_accepts_isolated_agent_turn_announce_delivery(
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
                "method": "cron.add",
                "params": {
                    "name": "Isolated Lane Announce",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": (
                            "Run the isolated lane from cron with explicit announce delivery."
                        ),
                    },
                    "delivery": {
                        "mode": "announce",
                        "channel": " TeLeGrAm ",
                        "to": " 7200373102 ",
                        "accountId": " coordinator ",
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
    assert response.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "accountId": "coordinator",
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "accountId": "coordinator",
    }
    with TestClient(app, client=("testclient", 50000)) as verify_client:
        stored_task = asyncio.run(verify_client.app.state.database.get_task_blueprint(1))
    assert stored_task is not None
    conversation_target = stored_task["conversation_target"]
    assert isinstance(conversation_target, dict)
    assert conversation_target["channel"] == "telegram"
    assert conversation_target["account_id"] == "coordinator"
    assert conversation_target["peer_kind"] == "channel"
    assert conversation_target["peer_id"] == "7200373102"


def test_gateway_node_method_call_endpoint_accepts_webhook_delivery_for_main_system_event(
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
                "method": "cron.add",
                "params": {
                    "name": "Webhook Wake",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Wake the main lane through webhook delivery.",
                    },
                    "delivery": {
                        "mode": " WeBhOoK ",
                        "to": " https://example.invalid/cron ",
                        "bestEffort": True,
                        "failureDestination": {
                            "mode": "webhook",
                            "to": "  https://example.invalid/failure  ",
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
    assert response.json()["delivery"] == {
        "mode": "webhook",
        "to": "https://example.invalid/cron",
        "bestEffort": True,
        "failureDestination": {
            "mode": "webhook",
            "to": "https://example.invalid/failure",
        },
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "webhook",
        "to": "https://example.invalid/cron",
        "bestEffort": True,
        "failureDestination": {
            "mode": "webhook",
            "to": "https://example.invalid/failure",
        },
    }


def test_gateway_node_method_call_endpoint_merges_cron_delivery_thread_id_patch(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        created = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Thread Hint Patch",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": (
                            "Patch the announce delivery thread hint without touching the "
                            "target."
                        ),
                    },
                    "delivery": {
                        "mode": "announce",
                        "channel": "telegram",
                        "to": "-100123:topic:42",
                    },
                },
            },
        )
        updated = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": created.json()["id"],
                    "patch": {
                        "delivery": {
                            "threadId": " 99 ",
                        }
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

    assert created.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "-100123:topic:42",
        "threadId": "99",
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "-100123:topic:42",
        "threadId": "99",
    }
    with TestClient(app, client=("testclient", 50000)) as verify_client:
        stored_task = asyncio.run(verify_client.app.state.database.get_task_blueprint(1))
    assert stored_task is not None
    assert stored_task["cron_delivery_thread_id"] == "99"


def test_gateway_node_method_call_endpoint_accepts_numeric_cron_delivery_thread_id(
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
                "method": "cron.add",
                "params": {
                    "name": "Numeric Thread Hint",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Round-trip a numeric announce delivery thread hint.",
                    },
                    "delivery": {
                        "mode": "announce",
                        "channel": "telegram",
                        "to": "-100123:topic:42",
                        "threadId": 77,
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
    assert response.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "-100123:topic:42",
        "threadId": 77,
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "-100123:topic:42",
        "threadId": 77,
    }
    with TestClient(app, client=("testclient", 50000)) as verify_client:
        stored_task = asyncio.run(verify_client.app.state.database.get_task_blueprint(1))
    assert stored_task is not None
    assert stored_task["cron_delivery_thread_id"] == 77


def test_gateway_node_method_call_endpoint_accepts_legacy_notify_flag(tmp_path) -> None:
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
                    "name": "Legacy Notify Webhook",
                    "enabled": True,
                    "notify": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Use the legacy cron webhook fallback.",
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
    assert response.json()["notify"] is True
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["notify"] is True
    with TestClient(app, client=("testclient", 50000)) as verify_client:
        stored_task = asyncio.run(verify_client.app.state.database.get_task_blueprint(1))
    assert stored_task is not None
    assert stored_task["cron_notify_enabled"] is True


def test_gateway_node_method_call_endpoint_ignores_announce_delivery_patch_for_main_system_event(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        created = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Main Lane Wake",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "main",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "systemEvent",
                        "text": "Resume the main lane from cron.",
                    },
                },
            },
        )
        update = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": created.json()["id"],
                    "patch": {
                        "delivery": {
                            "mode": "announce",
                            "channel": "telegram",
                            "to": "19098680",
                        }
                    },
                },
            },
        )

    assert created.status_code == 200
    assert update.status_code == 200
    assert update.json()["delivery"] == {"mode": "none"}


def test_gateway_node_method_call_endpoint_normalizes_deliver_delivery_mode_to_announce(
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
                "method": "cron.add",
                "params": {
                    "name": "Deliver Alias",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run the isolated lane from cron with the deliver alias.",
                    },
                    "delivery": {
                        "mode": " DeLiVeR ",
                        "channel": "Telegram",
                        "to": "7200373102",
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
    assert response.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
    }


def test_gateway_node_method_call_endpoint_rejects_target_like_delivery_channel_ids(
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
                "method": "cron.add",
                "params": {
                    "name": "Invalid Delivery Provider",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Reject target ids that get stuffed into delivery.channel.",
                    },
                    "delivery": {
                        "mode": "announce",
                        "channel": "C0AT2Q238MQ",
                        "to": "C0AT2Q238MQ",
                    },
                },
            },
        )

    assert response.status_code == 400
    assert "delivery.channel" in response.json()["detail"]


def test_gateway_node_method_call_endpoint_requires_delivery_channel_for_ambiguous_add(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.create_notification_route(
                name="Telegram Route",
                kind="webhook",
                target="https://example.invalid/telegram",
                events=["mission.completed"],
                conversation_target={"channel": "telegram", "account_id": "default"},
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission.completed"],
                conversation_target={"channel": "slack", "account_id": "default"},
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Ambiguous Announce Add",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Require a delivery channel when multiple routes are enabled.",
                    },
                    "delivery": {"mode": "announce"},
                },
            },
        )

    assert response.status_code == 400
    assert "delivery.channel is required" in response.json()["detail"]


def test_gateway_node_method_call_endpoint_requires_delivery_channel_for_ambiguous_update(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.create_notification_route(
                name="Telegram Route",
                kind="webhook",
                target="https://example.invalid/telegram",
                events=["mission.completed"],
                conversation_target={"channel": "telegram", "account_id": "default"},
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission.completed"],
                conversation_target={"channel": "slack", "account_id": "default"},
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="Nightly Ship",
                summary="Ship the next verified slice.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Run this on the isolated cron lane.",
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
                    "cron_session_target": "isolated",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "agentTurn",
                    "cron_delivery_mode": "none",
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": f"task-blueprint:{task_id}",
                    "patch": {"delivery": {"mode": "announce"}},
                },
            },
        )

    assert response.status_code == 400
    assert "patch.delivery.channel is required" in response.json()["detail"]


def test_gateway_node_method_call_endpoint_allows_announce_when_extra_routes_are_disabled(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.create_notification_route(
                name="Telegram Route",
                kind="webhook",
                target="https://example.invalid/telegram",
                events=["mission.completed"],
                conversation_target={"channel": "telegram", "account_id": "default"},
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Disabled Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission.completed"],
                conversation_target={"channel": "slack", "account_id": "default"},
                enabled=False,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Disabled Extra Route",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Allow announce delivery when only one enabled route remains.",
                    },
                    "delivery": {"mode": "announce"},
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["delivery"] == {"mode": "announce"}


def test_gateway_node_method_call_endpoint_supports_custom_cron_session_targets() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-custom-session-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Custom Session Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "session:project-alpha:ops",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run on the saved cron session.",
                    },
                },
            },
        )
        add_payload = add_response.json()
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": add_payload["id"],
                    "patch": {"sessionTarget": "session:project-beta:ops"},
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

    assert add_response.status_code == 200
    assert add_payload["sessionTarget"] == "session:project-alpha:ops"
    assert update_response.status_code == 200
    assert update_response.json()["sessionTarget"] == "session:project-beta:ops"
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["sessionTarget"] == "session:project-beta:ops"


def test_gateway_node_method_call_endpoint_rejects_unsafe_custom_cron_session_targets() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-custom-session-reject-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Unsafe Custom Session Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "session:../../outside",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run on the saved cron session.",
                    },
                },
            },
        )
        safe_add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Safe Custom Session Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "session:project-alpha:ops",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run on the saved cron session.",
                    },
                },
            },
        )
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": safe_add_response.json()["id"],
                    "patch": {"sessionTarget": "session:..\\outside"},
                },
            },
        )

    assert add_response.status_code == 400
    assert "invalid cron sessionTarget session id" in add_response.json()["detail"]
    assert safe_add_response.status_code == 200
    assert update_response.status_code == 400
    assert "invalid cron sessionTarget session id" in update_response.json()["detail"]


def test_gateway_node_method_call_endpoint_normalizes_current_cron_session_target_to_isolated(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-current-session-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Current Session Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "current",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Stay on the current cron lane.",
                    },
                },
            },
        )
        add_payload = add_response.json()
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": add_payload["id"],
                    "patch": {"sessionTarget": "current"},
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

    assert add_response.status_code == 200
    assert add_payload["sessionTarget"] == "isolated"
    assert update_response.status_code == 200
    assert update_response.json()["sessionTarget"] == "isolated"
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["sessionTarget"] == "isolated"


def test_gateway_node_method_call_endpoint_preserves_custom_cron_session_target_casing() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-custom-session-case-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        add_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.add",
                "params": {
                    "name": "Mixed Case Custom Session Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 3_600_000},
                    "sessionTarget": "session:MySessionID",
                    "wakeMode": "now",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run on the named cron lane.",
                    },
                },
            },
        )
        add_payload = add_response.json()
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "cron.update",
                "params": {
                    "id": add_payload["id"],
                    "patch": {"sessionTarget": "session:ProjectBeta:Ops"},
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

    assert add_response.status_code == 200
    assert add_payload["sessionTarget"] == "session:MySessionID"
    assert update_response.status_code == 200
    assert update_response.json()["sessionTarget"] == "session:ProjectBeta:Ops"
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["sessionTarget"] == "session:ProjectBeta:Ops"


def test_gateway_node_method_call_endpoint_infers_cron_add_at_schedule_kind() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-at-infer-api"
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
                    "name": "One Shot",
                    "enabled": True,
                    "schedule": {"at": "2026-04-18T12:00:00Z"},
                    "sessionTarget": "isolated",
                    "wakeMode": "next-heartbeat",
                    "payload": {
                        "kind": "agentTurn",
                        "message": "Run exactly once at noon UTC.",
                    },
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}


def test_gateway_node_method_call_endpoint_rejects_cron_add_main_agent_turn_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-main-agent-turn-reject-api"
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

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "invalid cron.add params: "
        "payload.kind='agentTurn' requires sessionTarget to leave 'main'"
    )


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


def test_gateway_node_method_call_endpoint_round_trips_cron_session_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-session-key-api"
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
                name="Session Key Repair",
                summary="Keep the cron route pinned to a stored session.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Keep the cron route pinned to a stored session.",
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
                    "cron_session_target": "isolated",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "agentTurn",
                    "cron_session_key": "agent:openzues:telegram:direct:123:thread:77",
                    "cron_delivery_channel": "last",
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
                        "sessionKey": "telegram:channel:deploy-room",
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
        stored = asyncio.run(database.get_task_blueprint(task_id))

    assert response.status_code == 200
    assert response.json()["sessionKey"] == "telegram:channel:deploy-room"
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["sessionKey"] == "telegram:channel:deploy-room"
    assert stored is not None
    assert stored["cron_session_key"] == "agent:openzues:telegram:channel:deploy-room"


def test_gateway_node_method_call_endpoint_supports_cron_update_anchor_ms() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-anchor-api"
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
                name="Anchored Ship",
                summary="Ship on the anchored minute boundary.",
                project_id=None,
                instance_id=None,
                cadence_minutes=60,
                enabled=True,
                payload={
                    "objective_template": "Ship on the anchored minute boundary.",
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
                    "schedule_anchor_ms": 123,
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
                        "schedule": {"kind": "every", "everyMs": 7_200_000, "anchorMs": 456},
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
    assert payload["schedule"] == {"kind": "every", "everyMs": 7_200_000, "anchorMs": 456}
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {"kind": "every", "everyMs": 7_200_000, "anchorMs": 456}


def test_gateway_node_method_call_endpoint_supports_cron_update_at_schedule() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-at-api"
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
                        "schedule": {"kind": "at", "at": "2026-04-18T12:00:00Z"},
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
    assert payload["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}


def test_gateway_node_method_call_endpoint_supports_cron_update_cron_schedule() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-cron-api"
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
                        "schedule": {
                            "kind": "cron",
                            "expr": "0 9 * * *",
                            "tz": "America/Chicago",
                            "staggerMs": 45_000,
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
    assert response.json()["schedule"] == {
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "America/Chicago",
        "staggerMs": 45_000,
    }
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["schedule"] == {
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "America/Chicago",
        "staggerMs": 45_000,
    }


def test_gateway_node_method_call_endpoint_infers_cron_update_at_schedule_kind() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-at-infer-api"
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
                        "schedule": {"at": "2026-04-18T12:00:00Z"},
                    },
                },
            },
        )

    assert response.status_code == 200
    assert response.json()["schedule"] == {"kind": "at", "at": "2026-04-18T12:00:00.000Z"}


def test_gateway_node_method_call_endpoint_supports_cron_update_isolated_agent_turn_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-isolated-api"
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
                        "sessionTarget": "isolated",
                        "wakeMode": "next-heartbeat",
                        "payload": {
                            "kind": "agentTurn",
                            "message": "Run this on the isolated cron lane.",
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
    assert payload["sessionTarget"] == "isolated"
    assert payload["wakeMode"] == "next-heartbeat"
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Run this on the isolated cron lane.",
        "model": "gpt-5.4-mini",
    }
    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["sessionTarget"] == "isolated"
    assert jobs[0]["wakeMode"] == "next-heartbeat"
    assert jobs[0]["payload"] == {
        "kind": "agentTurn",
        "message": "Run this on the isolated cron lane.",
        "model": "gpt-5.4-mini",
    }


def test_gateway_node_method_call_endpoint_rejects_cron_update_main_system_event_to_agent_turn(
    ) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-main-system-event-reject-api"
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
                    "objective_template": "Resume the main lane from cron.",
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
                    "cron_session_target": "main",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "systemEvent",
                    "cron_payload_text": "Resume the main lane from cron.",
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
                        "payload": {
                            "kind": "agentTurn",
                            "message": "Run this on the isolated cron lane.",
                        },
                    },
                },
            },
        )

    assert response.status_code == 400


def test_gateway_node_method_call_endpoint_rejects_cron_update_isolated_system_event_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-isolated-reject-api"
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
                        "sessionTarget": "isolated",
                        "payload": {
                            "kind": "systemEvent",
                            "text": "Resume the main lane from cron.",
                        },
                    },
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "invalid cron.update params: "
        "patch.payload.kind='systemEvent' requires patch.sessionTarget='main'"
    )


def test_gateway_node_method_call_endpoint_can_clear_explicit_none_delivery_back_to_announce(
    tmp_path,
) -> None:
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
                    "objective_template": "Run this on the isolated cron lane.",
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
                    "cron_session_target": "isolated",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "agentTurn",
                    "cron_delivery_mode": "none",
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
                        "delivery": {"mode": "announce"},
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
    assert response.json()["delivery"] == {"mode": "announce"}
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {"mode": "announce"}


def test_gateway_node_method_call_endpoint_normalizes_announce_delivery_metadata(
    tmp_path,
) -> None:
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
                    "objective_template": "Run this on the isolated cron lane.",
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
                    "cron_session_target": "isolated",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "agentTurn",
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
                        "delivery": {
                            "mode": "announce",
                            "channel": " TeLeGrAm ",
                            "to": " 7200373102 ",
                            "accountId": " coordinator ",
                            "bestEffort": True,
                            "failureDestination": {
                                "mode": "announce",
                                "channel": " Signal ",
                                "to": " +15550001111 ",
                                "accountId": " escalations ",
                            },
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
    assert response.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "accountId": "coordinator",
        "bestEffort": True,
        "failureDestination": {
            "mode": "announce",
            "channel": "signal",
            "to": "+15550001111",
            "accountId": "escalations",
        },
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "accountId": "coordinator",
        "bestEffort": True,
        "failureDestination": {
            "mode": "announce",
            "channel": "signal",
            "to": "+15550001111",
            "accountId": "escalations",
        },
    }


def test_gateway_node_method_call_endpoint_clears_cron_failure_destination_fields(tmp_path) -> None:
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
                    "objective_template": "Run this on the isolated cron lane.",
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
                    "cron_session_target": "isolated",
                    "cron_wake_mode": "next-heartbeat",
                    "cron_payload_kind": "agentTurn",
                    "cron_delivery_mode": "announce",
                    "cron_delivery_channel": "telegram",
                    "cron_delivery_to": "7200373102",
                    "cron_delivery_failure_destination": {
                        "mode": "announce",
                        "channel": "signal",
                        "to": "+15550001111",
                        "accountId": "escalations",
                    },
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
                        "delivery": {
                            "failureDestination": {
                                "channel": "   ",
                                "accountId": "",
                            },
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
    assert response.json()["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "failureDestination": {
            "mode": "announce",
            "to": "+15550001111",
        },
    }
    assert list_response.status_code == 200
    assert list_response.json()["jobs"][0]["delivery"] == {
        "mode": "announce",
        "channel": "telegram",
        "to": "7200373102",
        "failureDestination": {
            "mode": "announce",
            "to": "+15550001111",
        },
    }


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
        messages_after_now = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_control_chat_messages()),
            lambda messages: [
                message["content"] for message in messages if message["role"] == "user"
            ]
            == ["Resume parity from the latest checkpoint."],
        )
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
        events_before_tick = asyncio.run(client.app.state.database.list_events())
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
    assert [event["method"] for event in events_before_tick] == ["system-event", "system-event"]
    assert [event["payload"] for event in events_before_tick] == [
        {"text": "Resume parity from the latest checkpoint.", "reason": "wake"},
        {"text": "Check the queued parity nudge on the next heartbeat.", "reason": "wake"},
    ]

    assert acted is True
    assert [
        message["content"] for message in messages_after_tick if message["role"] == "user"
    ] == [
        "Resume parity from the latest checkpoint.",
        "Check the queued parity nudge on the next heartbeat.",
    ]
    assert len(wake_requests) == 2
    assert wake_requests[0]["mode"] == "now"
    assert wake_requests[0]["text"] == "Resume parity from the latest checkpoint."
    assert wake_requests[0]["status"] == "dispatched"
    assert wake_requests[1]["mode"] == "next-heartbeat"
    assert wake_requests[1]["text"] == "Check the queued parity nudge on the next heartbeat."
    assert wake_requests[1]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_allows_opaque_metadata_fields(tmp_path) -> None:
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
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                    "source": "heartbeat",
                    "requestId": "wake-meta-1",
                    "metadata": {"thread": "parity"},
                },
            },
        )
        messages = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_control_chat_messages()),
            lambda records: [message["content"] for message in records if message["role"] == "user"]
            == ["Resume parity from the latest checkpoint."],
        )
        events = asyncio.run(client.app.state.database.list_events())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert [message["content"] for message in messages if message["role"] == "user"] == [
        "Resume parity from the latest checkpoint."
    ]
    assert len(events) == 1
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"] == {
        "text": "Resume parity from the latest checkpoint.",
        "reason": "wake",
    }


def test_gateway_node_method_call_endpoint_wake_now_does_not_flush_next_heartbeat_rows(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
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
        wake_requests = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_gateway_wake_requests()),
            lambda rows: len(rows) == 2
            and rows[0]["status"] == "pending"
            and rows[1]["status"] == "dispatched",
        )
        messages = asyncio.run(client.app.state.database.list_control_chat_messages())

    assert queued_response.status_code == 200
    assert queued_response.json() == {"ok": True}
    assert now_response.status_code == 200
    assert now_response.json() == {"ok": True}
    assert [message["content"] for message in messages if message["role"] == "user"] == [
        "Resume parity from the latest checkpoint."
    ]
    assert len(wake_requests) == 2
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["text"] == "Check the queued parity nudge on the next heartbeat."
    assert wake_requests[0]["status"] == "pending"
    assert wake_requests[1]["mode"] == "now"
    assert wake_requests[1]["text"] == "Resume parity from the latest checkpoint."
    assert wake_requests[1]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_now_coalesces_duplicate_rows(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                },
            },
        )
        immediate_messages = asyncio.run(client.app.state.database.list_control_chat_messages())
        delayed_messages = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_control_chat_messages()),
            lambda records: [message["content"] for message in records if message["role"] == "user"]
            == ["Resume parity from the latest checkpoint."],
        )
        wake_requests = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_gateway_wake_requests()),
            lambda rows: len(rows) == 1 and rows[0]["status"] == "dispatched",
        )

    assert first_response.status_code == 200
    assert first_response.json() == {"ok": True}
    assert second_response.status_code == 200
    assert second_response.json() == {"ok": True}
    assert [message["content"] for message in immediate_messages if message["role"] == "user"] == []
    assert [message["content"] for message in delayed_messages if message["role"] == "user"] == [
        "Resume parity from the latest checkpoint."
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_now_batches_distinct_rows(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from checkpoint A.",
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from checkpoint B.",
                },
            },
        )
        immediate_messages = asyncio.run(client.app.state.database.list_control_chat_messages())
        delayed_messages = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_control_chat_messages()),
            lambda records: [message["content"] for message in records if message["role"] == "user"]
            == ["Resume parity from checkpoint B."],
        )
        wake_requests = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_gateway_wake_requests()),
            lambda rows: len(rows) == 1 and rows[0]["status"] == "dispatched",
        )

    assert first_response.status_code == 200
    assert first_response.json() == {"ok": True}
    assert second_response.status_code == 200
    assert second_response.json() == {"ok": True}
    assert [message["content"] for message in immediate_messages if message["role"] == "user"] == []
    assert [message["content"] for message in delayed_messages if message["role"] == "user"] == [
        "Resume parity from checkpoint B.",
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["text"] == "Resume parity from checkpoint B."
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_preserves_distinct_session_targets(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity from the latest checkpoint.",
                    "sessionKey": "openzues:thread:ops",
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity from the latest checkpoint.",
                    "sessionKey": "openzues:thread:main",
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert first_response.status_code == 200
    assert first_response.json() == {"ok": True}
    assert second_response.status_code == 200
    assert second_response.json() == {"ok": True}
    assert acted is True
    assert submit_calls == [
        ("Resume parity from the latest checkpoint.", "openzues:thread:ops"),
        ("Resume parity from the latest checkpoint.", "openzues:thread:main"),
    ]
    assert len(wake_requests) == 2
    assert [request["session_key"] for request in wake_requests] == [
        "openzues:thread:ops",
        "openzues:thread:main",
    ]
    assert [request["status"] for request in wake_requests] == ["dispatched", "dispatched"]


def test_gateway_node_method_call_endpoint_wake_resolves_main_agent_target(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        resolved_session_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.resolve",
                "params": {"key": "launch:mode:workspace_affinity", "agentId": "main"},
            },
        )
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity through the main agent target.",
                    "agentId": "main",
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        events = asyncio.run(client.app.state.database.list_events())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert resolved_session_response.status_code == 200
    resolved_session_key = resolved_session_response.json()["key"]
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert acted is True
    assert submit_calls == [
        ("Resume parity through the main agent target.", resolved_session_key),
    ]
    assert [event["payload"] for event in events] == [
        {
            "text": "Resume parity through the main agent target.",
            "reason": "wake",
            "agentId": "main",
            "sessionKey": resolved_session_key,
        }
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == resolved_session_key
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_derives_agent_identity_from_session_key(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []
    target_session_key = "agent:main:thread:demo"

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity through the explicit session target.",
                    "sessionKey": target_session_key,
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        events = asyncio.run(client.app.state.database.list_events())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert acted is True
    assert submit_calls == [
        ("Resume parity through the explicit session target.", target_session_key),
    ]
    assert [event["payload"] for event in events] == [
        {
            "text": "Resume parity through the explicit session target.",
            "reason": "wake",
            "agentId": "main",
            "sessionKey": target_session_key,
        }
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == target_session_key
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_preserves_explicit_reason_metadata(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []
    target_session_key = "agent:main:thread:demo"

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity through the cron wake.",
                    "reason": "cron:job-1",
                    "sessionKey": target_session_key,
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        events = asyncio.run(client.app.state.database.list_events())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert acted is True
    assert submit_calls == [("Resume parity through the cron wake.", target_session_key)]
    assert [event["payload"] for event in events] == [
        {
            "text": "Resume parity through the cron wake.",
            "reason": "cron:job-1",
            "agentId": "main",
            "sessionKey": target_session_key,
        }
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["reason"] == "cron:job-1"
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == target_session_key
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_upgrades_duplicate_pending_reason_by_priority(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    target_session_key = "agent:main:thread:demo"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity through the prioritized wake.",
                    "reason": "retry",
                    "sessionKey": target_session_key,
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity through the prioritized wake.",
                    "reason": "exec-event",
                    "sessionKey": target_session_key,
                },
            },
        )
        events = asyncio.run(client.app.state.database.list_events())
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert first_response.status_code == 200
    assert first_response.json() == {"ok": True}
    assert second_response.status_code == 200
    assert second_response.json() == {"ok": True}
    assert [event["payload"] for event in events] == [
        {
            "text": "Resume parity through the prioritized wake.",
            "reason": "retry",
            "agentId": "main",
            "sessionKey": target_session_key,
        },
        {
            "text": "Resume parity through the prioritized wake.",
            "reason": "exec-event",
            "agentId": "main",
            "sessionKey": target_session_key,
        },
    ]
    assert len(wake_requests) == 1
    assert wake_requests[0]["reason"] == "exec-event"
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == target_session_key
    assert wake_requests[0]["status"] == "pending"


def test_gateway_node_method_call_endpoint_wake_keeps_winning_text_on_lower_priority_followup(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    submit_calls: list[tuple[str, str | None]] = []
    target_session_key = "agent:main:thread:demo"

    async def fake_submit(
        prompt: str,
        dashboard: DashboardView,
        *,
        session_key: str | None = None,
    ) -> object:
        del dashboard
        submit_calls.append((prompt, session_key))
        return {"ok": True}

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        monkeypatch.setattr(client.app.state.control_chat_service, "submit", fake_submit)
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity from checkpoint A.",
                    "reason": "exec-event",
                    "sessionKey": target_session_key,
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "wake",
                "params": {
                    "mode": "next-heartbeat",
                    "text": "Resume parity from checkpoint B.",
                    "reason": "retry",
                    "sessionKey": target_session_key,
                },
            },
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        wake_requests = asyncio.run(client.app.state.database.list_gateway_wake_requests())

    assert first_response.status_code == 200
    assert first_response.json() == {"ok": True}
    assert second_response.status_code == 200
    assert second_response.json() == {"ok": True}
    assert acted is True
    assert submit_calls == [("Resume parity from checkpoint A.", target_session_key)]
    assert len(wake_requests) == 1
    assert wake_requests[0]["text"] == "Resume parity from checkpoint A."
    assert wake_requests[0]["reason"] == "exec-event"
    assert wake_requests[0]["agent_id"] == "main"
    assert wake_requests[0]["session_key"] == target_session_key
    assert wake_requests[0]["status"] == "dispatched"


def test_gateway_node_method_call_endpoint_wake_now_records_dispatched_wake_request(
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
                "method": "wake",
                "params": {
                    "mode": "now",
                    "text": "Resume parity from the latest checkpoint.",
                },
            },
        )
        wake_requests = _wait_for(
            lambda: asyncio.run(client.app.state.database.list_gateway_wake_requests()),
            lambda rows: len(rows) == 1 and rows[0]["status"] == "dispatched",
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "now"
    assert wake_requests[0]["text"] == "Resume parity from the latest checkpoint."
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


def test_gateway_node_method_call_endpoint_supports_agents_memory_file(
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
                    "name": "MEMORY.md",
                    "content": "Durable memory.\n",
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "agents.files.list", "params": {"agentId": "main"}},
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.get",
                "params": {"agentId": "main", "name": "MEMORY.md"},
            },
        )

    assert set_response.status_code == 200
    assert set_response.json()["file"]["name"] == "MEMORY.md"
    assert list_response.status_code == 200
    files_by_name = {entry["name"]: entry for entry in list_response.json()["files"]}
    assert "BOOTSTRAP.md" in files_by_name
    assert "MEMORY.md" in files_by_name
    assert get_response.status_code == 200
    assert get_response.json()["file"]["content"] == "Durable memory.\n"


def test_gateway_node_method_call_endpoint_supports_custom_agent_files(
    tmp_path,
    monkeypatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    agent_workspace = tmp_path / "api-agent-workspace"
    monkeypatch.chdir(workspace_root)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        create_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.create",
                "params": {
                    "name": "API Builder",
                    "workspace": str(agent_workspace),
                    "model": "gpt-5.4-mini",
                },
            },
        )
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.set",
                "params": {
                    "agentId": "api-builder",
                    "name": "MEMORY.md",
                    "content": "API builder memory.\n",
                },
            },
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.files.get",
                "params": {"agentId": "api-builder", "name": "MEMORY.md"},
            },
        )

    written_path = agent_workspace / "MEMORY.md"
    assert create_response.status_code == 200
    assert set_response.status_code == 200
    assert set_response.json()["workspace"] == str(agent_workspace)
    assert set_response.json()["file"]["path"] == str(written_path)
    assert get_response.status_code == 200
    assert get_response.json()["agentId"] == "api-builder"
    assert get_response.json()["workspace"] == str(agent_workspace)
    assert get_response.json()["file"]["content"] == "API builder memory.\n"
    assert written_path.read_text(encoding="utf-8") == "API builder memory.\n"
    assert not (workspace_root / "MEMORY.md").exists()


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


def test_gateway_node_method_call_endpoint_rejects_malformed_agent_identity_session_key(
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
                "method": "agent.identity.get",
                "params": {"sessionKey": "agent:main"},
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == 'invalid agent.identity.get params: malformed session key "agent:main"'
    )


def test_gateway_node_method_call_endpoint_rejects_agent_identity_session_key_mismatch(
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
                "method": "agent.identity.get",
                "params": {"agentId": "main", "sessionKey": "agent:other-agent:main"},
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "invalid agent.identity.get params: agent "
        '"main" does not match session key agent "other-agent"'
    )


def test_gateway_node_method_call_endpoint_supports_agents_mutation_lifecycle(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    workspace = tmp_path / "api-agent-workspace"
    updated_workspace = tmp_path / "api-agent-updated"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        create_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.create",
                "params": {
                    "name": "API Builder",
                    "workspace": str(workspace),
                    "model": "gpt-5.4-mini",
                    "emoji": "spark",
                    "avatar": "/static/api-builder.png",
                },
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "agents.list", "params": {}},
        )
        identity_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.identity.get",
                "params": {"sessionKey": "agent:api-builder:main"},
            },
        )
        update_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.update",
                "params": {
                    "agentId": "api-builder",
                    "name": "API Builder Updated",
                    "workspace": str(updated_workspace),
                    "model": "gpt-5.4",
                },
            },
        )
        delete_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agents.delete",
                "params": {"agentId": "api-builder", "deleteFiles": False},
            },
        )

    assert create_response.status_code == 200
    assert create_response.json()["agentId"] == "api-builder"
    assert list_response.status_code == 200
    custom = next(agent for agent in list_response.json()["agents"] if agent["id"] == "api-builder")
    assert custom["workspace"] == str(workspace)
    assert custom["identity"]["emoji"] == "spark"
    assert identity_response.status_code == 200
    assert identity_response.json() == {
        "agentId": "api-builder",
        "name": "API Builder",
        "avatar": "/static/api-builder.png",
        "emoji": "spark",
    }
    assert update_response.status_code == 200
    assert update_response.json() == {"ok": True, "agentId": "api-builder"}
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "ok": True,
        "agentId": "api-builder",
        "removedBindings": [],
    }


def test_gateway_node_method_call_endpoint_returns_doctor_memory_status_payload(
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
                "method": "doctor.memory.status",
                "params": {},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "agentId": "openzues",
        "embedding": {
            "ok": False,
            "error": "memory search unavailable",
        },
    }


def test_gateway_node_method_call_endpoint_reads_doctor_memory_dream_diary(
    tmp_path,
    monkeypatch,
) -> None:
    diary_path = tmp_path / "DREAMS.md"
    diary_path.write_text("# Dream Diary\n\n- API parity proof.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
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
                "method": "doctor.memory.dreamDiary",
                "params": {},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "agentId": "openzues",
        "found": True,
        "path": str(diary_path),
        "content": "# Dream Diary\n\n- API parity proof.\n",
        "updatedAtMs": payload["updatedAtMs"],
    }
    assert isinstance(payload["updatedAtMs"], int)


def test_gateway_node_method_call_endpoint_mutates_doctor_memory_family(
    tmp_path: Path,
) -> None:
    memory_dir = tmp_path / "memory"
    grounded_dir = memory_dir / "grounded-short-term"
    grounded_dir.mkdir(parents=True)
    (memory_dir / "2026-04-25.md").write_text(
        "# Daily Memory\n\n- API shipped parity work.\n",
        encoding="utf-8",
    )
    (grounded_dir / "short-term.md").write_text("- transient\n", encoding="utf-8")
    diary_path = tmp_path / "DREAMS.md"
    diary_path.write_text("# Dream Diary\n\n- duplicate\n- duplicate\n", encoding="utf-8")
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            memory_doctor_workspace=tmp_path,
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        dedupe_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "doctor.memory.dedupeDreamDiary",
                "params": {},
            },
        )
        backfill_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "doctor.memory.backfillDreamDiary",
                "params": {},
            },
        )
        reset_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "doctor.memory.resetDreamDiary",
                "params": {},
            },
        )
        reset_short_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "doctor.memory.resetGroundedShortTerm",
                "params": {},
            },
        )
        repair_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "doctor.memory.repairDreamingArtifacts",
                "params": {},
            },
        )

    assert dedupe_response.status_code == 200
    assert dedupe_response.json()["removedEntries"] == 1
    assert backfill_response.status_code == 200
    assert backfill_response.json()["written"] == 2
    assert reset_response.status_code == 200
    assert reset_response.json()["removedEntries"] == 2
    assert reset_short_response.status_code == 200
    assert reset_short_response.json()["removedShortTermEntries"] == 1
    assert repair_response.status_code == 200
    assert repair_response.json()["changed"] is False
    assert "openzues:dream-backfill" not in diary_path.read_text(encoding="utf-8")


def test_gateway_node_method_call_endpoint_supports_agent_wait_for_tracked_gateway_run() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-wait-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-wait-api.db")
    asyncio.run(database.initialize())
    session_key = "openzues:thread:agent-wait-api"
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Wait API Loop",
            objective="Wait for the tracked gateway API run to finish.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-wait-api",
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

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API wait finished.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        send_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.send",
                "params": {
                    "key": session_key,
                    "message": "continue",
                    "idempotencyKey": "run-agent-wait-api-1",
                },
            },
        )
        assert send_response.status_code == 200

        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "run-agent-wait-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["runId"] == "run-agent-wait-api-1"
    assert payload["status"] == "ok"
    assert isinstance(payload["startedAt"], int)
    assert isinstance(payload["endedAt"], int)
    assert payload["endedAt"] >= payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_supports_bounded_agent_launch_main_session() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Launch API Loop",
            objective="Launch the next parity slice through the API bridge.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "idempotencyKey": "agent-run-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_supports_bounded_agent_launch_by_session_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-session-id-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-session-id-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-launch-session-id-api",
    ).session_key
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent SessionId API Loop",
            objective="Launch parity through a sessionId-selected API thread.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-session-id-api",
            session_key=thread_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent sessionId launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "sessionId": "thread-agent-launch-session-id-api",
                    "idempotencyKey": "agent-run-session-id-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-session-id-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": thread_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-session-id-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-session-id-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-session-id-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_persists_agent_launch_session_label() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-label-persist-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-label-persist-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Label Persist API Loop",
            objective="Launch parity while persisting the requested session label.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-label-persist-api",
            session_key=main_session_key,
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
    asyncio.run(
        database.upsert_gateway_session_metadata(
            session_key=main_session_key,
            metadata={"model": "gpt-5.4-mini"},
        )
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent label persistence completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "label": "Parity Worker",
                    "idempotencyKey": "agent-run-label-persist-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-label-persist-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-label-persist-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-label-persist-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    metadata_row = asyncio.run(database.get_gateway_session_metadata(main_session_key))
    assert isinstance(metadata_row, dict)
    metadata = metadata_row.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata["label"] == "Parity Worker"
    assert metadata["model"] == "gpt-5.4-mini"
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-label-persist-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_supports_agent_launch_with_deliver_false() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-deliver-false-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-deliver-false-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Deliver False API Loop",
            objective="Launch parity while keeping delivery explicitly disabled.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-deliver-false-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent explicit non-delivery launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "deliver": False,
                    "idempotencyKey": "agent-run-deliver-false-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-deliver-false-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-deliver-false-api-1",
        "thinking": None,
        "deliver": False,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-deliver-false-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-deliver-false-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_supports_agent_launch_with_best_effort_false() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-best-effort-false-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-best-effort-false-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Best Effort False API Loop",
            objective="Launch parity while keeping best-effort delivery explicitly disabled.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-best-effort-false-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent best-effort false launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "bestEffortDeliver": False,
                    "idempotencyKey": "agent-run-best-effort-false-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-best-effort-false-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-best-effort-false-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-best-effort-false-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-best-effort-false-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_rejects_malformed_agent_session_keys(tmp_path) -> None:
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
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "sessionKey": "agent::main",
                    "idempotencyKey": "agent-run-malformed-session-key-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == 'invalid agent params: malformed session key "agent::main"'


def test_gateway_node_method_call_endpoint_rejects_agent_session_key_mismatch(tmp_path) -> None:
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
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "sessionKey": "agent:other-agent:main",
                    "idempotencyKey": "agent-run-session-key-agent-mismatch-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == 'invalid agent params: agent "main" does not match session key agent "other-agent"'
    )


@pytest.mark.parametrize(
    ("params", "expected_channel"),
    [
        (
            {
                "channel": "not-a-real-channel",
            },
            "not-a-real-channel",
        ),
        (
            {
                "replyChannel": "not-a-real-reply-channel",
            },
            "not-a-real-reply-channel",
        ),
    ],
)
def test_gateway_node_method_call_endpoint_rejects_unknown_agent_channel_hints(
    tmp_path,
    params: dict[str, str],
    expected_channel: str,
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
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "idempotencyKey": f"agent-run-unknown-channel-api-{expected_channel}",
                    **params,
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == f"invalid agent params: unknown channel: {expected_channel}"


@pytest.mark.parametrize(
    ("params",),
    [
        (
            {
                "channel": "last",
            },
        ),
        (
            {
                "replyChannel": "last",
            },
        ),
    ],
)
def test_gateway_node_method_call_endpoint_treats_last_agent_channel_hints_as_omitted(
    params: dict[str, str],
) -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-last-channel-hint-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-last-channel-hint-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Last Channel Hint API Loop",
            objective='Launch parity while treating "last" channel hints as omitted.',
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-last-channel-hint-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint='Gateway API agent "last" channel hint launch completed.',
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "idempotencyKey": "agent-run-last-channel-hint-api-1",
                    **params,
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-last-channel-hint-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-last-channel-hint-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-last-channel-hint-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-last-channel-hint-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_accepts_matching_key_and_session_id_selectors() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-agent-launch-matching-key-session-id-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-matching-key-session-id-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-matching-key-session-id-api",
    ).session_key
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Matching Key SessionId API Loop",
            objective="Launch parity through matching sessionKey and sessionId selectors.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-matching-key-session-id-api",
            session_key=thread_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent matching session selectors completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "sessionKey": thread_session_key,
                    "sessionId": "thread-agent-matching-key-session-id-api",
                    "idempotencyKey": "agent-run-matching-key-session-id-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-matching-key-session-id-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": thread_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-matching-key-session-id-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-matching-key-session-id-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-matching-key-session-id-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_ignores_blank_optional_agent_fields() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-optional-fields-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-optional-fields-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Blank Optional Fields API Loop",
            objective="Launch parity while treating blank unsupported strings as omitted.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-blank-optional-fields-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent blank optional fields launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "provider": "   ",
                    "replyTo": "   ",
                    "channel": "   ",
                    "threadId": "   ",
                    "groupId": "   ",
                    "lane": "   ",
                    "extraSystemPrompt": "   ",
                    "idempotencyKey": "agent-run-blank-optional-fields-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-blank-optional-fields-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-optional-fields-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-blank-optional-fields-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-blank-optional-fields-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_ignores_blank_agent_session_selectors() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-session-selectors-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-session-selectors-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Blank Session Selectors API Loop",
            objective="Launch parity while treating blank session selectors as omitted.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-blank-session-selectors-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent blank session selectors launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "sessionKey": "   ",
                    "sessionId": "   ",
                    "idempotencyKey": "agent-run-blank-session-selectors-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-blank-session-selectors-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-session-selectors-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-blank-session-selectors-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-blank-session-selectors-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_ignores_blank_agent_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-agent-id-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-agent-id-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Blank Agent Id API Loop",
            objective="Launch parity while treating blank agent ids as omitted.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-blank-agent-id-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent blank agent id launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "   ",
                    "idempotencyKey": "agent-run-blank-agent-id-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-blank-agent-id-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-agent-id-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-blank-agent-id-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-blank-agent-id-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_allows_blank_agent_thinking() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-thinking-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-thinking-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Blank Thinking API Loop",
            objective="Launch parity while preserving blank thinking hints.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-blank-thinking-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent blank thinking launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "thinking": "",
                    "idempotencyKey": "agent-run-blank-thinking-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-blank-thinking-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-thinking-api-1",
        "thinking": "",
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-blank-thinking-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-blank-thinking-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_ignores_blank_agent_label() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-label-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-label-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Blank Label API Loop",
            objective="Launch parity while treating blank labels as omitted.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-blank-label-api",
            session_key=main_session_key,
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
    asyncio.run(
        database.upsert_gateway_session_metadata(
            session_key=main_session_key,
            metadata={"label": "Pinned Worker", "model": "gpt-5.4"},
        )
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent blank label launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "label": "",
                    "idempotencyKey": "agent-run-blank-label-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-blank-label-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    metadata_row = asyncio.run(database.get_gateway_session_metadata(main_session_key))

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-label-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-blank-label-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert metadata_row is not None
    assert metadata_row["metadata"]["label"] == "Pinned Worker"
    assert metadata_row["metadata"]["model"] == "gpt-5.4"
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-blank-label-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


def test_gateway_node_method_call_endpoint_allows_empty_internal_events() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-empty-internal-events-api"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-empty-internal-events-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway Agent Empty Internal Events API Loop",
            objective="Launch parity while treating empty internal events as inert.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-empty-internal-events-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent empty internal events launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "internalEvents": [],
                    "idempotencyKey": "agent-run-empty-internal-events-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-empty-internal-events-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-empty-internal-events-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-empty-internal-events-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-empty-internal-events-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.parametrize(
    ("input_provenance", "expected_message"),
    [
        (
            {"kind": "not-a-real-kind"},
            "inputProvenance.kind must be one of: external_user, inter_session, internal_system",
        ),
        (
            {"kind": "inter_session", "unexpectedField": "drift"},
            "inputProvenance does not accept: unexpectedField",
        ),
    ],
)
def test_gateway_node_method_call_endpoint_rejects_invalid_agent_input_provenance(
    tmp_path,
    input_provenance: dict[str, str],
    expected_message: str,
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
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "inputProvenance": input_provenance,
                    "idempotencyKey": "agent-run-invalid-input-provenance-api-1",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_message


@pytest.mark.parametrize(
    ("attachments",),
    [
        (
            [
                {
                    "type": "image",
                    "mimeType": "image/png",
                    "fileName": "preview.png",
                }
            ],
        ),
        (
            [
                {
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                    }
                }
            ],
        ),
    ],
)
def test_gateway_node_method_call_endpoint_ignores_inert_agent_attachments(
    attachments: list[dict[str, object]],
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-inert-attachments-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-inert-attachments-api.db")
    asyncio.run(database.initialize())
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = asyncio.run(
        database.create_mission(
            name="Gateway API Agent Inert Attachments Loop",
            objective="Launch parity while treating inert attachments as omitted.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-agent-launch-inert-attachments-api",
            session_key=main_session_key,
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

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway API agent inert attachments launch completed.",
            )

    gateway_node_method_service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        database=database,
        gateway_node_method_service=gateway_node_method_service,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        launch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent",
                "params": {
                    "message": "Ship the next verified slice.",
                    "agentId": "main",
                    "attachments": attachments,
                    "idempotencyKey": "agent-run-inert-attachments-api-1",
                },
            },
        )
        wait_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "agent.wait",
                "params": {
                    "runId": "agent-run-inert-attachments-api-1",
                    "timeoutMs": 5,
                },
            },
        )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-inert-attachments-api-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["runId"] == "agent-run-inert-attachments-api-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert wait_response.status_code == 200
    wait_payload = wait_response.json()
    assert wait_payload["runId"] == "agent-run-inert-attachments-api-1"
    assert wait_payload["status"] == "ok"
    assert isinstance(wait_payload["startedAt"], int)
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.parametrize(
    ("params",),
    [
        ({"agentId": "   "},),
        ({"sessionKey": "   "},),
    ],
)
def test_gateway_node_method_call_endpoint_allows_blank_agent_identity_selectors(
    tmp_path,
    params: dict[str, str],
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
                "method": "agent.identity.get",
                "params": params,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
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
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "totalTokensFresh": False,
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
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "totalTokensFresh": False,
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
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "totalTokensFresh": False,
            "modelProvider": "openai",
            "model": "gpt-5.4-mini",
            "contextTokens": None,
            "label": "Parity Worker",
            "spawnedBy": "parity-conductor",
        },
    ]
    assert isinstance(payload["sessions"][1]["updatedAt"], int)
    assert payload["sessions"][1]["updatedAt"] > 0


def test_gateway_node_method_call_endpoint_sessions_list_surfaces_compaction_checkpoint_metadata(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-compaction-api"
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
        thread_id="thread-compaction-list",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.upsert_gateway_session_metadata(
                session_key=session_key,
                metadata={"label": "Checkpoint Worker"},
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="user",
                content="Alpha line 1\nAlpha line 2",
                mission_id=None,
                session_key=session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Bravo line 1",
                mission_id=None,
                session_key=session_key,
            )
        )
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="Charlie line 1\nCharlie line 2",
                mission_id=None,
                session_key=session_key,
            )
        )
        compact_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.compact",
                "params": {"key": session_key, "maxLines": 2},
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "sessions.list",
                "params": {"includeGlobal": True, "includeUnknown": False, "limit": 10},
            },
        )

    assert compact_response.status_code == 200
    assert list_response.status_code == 200
    payload = list_response.json()
    session_payload = next(
        session for session in payload["sessions"] if session["key"] == session_key
    )
    assert session_payload["compactionCheckpointCount"] == 1
    assert session_payload["latestCompactionCheckpoint"] == {
        "checkpointId": compact_response.json()["checkpointId"],
        "sessionKey": session_key,
        "sessionId": "thread-compaction-list",
        "createdAt": session_payload["latestCompactionCheckpoint"]["createdAt"],
        "reason": "manual",
        "summary": "Alpha line 1 Alpha line 2 Bravo line 1",
        "firstKeptEntryId": session_payload["latestCompactionCheckpoint"]["firstKeptEntryId"],
        "preCompaction": {
            "sessionId": "thread-compaction-list",
            "entryId": session_payload["latestCompactionCheckpoint"]["preCompaction"]["entryId"],
        },
        "postCompaction": {
            "sessionId": "thread-compaction-list",
            "entryId": session_payload["latestCompactionCheckpoint"]["postCompaction"]["entryId"],
        },
    }


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


def test_gateway_session_history_rest_endpoint_supports_cursor_pagination() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-api"
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
        database = client.app.state.database
        for content in ("first message", "second message", "third message"):
            asyncio.run(
                database.append_control_chat_message(
                    role="assistant",
                    content=content,
                    session_key=session_key,
                )
            )

        encoded_key = quote(session_key, safe="")
        first_response = client.get(f"/sessions/{encoded_key}/history?limit=2")
        second_response = client.get(
            f"/sessions/{encoded_key}/history?limit=2&cursor=2"
        )

    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["sessionKey"] == session_key
    assert [message["content"][0]["text"] for message in first_body["items"]] == [
        "second message",
        "third message",
    ]
    assert [message["__openclaw"]["seq"] for message in first_body["messages"]] == [2, 3]
    assert first_body["hasMore"] is True
    assert first_body["nextCursor"] == "2"

    assert second_response.status_code == 200
    second_body = second_response.json()
    assert [message["content"][0]["text"] for message in second_body["items"]] == [
        "first message"
    ]
    assert [message["__openclaw"]["seq"] for message in second_body["messages"]] == [1]
    assert second_body["hasMore"] is False
    assert "nextCursor" not in second_body


def test_gateway_session_history_rest_endpoint_reports_unknown_session() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-missing-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.get("/sessions/missing-session/history")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error": {
            "type": "not_found",
            "message": "Session not found: missing-session",
        },
    }


def test_gateway_session_history_rest_endpoint_streams_initial_sse_history() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-sse-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = "openzues:thread:sse"

    asyncio.run(app.state.database.initialize())
    asyncio.run(
        app.state.database.append_control_chat_message(
            role="assistant",
            content="streamed initial history",
            session_key=session_key,
        )
    )

    base_url, server, thread = _start_test_server(app)
    try:
        encoded_key = quote(session_key, safe="")
        timeout = httpx.Timeout(5.0, read=5.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "GET",
                f"{base_url}/sessions/{encoded_key}/history",
                headers={"accept": "text/event-stream"},
            ) as stream:
                assert stream.status_code == 200
                assert stream.headers["content-type"].startswith("text/event-stream")
                payload = _read_sse_payload(stream.iter_lines(), "history")
    finally:
        _stop_test_server(server, thread)

    assert payload["sessionKey"] == session_key
    assert payload["messages"][0]["content"][0]["text"] == "streamed initial history"


def test_gateway_session_history_rest_endpoint_streams_live_message_updates() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-live-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    app.state.control_plane_role = "leader"
    app.state.control_plane_owner_pid = None
    session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        ),
        thread_id="thread-history-live-sse-api",
    ).session_key
    asyncio.run(app.state.database.initialize())
    asyncio.run(
        app.state.database.create_mission(
            name="Gateway History SSE Loop",
            objective="Prove live session history streaming.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-history-live-sse-api",
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
    asyncio.run(
        app.state.database.append_control_chat_message(
            role="assistant",
            content="opening streamed history",
            session_key=session_key,
        )
    )

    base_url, server, thread = _start_test_server(app)
    app.state.control_plane_role = "leader"
    app.state.control_plane_owner_pid = None
    encoded_key = quote(session_key, safe="")
    try:
        timeout = httpx.Timeout(5.0, read=5.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "GET",
                f"{base_url}/sessions/{encoded_key}/history",
                headers={"accept": "text/event-stream"},
            ) as stream:
                assert stream.status_code == 200
                lines = stream.iter_lines()
                history_payload = _read_sse_payload(lines, "history")
                assert history_payload["sessionKey"] == session_key
                assert history_payload["messages"][0]["content"][0]["text"] == (
                    "opening streamed history"
                )

                inject_response = client.post(
                    f"{base_url}/api/gateway/node-methods/call",
                    json={
                        "method": "chat.inject",
                        "params": {
                            "sessionKey": session_key,
                            "message": "live streamed update",
                            "label": "History Stream",
                        },
                    },
                )
                assert inject_response.status_code == 200

                message_payload = _read_sse_payload(lines, "message")
    finally:
        _stop_test_server(server, thread)

    assert message_payload == {
        "sessionKey": session_key,
        "message": {
            "id": "2",
            "role": "assistant",
            "content": [{"type": "text", "text": "live streamed update"}],
            "__openclaw": {"id": "2", "seq": 2},
        },
        "messageId": "2",
        "messageSeq": 2,
    }


def test_gateway_session_history_rest_endpoint_streams_bounded_history_refresh() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-refresh-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        ),
        thread_id="thread-history-refresh-sse-api",
    ).session_key
    asyncio.run(app.state.database.initialize())
    asyncio.run(
        app.state.database.create_mission(
            name="Gateway History SSE Refresh Loop",
            objective="Prove bounded session history refresh streaming.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-history-refresh-sse-api",
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
    asyncio.run(
        app.state.database.append_control_chat_message(
            role="assistant",
            content="bounded opening history",
            session_key=session_key,
        )
    )

    base_url, server, thread = _start_test_server(app)
    app.state.control_plane_role = "leader"
    app.state.control_plane_owner_pid = None
    encoded_key = quote(session_key, safe="")
    try:
        timeout = httpx.Timeout(5.0, read=5.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "GET",
                f"{base_url}/sessions/{encoded_key}/history?limit=1",
                headers={"accept": "text/event-stream"},
            ) as stream:
                assert stream.status_code == 200
                lines = stream.iter_lines()
                opening_payload = _read_sse_payload(lines, "history")
                assert opening_payload["messages"][0]["content"][0]["text"] == (
                    "bounded opening history"
                )

                inject_response = client.post(
                    f"{base_url}/api/gateway/node-methods/call",
                    json={
                        "method": "chat.inject",
                        "params": {
                            "sessionKey": session_key,
                            "message": "bounded live refresh",
                            "label": "History Refresh",
                        },
                    },
                )
                assert inject_response.status_code == 200

                refresh_payload = _read_sse_payload(lines, "history")
    finally:
        _stop_test_server(server, thread)

    assert refresh_payload["sessionKey"] == session_key
    assert [message["content"][0]["text"] for message in refresh_payload["messages"]] == [
        "bounded live refresh"
    ]
    assert refresh_payload["hasMore"] is True
    assert refresh_payload["nextCursor"] == "2"


def test_gateway_session_history_rest_endpoint_refreshes_sse_on_session_change() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-change-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        ),
        thread_id="thread-history-change-sse-api",
    ).session_key
    asyncio.run(app.state.database.initialize())
    asyncio.run(
        app.state.database.create_mission(
            name="Gateway History SSE Change Loop",
            objective="Prove non-message session updates refresh history streams.",
            status="active",
            instance_id=7,
            project_id=None,
            thread_id="thread-history-change-sse-api",
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
    asyncio.run(
        app.state.database.append_control_chat_message(
            role="assistant",
            content="change opening history",
            session_key=session_key,
        )
    )

    base_url, server, thread = _start_test_server(app)
    app.state.control_plane_role = "leader"
    app.state.control_plane_owner_pid = None
    encoded_key = quote(session_key, safe="")
    try:
        timeout = httpx.Timeout(5.0, read=5.0)
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "GET",
                f"{base_url}/sessions/{encoded_key}/history",
                headers={"accept": "text/event-stream"},
            ) as stream:
                assert stream.status_code == 200
                lines = stream.iter_lines()
                opening_payload = _read_sse_payload(lines, "history")
                assert opening_payload["messages"][0]["content"][0]["text"] == (
                    "change opening history"
                )

                patch_response = client.post(
                    f"{base_url}/api/gateway/node-methods/call",
                    json={
                        "method": "sessions.patch",
                        "params": {"key": session_key, "label": "Renamed History"},
                    },
                )
                assert patch_response.status_code == 200

                refresh_payload = _read_sse_payload(lines, "history")
    finally:
        _stop_test_server(server, thread)

    assert refresh_payload["sessionKey"] == session_key
    assert [message["content"][0]["text"] for message in refresh_payload["messages"]] == [
        "change opening history"
    ]


def test_gateway_session_history_rest_endpoint_applies_default_text_cap() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-cap-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = "openzues:thread:rest-cap"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        asyncio.run(
            client.app.state.database.append_control_chat_message(
                role="assistant",
                content="a" * 12_005,
                session_key=session_key,
            )
        )

        encoded_key = quote(session_key, safe="")
        response = client.get(f"/sessions/{encoded_key}/history")

    assert response.status_code == 200
    body = response.json()
    assert body["hasMore"] is False
    assert body["messages"][0]["__openclaw"]["seq"] == 1
    assert body["messages"][0]["content"][0]["text"] == f'{"a" * 12_000}\n...(truncated)...'


def test_gateway_session_history_rest_endpoint_ignores_invalid_cursor() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-session-history-rest-cursor-api"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    session_key = "openzues:thread:rest-cursor"

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        for content in ("first message", "second message"):
            asyncio.run(
                client.app.state.database.append_control_chat_message(
                    role="assistant",
                    content=content,
                    session_key=session_key,
                )
            )

        encoded_key = quote(session_key, safe="")
        response = client.get(f"/sessions/{encoded_key}/history?limit=1&cursor=nope")

    assert response.status_code == 200
    body = response.json()
    assert [message["content"][0]["text"] for message in body["items"]] == ["second message"]
    assert body["hasMore"] is True
    assert body["nextCursor"] == "2"


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
                "params": {"key": "launch:mode:workspace_affinity"},
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


def test_gateway_node_method_call_endpoint_rejects_global_session_spawned_by_filter() -> None:
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
                "params": {
                    "key": current_session_key,
                    "spawnedBy": "parity-conductor",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "unknown session key"


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
                "params": {
                    "key": thread_session_key,
                    "spawnedBy": "parity-conductor",
                },
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


def test_gateway_node_method_call_endpoint_supports_config_open_file(
    tmp_path, monkeypatch
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    opened_paths: list[Path] = []

    def fake_open_path(path: Path) -> None:
        opened_paths.append(path)

    monkeypatch.setattr(
        "openzues.services.gateway_config._open_gateway_config_path",
        fake_open_path,
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.openFile", "params": {}},
        )

    expected_path = tmp_path / "data" / "settings" / "control-ui-config.json"
    assert response.status_code == 200
    assert response.json() == {"ok": True, "path": str(expected_path)}
    assert opened_paths == [expected_path]
    snapshot = json.loads(expected_path.read_text(encoding="utf-8"))
    assert snapshot["assistantName"] == "OpenZues"
    assert snapshot["assistantAgentId"] == "openzues"
    assert snapshot["assistantAvatar"] == "/static/favicon.svg"
    assert snapshot["basePath"] == ""
    assert snapshot["embedSandbox"] == "scripts"
    assert snapshot["localMediaPreviewRoots"] == []
    assert snapshot["allowExternalEmbedUrls"] is False
    assert isinstance(snapshot["serverVersion"], str)
    assert snapshot["serverVersion"]


def test_gateway_node_method_call_endpoint_returns_generic_error_when_config_open_command_fails(
    tmp_path, monkeypatch
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )

    def fake_open_path(_path: Path) -> None:
        raise subprocess.CalledProcessError(1, ["xdg-open"])

    monkeypatch.setattr(
        "openzues.services.gateway_config._open_gateway_config_path",
        fake_open_path,
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.openFile", "params": {}},
        )

    expected_path = tmp_path / "data" / "settings" / "control-ui-config.json"
    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "path": str(expected_path),
        "error": "failed to open config file",
    }
    assert expected_path.exists()


def test_gateway_node_method_call_endpoint_supports_config_write_lifecycle(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    raw_snapshot = json.dumps(
        {
            "basePath": "/gateway",
            "assistantName": "API Parity Builder",
            "assistantAvatar": "/static/parity.svg",
            "assistantAgentId": "openzues",
            "serverVersion": "9.9.9",
            "localMediaPreviewRoots": [],
            "embedSandbox": "scripts",
            "allowExternalEmbedUrls": False,
        }
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.set", "params": {"raw": raw_snapshot}},
        )
        patch_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "config.patch",
                "params": {
                    "raw": "{\"assistantName\":\"API Patched Builder\"}",
                    "baseHash": set_response.json()["hash"],
                    "sessionKey": "agent:main:thread:demo",
                    "note": "Patch the bounded config seam.",
                    "restartDelayMs": 0,
                },
            },
        )
        applied_raw = json.dumps(
            {
                **patch_response.json()["config"],
                "allowExternalEmbedUrls": True,
            }
        )
        apply_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "config.apply",
                "params": {
                    "raw": applied_raw,
                    "baseHash": patch_response.json()["hash"],
                    "sessionKey": "agent:main:thread:demo",
                    "note": "Apply the bounded config seam.",
                    "restartDelayMs": 0,
                },
            },
        )
        get_response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "config.get", "params": {}},
        )

    assert set_response.status_code == 200
    assert patch_response.status_code == 200
    assert apply_response.status_code == 200
    assert set_response.json()["config"]["assistantName"] == "API Parity Builder"
    assert patch_response.json()["config"]["assistantName"] == "API Patched Builder"
    assert apply_response.json()["config"]["allowExternalEmbedUrls"] is True
    assert apply_response.json()["restart"] is None
    assert apply_response.json()["sentinel"] is None
    assert get_response.json() == apply_response.json()["config"]


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
    assert any(command["name"] == "agents.list" for command in payload["commands"])
    assert any(command["name"] == "channels.status" for command in payload["commands"])
    assert any(command["name"] == "browser.act" for command in payload["commands"])
    assert any(command["name"] == "browser.auth.delete" for command in payload["commands"])
    assert any(command["name"] == "browser.auth.list" for command in payload["commands"])
    assert any(command["name"] == "browser.auth.login" for command in payload["commands"])
    assert any(command["name"] == "browser.auth.save" for command in payload["commands"])
    assert any(command["name"] == "browser.auth.show" for command in payload["commands"])
    assert any(command["name"] == "browser.batch" for command in payload["commands"])
    assert any(command["name"] == "browser.back" for command in payload["commands"])
    assert any(command["name"] == "browser.chat" for command in payload["commands"])
    assert any(command["name"] == "browser.clipboard.copy" for command in payload["commands"])
    assert any(command["name"] == "browser.clipboard.paste" for command in payload["commands"])
    assert any(command["name"] == "browser.clipboard.read" for command in payload["commands"])
    assert any(command["name"] == "browser.clipboard.write" for command in payload["commands"])
    assert any(command["name"] == "browser.close" for command in payload["commands"])
    assert any(command["name"] == "browser.confirm" for command in payload["commands"])
    assert any(command["name"] == "browser.cookies.clear" for command in payload["commands"])
    assert any(command["name"] == "browser.cookies.get" for command in payload["commands"])
    assert any(command["name"] == "browser.cookies.set" for command in payload["commands"])
    assert any(command["name"] == "browser.dashboard.start" for command in payload["commands"])
    assert any(command["name"] == "browser.dashboard.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.diff.snapshot" for command in payload["commands"])
    assert any(command["name"] == "browser.diff.screenshot" for command in payload["commands"])
    assert any(command["name"] == "browser.diff.url" for command in payload["commands"])
    assert any(command["name"] == "browser.deny" for command in payload["commands"])
    assert any(command["name"] == "browser.download" for command in payload["commands"])
    assert any(command["name"] == "browser.focus" for command in payload["commands"])
    assert any(command["name"] == "browser.forward" for command in payload["commands"])
    assert any(command["name"] == "browser.get" for command in payload["commands"])
    assert any(command["name"] == "browser.highlight" for command in payload["commands"])
    assert any(command["name"] == "browser.inspect" for command in payload["commands"])
    assert any(command["name"] == "browser.ios.device.list" for command in payload["commands"])
    assert any(command["name"] == "browser.ios.swipe" for command in payload["commands"])
    assert any(command["name"] == "browser.ios.tap" for command in payload["commands"])
    assert any(command["name"] == "browser.is" for command in payload["commands"])
    assert any(command["name"] == "browser.upload" for command in payload["commands"])
    assert any(command["name"] == "browser.profiler.start" for command in payload["commands"])
    assert any(command["name"] == "browser.profiler.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.record.restart" for command in payload["commands"])
    assert any(command["name"] == "browser.record.start" for command in payload["commands"])
    assert any(command["name"] == "browser.record.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.trace.start" for command in payload["commands"])
    assert any(command["name"] == "browser.trace.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.navigate" for command in payload["commands"])
    assert any(command["name"] == "browser.network.har.start" for command in payload["commands"])
    assert any(command["name"] == "browser.network.har.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.network.request" for command in payload["commands"])
    assert any(command["name"] == "browser.network.requests" for command in payload["commands"])
    assert any(command["name"] == "browser.open" for command in payload["commands"])
    assert any(command["name"] == "browser.pdf" for command in payload["commands"])
    assert any(command["name"] == "browser.profiles" for command in payload["commands"])
    assert any(command["name"] == "browser.reload" for command in payload["commands"])
    assert any(command["name"] == "browser.screenshot" for command in payload["commands"])
    assert any(command["name"] == "browser.set" for command in payload["commands"])
    assert any(command["name"] == "browser.session.current" for command in payload["commands"])
    assert any(command["name"] == "browser.session.list" for command in payload["commands"])
    assert any(command["name"] == "browser.start" for command in payload["commands"])
    assert any(command["name"] == "browser.stop" for command in payload["commands"])
    assert any(command["name"] == "browser.storage.clear" for command in payload["commands"])
    assert any(command["name"] == "browser.storage.get" for command in payload["commands"])
    assert any(command["name"] == "browser.storage.set" for command in payload["commands"])
    assert any(command["name"] == "browser.stream.disable" for command in payload["commands"])
    assert any(command["name"] == "browser.stream.enable" for command in payload["commands"])
    assert any(command["name"] == "browser.stream.status" for command in payload["commands"])
    assert any(command["name"] == "browser.tabs" for command in payload["commands"])


def test_gateway_node_method_call_endpoint_runs_browser_open_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def open_page(self, target: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "url": target, "session": session}

        def snapshot(self, *, session: str) -> dict[str, object]:
            raise AssertionError("snapshot should not be called")

        def console(self, *, session: str) -> dict[str, object]:
            raise AssertionError("console should not be called")

        def errors(self, *, session: str) -> dict[str, object]:
            raise AssertionError("errors should not be called")

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.open",
                "params": {
                    "target": "http://127.0.0.1:8884",
                    "session": "parity-browser",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "url": "http://127.0.0.1:8884",
        "session": "parity-browser",
    }


def test_gateway_node_method_call_endpoint_runs_browser_navigate_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def navigate(self, target: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "url": target, "session": session}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.navigate",
                "params": {
                    "url": "http://127.0.0.1:8884/dashboard",
                    "session": "parity-browser",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "url": "http://127.0.0.1:8884/dashboard",
        "session": "parity-browser",
    }


def test_gateway_node_method_call_endpoint_runs_browser_close_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def close(
            self,
            *,
            session: str,
            all_sessions: bool = False,
            target_id: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "allSessions": all_sessions,
                "targetId": target_id,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.close",
                "params": {"session": "parity-browser", "all": True},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "allSessions": True,
        "targetId": None,
    }


def test_gateway_node_method_call_endpoint_runs_browser_focus_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def focus(self, target_id: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "targetId": target_id}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.focus",
                "params": {"session": "parity-browser", "targetId": "2"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "session": "parity-browser", "targetId": "2"}


def test_gateway_node_method_call_endpoint_runs_browser_confirmation_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def confirm(self, action_id: str, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "actionId": action_id,
                "decision": "confirm",
            }

        def deny(self, action_id: str, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "actionId": action_id,
                "decision": "deny",
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        confirm_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.confirm",
                "params": {"session": "parity-browser", "id": "pending-123"},
            },
        )
        deny_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.deny",
                "params": {"session": "parity-browser", "id": "pending-456"},
            },
        )

    assert confirm_response.status_code == 200
    assert confirm_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "actionId": "pending-123",
        "decision": "confirm",
    }
    assert deny_response.status_code == 200
    assert deny_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "actionId": "pending-456",
        "decision": "deny",
    }


def test_gateway_node_method_call_endpoint_runs_browser_lifecycle_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def start(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "status": "ready"}

        def stop(self, *, session: str, all_sessions: bool = False) -> dict[str, object]:
            return {"ok": True, "session": session, "allSessions": all_sessions}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.start",
                "params": {"session": "parity-browser"},
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.stop",
                "params": {"session": "parity-browser", "all": True},
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "status": "ready",
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "allSessions": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_get_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def get(
            self,
            what: str,
            *,
            session: str,
            selector: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "what": what,
                "selector": selector,
                "value": "Zeus",
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.get",
                "params": {
                    "session": "parity-browser",
                    "what": "text",
                    "selector": "body",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "what": "text",
        "selector": "body",
        "value": "Zeus",
    }


def test_gateway_node_method_call_endpoint_runs_browser_is_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def is_state(self, state: str, selector: str, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "state": state,
                "selector": selector,
                "matched": True,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.is",
                "params": {
                    "session": "parity-browser",
                    "state": "visible",
                    "selector": "body",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "state": "visible",
        "selector": "body",
        "matched": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_history_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def history(self, action: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "action": action}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.reload",
                "params": {"session": "parity-browser"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "action": "reload",
    }


def test_gateway_node_method_call_endpoint_runs_browser_set_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def set_setting(
            self,
            setting: str,
            values: list[str],
            *,
            session: str,
        ) -> dict[str, object]:
            return {"ok": True, "session": session, "setting": setting, "values": values}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.set",
                "params": {
                    "session": "parity-browser",
                    "setting": "media",
                    "values": ["dark", "reduced-motion"],
                },
            },
        )
        headers_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.set",
                "params": {
                    "session": "parity-browser",
                    "setting": "headers",
                    "values": ['{"Authorization":"Bearer token","X-Test":"yes"}'],
                },
            },
        )
        credentials_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.set",
                "params": {
                    "session": "parity-browser",
                    "setting": "credentials",
                    "values": ["admin", "secret-token"],
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "setting": "media",
        "values": ["dark", "reduced-motion"],
    }
    assert headers_response.status_code == 200
    assert headers_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "setting": "headers",
        "values": ['{"Authorization":"Bearer token","X-Test":"yes"}'],
    }
    assert credentials_response.status_code == 200
    assert credentials_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "setting": "credentials",
        "values": ["admin", "secret-token"],
    }


def test_gateway_node_method_call_endpoint_runs_browser_batch_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def batch(
            self,
            commands: list[str],
            *,
            session: str,
            bail: bool = False,
        ) -> dict[str, object]:
            return {"ok": True, "session": session, "commandCount": len(commands), "bail": bail}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.batch",
                "params": {
                    "session": "parity-browser",
                    "commands": ["open https://example.com", "snapshot -i"],
                    "bail": True,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "commandCount": 2,
        "bail": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_dashboard_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def dashboard_start(
            self,
            *,
            session: str,
            port: int | None = None,
        ) -> dict[str, object]:
            return {"ok": True, "session": session, "dashboardRunning": True, "port": port}

        def dashboard_stop(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "dashboardRunning": False}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.dashboard.start",
                "params": {"session": "parity-browser", "port": 4849},
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.dashboard.stop",
                "params": {"session": "parity-browser"},
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "dashboardRunning": True,
        "port": 4849,
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "dashboardRunning": False,
    }


def test_gateway_node_method_call_endpoint_runs_browser_chat_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def chat(
            self,
            message: str,
            *,
            session: str,
            model: str | None = None,
            quiet: bool = False,
            verbose: bool = False,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "message": message,
                "model": model,
                "quiet": quiet,
                "verbose": verbose,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.chat",
                "params": {
                    "session": "parity-browser",
                    "message": "summarize the current page",
                    "model": "openai/gpt-4o",
                    "quiet": True,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "message": "summarize the current page",
        "model": "openai/gpt-4o",
        "quiet": True,
        "verbose": False,
    }


def test_gateway_node_method_call_endpoint_runs_browser_ios_provider_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def ios_device_list(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "deviceCount": 1}

        def ios_swipe(
            self,
            direction: str,
            *,
            session: str,
            distance: int | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "direction": direction,
                "distance": distance,
            }

        def ios_tap(self, target: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "target": target}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        devices_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.ios.device.list",
                "params": {"session": "parity-browser"},
            },
        )
        swipe_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.ios.swipe",
                "params": {"session": "parity-browser", "direction": "up", "distance": 500},
            },
        )
        tap_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.ios.tap",
                "params": {"session": "parity-browser", "target": "@e1"},
            },
        )

    assert devices_response.status_code == 200
    assert devices_response.json() == {"ok": True, "session": "parity-browser", "deviceCount": 1}
    assert swipe_response.status_code == 200
    assert swipe_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "direction": "up",
        "distance": 500,
    }
    assert tap_response.status_code == 200
    assert tap_response.json() == {"ok": True, "session": "parity-browser", "target": "@e1"}


def test_gateway_node_method_call_endpoint_runs_browser_stream_status_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def stream_status(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "streaming": False}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.stream.status",
                "params": {"session": "parity-browser"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "session": "parity-browser", "streaming": False}


def test_gateway_node_method_call_endpoint_runs_browser_stream_lifecycle_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def stream_enable(self, *, session: str, port: int | None = None) -> dict[str, object]:
            return {"ok": True, "session": session, "streaming": True, "port": port}

        def stream_disable(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "streaming": False}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        enable_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.stream.enable",
                "params": {"session": "parity-browser", "port": 9223},
            },
        )
        disable_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.stream.disable",
                "params": {"session": "parity-browser"},
            },
        )

    assert enable_response.status_code == 200
    assert enable_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "streaming": True,
        "port": 9223,
    }
    assert disable_response.status_code == 200
    assert disable_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "streaming": False,
    }


def test_gateway_node_method_call_endpoint_runs_browser_network_requests_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def network_requests(
            self,
            *,
            session: str,
            filter_pattern: str | None = None,
            resource_type: str | None = None,
            method: str | None = None,
            status: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "filter": filter_pattern,
                "type": resource_type,
                "method": method,
                "statusFilter": status,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.network.requests",
                "params": {
                    "session": "parity-browser",
                    "filter": "api",
                    "type": "fetch,xhr",
                    "method": "POST",
                    "status": "2xx",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "filter": "api",
        "type": "fetch,xhr",
        "method": "POST",
        "statusFilter": "2xx",
    }


def test_gateway_node_method_call_endpoint_runs_browser_network_request_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def network_request(self, request_id: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "requestId": request_id}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.network.request",
                "params": {"session": "parity-browser", "requestId": "1234.5"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "requestId": "1234.5",
    }


def test_gateway_node_method_call_endpoint_runs_browser_storage_inventory_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def cookies_get(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "cookieCount": 1}

        def storage_get(
            self,
            storage_type: str,
            *,
            session: str,
            key: str | None = None,
        ) -> dict[str, object]:
            return {"ok": True, "session": session, "type": storage_type, "key": key}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        cookies_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.cookies.get",
                "params": {"session": "parity-browser"},
            },
        )
        storage_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.storage.get",
                "params": {"session": "parity-browser", "type": "local", "key": "theme"},
            },
        )

    assert cookies_response.status_code == 200
    assert cookies_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "cookieCount": 1,
    }
    assert storage_response.status_code == 200
    assert storage_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "type": "local",
        "key": "theme",
    }


def test_gateway_node_method_call_endpoint_runs_browser_cookie_mutation_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def cookies_set(
            self,
            name: str,
            value: str,
            *,
            session: str,
            url: str | None = None,
            domain: str | None = None,
            path: str | None = None,
            http_only: bool | None = None,
            secure: bool | None = None,
            same_site: str | None = None,
            expires: int | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "name": name,
                "value": value,
                "url": url,
                "domain": domain,
                "path": path,
                "httpOnly": http_only,
                "secure": secure,
                "sameSite": same_site,
                "expires": expires,
            }

        def cookies_clear(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "operation": "clear"}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.cookies.set",
                "params": {
                    "session": "parity-browser",
                    "name": "session_id",
                    "value": "abc123",
                    "url": "https://app.example.test",
                    "path": "/app",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Strict",
                    "expires": 1_735_689_600,
                },
            },
        )
        clear_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.cookies.clear",
                "params": {"session": "parity-browser"},
            },
        )

    assert set_response.status_code == 200
    assert set_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "name": "session_id",
        "value": "abc123",
        "url": "https://app.example.test",
        "domain": None,
        "path": "/app",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Strict",
        "expires": 1_735_689_600,
    }
    assert clear_response.status_code == 200
    assert clear_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "operation": "clear",
    }


def test_gateway_node_method_call_endpoint_runs_browser_storage_mutation_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def storage_set(
            self,
            storage_type: str,
            key: str,
            value: str,
            *,
            session: str,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "type": storage_type,
                "key": key,
                "value": value,
            }

        def storage_clear(
            self,
            storage_type: str,
            *,
            session: str,
        ) -> dict[str, object]:
            return {"ok": True, "session": session, "type": storage_type}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        set_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.storage.set",
                "params": {
                    "session": "parity-browser",
                    "type": "local",
                    "key": "theme",
                    "value": "dark",
                },
            },
        )
        clear_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.storage.clear",
                "params": {"session": "parity-browser", "type": "session"},
            },
        )

    assert set_response.status_code == 200
    assert set_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "type": "local",
        "key": "theme",
        "value": "dark",
    }
    assert clear_response.status_code == 200
    assert clear_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "type": "session",
    }


def test_gateway_node_method_call_endpoint_runs_browser_session_inventory_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def session_current(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "currentSession": session}

        def session_list(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "sessionCount": 1}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        current_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.session.current",
                "params": {"session": "parity-browser"},
            },
        )
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.session.list",
                "params": {"session": "parity-browser"},
            },
        )

    assert current_response.status_code == 200
    assert current_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "currentSession": "parity-browser",
    }
    assert list_response.status_code == 200
    assert list_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "sessionCount": 1,
    }


def test_gateway_node_method_call_endpoint_runs_browser_diff_snapshot_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def diff_snapshot(
            self,
            *,
            session: str,
            selector: str | None = None,
            compact: bool = False,
            depth: int | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "selector": selector,
                "compact": compact,
                "depth": depth,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.diff.snapshot",
                "params": {
                    "session": "parity-browser",
                    "selector": "#app",
                    "compact": True,
                    "depth": 3,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "selector": "#app",
        "compact": True,
        "depth": 3,
    }


def test_gateway_node_method_call_endpoint_runs_browser_diff_url_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def diff_url(
            self,
            url1: str,
            url2: str,
            *,
            session: str,
            screenshot: bool = False,
            full_page: bool = False,
            wait_until: str | None = None,
            selector: str | None = None,
            compact: bool = False,
            depth: int | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "url1": url1,
                "url2": url2,
                "screenshot": screenshot,
                "fullPage": full_page,
                "waitUntil": wait_until,
                "selector": selector,
                "compact": compact,
                "depth": depth,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.diff.url",
                "params": {
                    "session": "parity-browser",
                    "url1": "http://127.0.0.1:8884/before",
                    "url2": "http://127.0.0.1:8884/after",
                    "screenshot": True,
                    "fullPage": True,
                    "waitUntil": "networkidle",
                    "selector": "#app",
                    "compact": True,
                    "depth": 3,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "url1": "http://127.0.0.1:8884/before",
        "url2": "http://127.0.0.1:8884/after",
        "screenshot": True,
        "fullPage": True,
        "waitUntil": "networkidle",
        "selector": "#app",
        "compact": True,
        "depth": 3,
    }


def test_gateway_node_method_call_endpoint_runs_browser_diff_screenshot_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def diff_screenshot(
            self,
            *,
            session: str,
            baseline_path: str,
            threshold: float | None = None,
            selector: str | None = None,
            full_page: bool = False,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "baselinePath": baseline_path,
                "threshold": threshold,
                "selector": selector,
                "fullPage": full_page,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.diff.screenshot",
                "params": {
                    "session": "parity-browser",
                    "baselinePath": "C:/Temp/openzues-browser-parity-baseline.png",
                    "threshold": 0.2,
                    "selector": "#app",
                    "fullPage": True,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "baselinePath": "C:/Temp/openzues-browser-parity-baseline.png",
        "threshold": 0.2,
        "selector": "#app",
        "fullPage": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_download_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def download(
            self,
            selector: str,
            *,
            session: str,
            filename_hint: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "selector": selector,
                "filenameHint": filename_hint,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.download",
                "params": {
                    "session": "parity-browser",
                    "selector": "@e4",
                    "filenameHint": "report.csv",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "selector": "@e4",
        "filenameHint": "report.csv",
    }


def test_gateway_node_method_call_endpoint_runs_browser_upload_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def upload(
            self,
            selector: str,
            file_paths: list[str],
            *,
            session: str,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "selector": selector,
                "files": file_paths,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.upload",
                "params": {
                    "session": "parity-browser",
                    "selector": "@e5",
                    "filePaths": ["C:/Temp/openzues-browser-upload-seed.txt"],
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "selector": "@e5",
        "files": ["C:/Temp/openzues-browser-upload-seed.txt"],
    }


def test_gateway_node_method_call_endpoint_runs_browser_trace_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def trace_start(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "traceRecording": True}

        def trace_stop(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "traceRecording": False,
                "path": "C:/Temp/openzues-browser-trace-parity-browser.zip",
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.trace.start",
                "params": {"session": "parity-browser"},
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.trace.stop",
                "params": {"session": "parity-browser"},
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "traceRecording": True,
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "traceRecording": False,
        "path": "C:/Temp/openzues-browser-trace-parity-browser.zip",
    }


def test_gateway_node_method_call_endpoint_runs_browser_network_har_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def network_har_start(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "harRecording": True}

        def network_har_stop(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "harRecording": False,
                "path": "C:/Temp/openzues-browser-har-parity-browser.har",
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.network.har.start",
                "params": {"session": "parity-browser"},
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.network.har.stop",
                "params": {"session": "parity-browser"},
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "harRecording": True,
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "harRecording": False,
        "path": "C:/Temp/openzues-browser-har-parity-browser.har",
    }


def test_gateway_node_method_call_endpoint_runs_browser_profiler_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def profiler_start(
            self,
            *,
            session: str,
            categories: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "categories": categories,
                "profilerRecording": True,
            }

        def profiler_stop(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "profilerRecording": False,
                "path": "C:/Temp/openzues-browser-profiler-parity-browser.json",
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.profiler.start",
                "params": {
                    "session": "parity-browser",
                    "categories": "devtools.timeline,v8.execute",
                },
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.profiler.stop",
                "params": {"session": "parity-browser"},
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "categories": "devtools.timeline,v8.execute",
        "profilerRecording": True,
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "profilerRecording": False,
        "path": "C:/Temp/openzues-browser-profiler-parity-browser.json",
    }


def test_gateway_node_method_call_endpoint_runs_browser_record_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def record_start(
            self,
            *,
            session: str,
            url: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "url": url,
                "path": "C:/Temp/openzues-browser-recording-parity-browser.webm",
                "recording": True,
            }

        def record_stop(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "path": "C:/Temp/openzues-browser-recording-parity-browser.webm",
                "recording": False,
            }

        def record_restart(
            self,
            *,
            session: str,
            url: str | None = None,
        ) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "url": url,
                "path": "C:/Temp/openzues-browser-recording-parity-browser-restart.webm",
                "recording": True,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        start_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.record.start",
                "params": {
                    "session": "parity-browser",
                    "url": "http://127.0.0.1:8884",
                },
            },
        )
        stop_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.record.stop",
                "params": {"session": "parity-browser"},
            },
        )
        restart_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.record.restart",
                "params": {
                    "session": "parity-browser",
                    "url": "http://127.0.0.1:8884/again",
                },
            },
        )

    assert start_response.status_code == 200
    assert start_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "url": "http://127.0.0.1:8884",
        "path": "C:/Temp/openzues-browser-recording-parity-browser.webm",
        "recording": True,
    }
    assert stop_response.status_code == 200
    assert stop_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "path": "C:/Temp/openzues-browser-recording-parity-browser.webm",
        "recording": False,
    }
    assert restart_response.status_code == 200
    assert restart_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "url": "http://127.0.0.1:8884/again",
        "path": "C:/Temp/openzues-browser-recording-parity-browser-restart.webm",
        "recording": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_debug_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def highlight(self, selector: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "selector": selector}

        def inspect(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "inspectorOpen": True}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        highlight_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.highlight",
                "params": {"session": "parity-browser", "selector": "@e2"},
            },
        )
        inspect_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.inspect",
                "params": {"session": "parity-browser"},
            },
        )

    assert highlight_response.status_code == 200
    assert highlight_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "selector": "@e2",
    }
    assert inspect_response.status_code == 200
    assert inspect_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "inspectorOpen": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_auth_metadata_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def auth_list(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "profileCount": 1}

        def auth_show(self, name: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "name": name}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        list_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.auth.list",
                "params": {"session": "parity-browser"},
            },
        )
        show_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.auth.show",
                "params": {"session": "parity-browser", "name": "github"},
            },
        )

    assert list_response.status_code == 200
    assert list_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "profileCount": 1,
    }
    assert show_response.status_code == 200
    assert show_response.json() == {"ok": True, "session": "parity-browser", "name": "github"}


def test_gateway_node_method_call_endpoint_runs_browser_auth_profile_mutation_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def auth_login(self, name: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "name": name, "loggedIn": True}

        def auth_delete(self, name: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "name": name, "deleted": True}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        login_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.auth.login",
                "params": {"session": "parity-browser", "name": "github"},
            },
        )
        delete_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.auth.delete",
                "params": {"session": "parity-browser", "name": "github"},
            },
        )

    assert login_response.status_code == 200
    assert login_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "name": "github",
        "loggedIn": True,
    }
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "ok": True,
        "session": "parity-browser",
        "name": "github",
        "deleted": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_auth_profile_save_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def auth_save(
            self,
            name: str,
            *,
            session: str,
            url: str,
            username: str,
            password: str,
            username_selector: str | None = None,
            password_selector: str | None = None,
            submit_selector: str | None = None,
        ) -> dict[str, object]:
            assert password == "secret-token"
            return {
                "ok": True,
                "session": session,
                "name": name,
                "url": url,
                "username": username,
                "usernameSelector": username_selector,
                "passwordSelector": password_selector,
                "submitSelector": submit_selector,
                "saved": True,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.auth.save",
                "params": {
                    "session": "parity-browser",
                    "name": "github",
                    "url": "https://github.com/login",
                    "username": "octo",
                    "password": "secret-token",
                    "usernameSelector": "#login",
                    "passwordSelector": "#password",
                    "submitSelector": "button[type=submit]",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "name": "github",
        "url": "https://github.com/login",
        "username": "octo",
        "usernameSelector": "#login",
        "passwordSelector": "#password",
        "submitSelector": "button[type=submit]",
        "saved": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_clipboard_runtime(
    tmp_path,
) -> None:
    class FakeBrowserRuntime:
        def clipboard_read(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "text": "copied text"}

        def clipboard_write(self, text: str, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "text": text}

        def clipboard_copy(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "copied": True}

        def clipboard_paste(self, *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "pasted": True}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        read_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.clipboard.read",
                "params": {"session": "parity-browser"},
            },
        )
        write_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.clipboard.write",
                "params": {"session": "parity-browser", "text": "copied text"},
            },
        )
        copy_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.clipboard.copy",
                "params": {"session": "parity-browser"},
            },
        )
        paste_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.clipboard.paste",
                "params": {"session": "parity-browser"},
            },
        )

    assert read_response.status_code == 200
    assert read_response.json() == {"ok": True, "session": "parity-browser", "text": "copied text"}
    assert write_response.status_code == 200
    assert write_response.json() == {"ok": True, "session": "parity-browser", "text": "copied text"}
    assert copy_response.status_code == 200
    assert copy_response.json() == {"ok": True, "session": "parity-browser", "copied": True}
    assert paste_response.status_code == 200
    assert paste_response.json() == {"ok": True, "session": "parity-browser", "pasted": True}


def test_gateway_node_method_call_endpoint_runs_browser_act_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def act(self, request: dict[str, object], *, session: str) -> dict[str, object]:
            return {"ok": True, "session": session, "kind": request["kind"]}

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.act",
                "params": {
                    "session": "parity-browser",
                    "request": {
                        "kind": "drag",
                        "source": "@card",
                        "destination": "@dropzone",
                    },
                },
            },
        )
        mouse_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.act",
                "params": {
                    "session": "parity-browser",
                    "request": {"kind": "mouse", "action": "move", "x": 15, "y": 30},
                },
            },
        )
        find_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.act",
                "params": {
                    "session": "parity-browser",
                    "request": {
                        "kind": "find",
                        "locator": "role",
                        "value": "button",
                        "action": "click",
                        "name": "Submit",
                        "exact": True,
                    },
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "session": "parity-browser", "kind": "drag"}
    assert mouse_response.status_code == 200
    assert mouse_response.json() == {"ok": True, "session": "parity-browser", "kind": "mouse"}
    assert find_response.status_code == 200
    assert find_response.json() == {"ok": True, "session": "parity-browser", "kind": "find"}


def test_gateway_node_method_call_endpoint_runs_browser_status_runtime(tmp_path) -> None:
    async def fake_status_service() -> dict[str, object]:
        return {
            "browser_posture": {
                "status": "ready",
                "headline": "Browser control is operator-ready",
            }
        }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            status_service=fake_status_service,
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "browser.status", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "headline": "Browser control is operator-ready",
    }


def test_gateway_node_method_call_endpoint_runs_browser_verify_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def verify(self, target: str, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "status": "ready",
                "summary": "url http://127.0.0.1:8884, content visible, no overlay.",
                "url": target,
                "session": session,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.verify",
                "params": {
                    "url": "http://127.0.0.1:8884",
                    "session": "parity-browser",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "status": "ready",
        "headline": "Browser verification passed",
        "summary": "url http://127.0.0.1:8884, content visible, no overlay.",
        "url": "http://127.0.0.1:8884",
        "session": "parity-browser",
    }


def test_gateway_node_method_call_endpoint_runs_browser_tabs_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def tabs(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "tabCount": 1,
                "tabs": [{"id": "tab-1", "url": "http://127.0.0.1:8884"}],
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.tabs",
                "params": {"session": "parity-browser"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "tabCount": 1,
        "tabs": [{"id": "tab-1", "url": "http://127.0.0.1:8884"}],
    }


def test_gateway_node_method_call_endpoint_runs_browser_profiles_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def profiles(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "profileCount": 1,
                "profiles": [{"name": "openzues", "status": "ready"}],
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.profiles",
                "params": {"session": "parity-browser"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "profileCount": 1,
        "profiles": [{"name": "openzues", "status": "ready"}],
    }


def test_gateway_node_method_call_endpoint_runs_browser_screenshot_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def screenshot(self, *, session: str, full_page: bool = False) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "path": "C:/tmp/openzues-browser.png",
                "fullPage": full_page,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.screenshot",
                "params": {"session": "parity-browser", "fullPage": True},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "path": "C:/tmp/openzues-browser.png",
        "fullPage": True,
    }


def test_gateway_node_method_call_endpoint_runs_browser_pdf_runtime(tmp_path) -> None:
    class FakeBrowserRuntime:
        def pdf(self, *, session: str) -> dict[str, object]:
            return {
                "ok": True,
                "session": session,
                "path": "C:/tmp/openzues-browser.pdf",
                "sizeBytes": 123,
            }

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(
        app_settings,
        gateway_node_method_service=GatewayNodeMethodService(
            GatewayNodeRegistry(),
            browser_runtime_service=FakeBrowserRuntime(),
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "browser.pdf",
                "params": {"session": "parity-browser"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session": "parity-browser",
        "path": "C:/tmp/openzues-browser.pdf",
        "sizeBytes": 123,
    }


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
    assert payload["channelOrder"] == ["discord", "slack", "telegram", "whatsapp"]
    assert payload["channelLabels"]["slack"] == "Slack"
    assert payload["channelDetailLabels"]["slack"] == "Slack"
    assert payload["channelMeta"][1] == {
        "id": "slack",
        "label": "Slack",
        "detailLabel": "Slack",
    }
    assert payload["channels"]["slack"] == {
        "routeCount": 1,
        "enabledRouteCount": 1,
        "conversationTargetCount": 1,
        "accountCount": 1,
    }
    assert payload["channelAccounts"]["slack"] == [
        {
            "accountId": "workspace-bot",
            "routeCount": 1,
            "enabledRouteCount": 1,
            "conversationTargetCount": 1,
        }
    ]
    assert payload["channelDefaultAccountId"]["slack"] == "workspace-bot"


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
    assert re.fullmatch(r"[0-9a-f]{64}", self_entry["deviceId"])
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


def test_secrets_reload_endpoint_counts_broken_secret_refs(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        vault_secret = client.post(
            "/api/vault-secrets",
            json={
                "label": "Healthy automation token",
                "kind": "token",
                "value": "super-secret-token",
                "notes": "Healthy shared credential.",
            },
        ).json()

        database = client.app.state.database
        asyncio.run(
            database.create_integration(
                name="Healthy GitHub",
                kind="github",
                project_id=None,
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=int(vault_secret["id"]),
                secret_label="GITHUB_TOKEN",
                secret_value=None,
                notes="Healthy ref.",
                enabled=True,
            )
        )
        asyncio.run(
            database.create_integration(
                name="Broken GitHub",
                kind="github",
                project_id=None,
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=999,
                secret_label="BROKEN_GITHUB_TOKEN",
                secret_value=None,
                notes="Broken ref.",
                enabled=True,
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Healthy Route",
                kind="webhook",
                target="https://example.invalid/healthy",
                events=["mission/completed"],
                enabled=True,
                secret_header_name="X-Healthy-Key",
                secret_token=None,
                vault_secret_id=int(vault_secret["id"]),
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Broken Route",
                kind="webhook",
                target="https://example.invalid/broken",
                events=["mission/completed"],
                enabled=True,
                secret_header_name="X-Broken-Key",
                secret_token=None,
                vault_secret_id=1000,
            )
        )

        response = client.post(
            "/api/gateway/node-methods/call",
            json={"method": "secrets.reload", "params": {}},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "warningCount": 2}


def test_secrets_resolve_endpoint_returns_validated_unavailable_contract(tmp_path) -> None:
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
                "method": "secrets.resolve",
                "params": {
                    "commandName": "memory status",
                    "targetIds": ["talk.providers.*.apiKey"],
                },
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "secrets.resolve is unavailable until command-target secret resolution is wired"
        )
    }


def test_message_action_endpoint_reports_unsupported_action_for_known_channel(
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
                "method": "message.action",
                "params": {
                    "channel": "whatsapp",
                    "action": "react",
                    "params": {
                        "chatJid": "+15551234567",
                        "messageId": "wamid.1",
                        "emoji": "✅",
                    },
                    "accountId": "default",
                    "requesterSenderId": "trusted-user",
                    "senderIsOwner": True,
                    "sessionKey": "agent:main:whatsapp:+15551234567",
                    "sessionId": "session-123",
                    "agentId": "main",
                    "toolContext": {
                        "currentChannelId": "channel:team:general",
                        "currentGraphChannelId": "graph:team/general",
                        "currentChannelProvider": "whatsapp",
                        "currentThreadTs": "1710000000.9999",
                        "currentMessageId": "wamid.1",
                        "replyToMode": "first",
                        "hasRepliedRef": {"value": True},
                        "skipCrossContextDecoration": True,
                    },
                    "idempotencyKey": "idem-message-action",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Channel whatsapp does not support action react."}


def test_message_action_endpoint_rejects_internal_webchat_channel(tmp_path) -> None:
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
                "method": "message.action",
                "params": {
                    "channel": "webchat",
                    "action": "react",
                    "params": {
                        "messageId": "webchat.1",
                        "emoji": "ok",
                    },
                    "idempotencyKey": "idem-message-action-webchat",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "unsupported channel: webchat (internal-only). Use `chat.send` for WebChat UI "
            "messages or choose a deliverable channel."
        )
    }


def test_message_action_endpoint_auto_picks_single_route_channel_when_omitted(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.create_notification_route(
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission/completed"],
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
                conversation_target={
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "message.action",
                "params": {
                    "action": "react",
                    "params": {
                        "messageId": "slack.1",
                        "emoji": "ok",
                    },
                    "idempotencyKey": "idem-message-action-autopick",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Channel slack does not support action react."}


@pytest.mark.parametrize(
    ("field", "extra_params"),
    [
        (
            "accountId",
            {"accountId": "   "},
        ),
        (
            "requesterSenderId",
            {"requesterSenderId": "   "},
        ),
        (
            "sessionKey",
            {"sessionKey": "   "},
        ),
        (
            "sessionId",
            {"sessionId": "   "},
        ),
        (
            "agentId",
            {"agentId": "   "},
        ),
    ],
)
def test_message_action_endpoint_allows_blank_optional_routing_identifiers(
    tmp_path,
    field: str,
    extra_params: dict[str, str],
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
                "method": "message.action",
                "params": {
                    "channel": "slack",
                    "action": "react",
                    "params": {
                        "messageId": "slack.1",
                        "emoji": "ok",
                    },
                    "idempotencyKey": f"idem-message-action-blank-{field}",
                    **extra_params,
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Channel slack does not support action react."}


def test_send_endpoint_delivers_channel_target_message_and_records_outbound_delivery(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "channel": "slack",
                    "accountId": "default",
                    "agentId": "main",
                    "threadId": "1710000000.9999",
                    "sessionKey": "agent:main:slack:channel:C123",
                    "idempotencyKey": "idem-send",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))
        messages = asyncio.run(
            database.list_control_chat_messages(limit=10, session_key=expected_session_key)
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": "idem-send",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert delivery is not None
    assert delivery["route_kind"] == "announce"
    assert delivery["event_type"] == "gateway/send"
    assert delivery["session_key"] == expected_session_key
    assert delivery["message_summary"] == "Ship parity."
    assert delivery["route_scope"]["source"] == "gateway.send"
    assert delivery["route_scope"]["source_session_key"] == "agent:main:slack:channel:C123"
    assert delivery["route_scope"]["thread_id"] == "1710000000.9999"
    assert len(messages) == 1
    assert messages[0]["id"] == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == "Ship parity."


def test_send_endpoint_reuses_idempotent_channel_target_delivery(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        first_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "idempotencyKey": "idem-send-retry",
                },
            },
        )
        second_response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "idempotencyKey": "idem-send-retry",
                },
            },
        )
        deliveries = asyncio.run(database.list_outbound_deliveries(limit=10))
        messages = asyncio.run(
            database.list_control_chat_messages(limit=10, session_key=expected_session_key)
        )

    expected_payload = {
        "ok": True,
        "runId": "idem-send-retry",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == expected_payload
    assert second_response.json() == expected_payload
    assert len(deliveries) == 1
    assert deliveries[0]["request_idempotency_key"] == "idem-send-retry"
    assert deliveries[0]["delivery_message_id"] == "1"
    assert len(messages) == 1
    assert messages[0]["id"] == 1
    assert messages[0]["content"] == "Ship parity."


def test_send_endpoint_delivers_channel_target_media_and_records_outbound_delivery(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "mediaUrl": " https://example.com/a.png ",
                    "mediaUrls": ["https://example.com/b.png", "https://example.com/a.png"],
                    "gifPlayback": True,
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "sessionKey": "agent:main:slack:channel:C123",
                    "idempotencyKey": "idem-send-media",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))
        messages = asyncio.run(
            database.list_control_chat_messages(limit=10, session_key=expected_session_key)
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": "idem-send-media",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert delivery is not None
    assert delivery["route_kind"] == "announce"
    assert delivery["event_type"] == "gateway/send"
    assert delivery["session_key"] == expected_session_key
    assert delivery["message_summary"] == "Media delivery (2 items)"
    assert delivery["route_scope"]["source"] == "gateway.send"
    assert delivery["route_scope"]["source_session_key"] == "agent:main:slack:channel:C123"
    assert delivery["route_scope"]["thread_id"] == "1710000000.9999"
    assert delivery["event_payload"]["mediaUrls"] == [
        "https://example.com/a.png",
        "https://example.com/b.png",
    ]
    assert delivery["event_payload"]["gifPlayback"] is True
    assert len(messages) == 1
    assert messages[0]["id"] == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == (
        "Media:\n"
        "1. https://example.com/a.png\n"
        "2. https://example.com/b.png\n\n"
        "Settings: gifPlayback=true"
    )


def test_send_endpoint_rejects_invalid_whatsapp_target_shape(tmp_path) -> None:
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
                "method": "send",
                "params": {
                    "to": "wat",
                    "message": "Ship parity.",
                    "channel": "whatsapp",
                    "idempotencyKey": "idem-send-whatsapp-invalid",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "WhatsApp target is required"}


def test_send_endpoint_rejects_blank_telegram_target_shape(tmp_path) -> None:
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
                "method": "send",
                "params": {
                    "to": "   ",
                    "message": "Ship parity.",
                    "channel": "telegram",
                    "idempotencyKey": "idem-send-telegram-blank",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Telegram target is required"}


@pytest.mark.parametrize(
    ("field", "extra_params"),
    [
        (
            "accountId",
            {"accountId": "   "},
        ),
        (
            "agentId",
            {"agentId": "   "},
        ),
        (
            "threadId",
            {"threadId": "   "},
        ),
        (
            "sessionKey",
            {"sessionKey": "   "},
        ),
    ],
)
def test_send_endpoint_allows_blank_optional_routing_identifiers(
    tmp_path,
    field: str,
    extra_params: dict[str, str],
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "channel": "slack",
                    "idempotencyKey": f"idem-send-blank-{field}",
                    **extra_params,
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": f"idem-send-blank-{field}",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "sessionKey": expected_session_key,
        },
    }


def test_send_endpoint_rejects_internal_webchat_channel(tmp_path) -> None:
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
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "channel": "webchat",
                    "idempotencyKey": "idem-send-webchat",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "unsupported channel: webchat (internal-only). Use `chat.send` for WebChat UI "
            "messages or choose a deliverable channel."
        )
    }


def test_send_endpoint_rejects_missing_channel_when_multiple_route_channels_configured(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        asyncio.run(
            database.create_notification_route(
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission/completed"],
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
                conversation_target={
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            )
        )
        asyncio.run(
            database.create_notification_route(
                name="Telegram Route",
                kind="webhook",
                target="https://example.invalid/telegram",
                events=["mission/completed"],
                enabled=True,
                secret_header_name=None,
                secret_token=None,
                vault_secret_id=None,
                conversation_target={
                    "channel": "telegram",
                    "account_id": "default",
                    "peer_kind": "group",
                    "peer_id": "12345",
                },
            )
        )
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "send",
                "params": {
                    "to": "channel:C123",
                    "message": "Ship parity.",
                    "idempotencyKey": "idem-send-no-channel",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Channel is required when multiple channels are configured: slack, telegram"
    }


def test_poll_endpoint_delivers_channel_target_poll_and_records_outbound_delivery(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Ship it?",
                    "options": ["Yes", "No"],
                    "maxSelections": 1,
                    "durationSeconds": 3600,
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "idempotencyKey": "idem-poll",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))
        messages = asyncio.run(
            database.list_control_chat_messages(limit=10, session_key=expected_session_key)
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": "idem-poll",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert delivery is not None
    assert delivery["route_kind"] == "announce"
    assert delivery["event_type"] == "gateway/poll"
    assert delivery["session_key"] == expected_session_key
    assert delivery["message_summary"] == "Ship it?"
    assert delivery["route_scope"]["source"] == "gateway.poll"
    assert delivery["route_scope"]["thread_id"] == "1710000000.9999"
    assert delivery["event_payload"]["question"] == "Ship it?"
    assert delivery["event_payload"]["options"] == ["Yes", "No"]
    assert delivery["event_payload"]["maxSelections"] == 1
    assert delivery["event_payload"]["durationSeconds"] == 3600
    assert len(messages) == 1
    assert messages[0]["id"] == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == (
        "Poll: Ship it?\n1. Yes\n2. No\n\nSettings: maxSelections=1, durationSeconds=3600"
    )


def test_poll_endpoint_allows_thread_id_and_routes_poll_to_thread_session(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Ship it?",
                    "options": ["Yes", "No"],
                    "maxSelections": 1,
                    "durationSeconds": 3600,
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "idempotencyKey": "idem-poll-thread",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": "idem-poll-thread",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }


def test_poll_endpoint_records_duration_hours_and_silent_settings(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Ship it?",
                    "options": ["Yes", "No"],
                    "durationHours": 24,
                    "silent": True,
                    "channel": "slack",
                    "accountId": "default",
                    "threadId": "1710000000.9999",
                    "idempotencyKey": "idem-poll-duration-hours",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))
        messages = asyncio.run(database.list_control_chat_messages(limit=10))

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert delivery is not None
    assert response.json()["runId"] == "idem-poll-duration-hours"
    assert response.json()["channel"] == "slack"
    assert response.json()["transport"] == {
        "runtime": "session-backed",
        "channel": "slack",
        "target": "channel:C123",
        "accountId": "default",
        "threadId": "1710000000.9999",
        "sessionKey": delivery["session_key"],
    }
    assert delivery["event_payload"]["durationHours"] == 24
    assert delivery["event_payload"]["silent"] is True
    assert messages[0]["content"] == (
        "Poll: Ship it?\n"
        "1. Yes\n"
        "2. No\n\n"
        "Settings: durationHours=24, silent=true"
    )


def test_poll_endpoint_records_is_anonymous_setting(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Ship it?",
                    "options": ["Yes", "No"],
                    "isAnonymous": False,
                    "channel": "slack",
                    "idempotencyKey": "idem-poll-anon",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert delivery is not None
    assert response.json()["runId"] == "idem-poll-anon"
    assert response.json()["channel"] == "slack"
    assert response.json()["transport"] == {
        "runtime": "session-backed",
        "channel": "slack",
        "target": "channel:C123",
        "sessionKey": delivery["session_key"],
    }
    assert delivery["event_payload"]["isAnonymous"] is False


def test_poll_endpoint_allows_large_duration_hours(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        database = client.app.state.database
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Ship it?",
                    "options": ["Yes", "No"],
                    "durationHours": 100_000,
                    "channel": "slack",
                    "idempotencyKey": "idem-poll-duration-hours-large",
                },
            },
        )
        delivery = asyncio.run(database.get_outbound_delivery(1))

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert delivery is not None
    assert response.json()["runId"] == "idem-poll-duration-hours-large"
    assert response.json()["channel"] == "slack"
    assert response.json()["transport"] == {
        "runtime": "session-backed",
        "channel": "slack",
        "target": "channel:C123",
        "sessionKey": delivery["session_key"],
    }
    assert delivery["event_payload"]["durationHours"] == 100_000


def test_poll_endpoint_rejects_invalid_whatsapp_target_shape(tmp_path) -> None:
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
                "method": "poll",
                "params": {
                    "to": "wat",
                    "question": "Where next?",
                    "options": ["Now", "Later"],
                    "channel": "whatsapp",
                    "idempotencyKey": "idem-poll-whatsapp-invalid",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "WhatsApp target is required"}


def test_poll_endpoint_rejects_blank_telegram_target_shape(tmp_path) -> None:
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
                "method": "poll",
                "params": {
                    "to": "   ",
                    "question": "Where next?",
                    "options": ["Now", "Later"],
                    "channel": "telegram",
                    "idempotencyKey": "idem-poll-telegram-blank",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Telegram target is required"}


def test_poll_endpoint_allows_blank_account_id(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)
    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        response = client.post(
            "/api/gateway/node-methods/call",
            json={
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Where next?",
                    "options": ["Now", "Later"],
                    "channel": "slack",
                    "accountId": "   ",
                    "idempotencyKey": "idem-poll-blank-account",
                },
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "runId": "idem-poll-blank-account",
        "channel": "slack",
        "messageId": "1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "sessionKey": expected_session_key,
        },
    }


def test_poll_endpoint_rejects_internal_webchat_channel(tmp_path) -> None:
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
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Where next?",
                    "options": ["Now", "Later"],
                    "channel": "webchat",
                    "idempotencyKey": "idem-poll-webchat",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "unsupported poll channel: webchat"}


def test_poll_endpoint_rejects_missing_channel_when_no_route_channels_configured(
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
                "method": "poll",
                "params": {
                    "to": "channel:C123",
                    "question": "Where next?",
                    "options": ["Now", "Later"],
                    "idempotencyKey": "idem-poll-no-channel",
                },
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Channel is required (no configured channels detected)."}


def test_system_event_endpoint_records_event_and_broadcasts_presence(tmp_path) -> None:
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
    registry = app.state.gateway_node_service.registry
    registry.register(
        _AutoReplyNodeConnection(registry, "conn-system-event-node-1"),
        GatewayNodeConnect(
            client_id="mobile-node-1",
            device_id="node-1",
            client_mode="mobile",
            display_name="Builder Phone",
            platform="ios",
            version="1.2.3",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1_700_000_000_000 - 5_000,
    )

    with TestClient(app, client=("testclient", 50000)) as client:
        _allow_mutating_api_requests(client)
        with client.websocket_connect("/ws") as websocket:
            response = client.post(
                "/api/gateway/node-methods/call",
                json={
                    "method": "system-event",
                    "params": {
                        "text": "note from api",
                        "reason": "heartbeat",
                        "tags": ["gateway", "api"],
                    },
                },
            )
            event = websocket.receive_json()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert event["type"] == "gateway_event"
    assert event["event"] == "presence"
    assert isinstance(event["payload"]["presence"], list)
    node_entry = next(
        entry for entry in event["payload"]["presence"] if entry.get("deviceId") == "node-1"
    )
    assert node_entry["host"] == "Builder Phone"

    database = Database(app_settings.db_path)
    asyncio.run(database.initialize())
    events = asyncio.run(database.list_events())
    assert len(events) == 1
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"] == {
        "text": "note from api",
        "reason": "heartbeat",
        "tags": ["gateway", "api"],
    }
    assert any(
        recorded.get("type") == "gateway_event" and recorded.get("event") == "presence"
        for recorded in hub.published_events
    )


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
