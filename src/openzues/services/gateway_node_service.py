from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime

from openzues.schemas import (
    GatewayCapabilityKnownNodeView,
    GatewayCapabilityNodeCatalogView,
    GatewayNodePendingActionAckView,
    GatewayNodePendingActionPullView,
    GatewayNodePendingWorkDrainView,
    GatewayNodePendingWorkEnqueueView,
)
from openzues.services.gateway_node_command_policy import (
    normalize_declared_node_commands,
    resolve_node_command_allowlist,
)
from openzues.services.gateway_node_pairing import (
    GatewayNodePairingService,
    GatewayPairedNode,
)
from openzues.services.gateway_node_pending_work import (
    NodePendingWorkPriority,
    NodePendingWorkType,
)
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.gateway_talk_mode import GatewayTalkModeService
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.manager import RuntimeManager


@dataclass(slots=True)
class _GatewayNodeServiceConnection:
    conn_id: str

    def send_gateway_event(self, event: str, payload: object) -> None:
        return None


def _build_wake_result(
    *,
    attempted: bool,
    available: bool,
    connected: bool,
    path: str,
    started_at: float,
) -> dict[str, object]:
    return {
        "attempted": attempted,
        "available": available,
        "connected": connected,
        "path": path,
        "durationMs": max(0, int((time.monotonic() - started_at) * 1000)),
    }


