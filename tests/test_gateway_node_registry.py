from __future__ import annotations

import asyncio

import pytest

from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
)


class FakeNodeConnection:
    def __init__(self, conn_id: str, *, fail_send: bool = False) -> None:
        self.conn_id = conn_id
        self.fail_send = fail_send
        self.sent_events: list[dict[str, object | None]] = []

    def send_gateway_event(self, event: str, payload: object) -> None:
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent_events.append({"event": event, "payload": payload})


def test_register_tracks_node_session_metadata() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")

    session = registry.register(
        connection,
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            client_mode="desktop",
            display_name="Builder",
            platform="windows",
            version="1.2.3",
            core_version="2.0.0",
            ui_version="3.0.0",
            device_family="laptop",
            model_identifier="surface",
            caps=("voice", "canvas"),
            commands=("node.invoke", "node.list"),
            permissions={"operator.read": True},
            path_env="C:\\tools",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1234,
    )

    assert session.node_id == "node-1"
    assert session.client_id == "lane-alpha"
    assert session.caps == ("voice", "canvas")
    assert session.commands == ("node.invoke", "node.list")
    assert session.permissions == {"operator.read": True}
    assert session.remote_ip == "10.0.0.5"
    assert session.connected_at_ms == 1234
    assert registry.get("node-1") == session
    assert registry.list_connected() == [session]


@pytest.mark.asyncio
async def test_invoke_dispatches_request_and_resolves_result() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")
    registry.register(connection, GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"))

    invoke_task = asyncio.create_task(
        registry.invoke(
            node_id="node-1",
            command="node.run",
            params={"job": "sync"},
            timeout_ms=250,
            idempotency_key="idem-1",
        )
    )
    await asyncio.sleep(0)

    assert connection.sent_events
    request = connection.sent_events[0]
    assert request["event"] == "node.invoke.request"
    request_payload = request["payload"]
    assert isinstance(request_payload, dict)
    assert request_payload["nodeId"] == "node-1"
    assert request_payload["command"] == "node.run"
    assert request_payload["paramsJSON"] == '{"job": "sync"}'
    assert request_payload["idempotencyKey"] == "idem-1"

    handled = registry.handle_invoke_result(
        request_id=str(request_payload["id"]),
        node_id="node-1",
        ok=True,
        payload={"status": "done"},
        payload_json='{"status":"done"}',
    )

    result = await invoke_task
    assert handled is True
    assert result.ok is True
    assert result.payload == {"status": "done"}
    assert result.payload_json == '{"status":"done"}'


@pytest.mark.asyncio
async def test_invoke_times_out_when_node_does_not_reply() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"),
    )

    result = await registry.invoke(
        node_id="node-1",
        command="node.run",
        timeout_ms=5,
    )

    assert result.ok is False
    assert result.error == {"code": "TIMEOUT", "message": "node invoke timed out"}


@pytest.mark.asyncio
async def test_unregister_rejects_pending_invokes_for_disconnected_node() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")
    registry.register(connection, GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"))

    invoke_task = asyncio.create_task(
        registry.invoke(node_id="node-1", command="node.run", timeout_ms=250)
    )
    await asyncio.sleep(0)

    assert registry.unregister("conn-1") == "node-1"
    assert registry.get("node-1") is None

    with pytest.raises(RuntimeError, match=r"node disconnected \(node.run\)"):
        await invoke_task
