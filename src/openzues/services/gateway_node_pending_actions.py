from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import uuid4

PENDING_NODE_ACTION_TTL_MS = 10 * 60_000
PENDING_NODE_ACTION_MAX_PER_NODE = 64


@dataclass(frozen=True, slots=True)
class PendingNodeAction:
    id: str
    node_id: str
    command: str
    params_json: str | None
    idempotency_key: str
    enqueued_at_ms: int


def _now_ms() -> int:
    return int(time.time() * 1000)


def _normalize_platform(value: str | None) -> str:
    return str(value or "").strip().lower()


def _is_foreground_restricted_ios_command(command: str) -> bool:
    return (
        command == "canvas.present"
        or command == "canvas.navigate"
        or command.startswith("canvas.")
        or command.startswith("camera.")
        or command.startswith("screen.")
        or command.startswith("talk.")
    )


def should_queue_as_pending_foreground_action(
    *,
    platform: str | None,
    command: str,
    error: object,
) -> bool:
    normalized_platform = _normalize_platform(platform)
    if not normalized_platform.startswith("ios") and not normalized_platform.startswith("ipados"):
        return False
    if not _is_foreground_restricted_ios_command(command):
        return False
    if not isinstance(error, dict):
        return False
    code = str(error.get("code") or "").strip().upper()
    message = str(error.get("message") or "").strip().upper()
    return code == "NODE_BACKGROUND_UNAVAILABLE" or "BACKGROUND_UNAVAILABLE" in message


class GatewayNodePendingActionQueue:
    def __init__(self) -> None:
        self._actions_by_node_id: dict[str, list[PendingNodeAction]] = {}

    def enqueue(
        self,
        *,
        node_id: str,
        command: str,
        params_json: str | None,
        idempotency_key: str,
        enqueued_at_ms: int | None = None,
    ) -> PendingNodeAction:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            raise ValueError("node_id required")
        now_ms = _now_ms() if enqueued_at_ms is None else int(enqueued_at_ms)
        queue = self._prune(normalized_node_id, now_ms)
        existing = next(
            (
                action
                for action in queue
                if action.idempotency_key == idempotency_key
            ),
            None,
        )
        if existing is not None:
            return existing
        action = PendingNodeAction(
            id=str(uuid4()),
            node_id=normalized_node_id,
            command=command,
            params_json=params_json,
            idempotency_key=idempotency_key,
            enqueued_at_ms=now_ms,
        )
        queue.append(action)
        if len(queue) > PENDING_NODE_ACTION_MAX_PER_NODE:
            del queue[: len(queue) - PENDING_NODE_ACTION_MAX_PER_NODE]
        self._actions_by_node_id[normalized_node_id] = queue
        return action

    def pull(
        self,
        node_id: str,
        *,
        now_ms: int | None = None,
        allowed_commands: tuple[str, ...] | None = None,
    ) -> list[PendingNodeAction]:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            return []
        queue = self._prune(normalized_node_id, _now_ms() if now_ms is None else int(now_ms))
        if not queue:
            return list(queue)
        if allowed_commands is None:
            return list(queue)
        allowed = [action for action in queue if action.command in allowed_commands]
        if len(allowed) != len(queue):
            if allowed:
                self._actions_by_node_id[normalized_node_id] = allowed
            else:
                self._actions_by_node_id.pop(normalized_node_id, None)
        return list(allowed)

    def ack(
        self,
        node_id: str,
        ids: list[str],
        *,
        now_ms: int | None = None,
    ) -> list[PendingNodeAction]:
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            return []
        queue = self._prune(normalized_node_id, _now_ms() if now_ms is None else int(now_ms))
        if not ids:
            return list(queue)
        id_set = {value.strip() for value in ids if value and value.strip()}
        remaining = [action for action in queue if action.id not in id_set]
        if remaining:
            self._actions_by_node_id[normalized_node_id] = remaining
        else:
            self._actions_by_node_id.pop(normalized_node_id, None)
        return list(remaining)

    def _prune(self, node_id: str, now_ms: int) -> list[PendingNodeAction]:
        queue = self._actions_by_node_id.get(node_id, [])
        minimum_timestamp = now_ms - PENDING_NODE_ACTION_TTL_MS
        live = [action for action in queue if action.enqueued_at_ms >= minimum_timestamp]
        if live:
            self._actions_by_node_id[node_id] = live
        else:
            self._actions_by_node_id.pop(node_id, None)
        return live
