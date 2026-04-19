from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from openzues.database import Database, utcnow
from openzues.schemas import (
    DiagnosticCheck,
    GatewayBootstrapView,
    GatewayCapabilityApprovalPostureView,
    GatewayCapabilityBrowserLaneView,
    GatewayCapabilityBrowserRuntimeView,
    GatewayCapabilityConnectedLaneHealthView,
    GatewayCapabilityDiagnosticsView,
    GatewayCapabilityEventCatalogView,
    GatewayCapabilityInventoryItemView,
    GatewayCapabilityInventoryView,
    GatewayCapabilityKnownNodeView,
    GatewayCapabilityLaneView,
    GatewayCapabilityLaunchPolicyView,
    GatewayCapabilityMemoryProofReferenceView,
    GatewayCapabilityMethodCatalogView,
    GatewayCapabilityMethodScopeView,
    GatewayCapabilityNodeCatalogView,
    GatewayCapabilityView,
    InstanceView,
    IntegrationView,
    MissionCreate,
    MissionView,
    OperatorView,
    ProjectView,
    RemoteRequestView,
    SignalLevel,
    TaskBlueprintView,
    TeamView,
)
from openzues.services.access import AccessService, build_access_posture
from openzues.services.continuity import build_continuity_packet
from openzues.services.environment import EnvironmentService
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.gateway_method_policy import (
    NODE_ROLE_GATEWAY_METHOD_SCOPE,
    ORDERED_OPERATOR_SCOPES,
    RESERVED_ADMIN_GATEWAY_METHOD_SCOPE,
    classify_gateway_methods,
    is_node_role_gateway_method,
    is_reserved_admin_gateway_method,
    list_known_gateway_events,
    list_known_gateway_methods,
)
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import (
    MEMPALACE_DIRECT_PROOF_MISSION_NAME,
    MEMPALACE_OPTIONAL_TOOLS,
    MEMPALACE_REQUIRED_TOOLS,
    build_mempalace_control_plane_proof_objective,
    is_mempalace_automation_task,
    is_mempalace_direct_proof_mission,
    is_mempalace_integration,
    parse_mempalace_control_plane_proof_signal,
    parse_mempalace_roundtrip_signal,
    parse_mempalace_writeback_signal,
)
from openzues.services.missions import MissionService
from openzues.services.ops_mesh import OpsMeshService, build_ops_mesh
from openzues.services.remote_ops import RemoteOpsService

logger = logging.getLogger(__name__)
GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True, slots=True)
class _MemoryProofLaunchTarget:
    instance_id: int
    instance_name: str
    project_id: int | None
    project_label: str | None
    cwd: str | None
    scope_label: str
    launch_label: str

    @property
    def session_key(self) -> str:
        scope = self.project_id if self.project_id is not None else "global"
        return f"gateway:memory-proof:{self.instance_id}:{scope}"


@dataclass(slots=True)
class _GatewayCapabilityNodeConnection:
    conn_id: str

    def send_gateway_event(self, event: str, payload: object) -> None:
        return None


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _diagnostic_evidence(check: DiagnosticCheck) -> str:
    detail = check.detail.strip()
    if not detail:
        return check.label
    return f"{check.label}: {detail}"


def _join_list(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _clip_text(value: str | None, *, limit: int = 220) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).split())
    if not cleaned:
        return None
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _catalog_item_name(item: object) -> str | None:
    if isinstance(item, str):
        name = item.strip()
        return name or None
    if not isinstance(item, dict):
        return None
    for key in ("name", "id", "uri", "method", "title", "serviceId"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    nested_service = item.get("service")
    if isinstance(nested_service, dict):
        for key in ("name", "id", "uri", "title"):
            raw = nested_service.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return None


def _plugin_entry_name(entry: object) -> str | None:
    if not isinstance(entry, dict):
        return None
    value = entry.get("name") or entry.get("id") or entry.get("source")
    if value is None:
        return None
    name = str(value).strip()
    return name or None


def _lane_plugin_names(
    instance: InstanceView,
    status_entries: list[dict[str, Any]] | None = None,
) -> list[str]:
    names: dict[str, str] = {}
    for entry in instance.plugins:
        if (name := _plugin_entry_name(entry)) is not None:
            names.setdefault(name.lower(), name)
    for entry in status_entries or []:
        source = entry.get("source")
        if source is None:
            continue
        name = str(source).strip()
        if name:
            names.setdefault(name.lower(), name)
    return sorted(names.values(), key=str.lower)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(UTC) - parsed).total_seconds() // 60))


def _format_age(minutes: int | None) -> str:
    if minutes is None:
        return "at an unknown time"
    if minutes < 60:
        return f"{minutes}m ago"
    if minutes < 24 * 60:
        hours, remainder = divmod(minutes, 60)
        return f"{hours}h {remainder}m ago" if remainder else f"{hours}h ago"
    days, remainder = divmod(minutes, 24 * 60)
    hours = remainder // 60
    return f"{days}d {hours}h ago" if hours else f"{days}d ago"


def _catalog_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, list):
        for item in value:
            if name := _catalog_item_name(item):
                names.append(name)
        return names
    if isinstance(value, dict):
        return [str(key).strip() for key in value if str(key).strip()]
    return []


def _catalog_method_scope_entries(value: Any) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                entries.append((item.strip(), None))
                continue
            if not isinstance(item, dict):
                continue
            name: str | None = None
            for key in ("name", "id", "uri", "method", "title"):
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    name = raw.strip()
                    break
            if name is None:
                continue
            raw_scope = item.get("scope")
            scope = raw_scope.strip() if isinstance(raw_scope, str) and raw_scope.strip() else None
            entries.append((name, scope))
        return entries
    if isinstance(value, dict):
        for key, raw_scope in value.items():
            name = str(key).strip()
            if not name:
                continue
            scope = (
                raw_scope.strip()
                if isinstance(raw_scope, str) and raw_scope.strip()
                else None
            )
            entries.append((name, scope))
    return entries


def _instance_connected_at_ms(instance: InstanceView) -> int:
    parsed = _parse_timestamp(instance.last_event_at)
    if parsed is None:
        return 0
    return int(parsed.timestamp() * 1000)


def _remembered_instance_node(instance: InstanceView) -> KnownNode:
    return KnownNode(
        node_id=str(instance.id),
        display_name=instance.name,
        platform=instance.transport,
        client_id=str(instance.id),
        client_mode=instance.transport,
        path_env=instance.cwd,
        paired=True,
        connected=False,
    )


def _build_known_node_catalog(instances: list[InstanceView]) -> GatewayCapabilityNodeCatalogView:
    registry = GatewayNodeRegistry()
    for instance in instances:
        registry.remember(_remembered_instance_node(instance))
        if not instance.connected:
            continue
        registry.register(
            _GatewayCapabilityNodeConnection(conn_id=f"gateway-capability:{instance.id}"),
            GatewayNodeConnect(
                client_id=str(instance.id),
                device_id=str(instance.id),
                client_mode=instance.transport,
                display_name=instance.name,
                platform=instance.transport,
                version=None,
                core_version=None,
                ui_version=None,
                device_family=None,
                model_identifier=None,
                caps=(),
                commands=(),
                permissions=None,
                path_env=instance.cwd,
            ),
            connected_at_ms=_instance_connected_at_ms(instance),
        )

    known_nodes = registry.list_known_nodes()
    nodes = [
        GatewayCapabilityKnownNodeView.model_validate(
            asdict(registry.describe_known_node(node.node_id) or node)
        )
        for node in known_nodes
    ]
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


