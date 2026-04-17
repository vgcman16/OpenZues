from __future__ import annotations

from openzues.services.gateway_node_pending_work import GatewayNodePendingWorkStore
from openzues.services.gateway_node_registry import GatewayNodeRegistry


def test_drain_returns_baseline_status_request_when_no_explicit_work_is_queued() -> None:
    store = GatewayNodePendingWorkStore()

    drained = store.drain("node-1")

    assert [item.id for item in drained.items] == ["baseline-status"]
    assert [item.type for item in drained.items] == ["status.request"]
    assert [item.priority for item in drained.items] == ["default"]
    assert drained.has_more is False


def test_enqueue_dedupes_work_by_type_and_acknowledge_removes_items() -> None:
    store = GatewayNodePendingWorkStore()

    first = store.enqueue(node_id="node-2", work_type="location.request")
    second = store.enqueue(node_id="node-2", work_type="location.request")

    assert first.deduped is False
    assert second.deduped is True
    assert second.item.id == first.item.id

    drained = store.drain("node-2")
    assert [item.type for item in drained.items] == ["location.request", "status.request"]

    acknowledged = store.acknowledge("node-2", [first.item.id, "baseline-status"])
    assert acknowledged.removed_item_ids == [first.item.id]

    after_ack = store.drain("node-2")
    assert [item.id for item in after_ack.items] == ["baseline-status"]


def test_drain_keeps_has_more_true_when_baseline_status_item_is_deferred() -> None:
    store = GatewayNodePendingWorkStore()
    store.enqueue(node_id="node-3", work_type="location.request")

    drained = store.drain("node-3", max_items=1)

    assert [item.type for item in drained.items] == ["location.request"]
    assert drained.has_more is True


def test_drain_only_nodes_do_not_allocate_state() -> None:
    store = GatewayNodePendingWorkStore()

    drained = store.drain("node-4")
    acknowledged = store.acknowledge("node-4", ["baseline-status"])

    assert [item.id for item in drained.items] == ["baseline-status"]
    assert acknowledged.revision == 0
    assert acknowledged.removed_item_ids == []
    assert store.state_count_for_tests() == 0


def test_expired_items_prune_state_during_drain() -> None:
    store = GatewayNodePendingWorkStore()
    queued = store.enqueue(node_id="node-5", work_type="location.request", expires_in_ms=5_000)
    assert store.state_count_for_tests() == 1

    store.drain("node-5", now_ms=queued.item.created_at_ms + 60_000)

    assert store.state_count_for_tests() == 0


def test_registry_exposes_pending_work_queue_helpers() -> None:
    registry = GatewayNodeRegistry()

    queued = registry.enqueue_pending_work(node_id="node-6", work_type="status.request")
    drained = registry.drain_pending_work("node-6")
    acknowledged = registry.acknowledge_pending_work("node-6", [queued.item.id])

    assert queued.deduped is False
    assert drained.items[0].type == "status.request"
    assert acknowledged.removed_item_ids == [queued.item.id]