def _wake_result_available(result: object) -> bool:
    if isinstance(result, dict):
        return bool(result.get("available"))
    return bool(result)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _instance_connected_at_ms(last_event_at: str | None) -> int:
    if not last_event_at:
        return 0
    try:
        parsed = datetime.fromisoformat(last_event_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return int(parsed.timestamp() * 1000)


def _node_id_for_instance(instance_id: int) -> str:
    return str(instance_id)


def _conn_id_for_node(node_id: str) -> str:
    return f"gateway-node-service:{node_id}"


def _remembered_instance_node(
    *,
    node_id: str,
    name: str,
    transport: str,
    cwd: str | None,
    previous: KnownNode | None = None,
) -> KnownNode:
    return KnownNode(
        node_id=node_id,
        display_name=name,
        platform=transport,
        client_id=node_id,
        client_mode=transport,
        path_env=cwd,
        device_family=previous.device_family if previous is not None else None,
        model_identifier=previous.model_identifier if previous is not None else None,
        caps=previous.caps if previous is not None else (),
        commands=previous.commands if previous is not None else (),
        permissions=previous.permissions if previous is not None else None,
        paired=True,
        connected=False,
        approved_at_ms=previous.approved_at_ms if previous is not None else None,
    )


def _build_catalog_view(
    nodes: list[GatewayCapabilityKnownNodeView],
) -> GatewayCapabilityNodeCatalogView:
    node_count = len(nodes)
    connected_count = sum(1 for node in nodes if node.connected)
    paired_count = sum(1 for node in nodes if node.paired)
    if not nodes:
        return GatewayCapabilityNodeCatalogView(
            headline="Gateway node registry is staged",
            summary="No saved or connected node catalog is visible yet.",
            node_count=0,
            connected_count=0,
            paired_count=0,
            nodes=[],
        )

    return GatewayCapabilityNodeCatalogView(
        headline="Gateway known node catalog is visible",
        summary=(
            f"{node_count} known node(s) are visible; {connected_count} currently connected "
            f"and {paired_count} saved in the lane roster."
        ),
        node_count=node_count,
        connected_count=connected_count,
        paired_count=paired_count,
        nodes=nodes,
    )


class GatewayNodeService:
    def __init__(
        self,
        manager: RuntimeManager,
        pairing_service: GatewayNodePairingService | None = None,
        talk_mode_service: GatewayTalkModeService | None = None,
        voicewake_service: GatewayVoiceWakeService | None = None,
    ) -> None:
        self.manager = manager
        self.pairing_service = pairing_service
        self._talk_mode_service = talk_mode_service
        self._voicewake_service = voicewake_service
        self.registry = GatewayNodeRegistry()
        self._managed_node_ids: set[str] = set()

    async def _sync(self) -> None:
        instances = await self.manager.list_views()
        active_node_ids = {_node_id_for_instance(instance.id) for instance in instances}

        for stale_node_id in self._managed_node_ids - active_node_ids:
            self.registry.unregister(_conn_id_for_node(stale_node_id))
            self.registry.forget(stale_node_id)
        self._managed_node_ids = active_node_ids

        for instance in instances:
            node_id = _node_id_for_instance(instance.id)
            previous = self.registry.describe_known_node(node_id)
            connected_at_ms = _instance_connected_at_ms(instance.last_event_at)
            self.registry.remember(
                _remembered_instance_node(
                    node_id=node_id,
                    name=instance.name,
                    transport=instance.transport,
                    cwd=instance.cwd,
                    previous=previous,
                )
            )
            conn_id = _conn_id_for_node(node_id)
            if not instance.connected:
                self.registry.unregister(conn_id)
                continue
            existing_session = self.registry.get(node_id)
            fresh_connection = existing_session is None or existing_session.conn_id != conn_id
            self.registry.register(
                _GatewayNodeServiceConnection(conn_id=conn_id),
                GatewayNodeConnect(
                    client_id=node_id,
                    device_id=node_id,
                    client_mode=instance.transport,
                    display_name=instance.name,
                    platform=instance.transport,
                    device_family=previous.device_family if previous is not None else None,
                    model_identifier=previous.model_identifier if previous is not None else None,
                    caps=previous.caps if previous is not None else (),
                    commands=previous.commands if previous is not None else (),
                    permissions=previous.permissions if previous is not None else None,
                    path_env=instance.cwd,
                ),
                connected_at_ms=connected_at_ms,
            )
            if self.pairing_service is not None:
                await self.pairing_service.update_paired_node_metadata(
                    node_id,
                    display_name=instance.name,
                    platform=instance.transport,
                    version=previous.version if previous is not None else None,
                    core_version=previous.core_version if previous is not None else None,
                    ui_version=previous.ui_version if previous is not None else None,
                    device_family=previous.device_family if previous is not None else None,
                    model_identifier=(
                        previous.model_identifier if previous is not None else None
                    ),
                    caps=(
                        list(previous.caps)
                        if previous is not None and previous.caps
                        else None
                    ),
                    commands=(
                        list(previous.commands)
                        if previous is not None and previous.commands
                        else None
                    ),
                    permissions=previous.permissions if previous is not None else None,
                    remote_ip=previous.remote_ip if previous is not None else None,
                    last_connected_at_ms=connected_at_ms,
                )
            if fresh_connection and self._voicewake_service is not None:
                self.registry.send_event(
                    node_id,
                    "voicewake.changed",
                    {"triggers": list(self._voicewake_service.load().triggers)},
                )
            if fresh_connection and self._talk_mode_service is not None:
                talk_mode = self._talk_mode_service.load()
                if talk_mode.updated_at_ms > 0:
                    self.registry.send_event(
                        node_id,
                        "talk.mode",
                        talk_mode.to_payload(),
                    )

    async def sync(self) -> None:
        await self._sync()

    async def _stage_scope_upgrade_request(
        self,
        node: KnownNode,
        *,
        paired_node: GatewayPairedNode,
    ) -> dict[str, object] | None:
        if self.pairing_service is None or not node.connected:
            return None
        allowlist = resolve_node_command_allowlist(
            platform=node.platform or paired_node.platform,
            device_family=node.device_family or paired_node.device_family,
        )
        live_commands = list(
            normalize_declared_node_commands(
                node.commands,
                allowlist=allowlist,
            )
        )
        approved_commands = set(
            normalize_declared_node_commands(
                paired_node.commands,
                allowlist=allowlist,
            )
        )
        if not live_commands or not any(command not in approved_commands for command in live_commands):
            return None
        return await self.pairing_service.request(
            node_id=node.node_id,
            display_name=node.display_name or paired_node.display_name,
            platform=node.platform or paired_node.platform,
            version=node.version or paired_node.version,
            core_version=node.core_version or paired_node.core_version,
            ui_version=node.ui_version or paired_node.ui_version,
            device_family=node.device_family or paired_node.device_family,
            model_identifier=node.model_identifier or paired_node.model_identifier,
            caps=list(node.caps) if node.caps else list(paired_node.caps),
            commands=live_commands,
            remote_ip=node.remote_ip or paired_node.remote_ip,
            silent=True,
            now_ms=_now_ms(),
        )

    async def wake_node(self, node_id: str) -> dict[str, object]:
        started_at = time.monotonic()
        await self._sync()
        if self.registry.get(node_id) is not None:
            return _build_wake_result(
                attempted=False,
                available=True,
                connected=True,
                path="already-connected",
                started_at=started_at,
            )

        try:
            instance_id = int(str(node_id).strip())
        except (TypeError, ValueError):
            return _build_wake_result(
                attempted=False,
                available=False,
                connected=False,
                path="invalid-node-id",
                started_at=started_at,
            )

        if instance_id not in self.manager.instances:
            return _build_wake_result(
                attempted=False,
                available=False,
                connected=False,
                path="unknown-managed-node",
                started_at=started_at,
            )

        try:
            await self.manager.connect_instance(instance_id)
        except Exception:
            await self._sync()
            return _build_wake_result(
                attempted=True,
                available=False,
                connected=self.registry.get(node_id) is not None,
                path="connect-error",
                started_at=started_at,
            )

        await self._sync()
        connected = self.registry.get(node_id) is not None
        return _build_wake_result(
            attempted=True,
            available=True,
            connected=connected,
            path="connected" if connected else "not-connected",
            started_at=started_at,
        )

    async def get_catalog_view(self) -> GatewayCapabilityNodeCatalogView:
        await self._sync()
        known_nodes = self.registry.list_known_nodes()
        known_nodes_by_id = {node.node_id: node for node in known_nodes}
        node_payloads: dict[str, dict[str, object | None]] = {
            node_id: asdict(node) for node_id, node in known_nodes_by_id.items()
        }
        if self.pairing_service is not None:
            for paired_node in await self.pairing_service.list_paired_nodes():
                existing_node = known_nodes_by_id.get(paired_node.node_id)
                if existing_node is not None:
                    await self._stage_scope_upgrade_request(
                        existing_node,
                        paired_node=paired_node,
                    )
                paired_payload = _catalog_paired_node_payload(paired_node)
                existing = node_payloads.get(paired_node.node_id)
                node_payloads[paired_node.node_id] = (
                    paired_payload
                    if existing is None
                    else _merge_catalog_node_payload(paired_payload, existing)
                )
        nodes = [
            GatewayCapabilityKnownNodeView.model_validate(node_payload)
            for node_payload in sorted(node_payloads.values(), key=_catalog_node_sort_key)
        ]
        return _build_catalog_view(nodes)

    async def get_node_view(self, node_id: str) -> GatewayCapabilityKnownNodeView | None:
        await self._sync()
        node = self.registry.describe_known_node(node_id)
        if node is not None:
            payload = asdict(node)
            if self.pairing_service is not None:
                paired_node = await self.pairing_service.get_paired_node(node_id)
                if paired_node is not None:
                    await self._stage_scope_upgrade_request(
                        node,
                        paired_node=paired_node,
                    )
                    payload = _merge_catalog_node_payload(
                        _catalog_paired_node_payload(paired_node),
                        payload,
                    )
            return GatewayCapabilityKnownNodeView.model_validate(payload)
        if self.pairing_service is None:
            return None
        paired_node = await self.pairing_service.get_paired_node(node_id)
        if paired_node is None:
            return None
        return GatewayCapabilityKnownNodeView.model_validate(
            _catalog_paired_node_payload(paired_node)
        )

    async def get_pending_action_view(self, node_id: str) -> GatewayNodePendingActionPullView:
        await self._sync()
        if self.registry.describe_known_node(node_id) is None:
            raise KeyError(node_id)
        result = self.registry.peek_pending_actions_result(node_id)
        return GatewayNodePendingActionPullView.model_validate(
            {
                "nodeId": result.node_id,
                "actions": result.actions,
            }
        )

    async def ack_pending_actions(
        self,
        node_id: str,
        ids: list[str],
    ) -> GatewayNodePendingActionAckView:
        await self._sync()
        if self.registry.describe_known_node(node_id) is None:
            raise KeyError(node_id)
        result = self.registry.ack_pending_actions_result(node_id, ids)
        return GatewayNodePendingActionAckView.model_validate(
            {
                "nodeId": result.node_id,
                "ackedIds": result.acked_ids,
                "remainingCount": result.remaining_count,
            }
        )

    async def get_pending_work_view(
        self,
        node_id: str,
        *,
        max_items: int | None = None,
    ) -> GatewayNodePendingWorkDrainView:
        await self._sync()
        if self.registry.describe_known_node(node_id) is None:
            raise KeyError(node_id)
        drained = self.registry.drain_pending_work(node_id, max_items=max_items)
        return GatewayNodePendingWorkDrainView.model_validate(
            {
                "nodeId": node_id,
                "revision": drained.revision,
                "items": [
                    {
                        "id": item.id,
                        "type": item.type,
                        "priority": item.priority,
                        "createdAtMs": item.created_at_ms,
                        "expiresAtMs": item.expires_at_ms,
                        "payload": item.payload,
                    }
                    for item in drained.items
                ],
                "hasMore": drained.has_more,
            }
        )

    async def enqueue_pending_work(
        self,
        node_id: str,
        *,
        work_type: NodePendingWorkType,
        priority: NodePendingWorkPriority | None = None,
        expires_in_ms: int | None = None,
        payload: dict[str, object] | None = None,
        wake: bool | None = None,
    ) -> GatewayNodePendingWorkEnqueueView:
        await self._sync()
        if self.registry.describe_known_node(node_id) is None:
            raise KeyError(node_id)
        queued = self.registry.enqueue_pending_work(
            node_id=node_id,
            work_type=work_type,
            priority=priority,
            expires_in_ms=expires_in_ms,
            payload=payload,
        )
        wake_triggered = False
        if wake is not False and not queued.deduped and self.registry.get(node_id) is None:
            wake_triggered = _wake_result_available(await self.wake_node(node_id))
        return GatewayNodePendingWorkEnqueueView.model_validate(
            {
                "nodeId": node_id,
                "revision": queued.revision,
                "queued": {
                    "id": queued.item.id,
                    "type": queued.item.type,
                    "priority": queued.item.priority,
                    "createdAtMs": queued.item.created_at_ms,
                    "expiresAtMs": queued.item.expires_at_ms,
                    "payload": queued.item.payload,
                },
                "wakeTriggered": wake_triggered,
            }
        )


def _catalog_paired_node_payload(node: GatewayPairedNode) -> dict[str, object | None]:
    return {
        "node_id": node.node_id,
        "display_name": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "core_version": node.core_version,
        "ui_version": node.ui_version,
        "client_id": None,
        "client_mode": None,
        "remote_ip": node.remote_ip,
        "device_family": node.device_family,
        "model_identifier": node.model_identifier,
        "path_env": None,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "permissions": node.permissions,
        "paired": True,
        "connected": False,
        "connected_at_ms": node.last_connected_at_ms,
        "approved_at_ms": node.approved_at_ms,
    }


def _merge_catalog_node_payload(
    persisted: dict[str, object | None],
    observed: dict[str, object | None],
) -> dict[str, object | None]:
    observed_caps = observed.get("caps")
    observed_commands = observed.get("commands")
    visible_commands = _visible_paired_commands(
        persisted.get("commands"),
        observed_commands,
    )
    return {
        "node_id": observed["node_id"],
        "display_name": observed.get("display_name") or persisted.get("display_name"),
        "platform": observed.get("platform") or persisted.get("platform"),
        "version": observed.get("version") or persisted.get("version"),
        "core_version": observed.get("core_version") or persisted.get("core_version"),
        "ui_version": observed.get("ui_version") or persisted.get("ui_version"),
        "client_id": observed.get("client_id"),
        "client_mode": observed.get("client_mode"),
        "remote_ip": observed.get("remote_ip") or persisted.get("remote_ip"),
        "device_family": observed.get("device_family") or persisted.get("device_family"),
        "model_identifier": observed.get("model_identifier") or persisted.get("model_identifier"),
        "path_env": observed.get("path_env"),
        "caps": observed_caps if observed_caps is not None else persisted.get("caps") or [],
        "commands": visible_commands if visible_commands is not None else [],
        "permissions": (
            observed.get("permissions")
            if observed.get("permissions") is not None
            else persisted.get("permissions")
        ),
        "paired": bool(observed.get("paired") or persisted.get("paired")),
        "connected": bool(observed.get("connected")),
        "connected_at_ms": (
            observed.get("connected_at_ms")
            if observed.get("connected_at_ms") is not None
            else persisted.get("connected_at_ms")
        ),
        "approved_at_ms": (
            observed.get("approved_at_ms")
            if observed.get("approved_at_ms") is not None
            else persisted.get("approved_at_ms")
        ),
    }


def _catalog_node_sort_key(payload: dict[str, object | None]) -> tuple[int, str, str]:
    display_name = str(payload.get("display_name") or payload.get("node_id") or "").strip().lower()
    return (0 if payload.get("connected") else 1, display_name, str(payload.get("node_id") or ""))


def _visible_paired_commands(
    persisted_commands: object,
    observed_commands: object,
) -> list[str] | None:
    approved = (
        [command for command in persisted_commands if isinstance(command, str)]
        if isinstance(persisted_commands, list)
        else None
    )
    live = (
        [command for command in observed_commands if isinstance(command, str)]
        if isinstance(observed_commands, list)
        else None
    )
    if live is None:
        return approved
    if approved is None:
        return live
    approved_set = set(approved)
    return [command for command in live if command in approved_set]
