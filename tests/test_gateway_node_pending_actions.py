from __future__ import annotations

from openzues.services.gateway_node_pending_actions import (
    GatewayNodePendingActionQueue,
    should_queue_as_pending_foreground_action,
)
from openzues.services.gateway_node_registry import GatewayNodeConnect, GatewayNodeRegistry


class _FakeNodeConnection:
    def __init__(self, conn_id: str) -> None:
        self.conn_id = conn_id

    def send_gateway_event(self, event: str, payload: object) -> None:
        return None


def test_enqueue_pending_action_dedupes_by_idempotency_key_and_acknowledges() -> None:
    queue = GatewayNodePendingActionQueue()

    first = queue.enqueue(
        node_id="node-1",
        command="screen.snapshot",
        params_json='{"mode":"full"}',
        idempotency_key="idem-1",
        enqueued_at_ms=1_000,
    )
    second = queue.enqueue(
        node_id="node-1",
        command="screen.snapshot",
        params_json='{"mode":"full"}',
        idempotency_key="idem-1",
        enqueued_at_ms=2_000,
    )

    assert second.id == first.id
    assert [item.id for item in queue.pull("node-1", now_ms=2_000)] == [first.id]

    remaining = queue.ack("node-1", [first.id], now_ms=2_000)
    assert remaining == []


def test_pull_pending_actions_prunes_expired_entries() -> None:
    queue = GatewayNodePendingActionQueue()
    queued = queue.enqueue(
        node_id="node-2",
        command="screen.snapshot",
        params_json=None,
        idempotency_key="idem-2",
        enqueued_at_ms=1_000,
    )

    pulled = queue.pull("node-2", now_ms=queued.enqueued_at_ms + 601_000)

    assert pulled == []


def test_queue_caps_to_sixty_four_entries_per_node() -> None:
    queue = GatewayNodePendingActionQueue()

    for index in range(65):
        queue.enqueue(
            node_id="node-3",
            command=f"screen.snapshot.{index}",
            params_json=None,
            idempotency_key=f"idem-{index}",
            enqueued_at_ms=1_000 + index,
        )

    pulled = queue.pull("node-3", now_ms=70_000)

    assert len(pulled) == 64
    assert pulled[0].command == "screen.snapshot.1"
    assert pulled[-1].command == "screen.snapshot.64"


def test_registry_pull_pending_actions_filters_commands_not_declared_by_node() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        _FakeNodeConnection("conn-1"),
        GatewayNodeConnect(
            client_id="lane-alpha",
            device_id="node-4",
            commands=("canvas.present",),
        ),
    )
    registry.enqueue_pending_action(
        node_id="node-4",
        command="canvas.present",
        params_json=None,
        idempotency_key="allowed",
        enqueued_at_ms=1_000,
    )
    registry.enqueue_pending_action(
        node_id="node-4",
        command="camera.capture",
        params_json=None,
        idempotency_key="blocked",
        enqueued_at_ms=2_000,
    )

    pulled = registry.pull_pending_actions("node-4", now_ms=3_000)

    assert [item.command for item in pulled] == ["canvas.present"]
    assert [item.command for item in registry.pull_pending_actions("node-4", now_ms=3_000)] == [
        "canvas.present"
    ]


def test_should_queue_as_pending_foreground_action_matches_ios_background_gate() -> None:
    assert (
        should_queue_as_pending_foreground_action(
            platform="ios",
            command="screen.snapshot",
            error={
                "code": "NODE_BACKGROUND_UNAVAILABLE",
                "message": "background_unavailable",
            },
        )
        is True
    )
    assert (
        should_queue_as_pending_foreground_action(
            platform="android",
            command="screen.snapshot",
            error={
                "code": "NODE_BACKGROUND_UNAVAILABLE",
                "message": "background_unavailable",
            },
        )
        is False
    )
    assert (
        should_queue_as_pending_foreground_action(
            platform="ios",
            command="system.run",
            error={
                "code": "NODE_BACKGROUND_UNAVAILABLE",
                "message": "background_unavailable",
            },
        )
        is False
    )
