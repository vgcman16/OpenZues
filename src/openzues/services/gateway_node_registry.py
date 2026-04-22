from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from openzues.services.gateway_node_command_policy import (
    normalize_declared_node_commands,
    resolve_node_command_allowlist,
)
from openzues.services.gateway_node_pending_actions import (
    GatewayNodePendingActionQueue,
    PendingNodeAction,
    should_queue_as_pending_foreground_action,
)
from openzues.services.gateway_node_pending_work import (
    GatewayNodePendingWorkStore,
    NodePendingWorkAcknowledgeResult,
    NodePendingWorkDrainResult,
    NodePendingWorkEnqueueResult,
    NodePendingWorkPriority,
    NodePendingWorkType,
)


class GatewayNodeConnection(Protocol):
    conn_id: str

    def send_gateway_event(self, event: str, payload: object) -> None: ...


@dataclass(frozen=True, slots=True)
class GatewayNodeConnect:
    client_id: str
    device_id: str | None = None
    client_mode: str | None = None
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    permissions: dict[str, bool] | None = None
    path_env: str | None = None
    canvas_host_url: str | None = None


@dataclass(slots=True)
class NodeSession:
    node_id: str
    conn_id: str
    connection: GatewayNodeConnection
    client_id: str | None = None
    client_mode: str | None = None
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    remote_ip: str | None = None
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    permissions: dict[str, bool] | None = None
    path_env: str | None = None
    canvas_host_url: str | None = None
    canvas_capability: str | None = None
    canvas_capability_expires_at_ms: int | None = None
    connected_at_ms: int = 0


@dataclass(frozen=True, slots=True)
class KnownNode:
    node_id: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    client_id: str | None = None
    client_mode: str | None = None
    remote_ip: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    path_env: str | None = None
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    permissions: dict[str, bool] | None = None
    paired: bool = False
    connected: bool = True
    connected_at_ms: int | None = None
    approved_at_ms: int | None = None


@dataclass(frozen=True, slots=True)
class NodeInvokeResult:
    ok: bool
    payload: Any = None
    payload_json: str | None = None
    error: dict[str, str | None] | None = None
    queued_action_id: str | None = None


@dataclass(frozen=True, slots=True)
class NodePendingActionPullResult:
    node_id: str
    actions: list[dict[str, object | None]]


@dataclass(frozen=True, slots=True)
class NodePendingActionAckResult:
    node_id: str
    acked_ids: list[str]
    remaining_count: int


@dataclass(slots=True)
class _PendingInvoke:
    node_id: str
    command: str
    future: asyncio.Future[NodeInvokeResult]
    timer: asyncio.TimerHandle


def _normalize_declared_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _normalize_permissions(value: object) -> dict[str, bool] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, bool] = {}
    for key, allowed in value.items():
        if isinstance(key, str) and isinstance(allowed, bool):
            normalized[key] = allowed
    if normalized:
        return normalized
    return {} if not value else None


def _normalize_optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _unique_sorted_strings(value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({item.strip() for item in value if item.strip()}))


def _known_node_sort_key(node: KnownNode) -> tuple[int, str, str]:
    display_name = (node.display_name or node.node_id).strip().lower()
    return (0 if node.connected else 1, display_name, node.node_id)


def _build_known_node(session: NodeSession) -> KnownNode:
    return KnownNode(
        node_id=session.node_id,
        display_name=session.display_name,
        platform=session.platform,
        version=session.version,
        core_version=session.core_version,
        ui_version=session.ui_version,
        client_id=session.client_id,
        client_mode=session.client_mode,
        remote_ip=session.remote_ip,
        device_family=session.device_family,
        model_identifier=session.model_identifier,
        path_env=session.path_env,
        caps=_unique_sorted_strings(session.caps),
        commands=_unique_sorted_strings(session.commands),
        permissions=session.permissions,
        paired=False,
        connected=True,
        connected_at_ms=session.connected_at_ms,
        approved_at_ms=None,
    )


