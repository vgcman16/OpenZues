from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4


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
    connected_at_ms: int = 0


@dataclass(frozen=True, slots=True)
class NodeInvokeResult:
    ok: bool
    payload: Any = None
    payload_json: str | None = None
    error: dict[str, str | None] | None = None


@dataclass(slots=True)
class _PendingInvoke:
    node_id: str
    command: str
    future: asyncio.Future[NodeInvokeResult]
    timer: asyncio.TimerHandle


class GatewayNodeRegistry:
    def __init__(self) -> None:
        self._nodes_by_id: dict[str, NodeSession] = {}
        self._nodes_by_conn: dict[str, str] = {}
        self._pending_invokes: dict[str, _PendingInvoke] = {}

    def register(
        self,
        connection: GatewayNodeConnection,
        connect: GatewayNodeConnect,
        *,
        remote_ip: str | None = None,
        connected_at_ms: int | None = None,
    ) -> NodeSession:
        node_id = connect.device_id or connect.client_id
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
            caps=tuple(connect.caps),
            commands=tuple(connect.commands),
            permissions=dict(connect.permissions) if connect.permissions is not None else None,
            path_env=connect.path_env,
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

        request_id = str(uuid4())
        payload = {
            "id": request_id,
            "nodeId": node_id,
            "command": command,
            "paramsJSON": json.dumps(params) if params is not None else None,
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
        return await future

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
