from __future__ import annotations

import asyncio

import pytest

from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
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


def test_register_normalizes_malformed_connect_metadata() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")

    session = registry.register(
        connection,
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            caps=("voice", 7, None),  # type: ignore[arg-type]
            commands="node.run",  # type: ignore[arg-type]
            permissions={"operator.read": True, "operator.write": "yes"},  # type: ignore[dict-item]
            path_env=123,  # type: ignore[arg-type]
        ),
    )

    assert session.caps == ("voice",)
    assert session.commands == ()
    assert session.permissions == {"operator.read": True}
    assert session.path_env is None


def test_list_known_nodes_shapes_and_sorts_connected_catalog() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-2"),
        GatewayNodeConnect(
            client_id="lane-zulu",
            device_id="node-z",
            display_name="Zulu",
            platform="android",
            caps=("voice", "canvas", "voice"),
            commands=("node.describe", "node.list", "node.describe"),
        ),
        connected_at_ms=20,
    )
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-a",
            display_name="Alpha",
            platform="ios",
            permissions={"operator.read": True},
        ),
        connected_at_ms=10,
    )

    nodes = registry.list_known_nodes()

    assert [node.node_id for node in nodes] == ["node-a", "node-z"]
    assert nodes[0].display_name == "Alpha"
    assert nodes[0].connected is True
    assert nodes[0].paired is False
    assert nodes[0].approved_at_ms is None
    assert nodes[1].caps == ("canvas", "voice")
    assert nodes[1].commands == ("node.describe", "node.list")


def test_describe_known_node_returns_catalog_entry_for_connected_node() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            display_name="Builder",
            platform="windows",
            version="1.2.3",
            core_version="2.0.0",
            ui_version="3.0.0",
            device_family="laptop",
            model_identifier="surface",
            caps=("voice", "canvas"),
            commands=("node.list", "node.describe"),
            permissions={"operator.read": True},
            path_env="C:\\tools",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1234,
    )

    node = registry.describe_known_node("node-1")

    assert node is not None
    assert node.node_id == "node-1"
    assert node.display_name == "Builder"
    assert node.platform == "windows"
    assert node.version == "1.2.3"
    assert node.core_version == "2.0.0"
    assert node.ui_version == "3.0.0"
    assert node.client_id == "lane-alpha"
    assert node.client_mode is None
    assert node.remote_ip == "10.0.0.5"
    assert node.device_family == "laptop"
    assert node.model_identifier == "surface"
    assert node.path_env == "C:\\tools"
    assert node.caps == ("canvas", "voice")
    assert node.commands == ("node.describe", "node.list")
    assert node.permissions == {"operator.read": True}
    assert node.connected is True
    assert node.connected_at_ms == 1234
    assert registry.describe_known_node("missing-node") is None


def test_list_known_nodes_merges_remembered_and_connected_state() -> None:
    registry = GatewayNodeRegistry()
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Remembered Builder",
            platform="desktop",
            client_id="saved-node-1",
            client_mode="desktop",
            remote_ip="10.0.0.4",
            path_env="C:\\remembered",
            caps=("system",),
            commands=("system.run",),
            permissions={"operator.read": True},
            paired=True,
            connected=False,
            approved_at_ms=99,
        )
    )
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            display_name="Live Builder",
            platform="windows",
            version="1.2.3",
            caps=("canvas", "voice"),
            commands=("canvas.snapshot",),
            path_env="C:\\live",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1234,
    )

    node = registry.describe_known_node("node-1")

    assert node is not None
    assert node.node_id == "node-1"
    assert node.display_name == "Live Builder"
    assert node.platform == "windows"
    assert node.client_id == "live-node-1"
    assert node.remote_ip == "10.0.0.5"
    assert node.path_env == "C:\\live"
    assert node.caps == ("canvas", "voice")
    assert node.commands == ("canvas.snapshot",)
    assert node.permissions == {"operator.read": True}
    assert node.paired is True
    assert node.connected is True
    assert node.connected_at_ms == 1234
    assert node.approved_at_ms == 99


def test_describe_known_node_surfaces_offline_remembered_node() -> None:
    registry = GatewayNodeRegistry()
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Remembered Builder",
            platform="desktop",
            client_id="saved-node-1",
            client_mode="desktop",
            path_env="C:\\remembered",
            caps=("system",),
            commands=("system.run",),
            paired=True,
            connected=False,
            approved_at_ms=99,
        )
    )

    node = registry.describe_known_node("node-1")

    assert node is not None
    assert node.node_id == "node-1"
    assert node.display_name == "Remembered Builder"
    assert node.platform == "desktop"
    assert node.client_id == "saved-node-1"
    assert node.path_env == "C:\\remembered"
    assert node.caps == ("system",)
    assert node.commands == ("system.run",)
    assert node.paired is True
    assert node.connected is False
    assert node.connected_at_ms is None
    assert node.approved_at_ms == 99


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
async def test_invoke_returns_unavailable_when_request_delivery_fails() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1", fail_send=True),
        GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"),
    )

    result = await registry.invoke(
        node_id="node-1",
        command="node.run",
        timeout_ms=250,
    )

    assert result.ok is False
    assert result.error == {
        "code": "UNAVAILABLE",
        "message": "failed to send invoke to node",
    }