def _normalize_known_node(node: KnownNode) -> KnownNode:
    return KnownNode(
        node_id=node.node_id,
        display_name=node.display_name,
        platform=node.platform,
        version=node.version,
        core_version=node.core_version,
        ui_version=node.ui_version,
        client_id=node.client_id,
        client_mode=node.client_mode,
        remote_ip=node.remote_ip,
        device_family=node.device_family,
        model_identifier=node.model_identifier,
        path_env=node.path_env,
        caps=_unique_sorted_strings(node.caps),
        commands=_unique_sorted_strings(node.commands),
        permissions=node.permissions,
        paired=node.paired,
        connected=False,
        connected_at_ms=None,
        approved_at_ms=node.approved_at_ms,
    )


def _merge_known_node(
    *,
    node_id: str,
    remembered: KnownNode | None,
    session: NodeSession | None,
) -> KnownNode:
    if session is None:
        if remembered is None:
            raise KeyError(node_id)
        return remembered

    live = _build_known_node(session)
    if remembered is None:
        return live

    return KnownNode(
        node_id=node_id,
        display_name=live.display_name or remembered.display_name,
        platform=live.platform or remembered.platform,
        version=live.version or remembered.version,
        core_version=live.core_version or remembered.core_version,
        ui_version=live.ui_version or remembered.ui_version,
        client_id=live.client_id or remembered.client_id,
        client_mode=live.client_mode or remembered.client_mode,
        remote_ip=live.remote_ip or remembered.remote_ip,
        device_family=live.device_family or remembered.device_family,
        model_identifier=live.model_identifier or remembered.model_identifier,
        path_env=live.path_env or remembered.path_env,
        caps=live.caps,
        commands=live.commands,
        permissions=live.permissions if live.permissions is not None else remembered.permissions,
        paired=remembered.paired or live.paired,
        connected=True,
        connected_at_ms=live.connected_at_ms,
        approved_at_ms=remembered.approved_at_ms or live.approved_at_ms,
    )


