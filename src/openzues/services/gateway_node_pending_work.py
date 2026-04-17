from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

NodePendingWorkType = Literal["status.request", "location.request"]
NodePendingWorkPriority = Literal["default", "normal", "high"]

DEFAULT_STATUS_ITEM_ID = "baseline-status"
DEFAULT_STATUS_PRIORITY: NodePendingWorkPriority = "default"
DEFAULT_PRIORITY: NodePendingWorkPriority = "normal"
DEFAULT_MAX_ITEMS = 4
MAX_ITEMS = 10
MIN_EXPIRY_MS = 1_000

_PRIORITY_RANK: dict[NodePendingWorkPriority, int] = {
    "high": 3,
    "normal": 2,
    "default": 1,
}


@dataclass(frozen=True, slots=True)
class NodePendingWorkItem:
    id: str
    type: NodePendingWorkType
    priority: NodePendingWorkPriority
    created_at_ms: int
    expires_at_ms: int | None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class NodePendingWorkEnqueueResult:
    revision: int
    item: NodePendingWorkItem
    deduped: bool


@dataclass(frozen=True, slots=True)
class NodePendingWorkDrainResult:
    revision: int
    items: list[NodePendingWorkItem]
    has_more: bool


@dataclass(frozen=True, slots=True)
class NodePendingWorkAcknowledgeResult:
    revision: int
    removed_item_ids: list[str]


@dataclass(slots=True)
class _NodePendingWorkState:
    revision: int = 0
    items_by_id: dict[str, NodePendingWorkItem] = field(default_factory=dict)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _make_baseline_status_item(now_ms: int) -> NodePendingWorkItem:
    return NodePendingWorkItem(
        id=DEFAULT_STATUS_ITEM_ID,
        type="status.request",
        priority=DEFAULT_STATUS_PRIORITY,
        created_at_ms=now_ms,
        expires_at_ms=None,
    )


def _sorted_items(state: _NodePendingWorkState) -> list[NodePendingWorkItem]:
    return sorted(
        state.items_by_id.values(),
        key=lambda item: (
            -_PRIORITY_RANK[item.priority],
            item.created_at_ms,
            item.id,
        ),
    )


class GatewayNodePendingWorkStore:
    def __init__(self) -> None:
        self._state_by_node_id: dict[str, _NodePendingWorkState] = {}

    def enqueue(
        self,
        *,
        node_id: str,
        work_type: NodePendingWorkType,
        priority: NodePendingWorkPriority | None = None,
        expires_in_ms: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NodePendingWorkEnqueueResult:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            raise ValueError("node_id required")

        now_ms = _now_ms()
        state = self._get_or_create_state(normalized_node_id)
        self._prune_expired(state, now_ms)
        existing = next(
            (item for item in state.items_by_id.values() if item.type == work_type),
            None,
        )
        if existing is not None:
            return NodePendingWorkEnqueueResult(
                revision=state.revision,
                item=existing,
                deduped=True,
            )

        item = NodePendingWorkItem(
            id=str(uuid4()),
            type=work_type,
            priority=priority or DEFAULT_PRIORITY,
            created_at_ms=now_ms,
            expires_at_ms=(
                now_ms + max(MIN_EXPIRY_MS, int(expires_in_ms))
                if isinstance(expires_in_ms, (int, float))
                and int(expires_in_ms) > 0
                else None
            ),
            payload=payload or None,
        )
        state.items_by_id[item.id] = item
        state.revision += 1
        return NodePendingWorkEnqueueResult(
            revision=state.revision,
            item=item,
            deduped=False,
        )

    def drain(
        self,
        node_id: str,
        *,
        max_items: int | None = None,
        include_default_status: bool = True,
        now_ms: int | None = None,
    ) -> NodePendingWorkDrainResult:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            return NodePendingWorkDrainResult(revision=0, items=[], has_more=False)

        resolved_now_ms = _now_ms() if now_ms is None else int(now_ms)
        state = self._state_by_node_id.get(normalized_node_id)
        revision = state.revision if state is not None else 0
        if state is not None:
            self._prune_expired(state, resolved_now_ms)
            self._prune_state_if_empty(normalized_node_id, state)

        resolved_state = self._state_by_node_id.get(normalized_node_id)
        explicit_items = _sorted_items(resolved_state) if resolved_state is not None else []
        resolved_max_items = min(MAX_ITEMS, max(1, int(max_items or DEFAULT_MAX_ITEMS)))
        items = explicit_items[:resolved_max_items]
        has_explicit_status = any(item.type == "status.request" for item in explicit_items)
        include_baseline = include_default_status and not has_explicit_status
        if include_baseline and len(items) < resolved_max_items:
            items.append(_make_baseline_status_item(resolved_now_ms))

        explicit_returned_count = sum(1 for item in items if item.id != DEFAULT_STATUS_ITEM_ID)
        baseline_included = any(item.id == DEFAULT_STATUS_ITEM_ID for item in items)
        has_more = len(explicit_items) > explicit_returned_count or (
            include_baseline and not baseline_included
        )
        return NodePendingWorkDrainResult(
            revision=revision,
            items=items,
            has_more=has_more,
        )

    def acknowledge(
        self,
        node_id: str,
        item_ids: list[str],
    ) -> NodePendingWorkAcknowledgeResult:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            return NodePendingWorkAcknowledgeResult(revision=0, removed_item_ids=[])

        state = self._state_by_node_id.get(normalized_node_id)
        if state is None:
            return NodePendingWorkAcknowledgeResult(revision=0, removed_item_ids=[])

        removed_item_ids: list[str] = []
        for item_id in item_ids:
            trimmed_id = item_id.strip()
            if not trimmed_id or trimmed_id == DEFAULT_STATUS_ITEM_ID:
                continue
            if state.items_by_id.pop(trimmed_id, None) is not None:
                removed_item_ids.append(trimmed_id)

        if removed_item_ids:
            state.revision += 1
        self._prune_state_if_empty(normalized_node_id, state)
        return NodePendingWorkAcknowledgeResult(
            revision=state.revision,
            removed_item_ids=removed_item_ids,
        )

    def reset_for_tests(self) -> None:
        self._state_by_node_id.clear()

    def state_count_for_tests(self) -> int:
        return len(self._state_by_node_id)

    def _get_or_create_state(self, node_id: str) -> _NodePendingWorkState:
        state = self._state_by_node_id.get(node_id)
        if state is None:
            state = _NodePendingWorkState()
            self._state_by_node_id[node_id] = state
        return state

    def _prune_expired(self, state: _NodePendingWorkState, now_ms: int) -> bool:
        changed = False
        for item_id, item in list(state.items_by_id.items()):
            if item.expires_at_ms is not None and item.expires_at_ms <= now_ms:
                state.items_by_id.pop(item_id, None)
                changed = True
        if changed:
            state.revision += 1
        return changed

    def _prune_state_if_empty(self, node_id: str, state: _NodePendingWorkState) -> None:
        if not state.items_by_id:
            self._state_by_node_id.pop(node_id, None)