@pytest.mark.asyncio
async def test_invoke_queues_ios_foreground_commands_when_background_unavailable() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            platform="ios",
            commands=("canvas.present",),
        ),
    )

    invoke_task = asyncio.create_task(
        registry.invoke(
            node_id="node-1",
            command="canvas.present",
            params={"mode": "full"},
            timeout_ms=250,
            idempotency_key="idem-ios-1",
        )
    )
    await asyncio.sleep(0)

    request = connection.sent_events[0]
    request_payload = request["payload"]
    assert isinstance(request_payload, dict)

    handled = registry.handle_invoke_result(
        request_id=str(request_payload["id"]),
        node_id="node-1",
        ok=False,
        error={
            "code": "NODE_BACKGROUND_UNAVAILABLE",
            "message": "background_unavailable",
        },
    )

    result = await invoke_task

    assert handled is True
    assert result.ok is False
    assert result.error == {
        "code": "QUEUED_UNTIL_FOREGROUND",
        "message": "node command queued until iOS returns to foreground",
    }
    assert result.queued_action_id is not None
    pulled = registry.pull_pending_actions("node-1")
    assert [item.id for item in pulled] == [result.queued_action_id]
    assert pulled[0].command == "canvas.present"
    assert pulled[0].params_json == '{"mode": "full"}'


@pytest.mark.asyncio
async def test_invoke_reuses_existing_pending_action_for_repeated_idempotency_key() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            platform="ios",
            commands=("canvas.present",),
        ),
    )

    async def queue_once() -> tuple[object, object]:
        invoke_task = asyncio.create_task(
            registry.invoke(
                node_id="node-1",
                command="canvas.present",
                params={"mode": "full"},
                timeout_ms=250,
                idempotency_key="idem-ios-dup",
            )
        )
        await asyncio.sleep(0)
        request = connection.sent_events[-1]
        request_payload = request["payload"]
        assert isinstance(request_payload, dict)
        registry.handle_invoke_result(
            request_id=str(request_payload["id"]),
            node_id="node-1",
            ok=False,
            error={
                "code": "NODE_BACKGROUND_UNAVAILABLE",
                "message": "background_unavailable",
            },
        )
        result = await invoke_task
        return request_payload, result

    _first_payload, first_result = await queue_once()
    _second_payload, second_result = await queue_once()

    assert first_result.queued_action_id is not None
    assert second_result.queued_action_id == first_result.queued_action_id
    pulled = registry.pull_pending_actions("node-1")
    assert [item.id for item in pulled] == [first_result.queued_action_id]


def test_send_event_reports_delivery_failures() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1", fail_send=True),
        GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"),
    )

    assert registry.send_event("node-1", "voicewake.changed", {"enabled": True}) is False
    assert registry.send_event("missing-node", "voicewake.changed", {"enabled": True}) is False


def test_pull_pending_actions_prunes_queue_when_connected_node_declares_no_commands() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(client_id="lane-alpha", device_id="node-1"),
    )
    registry.enqueue_pending_action(
        node_id="node-1",
        command="screen.snapshot",
        params_json=None,
        idempotency_key="idem-no-commands",
        enqueued_at_ms=1_000,
    )

    pulled = registry.pull_pending_actions("node-1", now_ms=2_000)

    assert pulled == []
    assert registry.pull_pending_actions("node-1", now_ms=2_000) == []


def test_pull_pending_actions_result_matches_node_pending_pull_payload_shape() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            commands=("canvas.present",),
        ),
    )
    queued = registry.enqueue_pending_action(
        node_id="node-1",
        command="canvas.present",
        params_json='{"mode":"full"}',
        idempotency_key="idem-pull-view",
        enqueued_at_ms=1_000,
    )

    pulled = registry.pull_pending_actions_result("node-1", now_ms=2_000)

    assert pulled.node_id == "node-1"
    assert pulled.actions == [
        {
            "id": queued.id,
            "command": "canvas.present",
            "paramsJSON": '{"mode":"full"}',
            "enqueuedAtMs": 1_000,
        }
    ]


def test_ack_pending_actions_result_echoes_sanitized_ids_and_remaining_count() -> None:
    registry = GatewayNodeRegistry()
    registry.enqueue_pending_action(
        node_id="node-1",
        command="canvas.present",
        params_json=None,
        idempotency_key="idem-ack-1",
        enqueued_at_ms=1_000,
    )
    second = registry.enqueue_pending_action(
        node_id="node-1",
        command="camera.capture",
        params_json=None,
        idempotency_key="idem-ack-2",
        enqueued_at_ms=2_000,
    )

    acked = registry.ack_pending_actions_result(
        "node-1",
        [" ", second.id, second.id, "\t"],
        now_ms=3_000,
    )

    assert acked.node_id == "node-1"
    assert acked.acked_ids == [second.id]
    assert acked.remaining_count == 1


def test_pull_pending_actions_filters_commands_not_allowlisted_for_platform() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-1",
            platform="ios",
            commands=("canvas.present", "system.run"),
        ),
    )
    registry.enqueue_pending_action(
        node_id="node-1",
        command="canvas.present",
        params_json=None,
        idempotency_key="idem-allowed",
        enqueued_at_ms=1_000,
    )
    registry.enqueue_pending_action(
        node_id="node-1",
        command="system.run",
        params_json=None,
        idempotency_key="idem-blocked",
        enqueued_at_ms=2_000,
    )

    pulled = registry.pull_pending_actions("node-1", now_ms=3_000)

    assert [item.command for item in pulled] == ["canvas.present"]
    assert [item.command for item in registry.pull_pending_actions("node-1", now_ms=3_000)] == [
        "canvas.present"
    ]


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