class GatewayNodeRegistry:
    def __init__(self) -> None:
        self._nodes_by_id: dict[str, NodeSession] = {}
        self._nodes_by_conn: dict[str, str] = {}
        self._remembered_nodes_by_id: dict[str, KnownNode] = {}
        self._pending_invokes: dict[str, _PendingInvoke] = {}
        self._pending_work = GatewayNodePendingWorkStore()
        self._pending_actions = GatewayNodePendingActionQueue()

    def remember(self, node: KnownNode) -> None:
        self._remembered_nodes_by_id[node.node_id] = _normalize_known_node(node)

    def forget(self, node_id: str) -> None:
        self._remembered_nodes_by_id.pop(node_id, None)

    def register(
        self,
        connection: GatewayNodeConnection,
        connect: GatewayNodeConnect,
        *,
        remote_ip: str | None = None,
        connected_at_ms: int | None = None,
    ) -> NodeSession:
        node_id = connect.device_id or connect.client_id
        caps = _normalize_declared_strings(connect.caps)
        commands = _normalize_declared_strings(connect.commands)
        permissions = _normalize_permissions(connect.permissions)
        path_env = _normalize_optional_string(connect.path_env)
        canvas_host_url = _normalize_optional_string(connect.canvas_host_url)
        session = NodeSession(
            node_id=node_id,
            conn_id=connection.conn_id,
            connection=connection,
            client_id=connect.client_id,
            client_mode=connect.client_mode,
            display_name=connect.display_name,
            platform=connect.platform,
            version=connect.version,
            core_version=connect.core_version,
            ui_version=connect.ui_version,
            device_family=connect.device_family,
            model_identifier=connect.model_identifier,
            remote_ip=remote_ip,
            caps=caps,
            commands=commands,
            permissions=permissions,
            path_env=path_env,
            canvas_host_url=canvas_host_url,
            connected_at_ms=(
                int(time.time() * 1000) if connected_at_ms is None else int(connected_at_ms)
            ),
        )
        self._nodes_by_id[node_id] = session
        self._nodes_by_conn[connection.conn_id] = node_id
        return session

    def unregister(self, conn_id: str) -> str | None:
        node_id = self._nodes_by_conn.pop(conn_id, None)
        if node_id is None:
            return None
        self._nodes_by_id.pop(node_id, None)
        for request_id, pending in list(self._pending_invokes.items()):
            if pending.node_id != node_id:
                continue
            pending.timer.cancel()
            if not pending.future.done():
                pending.future.set_exception(
                    RuntimeError(f"node disconnected ({pending.command})")
                )
            self._pending_invokes.pop(request_id, None)
        return node_id

    def list_connected(self) -> list[NodeSession]:
        return list(self._nodes_by_id.values())

    def list_known_nodes(self) -> list[KnownNode]:
        node_ids = {*self._remembered_nodes_by_id.keys(), *self._nodes_by_id.keys()}
        known_nodes = [
            _merge_known_node(
                node_id=node_id,
                remembered=self._remembered_nodes_by_id.get(node_id),
                session=self._nodes_by_id.get(node_id),
            )
            for node_id in node_ids
        ]
        return sorted(known_nodes, key=_known_node_sort_key)

    def describe_known_node(self, node_id: str) -> KnownNode | None:
        remembered = self._remembered_nodes_by_id.get(node_id)
        session = self._nodes_by_id.get(node_id)
        if remembered is None and session is None:
            return None
        return _merge_known_node(
            node_id=node_id,
            remembered=remembered,
            session=session,
        )

    def get(self, node_id: str) -> NodeSession | None:
        return self._nodes_by_id.get(node_id)

    async def invoke(
        self,
        *,
        node_id: str,
        command: str,
        params: object | None = None,
        timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> NodeInvokeResult:
        node = self._nodes_by_id.get(node_id)
        if node is None:
            return NodeInvokeResult(
                ok=False,
                error={"code": "NOT_CONNECTED", "message": "node not connected"},
            )

        params_json = json.dumps(params) if params is not None else None
        request_id = str(uuid4())
        payload = {
            "id": request_id,
            "nodeId": node_id,
            "command": command,
            "paramsJSON": params_json,
            "timeoutMs": timeout_ms,
            "idempotencyKey": idempotency_key,
        }
        if not self._send_event_to_session(node, "node.invoke.request", payload):
            return NodeInvokeResult(
                ok=False,
                error={"code": "UNAVAILABLE", "message": "failed to send invoke to node"},
            )

        resolved_timeout_ms = 30_000 if timeout_ms is None else int(timeout_ms)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[NodeInvokeResult] = loop.create_future()

        def _expire_pending_invoke() -> None:
            self._pending_invokes.pop(request_id, None)
            if not future.done():
                future.set_result(
                    NodeInvokeResult(
                        ok=False,
                        error={"code": "TIMEOUT", "message": "node invoke timed out"},
                    )
                )

        timer = loop.call_later(resolved_timeout_ms / 1000, _expire_pending_invoke)
        self._pending_invokes[request_id] = _PendingInvoke(
            node_id=node_id,
            command=command,
            future=future,
            timer=timer,
        )
        result = await future
        if result.ok:
            return result
        if not should_queue_as_pending_foreground_action(
            platform=node.platform,
            command=command,
            error=result.error,
        ):
            return result
        queued = self.enqueue_pending_action(
            node_id=node_id,
            command=command,
            params_json=params_json,
            idempotency_key=idempotency_key or request_id,
        )
        return NodeInvokeResult(
            ok=False,
            error={
                "code": "QUEUED_UNTIL_FOREGROUND",
                "message": "node command queued until iOS returns to foreground",
            },
            queued_action_id=queued.id,
        )

    def handle_invoke_result(
        self,
        *,
        request_id: str,
        node_id: str,
        ok: bool,
        payload: object | None = None,
        payload_json: str | None = None,
        error: dict[str, str | None] | None = None,
    ) -> bool:
        pending = self._pending_invokes.get(request_id)
        if pending is None or pending.node_id != node_id:
            return False
        pending.timer.cancel()
        self._pending_invokes.pop(request_id, None)
        if not pending.future.done():
            pending.future.set_result(
                NodeInvokeResult(
                    ok=ok,
                    payload=payload,
                    payload_json=payload_json,
                    error=error,
                )
            )
        return True

    def send_event(self, node_id: str, event: str, payload: object | None = None) -> bool:
        node = self._nodes_by_id.get(node_id)
        if node is None:
            return False
        return self._send_event_to_session(node, event, payload)

    def enqueue_pending_work(
        self,
        *,
        node_id: str,
        work_type: NodePendingWorkType,
        priority: NodePendingWorkPriority | None = None,
        expires_in_ms: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NodePendingWorkEnqueueResult:
        return self._pending_work.enqueue(
            node_id=node_id,
            work_type=work_type,
            priority=priority,
            expires_in_ms=expires_in_ms,
            payload=payload,
        )

    def drain_pending_work(
        self,
        node_id: str,
        *,
        max_items: int | None = None,
        include_default_status: bool = True,
        now_ms: int | None = None,
    ) -> NodePendingWorkDrainResult:
        return self._pending_work.drain(
            node_id,
            max_items=max_items,
            include_default_status=include_default_status,
            now_ms=now_ms,
        )

    def acknowledge_pending_work(
        self,
        node_id: str,
        item_ids: list[str],
    ) -> NodePendingWorkAcknowledgeResult:
        return self._pending_work.acknowledge(node_id, item_ids)

    def enqueue_pending_action(
        self,
        *,
        node_id: str,
        command: str,
        params_json: str | None,
        idempotency_key: str,
        enqueued_at_ms: int | None = None,
    ) -> PendingNodeAction:
        return self._pending_actions.enqueue(
            node_id=node_id,
            command=command,
            params_json=params_json,
            idempotency_key=idempotency_key,
            enqueued_at_ms=enqueued_at_ms,
        )

    def pull_pending_actions(
        self,
        node_id: str,
        *,
        now_ms: int | None = None,
    ) -> list[PendingNodeAction]:
        session = self._nodes_by_id.get(node_id)
        allowed_commands = None
        if session is not None:
            allowlist = resolve_node_command_allowlist(
                platform=session.platform,
                device_family=session.device_family,
            )
            allowed_commands = normalize_declared_node_commands(
                session.commands,
                allowlist=allowlist,
            )
        return self._pending_actions.pull(
            node_id,
            now_ms=now_ms,
            allowed_commands=allowed_commands,
        )

    def peek_pending_actions(
        self,
        node_id: str,
        *,
        now_ms: int | None = None,
    ) -> list[PendingNodeAction]:
        return self._pending_actions.pull(node_id, now_ms=now_ms, allowed_commands=None)

    def ack_pending_actions(
        self,
        node_id: str,
        ids: list[str],
        *,
        now_ms: int | None = None,
    ) -> list[PendingNodeAction]:
        return self._pending_actions.ack(node_id, ids, now_ms=now_ms)

    def pull_pending_actions_result(
        self,
        node_id: str,
        *,
        now_ms: int | None = None,
    ) -> NodePendingActionPullResult:
        actions = self.pull_pending_actions(node_id, now_ms=now_ms)
        return NodePendingActionPullResult(
            node_id=node_id,
            actions=[
                {
                    "id": action.id,
                    "command": action.command,
                    "paramsJSON": action.params_json,
                    "enqueuedAtMs": action.enqueued_at_ms,
                }
                for action in actions
            ],
        )

    def peek_pending_actions_result(
        self,
        node_id: str,
        *,
        now_ms: int | None = None,
    ) -> NodePendingActionPullResult:
        actions = self.peek_pending_actions(node_id, now_ms=now_ms)
        return NodePendingActionPullResult(
            node_id=node_id,
            actions=[
                {
                    "id": action.id,
                    "command": action.command,
                    "paramsJSON": action.params_json,
                    "enqueuedAtMs": action.enqueued_at_ms,
                }
                for action in actions
            ],
        )

    def ack_pending_actions_result(
        self,
        node_id: str,
        ids: list[str],
        *,
        now_ms: int | None = None,
    ) -> NodePendingActionAckResult:
        sanitized_ids = _sanitize_pending_action_ids(ids)
        remaining = self.ack_pending_actions(node_id, sanitized_ids, now_ms=now_ms)
        return NodePendingActionAckResult(
            node_id=node_id,
            acked_ids=sanitized_ids,
            remaining_count=len(remaining),
        )

    def _send_event_to_session(
        self,
        node: NodeSession,
        event: str,
        payload: object | None,
    ) -> bool:
        try:
            node.connection.send_gateway_event(event, payload)
        except Exception:
            return False
        return True


def _sanitize_pending_action_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    sanitized: list[str] = []
    for value in ids:
        trimmed = value.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        sanitized.append(trimmed)
    return sanitized