def _is_browser_runtime_name(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and "browser" in text


def _build_browser_runtime_view(
    instances: list[InstanceView],
    mcp_server_status_by_instance: dict[int, list[dict[str, Any]]],
) -> GatewayCapabilityBrowserRuntimeView | None:
    lane_views: list[GatewayCapabilityBrowserLaneView] = []
    methods_by_name: dict[str, str] = {}
    services_by_name: dict[str, str] = {}
    plugins_by_name: dict[str, str] = {}
    servers_by_name: dict[str, str] = {}

    for instance in instances:
        status_entries = mcp_server_status_by_instance.get(instance.id, [])
        browser_methods = sorted(
            {
                method_name
                for entry in status_entries
                for method_name, _scope in _catalog_method_scope_entries(entry.get("tools"))
                if _is_browser_runtime_name(method_name)
                or method_name.lower().startswith("browser.")
            },
            key=str.lower,
        )
        browser_services = sorted(
            {
                service_name
                for entry in status_entries
                for service_name in _catalog_names(entry.get("services"))
                if _is_browser_runtime_name(service_name)
            },
            key=str.lower,
        )
        browser_plugins = [
            name
            for name in _lane_plugin_names(instance, status_entries)
            if _is_browser_runtime_name(name)
        ]
        browser_servers = sorted(
            {
                name
                for entry in [*instance.mcp_servers, *status_entries]
                if isinstance(entry, dict)
                and _is_browser_runtime_name(
                    str(entry.get("name") or entry.get("id") or entry.get("source") or "")
                )
                and (
                    name := str(
                        entry.get("name") or entry.get("id") or entry.get("source") or ""
                    ).strip()
                )
            },
            key=str.lower,
        )

        if not (
            browser_methods
            or browser_services
            or browser_plugins
            or browser_servers
        ):
            continue

        for method_name in browser_methods:
            methods_by_name.setdefault(method_name.lower(), method_name)
        for service_name in browser_services:
            services_by_name.setdefault(service_name.lower(), service_name)
        for plugin_name in browser_plugins:
            plugins_by_name.setdefault(plugin_name.lower(), plugin_name)
        for server_name in browser_servers:
            servers_by_name.setdefault(server_name.lower(), server_name)

        ready = instance.connected and bool(browser_methods) and bool(browser_services)
        if ready:
            level: SignalLevel = "ready"
            summary = (
                f"{instance.name} publishes {len(browser_methods)} browser method(s) and "
                f"{len(browser_services)} browser service(s)."
            )
        elif instance.connected:
            level = "warn"
            summary_parts = []
            if browser_methods:
                summary_parts.append(f"{len(browser_methods)} method(s)")
            if browser_services:
                summary_parts.append(f"{len(browser_services)} service(s)")
            if browser_plugins:
                summary_parts.append(f"{len(browser_plugins)} plugin signal(s)")
            if browser_servers:
                summary_parts.append(f"{len(browser_servers)} MCP server signal(s)")
            summary = (
                f"{instance.name} publishes {_join_list(summary_parts)}, but the full "
                "browser-control contract is not complete yet."
            )
        else:
            level = "info"
            summary = (
                f"{instance.name} shows browser runtime signals on an offline lane."
            )

        lane_views.append(
            GatewayCapabilityBrowserLaneView(
                instance_id=instance.id,
                instance_name=instance.name,
                connected=instance.connected,
                level=level,
                ready=ready,
                method_count=len(browser_methods),
                service_count=len(browser_services),
                methods=browser_methods,
                services=browser_services,
                plugins=browser_plugins,
                servers=browser_servers,
                summary=summary,
            )
        )

    if not lane_views:
        return None

    lane_views.sort(key=lambda lane: (not lane.connected, lane.instance_name.lower()))
    lane_count = len(lane_views)
    connected_lane_count = sum(lane.connected for lane in lane_views)
    ready_lane_count = sum(lane.ready for lane in lane_views)
    partial_connected_count = sum(lane.connected and not lane.ready for lane in lane_views)
    methods = sorted(methods_by_name.values(), key=str.lower)
    services = sorted(services_by_name.values(), key=str.lower)
    plugins = sorted(plugins_by_name.values(), key=str.lower)
    servers = sorted(servers_by_name.values(), key=str.lower)

    if ready_lane_count and not partial_connected_count:
        status: SignalLevel = "ready"
        headline = "Browser runtime is live"
        summary = (
            f"{ready_lane_count} connected lane(s) publish {len(methods)} browser method(s) "
            f"and {len(services)} browser service(s)."
        )
        recommended_action = (
            "Use the live browser lane when parity work needs browser-led verification or "
            "browser-control execution."
        )
    elif ready_lane_count:
        status = "warn"
        headline = "Browser runtime is live with gaps"
        summary = (
            f"{ready_lane_count} connected lane(s) publish the browser-control contract, "
            f"but {partial_connected_count} connected lane(s) still expose only part of it."
        )
        recommended_action = (
            "Refresh the partial browser lanes so methods and browser-control services "
            "publish together."
        )
    elif connected_lane_count:
        status = "warn"
        headline = "Browser runtime is partial"
        summary = (
            f"Browser runtime signals are visible on {connected_lane_count} connected lane(s), "
            "but no connected lane currently publishes both callable browser methods and "
            "browser-control services."
        )
        recommended_action = (
            "Refresh the connected browser lane so the callable browser methods and "
            "browser-control service publish together before relying on it."
        )
    else:
        status = "info"
        headline = "Browser runtime is only visible on offline lanes"
        summary = (
            f"{lane_count} offline lane(s) still advertise browser runtime signals, but no "
            "connected lane is ready right now."
        )
        recommended_action = (
            "Reconnect the browser lane before relying on browser-control parity."
        )

    if plugins:
        summary += f" Plugin signals: {_join_list(plugins[:3])}."
    if servers:
        summary += f" MCP servers: {_join_list(servers[:3])}."

    return GatewayCapabilityBrowserRuntimeView(
        headline=headline,
        summary=summary,
        status=status,
        lane_count=lane_count,
        connected_lane_count=connected_lane_count,
        ready_lane_count=ready_lane_count,
        method_count=len(methods),
        service_count=len(services),
        plugin_count=len(plugins),
        server_count=len(servers),
        methods=methods,
        services=services,
        plugins=plugins,
        servers=servers,
        recommended_action=recommended_action,
        lanes=lane_views,
    )


def _build_mempalace_tool_proof(
    instance: InstanceView,
    status_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    known_tools = set((*MEMPALACE_REQUIRED_TOOLS, *MEMPALACE_OPTIONAL_TOOLS))
    best_candidate: dict[str, Any] | None = None
    best_rank: tuple[int, int, int, str] | None = None

    for entry in status_entries:
        tool_names = set(_catalog_names(entry.get("tools")))
        if not (is_mempalace_integration(entry) or tool_names.intersection(known_tools)):
            continue

        server_name = (
            str(entry.get("name") or entry.get("source") or "MemPalace MCP server").strip()
            or "MemPalace MCP server"
        )
        missing_tools = [
            tool_name for tool_name in MEMPALACE_REQUIRED_TOOLS if tool_name not in tool_names
        ]
        available_tools = sorted(tool_names.intersection(known_tools))
        auth_status = str(entry.get("authStatus") or "").strip().lower()
        auth_gap = auth_status in {"missing", "degraded"}

        if not missing_tools and not auth_gap:
            summary = (
                f"{instance.name} exposes {server_name} with "
                f"{_join_list(list(MEMPALACE_REQUIRED_TOOLS))}."
            )
            action = ""
            status = "ready"
        else:
            summary = f"{instance.name} publishes {server_name}"
            if missing_tools and auth_gap:
                summary += (
                    f", but missing {_join_list(missing_tools)} and reporting auth status "
                    f"'{auth_status}'."
                )
                action = (
                    "Expose the full MemPalace tool contract and clear the lane auth gap before "
                    "relying on automatic memory maintenance."
                )
            elif missing_tools:
                summary += f", but missing {_join_list(missing_tools)}."
                action = (
                    "Expose mempalace_status, mempalace_search, and mempalace_diary_write on the "
                    "connected MemPalace lane before relying on automatic memory maintenance."
                )
            else:
                summary += f", but auth status is '{auth_status}'."
                action = (
                    "Clear the MemPalace MCP auth gap on the connected lane before relying on "
                    "automatic memory maintenance."
                )
            if available_tools:
                summary += f" Visible tools: {_join_list(available_tools)}."
            status = "warn"

        rank = (
            0 if status == "ready" else 1,
            len(missing_tools),
            -len(available_tools),
            server_name.lower(),
        )
        candidate = {
            "status": status,
            "summary": summary,
            "action": action,
        }
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_candidate = candidate

    return best_candidate


def _build_callable_method_catalog(
    instances: list[InstanceView],
    mcp_server_status_by_instance: dict[int, list[dict[str, Any]]],
) -> GatewayCapabilityMethodCatalogView:
    connected_lane_names: set[str] = set()
    server_names: dict[str, str] = {}
    tool_names: dict[str, str] = {}
    scoped_methods: dict[str, dict[str, str]] = {}

    for instance in instances:
        if not instance.connected:
            continue
        for entry in mcp_server_status_by_instance.get(instance.id, []):
            if not isinstance(entry, dict):
                continue
            server_name = str(entry.get("name") or entry.get("source") or "MCP server").strip()
            if not server_name:
                server_name = "MCP server"
            tool_entries = _catalog_method_scope_entries(entry.get("tools"))
            names = [name for name, _scope in tool_entries]
            if not names:
                continue
            connected_lane_names.add(instance.name)
            server_names.setdefault(server_name.lower(), server_name)
            for tool_name in names:
                tool_names.setdefault(tool_name.lower(), tool_name)
            plugin_method_scopes = {
                name.lower(): scope
                for name, scope in tool_entries
                if scope is not None
            }
            for scope, methods in classify_gateway_methods(
                names,
                plugin_method_scopes=plugin_method_scopes,
            ).items():
                bucket = scoped_methods.setdefault(scope, {})
                for method_name in methods:
                    bucket.setdefault(method_name.lower(), method_name)
            node_bucket = scoped_methods.setdefault(NODE_ROLE_GATEWAY_METHOD_SCOPE, {})
            for method_name in names:
                if is_node_role_gateway_method(method_name):
                    node_bucket.setdefault(method_name.lower(), method_name)

    tools = sorted(tool_names.values(), key=str.lower)
    servers = sorted(server_names.values(), key=str.lower)

    def _scope_groups_for_methods(method_names: list[str]) -> tuple[
        list[GatewayCapabilityMethodScopeView],
        int,
        list[str],
    ]:
        groups = [
            GatewayCapabilityMethodScopeView(
                scope=scope,
                method_count=len(methods),
                methods=methods,
            )
            for scope in ORDERED_OPERATOR_SCOPES
            if (methods := sorted(scoped_methods.get(scope, {}).values(), key=str.lower))
        ]
        if node_methods := sorted(
            scoped_methods.get(NODE_ROLE_GATEWAY_METHOD_SCOPE, {}).values(),
            key=str.lower,
        ):
            groups.append(
                GatewayCapabilityMethodScopeView(
                    scope=NODE_ROLE_GATEWAY_METHOD_SCOPE,
                    method_count=len(node_methods),
                    methods=node_methods,
                )
            )
        classified_count = sum(group.method_count for group in groups)
        reserved_admin_group = next(
            (
                group
                for group in groups
                if group.scope == RESERVED_ADMIN_GATEWAY_METHOD_SCOPE
            ),
            None,
        )
        reserved_methods = (
            [
                method
                for method in reserved_admin_group.methods
                if is_reserved_admin_gateway_method(method)
            ]
            if reserved_admin_group is not None
            else []
        )
        return groups, classified_count, reserved_methods

    scope_groups, classified_method_count, reserved_tools = _scope_groups_for_methods(tools)
    lane_count = len(connected_lane_names)

    if not tools:
        tools = list(list_known_gateway_methods())
        scoped_methods = {}
        for scope, methods in classify_gateway_methods(tools).items():
            bucket = scoped_methods.setdefault(scope, {})
            for method_name in methods:
                bucket.setdefault(method_name.lower(), method_name)
        node_bucket = scoped_methods.setdefault(NODE_ROLE_GATEWAY_METHOD_SCOPE, {})
        for method_name in tools:
            if is_node_role_gateway_method(method_name):
                node_bucket.setdefault(method_name.lower(), method_name)
        scope_groups, classified_method_count, reserved_tools = _scope_groups_for_methods(tools)

    if tools:
        if server_names:
            headline = "Gateway callable methods are visible"
            summary = (
                f"{len(tools)} callable method(s) are visible across {len(servers)} MCP server "
                f"catalog(s) on {lane_count} connected lane(s)."
            )
        else:
            headline = "Gateway method registry is staged"
            summary = (
                f"{len(tools)} built-in gateway method(s) are registered locally while "
                "lane-published MCP catalogs are offline."
            )
        if scope_groups:
            scope_summary = ", ".join(
                f"{group.scope} {group.method_count}" for group in scope_groups
            )
            summary += f" Scope coverage: {scope_summary}."
        if reserved_tools:
            summary += (
                f" {len(reserved_tools)} reserved admin method(s) require "
                f"{RESERVED_ADMIN_GATEWAY_METHOD_SCOPE}."
            )
    elif servers:
        headline = "Gateway callable methods are staged"
        summary = (
            f"{len(servers)} MCP server catalog(s) are visible on {lane_count} connected "
            "lane(s), but no callable tool names were published yet."
        )
    else:
        headline = "Gateway callable methods are idle"
        summary = "No lane-published MCP server catalogs are exposing callable tools yet."

    return GatewayCapabilityMethodCatalogView(
        headline=headline,
        summary=summary,
        tool_count=len(tools),
        server_count=len(servers),
        lane_count=lane_count,
        classified_method_count=classified_method_count,
        reserved_admin_method_count=len(reserved_tools),
        reserved_admin_scope=(
            RESERVED_ADMIN_GATEWAY_METHOD_SCOPE if reserved_tools else None
        ),
        tools=tools,
        servers=servers,
        reserved_admin_methods=reserved_tools,
        scopes=scope_groups,
    )


def _build_gateway_event_catalog() -> GatewayCapabilityEventCatalogView:
    events = list(list_known_gateway_events())
    return GatewayCapabilityEventCatalogView(
        headline="Gateway event registry is staged",
        summary=(
            f"{len(events)} built-in gateway event(s) are registered locally to mirror "
            "the OpenClaw event surface while lane-published event catalogs are offline."
        ),
        event_count=len(events),
        events=events,
    )


def _task_value(task: Any, field: str) -> Any:
    if isinstance(task, dict):
        return task.get(field)
    return getattr(task, field, None)


def _task_reference_time(task: Any) -> datetime:
    last_launched = _parse_timestamp(str(_task_value(task, "last_launched_at") or ""))
    if last_launched is not None:
        return last_launched
    updated_at = _task_value(task, "updated_at")
    if isinstance(updated_at, datetime):
        return updated_at
    return datetime.min.replace(tzinfo=UTC)


def _build_memory_loop_freshness(tasks: list[Any]) -> dict[str, str] | None:
    if not tasks:
        return None

    task = max(tasks, key=_task_reference_time)
    task_name = (
        str(_task_value(task, "name") or "MemPalace Memory Loop").strip() or "MemPalace Memory Loop"
    )
    last_status = str(_task_value(task, "last_status") or "").strip().lower()
    last_launched_at = str(_task_value(task, "last_launched_at") or "").strip() or None
    last_result_summary = str(_task_value(task, "last_result_summary") or "").strip()
    cadence_minutes = _task_value(task, "cadence_minutes")
    cadence = int(cadence_minutes) if isinstance(cadence_minutes, int) else None
    age_minutes = _minutes_since(last_launched_at)

    if last_status == "failed":
        summary = f"{task_name} last failed {_format_age(age_minutes)}."
        if last_result_summary:
            summary += f" {last_result_summary}"
        return {
            "status": "warn",
            "summary": summary,
            "action": (
                "Inspect the failed MemPalace maintenance run and repair the lane or tool gap "
                "before relying on automatic memory refresh."
            ),
        }
    if last_status == "completed":
        summary = f"{task_name} last completed {_format_age(age_minutes)}."
        if last_result_summary:
            summary += f" {last_result_summary}"
        if cadence is not None and age_minutes is not None and age_minutes > cadence * 2:
            return {
                "status": "warn",
                "summary": (
                    f"{summary} The maintenance loop is overdue for its {cadence}m cadence."
                ),
                "action": (
                    "Trigger or inspect the MemPalace maintenance loop so memory freshness does "
                    "not drift behind the configured cadence."
                ),
            }
        return {"status": "ready", "summary": summary, "action": ""}
    if last_status == "active":
        return {
            "status": "info",
            "summary": f"{task_name} is running right now.",
            "action": "",
        }
    return {
        "status": "info",
        "summary": (f"{task_name} is armed but has not completed its first maintenance pass yet."),
        "action": "",
    }


def _latest_missions_by_task(missions: list[MissionView]) -> dict[int, MissionView]:
    latest: dict[int, MissionView] = {}
    for mission in missions:
        if mission.task_blueprint_id is None:
            continue
        current = latest.get(mission.task_blueprint_id)
        if current is None or mission.updated_at > current.updated_at:
            latest[mission.task_blueprint_id] = mission
    return latest


def _memory_task_report_text(
    task: Any,
    *,
    latest_missions_by_task: dict[int, MissionView],
) -> str:
    task_id = _task_value(task, "id")
    latest_mission = latest_missions_by_task.get(task_id) if isinstance(task_id, int) else None
    if latest_mission is not None and latest_mission.last_checkpoint:
        return latest_mission.last_checkpoint
    return str(_task_value(task, "last_result_summary") or "")


def _format_writeback_scope(task: Any, project_labels: dict[int, str]) -> str:
    project_id = _task_value(task, "project_id")
    if isinstance(project_id, int) and project_id in project_labels:
        return project_labels[project_id]
    return "global memory scope"


def _build_memory_writeback_freshness(
    tasks: list[Any],
    *,
    project_labels: dict[int, str],
    latest_missions_by_task: dict[int, MissionView],
) -> dict[str, Any] | None:
    if not tasks:
        return None

    successful: list[tuple[datetime, str]] = []
    warnings: list[str] = []
    missing: list[str] = []

    for task in tasks:
        scope_label = _format_writeback_scope(task, project_labels)
        signal = parse_mempalace_writeback_signal(
            _memory_task_report_text(task, latest_missions_by_task=latest_missions_by_task)
        )
        if signal is None:
            if str(_task_value(task, "last_status") or "").strip().lower() == "completed":
                missing.append(scope_label)
            continue
        if signal["successful"]:
            successful.append((signal["at"], scope_label))
            continue
        status = str(signal["status"] or "").strip() or "unreported"
        detail = f"{scope_label} writeback status is '{status}'."
        if signal.get("at_text") and str(signal["at_text"]).lower() not in {
            "n/a",
            "na",
            "none",
            "unknown",
        }:
            detail += f" Reported time: {signal['at_text']}."
        warnings.append(detail)

    if successful:
        successful.sort(key=lambda item: item[0], reverse=True)
        latest_at, latest_scope = successful[0]
        newest_age = _format_age(_minutes_since(latest_at.isoformat()))
        summary = f"Last durable writeback was reported {newest_age} for {latest_scope}."
        if len(successful) > 1:
            summary += f" {len(successful)} memory scope(s) have explicit writeback proof."
        return {
            "status": "ready",
            "summary": summary,
            "evidence": [
                (
                    f"{scope_label} writeback reported at "
                    f"{at.astimezone(UTC).isoformat().replace('+00:00', 'Z')}."
                )
                for at, scope_label in successful[:3]
            ],
            "action": "",
        }
    if warnings:
        return {
            "status": "warn",
            "summary": warnings[0],
            "evidence": warnings[:3],
            "action": (
                "Run the MemPalace maintenance loop again and return an explicit writeback "
                "status/timestamp block so durable recall freshness is provable."
            ),
        }
    if missing:
        scope_phrase = _join_list(missing[:3])
        return {
            "status": "info",
            "summary": (
                f"{scope_phrase} completed memory maintenance, but no explicit durable writeback "
                "timestamp has been reported yet."
            ),
            "evidence": [
                (
                    f"{scope_label} has no structured writeback signal yet. The next maintenance "
                    "run should report one."
                )
                for scope_label in missing[:3]
            ],
            "action": "",
        }
    return None


def _build_memory_roundtrip_freshness(
    tasks: list[Any],
    *,
    project_labels: dict[int, str],
    latest_missions_by_task: dict[int, MissionView],
) -> dict[str, Any] | None:
    if not tasks:
        return None

    successful: list[tuple[datetime, str, str | None]] = []
    warnings: list[str] = []
    missing: list[str] = []

    for task in tasks:
        scope_label = _format_writeback_scope(task, project_labels)
        signal = parse_mempalace_roundtrip_signal(
            _memory_task_report_text(task, latest_missions_by_task=latest_missions_by_task)
        )
        if signal is None:
            if str(_task_value(task, "last_status") or "").strip().lower() == "completed":
                missing.append(scope_label)
            continue
        if signal["successful"]:
            successful.append((signal["at"], scope_label, signal.get("detail")))
            continue
        status = str(signal["status"] or "").strip() or "unreported"
        warning_detail = f"{scope_label} roundtrip status is '{status}'."
        if signal.get("detail"):
            warning_detail += f" {signal['detail']}"
        if signal.get("at_text") and str(signal["at_text"]).lower() not in {
            "n/a",
            "na",
            "none",
            "unknown",
        }:
            warning_detail += f" Reported time: {signal['at_text']}."
        warnings.append(warning_detail)

    if successful:
        successful.sort(key=lambda item: item[0], reverse=True)
        latest_at, latest_scope, _ = successful[0]
        newest_age = _format_age(_minutes_since(latest_at.isoformat()))
        summary = f"Last MemPalace roundtrip proof was reported {newest_age} for {latest_scope}."
        if len(successful) > 1:
            summary += f" {len(successful)} memory scope(s) have explicit readback proof."
        evidence: list[str] = []
        for at, scope_label, proof_detail in successful[:3]:
            timestamp = at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            line = f"{scope_label} roundtrip verified at {timestamp}."
            if proof_detail:
                line += f" {proof_detail}"
            evidence.append(line)
        return {
            "status": "ready",
            "summary": summary,
            "evidence": evidence,
            "action": "",
        }
    if warnings:
        return {
            "status": "warn",
            "summary": warnings[0],
            "evidence": warnings[:3],
            "action": (
                "Run the MemPalace maintenance loop again and confirm the freshly written memory "
                "can be recalled through mempalace_search or mempalace_diary_read before "
                "treating memory as fully proven."
            ),
        }
    if missing:
        scope_phrase = _join_list(missing[:3])
        return {
            "status": "info",
            "summary": (
                f"{scope_phrase} completed memory maintenance, but no explicit MemPalace "
                "roundtrip proof has been reported yet."
            ),
            "evidence": [
                (
                    f"{scope_label} has no structured roundtrip signal yet. The next maintenance "
                    "run should confirm recall through mempalace_search or mempalace_diary_read."
                )
                for scope_label in missing[:3]
            ],
            "action": "",
        }
    return None


def _build_task_memory_proof_reference(
    tasks: list[Any],
    *,
    project_labels: dict[int, str],
    latest_missions_by_task: dict[int, MissionView],
) -> GatewayCapabilityMemoryProofReferenceView | None:
    latest_pair: tuple[Any, MissionView] | None = None
    for task in tasks:
        task_id = _task_value(task, "id")
        if not isinstance(task_id, int):
            continue
        mission = latest_missions_by_task.get(task_id)
        if mission is None:
            continue
        if latest_pair is None or mission.updated_at > latest_pair[1].updated_at:
            latest_pair = (task, mission)
    if latest_pair is None:
        return None

    task, mission = latest_pair
    scope_label = _format_writeback_scope(task, project_labels)
    report_text = _memory_task_report_text(task, latest_missions_by_task=latest_missions_by_task)
    roundtrip_signal = parse_mempalace_roundtrip_signal(report_text)
    writeback_signal = parse_mempalace_writeback_signal(report_text)
    checkpoint_excerpt = _clip_text(mission.last_checkpoint or report_text, limit=240)
    task_name = str(_task_value(task, "name") or mission.name).strip() or mission.name

    if roundtrip_signal is not None:
        signal_scope = str(roundtrip_signal.get("scope") or "").strip() or scope_label
        detail = _clip_text(roundtrip_signal.get("detail"), limit=180)
        if roundtrip_signal["successful"]:
            age = _format_age(_minutes_since(roundtrip_signal["at"].isoformat()))
            summary = (
                f"Mission {mission.id} ({mission.name}) verified MemPalace roundtrip recall "
                f"{age} for {signal_scope}."
            )
        else:
            summary = (
                f"Mission {mission.id} ({mission.name}) reported MemPalace roundtrip status "
                f"'{roundtrip_signal['status'] or 'unreported'}' for {signal_scope}."
            )
        if detail:
            summary += f" {detail}"
        return GatewayCapabilityMemoryProofReferenceView(
            mission_id=mission.id,
            mission_name=mission.name,
            task_blueprint_id=mission.task_blueprint_id,
            task_name=task_name,
            scope_label=signal_scope,
            proof_kind="roundtrip",
            proof_status=str(roundtrip_signal["status"] or ""),
            summary=summary,
            checkpoint_excerpt=checkpoint_excerpt,
            continuity_path=f"/api/missions/{mission.id}/continuity",
            updated_at=mission.updated_at,
        )

    if writeback_signal is not None:
        signal_scope = str(writeback_signal.get("scope") or "").strip() or scope_label
        if writeback_signal["successful"]:
            age = _format_age(_minutes_since(writeback_signal["at"].isoformat()))
            summary = (
                f"Mission {mission.id} ({mission.name}) reported durable MemPalace writeback "
                f"{age} for {signal_scope}, but no structured roundtrip block is visible yet."
            )
        else:
            summary = (
                f"Mission {mission.id} ({mission.name}) reported MemPalace writeback status "
                f"'{writeback_signal['status'] or 'unreported'}' for {signal_scope}."
            )
        return GatewayCapabilityMemoryProofReferenceView(
            mission_id=mission.id,
            mission_name=mission.name,
            task_blueprint_id=mission.task_blueprint_id,
            task_name=task_name,
            scope_label=signal_scope,
            proof_kind="writeback",
            proof_status=str(writeback_signal["status"] or ""),
            summary=summary,
            checkpoint_excerpt=checkpoint_excerpt,
            continuity_path=f"/api/missions/{mission.id}/continuity",
            updated_at=mission.updated_at,
        )

    summary = (
        f"Mission {mission.id} ({mission.name}) is the latest MemPalace maintenance checkpoint "
        f"for {scope_label}, but no structured proof block was reported."
    )
    return GatewayCapabilityMemoryProofReferenceView(
        mission_id=mission.id,
        mission_name=mission.name,
        task_blueprint_id=mission.task_blueprint_id,
        task_name=task_name,
        scope_label=scope_label,
        proof_kind="checkpoint",
        proof_status=mission.status,
        summary=summary,
        checkpoint_excerpt=checkpoint_excerpt,
        continuity_path=f"/api/missions/{mission.id}/continuity",
        updated_at=mission.updated_at,
    )


def _build_direct_memory_proof_state(
    missions: list[MissionView],
    *,
    project_labels: dict[int, str],
) -> dict[str, Any] | None:
    latest = max(
        (mission for mission in missions if is_mempalace_direct_proof_mission(mission)),
        key=lambda mission: mission.updated_at,
        default=None,
    )
    if latest is None:
        return None

    scope_label = (
        (project_labels.get(latest.project_id) if latest.project_id is not None else None)
        or latest.project_label
        or latest.instance_name
        or "connected memory lane"
    )
    checkpoint_excerpt = _clip_text(latest.last_checkpoint or latest.objective, limit=240)
    signal = parse_mempalace_control_plane_proof_signal(latest.last_checkpoint)

    if signal is None:
        summary = (
            f"Mission {latest.id} ({latest.name}) is the latest direct MemPalace proof "
            "checkpoint for "
            f"{scope_label}, but no structured control-plane proof block was reported."
        )
        reference = GatewayCapabilityMemoryProofReferenceView(
            mission_id=latest.id,
            mission_name=latest.name,
            task_blueprint_id=latest.task_blueprint_id,
            task_name=latest.name,
            scope_label=scope_label,
            proof_kind="checkpoint",
            proof_status=latest.status,
            summary=summary,
            checkpoint_excerpt=checkpoint_excerpt,
            continuity_path=f"/api/missions/{latest.id}/continuity",
            updated_at=latest.updated_at,
        )
        return {
            "status": "info",
            "summary": (
                f"Last backend-triggered memory proof for {scope_label} did not "
                "report a structured "
                "control-plane proof block yet."
            ),
            "evidence": [summary],
            "action": (
                "Rerun the direct memory proof so Gateway Doctor can capture a structured "
                "control-plane MemPalace proof."
            ),
            "reference": reference,
        }

    signal_scope = str(signal.get("scope") or "").strip() or scope_label
    detail = _clip_text(signal.get("detail"), limit=180)
    at_value = signal["at"].isoformat() if signal.get("at") is not None else signal.get("at_text")
    proof_age = _format_age(_minutes_since(str(at_value or "")))

    if signal["successful"]:
        summary = (
            f"Last backend-triggered control-plane proof verified live MemPalace access "
            f"{proof_age} for {signal_scope}."
        )
        reference_summary = (
            f"Mission {latest.id} ({latest.name}) verified backend-triggered MemPalace access "
            f"{proof_age} for {signal_scope}."
        )
        evidence = [
            (f"{signal_scope} direct proof verified through live MemPalace calls {proof_age}.")
        ]
        if detail:
            evidence.append(detail)
        action = ""
        status = "ready"
    else:
        proof_status = str(signal.get("status") or "unreported").strip() or "unreported"
        summary = (
            f"Last backend-triggered control-plane proof reported status '{proof_status}' for "
            f"{signal_scope}."
        )
        reference_summary = (
            f"Mission {latest.id} ({latest.name}) reported control-plane proof status "
            f"'{proof_status}' for {signal_scope}."
        )
        evidence = [summary]
        if detail:
            evidence.append(detail)
        action = (
            "Run the direct memory proof again after reconnecting or repairing the MemPalace "
            "lane so Gateway Doctor has live control-plane evidence."
        )
        status = "warn"

    if detail:
        reference_summary += f" {detail}"

    reference = GatewayCapabilityMemoryProofReferenceView(
        mission_id=latest.id,
        mission_name=latest.name,
        task_blueprint_id=latest.task_blueprint_id,
        task_name=latest.name,
        scope_label=signal_scope,
        proof_kind="control_plane",
        proof_status=str(signal.get("status") or ""),
        summary=reference_summary,
        checkpoint_excerpt=checkpoint_excerpt,
        continuity_path=f"/api/missions/{latest.id}/continuity",
        updated_at=latest.updated_at,
    )
    return {
        "status": status,
        "summary": summary,
        "evidence": evidence[:3],
        "action": action,
        "reference": reference,
    }


def _build_memory_proof_continuity(
    *,
    reference: GatewayCapabilityMemoryProofReferenceView | None,
    missions: list[MissionView],
    instances: list[InstanceView],
    project_labels: dict[int, str],
) -> Any | None:
    if reference is None:
        return None
    mission = next(
        (candidate for candidate in missions if candidate.id == reference.mission_id),
        None,
    )
    if mission is None:
        return None
    instance_connected = next(
        (instance.connected for instance in instances if instance.id == mission.instance_id),
        False,
    )
    return build_continuity_packet(
        mission,
        instance_connected=instance_connected,
        checkpoints=mission.checkpoints,
        project_label=project_labels.get(mission.project_id)
        if mission.project_id is not None
        else None,
    )


def _serialize_project(row: dict[str, Any]) -> ProjectView:
    path = Path(str(row["path"])).expanduser()
    return ProjectView.model_validate(
        {
            **row,
            "exists": path.exists(),
            "is_git_repo": False,
            "branch": None,
            "git_status": None,
            "recent_commits": [],
            "pull_requests": [],
            "last_scan_at": None,
        }
    )


class GatewayCapabilityService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        missions: MissionService,
        access: AccessService,
        remote_ops: RemoteOpsService,
        ops_mesh: OpsMeshService,
        gateway_bootstrap: GatewayBootstrapService,
        environment: EnvironmentService,
    ) -> None:
        self.database = database
        self.manager = manager
        self.missions = missions
        self.access = access
        self.remote_ops = remote_ops
        self.ops_mesh = ops_mesh
        self.gateway_bootstrap = gateway_bootstrap
        self.environment = environment

    async def get_view(self) -> GatewayCapabilityView:
        diagnostics = self.environment.collect()
        gateway_task = asyncio.create_task(self.gateway_bootstrap.get_view())
        instances_task = asyncio.create_task(self.manager.list_views())
        missions_task = asyncio.create_task(self.missions.list_views())
        teams_task = asyncio.create_task(self.access.list_team_views())
        operators_task = asyncio.create_task(self.access.list_operator_views())
        remote_requests_task = asyncio.create_task(self.remote_ops.list_remote_request_views())
        integrations_task = asyncio.create_task(self.ops_mesh.list_integration_views())
        task_blueprints_task = asyncio.create_task(self.ops_mesh.list_task_blueprint_views())
        projects_task = asyncio.create_task(self.database.list_projects())

        await instances_task
        gathered = await asyncio.gather(
            gateway_task,
            missions_task,
            teams_task,
            operators_task,
            remote_requests_task,
            integrations_task,
            task_blueprints_task,
            projects_task,
        )
        gateway = cast(GatewayBootstrapView, gathered[0])
        missions = cast(list[MissionView], gathered[1])
        teams = cast(list[TeamView], gathered[2])
        operators = cast(list[OperatorView], gathered[3])
        remote_requests = cast(list[RemoteRequestView], gathered[4])
        integrations = cast(list[IntegrationView], gathered[5])
        task_blueprints = cast(list[TaskBlueprintView], gathered[6])
        project_rows = cast(list[dict[str, Any]], gathered[7])
        instances = await self.manager.list_views()
        mcp_server_status_by_instance = await self._load_mcp_server_status_catalog(instances)
        access_posture = build_access_posture(teams, operators, remote_requests)
        projects = [_serialize_project(project) for project in project_rows]
        ops_view = build_ops_mesh(
            instances,
            missions,
            projects,
            [],
            [],
            [],
            [],
            integrations,
            [],
            [],
            access_posture=access_posture,
            teams=teams,
            operators=operators,
            remote_requests=remote_requests,
        )

        connected_lane_health = self._build_lane_health(
            instances,
            mcp_server_status_by_instance=mcp_server_status_by_instance,
        )
        inventory = self._build_inventory(
            instances,
            ops_view.integrations_inventory,
            gateway=gateway,
            integrations=integrations,
            missions=missions,
            projects=projects,
            project_labels={project.id: project.label for project in projects},
            mcp_server_status_by_instance=mcp_server_status_by_instance,
            task_blueprints=task_blueprints,
        )
        approval_posture = self._build_approval_posture(
            gateway=gateway,
            lanes=connected_lane_health,
            access_posture=access_posture,
            remote_requests=remote_requests,
        )
        diagnostics_view = self._build_diagnostics_summary(diagnostics.checks)
        launch_policy_summary = gateway.launch_defaults_summary
        if (
            gateway.launch_route is not None
            and gateway.launch_route.conversation_reuse is not None
        ):
            launch_policy_summary = (
                f"{launch_policy_summary} {gateway.launch_route.conversation_reuse.summary}"
            ).strip()
        launch_policy = GatewayCapabilityLaunchPolicyView(
            headline=(
                "Saved remote launch policy"
                if gateway.setup_mode == "remote"
                else "Saved local launch policy"
            ),
            summary=launch_policy_summary,
            setup_mode=gateway.setup_mode,
            setup_flow=gateway.setup_flow,
            route_binding_mode=gateway.route_binding_mode,
            run_verification=gateway.run_verification,
            use_builtin_agents=gateway.use_builtin_agents,
            auto_commit=gateway.auto_commit,
            pause_on_approval=gateway.pause_on_approval,
            auto_recover=gateway.auto_recover,
            auto_recover_limit=gateway.auto_recover_limit,
            allow_failover=gateway.allow_failover,
            model=gateway.model,
            max_turns=gateway.max_turns,
            toolsets=gateway.toolsets,
            tool_policy=gateway.tool_policy,
            launch_route=gateway.launch_route,
        )

        warnings = _unique(
            [
                *gateway.warnings,
                *(gateway.launch_route.warnings if gateway.launch_route is not None else []),
                *(diagnostics_view.evidence[:2] if diagnostics_view.fail_count else []),
                (inventory.memory_summary if inventory.memory_status == "warn" else ""),
                (inventory.summary if inventory.tracked_gap_count else ""),
                (
                    "All registered lanes are offline right now."
                    if connected_lane_health.total_count
                    and not connected_lane_health.connected_count
                    else ""
                ),
                (approval_posture.summary if approval_posture.approval_count else ""),
            ]
        )
        warnings = [warning for warning in warnings if warning]

        level = self._resolve_level(
            gateway=gateway,
            diagnostics=diagnostics_view,
            connected_lane_health=connected_lane_health,
            inventory=inventory,
            approval_posture=approval_posture,
        )
        headline = self._build_headline(level=level, gateway=gateway)
        summary = self._build_summary(
            gateway=gateway,
            lanes=connected_lane_health,
            inventory=inventory,
            approvals=approval_posture,
        )

        return GatewayCapabilityView(
            level=level,
            headline=headline,
            summary=summary,
            warnings=warnings,
            connected_lane_health=connected_lane_health,
            inventory=inventory,
            approval_posture=approval_posture,
            launch_policy=launch_policy,
            diagnostics=diagnostics_view,
            checked_at=diagnostics.checked_at or utcnow(),
        )

    async def launch_memory_proof(self, *, instance_id: int | None = None) -> MissionView:
        gateway = await self.gateway_bootstrap.get_view()
        instances = await self.manager.list_views()
        instance_by_id = {instance.id: instance for instance in instances}
        if instance_id is not None and instance_id not in instance_by_id:
            raise ValueError(f"Unknown instance {instance_id}.")

        mcp_server_status_by_instance = await self._load_mcp_server_status_catalog(instances)
        task_blueprints = await self.ops_mesh.list_task_blueprint_views()
        projects = [_serialize_project(project) for project in await self.database.list_projects()]
        target = self._select_memory_proof_launch_target(
            instances=instances,
            gateway=gateway,
            projects=projects,
            task_blueprints=task_blueprints,
            mcp_server_status_by_instance=mcp_server_status_by_instance,
            requested_instance_id=instance_id,
        )
        if target is None:
            if instance_id is not None:
                instance = instance_by_id[instance_id]
                if not instance.connected:
                    raise ValueError(
                        f"{instance.name} is not connected, so Gateway Doctor cannot "
                        "launch a direct memory proof there yet."
                    )
                raise ValueError(
                    f"{instance.name} does not currently expose the full live "
                    "MemPalace tool contract needed for a direct proof."
                )
            raise ValueError(
                "No connected lane currently exposes the full live MemPalace tool "
                "contract needed for a direct proof."
            )

        runtime = await self.manager.get(target.instance_id)
        if not runtime.connected:
            runtime = await self.manager.connect_instance(target.instance_id)
        if not runtime.connected or runtime.client is None:
            raise ValueError(
                f"{target.instance_name} is not connected, so Gateway Doctor cannot "
                "launch a direct memory proof there yet."
            )

        existing = await self._find_inflight_memory_proof(target.session_key)
        if existing is not None:
            if existing.status == "paused":
                return await self.missions.run_now(existing.id)
            return existing

        payload = MissionCreate(
            name=f"{MEMPALACE_DIRECT_PROOF_MISSION_NAME}: {target.scope_label}",
            objective=build_mempalace_control_plane_proof_objective(
                project_label=target.project_label or target.scope_label,
                project_path=target.cwd or runtime.cwd,
            ),
            instance_id=target.instance_id,
            project_id=target.project_id,
            task_blueprint_id=None,
            cwd=target.cwd or runtime.cwd,
            thread_id=None,
            session_key=target.session_key,
            model=gateway.model,
            reasoning_effort=None,
            collaboration_mode=None,
            max_turns=1,
            use_builtin_agents=False,
            run_verification=False,
            auto_commit=False,
            pause_on_approval=gateway.pause_on_approval,
            allow_auto_reflexes=False,
            auto_recover=False,
            auto_recover_limit=0,
            reflex_cooldown_seconds=gateway.reflex_cooldown_seconds,
            allow_failover=False,
            toolsets=[],
            start_immediately=False,
        )
        mission = await self.missions.create(payload)
        return await self.missions.run_now(mission.id)

    async def _find_inflight_memory_proof(self, session_key: str) -> MissionView | None:
        missions = await self.missions.list_views()
        candidates = [
            mission
            for mission in missions
            if mission.session_key == session_key
            and mission.status in {"active", "blocked", "paused"}
            and is_mempalace_direct_proof_mission(mission)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda mission: mission.updated_at, reverse=True)
        return candidates[0]

    def _select_memory_proof_launch_target(
        self,
        *,
        instances: list[InstanceView],
        gateway: GatewayBootstrapView,
        projects: list[ProjectView],
        task_blueprints: list[Any],
        mcp_server_status_by_instance: dict[int, list[dict[str, Any]]],
        requested_instance_id: int | None,
    ) -> _MemoryProofLaunchTarget | None:
        ready_instances = {
            instance.id: instance
            for instance in instances
            if instance.connected
            and (
                (
                    proof := _build_mempalace_tool_proof(
                        instance,
                        mcp_server_status_by_instance.get(instance.id, []),
                    )
                )
                is not None
                and proof["status"] == "ready"
            )
        }
        if requested_instance_id is not None and requested_instance_id not in ready_instances:
            return None

        project_by_id = {project.id: project for project in projects}
        candidate_by_key: dict[
            tuple[int, int | None], tuple[tuple[int, int, str], _MemoryProofLaunchTarget]
        ] = {}

        def add_candidate(
            *,
            instance_id: int,
            project_id: int | None,
            cwd: str | None,
            project_label: str | None,
            source_rank: int,
        ) -> None:
            if instance_id not in ready_instances:
                return
            if requested_instance_id is not None and requested_instance_id != instance_id:
                return
            instance = ready_instances[instance_id]
            project = project_by_id.get(project_id) if project_id is not None else None
            resolved_project_label = project.label if project is not None else project_label
            resolved_cwd = (
                cwd
                or (project.path if project is not None else instance.cwd)
                or gateway.default_cwd
            )
            scope_label = resolved_project_label or instance.name
            target = _MemoryProofLaunchTarget(
                instance_id=instance.id,
                instance_name=instance.name,
                project_id=project.id if project is not None else project_id,
                project_label=resolved_project_label,
                cwd=resolved_cwd,
                scope_label=scope_label,
                launch_label=f"Run direct memory proof for {scope_label}",
            )
            preferred_rank = (
                0 if gateway.instance is not None and gateway.instance.id == instance.id else 1
            )
            score = (source_rank, preferred_rank, scope_label.lower())
            key = (target.instance_id, target.project_id)
            current = candidate_by_key.get(key)
            if current is None or score < current[0]:
                candidate_by_key[key] = (score, target)

        for task in task_blueprints:
            if not getattr(task, "enabled", False) or not is_mempalace_automation_task(task):
                continue
            task_instance_id = getattr(task, "instance_id", None)
            if not isinstance(task_instance_id, int):
                continue
            task_project_id = getattr(task, "project_id", None)
            add_candidate(
                instance_id=task_instance_id,
                project_id=task_project_id if isinstance(task_project_id, int) else None,
                cwd=getattr(task, "cwd", None),
                project_label=(
                    project_by_id[task_project_id].label
                    if isinstance(task_project_id, int) and task_project_id in project_by_id
                    else None
                ),
                source_rank=0,
            )

        if gateway.instance is not None:
            gateway_project_id = gateway.project.id if gateway.project is not None else None
            add_candidate(
                instance_id=gateway.instance.id,
                project_id=gateway_project_id,
                cwd=gateway.default_cwd,
                project_label=gateway.project.label if gateway.project is not None else None,
                source_rank=1,
            )

        for instance in ready_instances.values():
            add_candidate(
                instance_id=instance.id,
                project_id=None,
                cwd=instance.cwd or gateway.default_cwd,
                project_label=None,
                source_rank=2,
            )

        if not candidate_by_key:
            return None
        return min(candidate_by_key.values(), key=lambda item: item[0])[1]

    async def _load_mcp_server_status_catalog(
        self,
        instances: list[InstanceView],
    ) -> dict[int, list[dict[str, Any]]]:
        connected_instances = [instance for instance in instances if instance.connected]
        if not connected_instances:
            return {}

        status_by_instance: dict[int, list[dict[str, Any]]] = {}
        responses = await asyncio.gather(
            *(self._refresh_mcp_server_status(instance.id) for instance in connected_instances)
        )
        for instance, response in zip(connected_instances, responses, strict=False):
            status_by_instance[instance.id] = response
        return status_by_instance

    async def _refresh_mcp_server_status(
        self,
        instance_id: int,
    ) -> list[dict[str, Any]]:
        runtime = self.manager.instances.get(instance_id)
        cached = [
            dict(item)
            for item in (runtime.mcp_server_status if runtime is not None else [])
            if isinstance(item, dict)
        ]
        if cached:
            return cached
        try:
            response = await asyncio.wait_for(
                self.manager.list_mcp_server_status(instance_id, refresh=True),
                timeout=GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning(
                "Gateway capability timed out while refreshing MCP server status for instance %s; "
                "using cached lane status instead.",
                instance_id,
            )
            return cached
        except Exception as exc:
            logger.warning(
                "Gateway capability could not load MCP server status for instance %s: %s",
                instance_id,
                exc,
            )
            return cached
        return response if isinstance(response, list) else cached

    def _build_lane_health(
        self,
        instances: list[InstanceView],
        *,
        mcp_server_status_by_instance: dict[int, list[dict[str, Any]]],
    ) -> GatewayCapabilityConnectedLaneHealthView:
        lanes: list[GatewayCapabilityLaneView] = []
        connected_count = 0
        ready_count = 0
        warning_count = 0
        approval_count = 0

        for instance in instances:
            lane_approvals = len(instance.unresolved_requests)
            approval_count += lane_approvals
            app_count = len(instance.apps)
            plugin_names = _lane_plugin_names(
                instance,
                mcp_server_status_by_instance.get(instance.id, []),
            )
            plugin_count = len(plugin_names)
            mcp_server_count = len(instance.mcp_servers)
            warnings: list[str] = []
            level: SignalLevel

            if not instance.connected:
                level = "warn"
                summary = "Lane is disconnected from Codex right now."
                warnings.append("Reconnect this lane before relying on it for launches.")
            elif instance.error:
                connected_count += 1
                level = "warn"
                summary = f"Lane is connected, but runtime is reporting: {instance.error}"
                warnings.append(instance.error)
                warning_count += 1
            elif lane_approvals:
                connected_count += 1
                level = "warn"
                summary = (
                    f"{lane_approvals} approval request(s) are waiting while the lane publishes "
                    f"{app_count} app(s), {plugin_count} plugin(s), and "
                    f"{mcp_server_count} MCP server(s)."
                )
                warnings.append(
                    "Resolve the pending approval queue before assuming this lane is clear."
                )
                warning_count += 1
            else:
                connected_count += 1
                level = "ready"
                ready_count += 1
                if app_count or plugin_count or mcp_server_count:
                    summary = (
                        f"Lane is connected and publishing {app_count} app(s), {plugin_count} "
                        f"plugin(s), and {mcp_server_count} MCP server(s)."
                    )
                else:
                    summary = (
                        "Lane is connected, but it is not publishing any apps, plugins, "
                        "or MCP servers yet."
                    )

            lanes.append(
                GatewayCapabilityLaneView(
                    instance_id=instance.id,
                    instance_name=instance.name,
                    connected=instance.connected,
                    level=level,
                    summary=summary,
                    approval_count=lane_approvals,
                    app_count=app_count,
                    plugin_count=plugin_count,
                    mcp_server_count=mcp_server_count,
                    warnings=warnings,
                    last_event_at=instance.last_event_at,
                )
            )

        total_count = len(instances)
        offline_count = total_count - connected_count
        if not total_count:
            headline = "Connected lane health is idle"
            summary = "No Codex lanes are registered yet."
        elif not connected_count:
            headline = "Connected lane health has no live lanes"
            summary = "OpenZues has saved lanes, but none of them are connected right now."
        elif warning_count:
            headline = "Connected lane health has live warnings"
            summary = (
                f"{warning_count} connected lane(s) need attention across approvals "
                "or runtime posture."
            )
        else:
            headline = "Connected lane health is ready"
            summary = f"{connected_count} connected lane(s) are ready for operator work."

        lanes.sort(
            key=lambda lane: (
                0 if lane.connected else 1,
                0 if lane.level == "ready" else 1,
                lane.instance_name.lower(),
            )
        )
        return GatewayCapabilityConnectedLaneHealthView(
            headline=headline,
            summary=summary,
            total_count=total_count,
            connected_count=connected_count,
            ready_count=ready_count,
            warning_count=warning_count,
            offline_count=offline_count,
            approval_count=approval_count,
            lanes=lanes,
        )

    def _build_inventory(
        self,
        instances: list[InstanceView],
        integrations_inventory,
        *,
        gateway: GatewayBootstrapView,
        integrations,
        missions,
        projects,
        project_labels,
        mcp_server_status_by_instance,
        task_blueprints,
    ) -> GatewayCapabilityInventoryView:
        catalog: dict[tuple[str, str], dict[str, Any]] = {}
        for instance in instances:
            status_entries = mcp_server_status_by_instance.get(instance.id, [])
            for kind, entries in (
                ("app", instance.apps),
                (
                    "plugin",
                    [{"name": name} for name in _lane_plugin_names(instance, status_entries)],
                ),
                ("mcp_server", instance.mcp_servers),
                (
                    "service",
                    [
                        {"name": service_name}
                        for entry in status_entries
                        if isinstance(entry, dict)
                        for service_name in _catalog_names(entry.get("services"))
                    ],
                ),
            ):
                for entry in entries:
                    name = str(
                        entry.get("name")
                        or entry.get("id")
                        or entry.get("source")
                        or "Unnamed capability"
                    ).strip()
                    if not name:
                        continue
                    bucket = catalog.setdefault(
                        (kind, name.lower()),
                        {
                            "kind": kind,
                            "name": name,
                            "lanes": set(),
                            "ready_lanes": set(),
                        },
                    )
                    bucket["lanes"].add(instance.name)
                    if instance.connected:
                        bucket["ready_lanes"].add(instance.name)

        items: list[GatewayCapabilityInventoryItemView] = []
        for bucket in catalog.values():
            ready_lane_count = len(bucket["ready_lanes"])
            total_lane_count = len(bucket["lanes"])
            if ready_lane_count:
                summary = f"Published on {ready_lane_count} connected lane(s)."
            else:
                summary = "Only published on offline lanes right now."
            items.append(
                GatewayCapabilityInventoryItemView(
                    kind=bucket["kind"],
                    name=bucket["name"],
                    ready_lane_count=ready_lane_count,
                    total_lane_count=total_lane_count,
                    summary=summary,
                    lanes=sorted(bucket["lanes"]),
                )
            )

        app_count = sum(item.kind == "app" for item in items)
        plugin_count = sum(item.kind == "plugin" for item in items)
        mcp_server_count = sum(item.kind == "mcp_server" for item in items)
        service_count = sum(item.kind == "service" for item in items)
        tracked_ready_count = int(integrations_inventory.ready_count)
        tracked_gap_count = int(integrations_inventory.gap_count)
        tracked_count = int(integrations_inventory.tracked_count)
        observed_count = int(integrations_inventory.observed_count)
        method_catalog = _build_callable_method_catalog(instances, mcp_server_status_by_instance)
        event_catalog = _build_gateway_event_catalog()
        node_catalog = _build_known_node_catalog(instances)
        browser_runtime = _build_browser_runtime_view(
            instances,
            mcp_server_status_by_instance,
        )
        tracked_memory_items = [
            item
            for item in integrations_inventory.items
            if item.tracked and is_mempalace_integration(item)
        ]
        tracked_memory_integrations = [
            integration
            for integration in integrations
            if integration.enabled and is_mempalace_integration(integration)
        ]
        tracked_memory_ready = [item for item in tracked_memory_items if item.readiness == "ready"]
        tracked_memory_gaps = [
            item
            for item in tracked_memory_items
            if item.readiness in {"lane_gap", "auth_gap", "degraded"}
        ]
        enabled_memory_tasks = [
            task for task in task_blueprints if task.enabled and is_mempalace_automation_task(task)
        ]
        disabled_memory_tasks = [
            task
            for task in task_blueprints
            if not task.enabled and is_mempalace_automation_task(task)
        ]
        tracked_memory_project_ids = {
            integration.project_id for integration in tracked_memory_integrations
        }
        enabled_memory_task_project_ids = {task.project_id for task in enabled_memory_tasks}
        matched_enabled_memory_task_count = sum(
            1
            for project_id in tracked_memory_project_ids
            if project_id in enabled_memory_task_project_ids
        )
        observed_memory_items = [item for item in items if is_mempalace_integration(item)]
        observed_memory_ready_lanes = sum(item.ready_lane_count for item in observed_memory_items)
        observed_memory_total_lanes = sum(item.total_lane_count for item in observed_memory_items)
        connected_observed_memory_lanes = [
            instance.name
            for instance in instances
            if instance.connected
            and any(is_mempalace_integration(entry) for entry in instance.mcp_servers)
        ]
        memory_tool_proofs: list[dict[str, Any]] = []
        for instance in instances:
            if not instance.connected:
                continue
            proof = _build_mempalace_tool_proof(
                instance,
                mcp_server_status_by_instance.get(instance.id, []),
            )
            if proof is not None:
                memory_tool_proofs.append(proof)
        memory_tool_ready_proofs = [
            proof for proof in memory_tool_proofs if proof["status"] == "ready"
        ]
        memory_tool_gap_proofs = [
            proof for proof in memory_tool_proofs if proof["status"] != "ready"
        ]
        latest_missions_by_task = _latest_missions_by_task(missions)
        memory_loop_freshness = _build_memory_loop_freshness(enabled_memory_tasks)
        memory_writeback_freshness = _build_memory_writeback_freshness(
            enabled_memory_tasks,
            project_labels=project_labels,
            latest_missions_by_task=latest_missions_by_task,
        )
        memory_roundtrip_freshness = _build_memory_roundtrip_freshness(
            enabled_memory_tasks,
            project_labels=project_labels,
            latest_missions_by_task=latest_missions_by_task,
        )
        task_memory_proof_reference = _build_task_memory_proof_reference(
            enabled_memory_tasks,
            project_labels=project_labels,
            latest_missions_by_task=latest_missions_by_task,
        )
        direct_memory_proof = _build_direct_memory_proof_state(
            missions,
            project_labels=project_labels,
        )
        memory_proof_reference = (
            direct_memory_proof["reference"]
            if direct_memory_proof is not None
            else task_memory_proof_reference
        )
        memory_proof_continuity = _build_memory_proof_continuity(
            reference=memory_proof_reference,
            missions=missions,
            instances=instances,
            project_labels=project_labels,
        )
        memory_proof_target = self._select_memory_proof_launch_target(
            instances=instances,
            gateway=gateway,
            projects=projects,
            task_blueprints=task_blueprints,
            mcp_server_status_by_instance=mcp_server_status_by_instance,
            requested_instance_id=None,
        )
        memory_evidence = [
            str(proof["summary"])
            for proof in [*memory_tool_gap_proofs, *memory_tool_ready_proofs][:3]
        ]
        if (
            not memory_evidence
            and connected_observed_memory_lanes
            and (tracked_memory_ready or observed_memory_ready_lanes)
        ):
            memory_evidence = [
                (
                    f"{_join_list(connected_observed_memory_lanes[:3])} publish MemPalace in "
                    "inventory, but no callable tool catalog is visible yet."
                )
            ]
        if memory_loop_freshness is not None:
            memory_evidence.append(memory_loop_freshness["summary"])
        if memory_writeback_freshness is not None:
            memory_evidence.extend(memory_writeback_freshness["evidence"])
        if memory_roundtrip_freshness is not None:
            memory_evidence.extend(memory_roundtrip_freshness["evidence"])
        if direct_memory_proof is not None:
            memory_evidence.extend(direct_memory_proof["evidence"])
        tool_ready_clause = (
            f" Callable tool proof passed on {len(memory_tool_ready_proofs)} connected lane(s)."
            if memory_tool_ready_proofs
            else ""
        )
        tool_gap_clause = ""
        tool_gap_action: str | None = None
        if memory_tool_gap_proofs:
            tool_gap_clause = (
                f" Callable tool proof is incomplete on {len(memory_tool_gap_proofs)} connected "
                "lane(s)."
            )
            tool_gap_action = str(memory_tool_gap_proofs[0]["action"] or "")
        elif connected_observed_memory_lanes and (
            tracked_memory_ready or observed_memory_ready_lanes
        ):
            tool_gap_clause = (
                " Callable tool proof is unavailable on the connected MemPalace lane right now."
            )
            tool_gap_action = (
                "Refresh the connected MemPalace lane so OpenZues can read the live MemPalace "
                "tool catalog before relying on automatic memory maintenance."
            )

        memory_status: SignalLevel
        if tracked_memory_ready and matched_enabled_memory_task_count and memory_tool_ready_proofs:
            memory_status = "ready"
            memory_summary = (
                f"MemPalace is tracked and live for {len(tracked_memory_ready)} project or global "
                f"integration scope(s). Automatic memory loop is armed.{tool_ready_clause}"
            )
            memory_recommended_action = (
                "Let the scheduled MemPalace loop keep consolidating durable recall, and prefer "
                "those memory-backed lanes when history matters."
            )
        elif tracked_memory_ready and matched_enabled_memory_task_count:
            memory_status = "warn"
            memory_summary = (
                f"MemPalace is tracked and live for {len(tracked_memory_ready)} project or global "
                "integration scope(s), and the automatic memory loop is armed, but callable tool "
                "proof is not complete yet."
                f"{tool_gap_clause or ' No live MemPalace tool proof is visible yet.'}"
            )
            memory_recommended_action = tool_gap_action or (
                "Refresh the connected MemPalace lane so OpenZues can prove the live MemPalace "
                "tool contract before relying on automatic maintenance."
            )
        elif tracked_memory_ready:
            memory_status = "warn"
            if disabled_memory_tasks:
                memory_summary = (
                    f"MemPalace is tracked and live for {len(tracked_memory_ready)} project or "
                    "global integration scope(s), but the automatic memory loop is disabled."
                )
                memory_recommended_action = (
                    "Re-enable the MemPalace Memory Loop task so Zeus keeps refreshing durable "
                    "memory automatically."
                )
            else:
                memory_summary = (
                    f"MemPalace is tracked and live for {len(tracked_memory_ready)} project or "
                    "global integration scope(s), but no automatic memory loop is armed yet."
                )
                memory_recommended_action = (
                    "Rerun bootstrap with MemPalace enabled, or add the MemPalace Memory Loop "
                    "task for this workspace."
                )
            memory_summary += tool_ready_clause or tool_gap_clause
        elif tracked_memory_gaps:
            memory_status = "warn"
            if len(tracked_memory_gaps) == 1:
                memory_summary = tracked_memory_gaps[0].summary
                if enabled_memory_tasks:
                    memory_summary += (
                        " Automatic memory maintenance is staged, but the live lane "
                        "gap is still open."
                    )
                memory_recommended_action = tracked_memory_gaps[0].recommended_action
            else:
                memory_summary = (
                    f"MemPalace is tracked in {len(tracked_memory_items)} scope(s), but "
                    f"{len(tracked_memory_gaps)} still have live lane or auth gaps."
                )
                if enabled_memory_tasks:
                    memory_summary += (
                        " Automatic memory maintenance is staged, but it cannot run "
                        "cleanly until those gaps close."
                    )
                memory_recommended_action = tracked_memory_gaps[0].recommended_action
            memory_summary += tool_ready_clause
        elif observed_memory_ready_lanes:
            memory_status = "info"
            if memory_tool_ready_proofs:
                memory_summary = (
                    f"MemPalace is callable on {len(memory_tool_ready_proofs)} connected lane(s), "
                    "but no tracked project memory integration is using it yet."
                )
            elif memory_tool_gap_proofs:
                memory_summary = (
                    f"MemPalace is visible on {observed_memory_ready_lanes} connected lane(s), but "
                    "callable tool proof is incomplete."
                )
            else:
                memory_summary = (
                    f"MemPalace is visible on {observed_memory_ready_lanes} "
                    "connected lane(s), but no "
                    "tracked project memory integration is using it yet."
                )
            memory_recommended_action = (
                "Stage MemPalace through onboarding or the integrations inventory before you rely "
                "on it in mission prompts."
            )
        elif observed_memory_total_lanes:
            memory_status = "info"
            memory_summary = (
                "MemPalace is only visible on offline lanes right now, so no live memory-backed "
                "lane is available."
            )
            memory_recommended_action = (
                "Reconnect the published MemPalace lane before using project memory."
            )
        else:
            memory_status = "info"
            memory_summary = (
                "MemPalace is not staged through a tracked integration or published "
                "on any live lane yet."
            )
            memory_recommended_action = (
                "Enable the MemPalace preset during onboarding when a workspace "
                "needs durable recall."
            )

        if memory_loop_freshness is not None and memory_loop_freshness["status"] == "warn":
            memory_summary += f" {memory_loop_freshness['summary']}"
            if memory_status == "ready":
                memory_status = "warn"
            if not memory_recommended_action or memory_recommended_action.startswith(
                "Let the scheduled MemPalace loop"
            ):
                memory_recommended_action = memory_loop_freshness["action"]
        if memory_writeback_freshness is not None:
            memory_summary += f" {memory_writeback_freshness['summary']}"
            if memory_writeback_freshness["status"] == "warn" and memory_status == "ready":
                memory_status = "warn"
            if (
                memory_writeback_freshness["status"] == "warn"
                and memory_writeback_freshness["action"]
                and (
                    not memory_recommended_action
                    or memory_recommended_action.startswith("Let the scheduled MemPalace loop")
                )
            ):
                memory_recommended_action = memory_writeback_freshness["action"]
        if memory_roundtrip_freshness is not None:
            memory_summary += f" {memory_roundtrip_freshness['summary']}"
            if memory_roundtrip_freshness["status"] == "warn" and memory_status == "ready":
                memory_status = "warn"
            if (
                memory_roundtrip_freshness["status"] == "warn"
                and memory_roundtrip_freshness["action"]
                and (
                    not memory_recommended_action
                    or memory_recommended_action.startswith("Let the scheduled MemPalace loop")
                    or "explicit writeback" in memory_recommended_action
                )
            ):
                memory_recommended_action = memory_roundtrip_freshness["action"]
        if direct_memory_proof is not None:
            memory_summary += f" {direct_memory_proof['summary']}"
            if direct_memory_proof["status"] == "warn" and memory_status == "ready":
                memory_status = "warn"
            if direct_memory_proof["action"] and (
                not memory_recommended_action
                or memory_recommended_action.startswith("Let the scheduled MemPalace loop")
                or "explicit writeback" in memory_recommended_action
                or "confirm the freshly written memory can be recalled" in memory_recommended_action
            ):
                memory_recommended_action = direct_memory_proof["action"]

        memory_evidence = _unique(memory_evidence)

        if tracked_gap_count:
            headline = "Gateway inventory has live gaps"
            summary = integrations_inventory.summary
        elif items or tracked_count or observed_count:
            headline = "Gateway inventory is active"
            summary = (
                f"{tracked_ready_count} tracked capability(ies) are ready; "
                f"{app_count} app(s), {plugin_count} plugin(s), "
                f"{service_count} service(s), and {mcp_server_count} MCP server(s) "
                "are visible across live lane catalogs."
            )
        else:
            headline = "Gateway inventory is idle"
            summary = (
                "No lane-published apps, plugins, services, MCP servers, or tracked "
                "integrations are visible yet."
            )

        if method_catalog.tool_count:
            summary = f"{summary} {method_catalog.summary}"
        if event_catalog.event_count:
            summary = f"{summary} {event_catalog.summary}"

        items.sort(key=lambda item: (item.kind, item.name.lower()))
        return GatewayCapabilityInventoryView(
            headline=headline,
            summary=summary,
            app_count=app_count,
            plugin_count=plugin_count,
            mcp_server_count=mcp_server_count,
            service_count=service_count,
            tracked_ready_count=tracked_ready_count,
            tracked_gap_count=tracked_gap_count,
            tracked_count=tracked_count,
            observed_count=observed_count,
            memory_status=memory_status,
            memory_summary=memory_summary,
            memory_recommended_action=memory_recommended_action,
            memory_evidence=memory_evidence,
            memory_proof_reference=memory_proof_reference,
            memory_proof_continuity=memory_proof_continuity,
            memory_proof_launchable=memory_proof_target is not None,
            memory_proof_target_instance_id=(
                memory_proof_target.instance_id if memory_proof_target is not None else None
            ),
            memory_proof_launch_label=(
                memory_proof_target.launch_label if memory_proof_target is not None else None
            ),
            method_catalog=method_catalog,
            event_catalog=event_catalog,
            node_catalog=node_catalog,
            browser_runtime=browser_runtime,
            items=items,
        )

    def _build_approval_posture(
        self,
        *,
        gateway: GatewayBootstrapView,
        lanes: GatewayCapabilityConnectedLaneHealthView,
        access_posture,
        remote_requests: list[RemoteRequestView],
    ) -> GatewayCapabilityApprovalPostureView:
        approval_count = lanes.approval_count
        lane_count_with_approvals = sum(lane.approval_count > 0 for lane in lanes.lanes)
        api_key_count = int(access_posture.api_key_count)
        recent_remote_request_count = int(access_posture.recent_remote_request_count)

        if approval_count:
            headline = "Approvals are waiting"
            summary = (
                f"{approval_count} approval request(s) are waiting across "
                f"{lane_count_with_approvals} "
                "lane(s). "
                + (
                    "Launches pause automatically."
                    if gateway.pause_on_approval
                    else "Launches will not pause automatically."
                )
            )
        elif not gateway.pause_on_approval:
            headline = "Approval pauses are disabled"
            summary = "Saved launches will continue without an automatic approval pause."
        elif gateway.setup_mode == "remote" and not api_key_count:
            headline = "Remote approval posture is not armed"
            summary = (
                "Remote-first gateway posture is saved, but no active operator API "
                "key is available yet."
            )
        elif recent_remote_request_count:
            failed_recent = sum(request.status == "failed" for request in remote_requests[:25])
            headline = "Approval posture and remote ingress are active"
            summary = (
                f"{recent_remote_request_count} authenticated remote request(s) landed recently"
                + (f", including {failed_recent} failure(s)." if failed_recent else ".")
            )
        else:
            headline = "Approval posture is armed"
            summary = (
                "Launches pause on approval, and no pending approval requests are "
                "blocking the gateway."
            )

        return GatewayCapabilityApprovalPostureView(
            headline=headline,
            summary=summary,
            pause_on_approval=gateway.pause_on_approval,
            approval_count=approval_count,
            lane_count_with_approvals=lane_count_with_approvals,
            operator_api_key_count=api_key_count,
            recent_remote_request_count=recent_remote_request_count,
        )

    def _build_diagnostics_summary(
        self,
        checks: list[DiagnosticCheck],
    ) -> GatewayCapabilityDiagnosticsView:
        ok_count = sum(check.status == "ok" for check in checks)
        warn_count = sum(check.status == "warn" for check in checks)
        fail_count = sum(check.status == "fail" for check in checks)
        evidence = [
            _diagnostic_evidence(check) for check in checks if check.status in {"warn", "fail"}
        ]
        if fail_count:
            headline = "Gateway diagnostics need repair"
            summary = f"{fail_count} diagnostic check(s) failed and {warn_count} more are warning."
        elif warn_count:
            headline = "Gateway diagnostics have warnings"
            summary = f"{warn_count} diagnostic check(s) still need attention."
        else:
            headline = "Gateway diagnostics are steady"
            summary = "Environment and desktop diagnostics are clear."
        return GatewayCapabilityDiagnosticsView(
            headline=headline,
            summary=summary,
            ok_count=ok_count,
            warn_count=warn_count,
            fail_count=fail_count,
            evidence=evidence[:4],
        )

    def _resolve_level(
        self,
        *,
        gateway: GatewayBootstrapView,
        diagnostics: GatewayCapabilityDiagnosticsView,
        connected_lane_health: GatewayCapabilityConnectedLaneHealthView,
        inventory: GatewayCapabilityInventoryView,
        approval_posture: GatewayCapabilityApprovalPostureView,
    ) -> SignalLevel:
        offline_only = (
            connected_lane_health.offline_count > 0
            and connected_lane_health.connected_count == 0
        )
        if gateway.status == "degraded" or diagnostics.fail_count:
            return "critical"
        if (
            gateway.status in {"unconfigured", "staged"}
            or inventory.tracked_gap_count
            or inventory.memory_status == "warn"
            or approval_posture.approval_count
            or connected_lane_health.warning_count
            or offline_only
            or diagnostics.warn_count
        ):
            return "warn"
        if connected_lane_health.connected_count or inventory.items or gateway.status == "ready":
            return "ready"
        return "info"

    def _build_headline(self, *, level: SignalLevel, gateway: GatewayBootstrapView) -> str:
        if level == "critical":
            return "Gateway capability needs repair"
        if level == "warn":
            if gateway.status == "unconfigured":
                return "Gateway capability is not configured yet"
            return "Gateway capability has live gaps"
        if level == "ready":
            return "Gateway capability is operator-ready"
        return "Gateway capability is idle"

    def _build_summary(
        self,
        *,
        gateway: GatewayBootstrapView,
        lanes: GatewayCapabilityConnectedLaneHealthView,
        inventory: GatewayCapabilityInventoryView,
        approvals: GatewayCapabilityApprovalPostureView,
    ) -> str:
        parts = [
            f"{lanes.connected_count}/{lanes.total_count} lane(s) connected",
            (
                f"{inventory.tracked_ready_count} tracked capability(ies) ready"
                if inventory.tracked_count or inventory.items
                else "no tracked gateway inventory yet"
            ),
        ]
        if inventory.memory_status == "ready":
            parts.append("MemPalace memory live")
            if "automatic memory loop is armed" in inventory.memory_summary.lower():
                parts.append("automatic memory loop armed")
        elif inventory.memory_status == "warn":
            parts.append("MemPalace memory gap open")
        if inventory.tracked_gap_count:
            parts.append(f"{inventory.tracked_gap_count} tracked gap(s) still open")
        if approvals.approval_count:
            parts.append(f"{approvals.approval_count} approval request(s) waiting")
        else:
            parts.append(
                "approval pauses armed" if gateway.pause_on_approval else "approval pauses disabled"
            )
        parts.append(gateway.launch_defaults_summary)
        return ". ".join(parts) + "."
