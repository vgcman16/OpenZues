from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from openzues.schemas import (
    GatewayCapabilityMethodCatalogView,
    GatewayCapabilityMethodScopeView,
)

ADMIN_GATEWAY_METHOD_SCOPE = "operator.admin"
READ_GATEWAY_METHOD_SCOPE = "operator.read"
WRITE_GATEWAY_METHOD_SCOPE = "operator.write"
APPROVALS_GATEWAY_METHOD_SCOPE = "operator.approvals"
PAIRING_GATEWAY_METHOD_SCOPE = "operator.pairing"
TALK_SECRETS_GATEWAY_METHOD_SCOPE = "operator.talk.secrets"
NODE_ROLE_GATEWAY_METHOD_SCOPE = "node.role"

ORDERED_OPERATOR_SCOPES = (
    ADMIN_GATEWAY_METHOD_SCOPE,
    READ_GATEWAY_METHOD_SCOPE,
    WRITE_GATEWAY_METHOD_SCOPE,
    APPROVALS_GATEWAY_METHOD_SCOPE,
    PAIRING_GATEWAY_METHOD_SCOPE,
    TALK_SECRETS_GATEWAY_METHOD_SCOPE,
)

NODE_ROLE_GATEWAY_METHODS = (
    "node.invoke.result",
    "node.event",
    "node.pending.drain",
    "node.canvas.capability.refresh",
    "node.pending.pull",
    "node.pending.ack",
    "skills.bins",
)

KNOWN_GATEWAY_EVENTS = (
    "connect.challenge",
    "agent",
    "chat",
    "session.message",
    "session.tool",
    "sessions.changed",
    "presence",
    "tick",
    "talk.mode",
    "shutdown",
    "health",
    "heartbeat",
    "cron",
    "node.pair.requested",
    "node.pair.resolved",
    "node.invoke.request",
    "device.pair.requested",
    "device.pair.resolved",
    "voicewake.changed",
    "exec.approval.requested",
    "exec.approval.resolved",
    "plugin.approval.requested",
    "plugin.approval.resolved",
    "update.available",
)

# OpenClaw keeps a canonical gateway method registry in src/gateway/server-methods-list.ts.
# Keep the built-in reserved/admin and OpenZues-only control-plane methods explicit here so
# the target can surface a stable registry even when no live lane catalog is publishing tools.
KNOWN_RESERVED_ADMIN_GATEWAY_METHODS = (
    "config.apply",
    "config.openFile",
    "config.patch",
    "config.schema",
    "config.set",
    "exec.approvals.get",
    "exec.approvals.set",
    "exec.approvals.node.get",
    "exec.approvals.node.set",
    "update.run",
    "wizard.cancel",
    "wizard.next",
    "wizard.start",
    "wizard.status",
)

KNOWN_CONTROL_PLANE_GATEWAY_METHODS = (
    "chat.inject",
    "connect",
    "push.test",
    "sessions.get",
    "sessions.resolve",
    "sessions.steer",
    "sessions.usage",
    "sessions.usage.logs",
    "sessions.usage.timeseries",
    "web.login.start",
    "web.login.wait",
)

EXPLICIT_GATEWAY_METHOD_SCOPE_GROUPS: dict[str, tuple[str, ...]] = {
    APPROVALS_GATEWAY_METHOD_SCOPE: (
        "exec.approval.get",
        "exec.approval.list",
        "exec.approval.request",
        "exec.approval.waitDecision",
        "exec.approval.resolve",
        "plugin.approval.list",
        "plugin.approval.request",
        "plugin.approval.waitDecision",
        "plugin.approval.resolve",
    ),
    PAIRING_GATEWAY_METHOD_SCOPE: (
        "node.pair.request",
        "node.pair.list",
        "node.pair.reject",
        "node.pair.verify",
        "node.pair.approve",
        "device.pair.list",
        "device.pair.approve",
        "device.pair.reject",
        "device.pair.remove",
        "device.token.rotate",
        "device.token.revoke",
        "node.rename",
    ),
    READ_GATEWAY_METHOD_SCOPE: (
        "health",
        "doctor.memory.status",
        "doctor.memory.dreamDiary",
        "logs.tail",
        "channels.status",
        "status",
        "usage.status",
        "usage.cost",
        "tts.status",
        "tts.providers",
        "commands.list",
        "models.list",
        "models.authStatus",
        "tools.catalog",
        "tools.effective",
        "agents.list",
        "agent.identity.get",
        "skills.status",
        "skills.search",
        "skills.detail",
        "voicewake.get",
        "sessions.list",
        "sessions.get",
        "sessions.preview",
        "sessions.resolve",
        "sessions.compaction.list",
        "sessions.compaction.get",
        "sessions.subscribe",
        "sessions.unsubscribe",
        "sessions.messages.subscribe",
        "sessions.messages.unsubscribe",
        "sessions.usage",
        "sessions.usage.timeseries",
        "sessions.usage.logs",
        "cron.list",
        "cron.status",
        "cron.runs",
        "gateway.identity.get",
        "system-presence",
        "last-heartbeat",
        "node.list",
        "node.describe",
        "chat.history",
        "config.get",
        "config.schema.lookup",
        "talk.config",
        "agents.files.list",
        "agents.files.get",
    ),
    WRITE_GATEWAY_METHOD_SCOPE: (
        "message.action",
        "send",
        "poll",
        "agent",
        "agent.wait",
        "wake",
        "talk.mode",
        "talk.speak",
        "tts.enable",
        "tts.disable",
        "tts.convert",
        "tts.setProvider",
        "voicewake.set",
        "node.invoke",
        "chat.send",
        "chat.abort",
        "sessions.create",
        "sessions.send",
        "sessions.steer",
        "sessions.abort",
        "sessions.compaction.branch",
        "doctor.memory.backfillDreamDiary",
        "doctor.memory.resetDreamDiary",
        "doctor.memory.resetGroundedShortTerm",
        "doctor.memory.repairDreamingArtifacts",
        "doctor.memory.dedupeDreamDiary",
        "push.test",
        "node.pending.enqueue",
    ),
    ADMIN_GATEWAY_METHOD_SCOPE: (
        "channels.start",
        "channels.logout",
        "agents.create",
        "agents.update",
        "agents.delete",
        "skills.install",
        "skills.update",
        "secrets.reload",
        "secrets.resolve",
        "cron.add",
        "cron.update",
        "cron.remove",
        "cron.run",
        "sessions.patch",
        "sessions.reset",
        "sessions.delete",
        "sessions.compact",
        "sessions.compaction.restore",
        "connect",
        "chat.inject",
        "web.login.start",
        "web.login.wait",
        "set-heartbeats",
        "system-event",
        "agents.files.set",
    ),
    TALK_SECRETS_GATEWAY_METHOD_SCOPE: (),
}

EXPLICIT_GATEWAY_METHOD_SCOPE_BY_NAME = {
    method: scope
    for scope, methods in EXPLICIT_GATEWAY_METHOD_SCOPE_GROUPS.items()
    for method in methods
}

RESERVED_ADMIN_GATEWAY_METHOD_PREFIXES = (
    "exec.approvals.",
    "config.",
    "wizard.",
    "update.",
)

RESERVED_ADMIN_GATEWAY_METHOD_SCOPE = ADMIN_GATEWAY_METHOD_SCOPE


@dataclass(frozen=True, slots=True)
class GatewayMethodScopeNormalization:
    scope: str | None
    coerced_to_reserved_admin: bool


@dataclass(frozen=True, slots=True)
class GatewayMethodAuthorization:
    allowed: bool
    missing_scope: str | None = None


def is_reserved_admin_gateway_method(method: str) -> bool:
    return any(method.startswith(prefix) for prefix in RESERVED_ADMIN_GATEWAY_METHOD_PREFIXES)


def resolve_reserved_gateway_method_scope(method: str) -> str | None:
    if not is_reserved_admin_gateway_method(method):
        return None
    return RESERVED_ADMIN_GATEWAY_METHOD_SCOPE


def normalize_plugin_gateway_method_scope(
    method: str,
    scope: str | None,
) -> GatewayMethodScopeNormalization:
    reserved_scope = resolve_reserved_gateway_method_scope(method)
    if reserved_scope is None or scope is None or scope == reserved_scope:
        return GatewayMethodScopeNormalization(
            scope=scope,
            coerced_to_reserved_admin=False,
        )
    return GatewayMethodScopeNormalization(
        scope=reserved_scope,
        coerced_to_reserved_admin=True,
    )


def is_node_role_gateway_method(method: str) -> bool:
    return method in NODE_ROLE_GATEWAY_METHODS


def resolve_gateway_method_scope(method: str) -> str | None:
    explicit_scope = EXPLICIT_GATEWAY_METHOD_SCOPE_BY_NAME.get(method)
    if explicit_scope is not None:
        return explicit_scope
    return resolve_reserved_gateway_method_scope(method)


def resolve_gateway_method_scope_with_plugin_scope(
    method: str,
    plugin_scope: str | None,
) -> str | None:
    explicit_scope = resolve_gateway_method_scope(method)
    if explicit_scope is not None:
        return explicit_scope
    if plugin_scope is None:
        return None
    return normalize_plugin_gateway_method_scope(method, plugin_scope).scope


def resolve_required_operator_scope_for_method(
    method: str,
    plugin_scope: str | None = None,
) -> str | None:
    return resolve_gateway_method_scope_with_plugin_scope(method, plugin_scope)


def resolve_least_privilege_operator_scopes_for_method(
    method: str,
    plugin_scope: str | None = None,
) -> list[str]:
    required_scope = resolve_required_operator_scope_for_method(method, plugin_scope)
    if required_scope is None:
        return []
    return [required_scope]


def list_known_gateway_methods() -> tuple[str, ...]:
    ordered_methods: list[str] = []
    seen: set[str] = set()
    for method in (
        *KNOWN_RESERVED_ADMIN_GATEWAY_METHODS,
        *KNOWN_CONTROL_PLANE_GATEWAY_METHODS,
        *NODE_ROLE_GATEWAY_METHODS,
        *(
            method
            for methods in EXPLICIT_GATEWAY_METHOD_SCOPE_GROUPS.values()
            for method in methods
        ),
    ):
        normalized = str(method).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered_methods.append(normalized)
    return tuple(sorted(ordered_methods, key=str.lower))


def list_known_gateway_events() -> tuple[str, ...]:
    ordered_events: list[str] = []
    seen: set[str] = set()
    for event in KNOWN_GATEWAY_EVENTS:
        normalized = str(event).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered_events.append(normalized)
    return tuple(ordered_events)


def build_known_gateway_method_catalog() -> GatewayCapabilityMethodCatalogView:
    tools = list(list_known_gateway_methods())
    classified_methods = classify_gateway_methods(tools)
    scope_groups = [
        GatewayCapabilityMethodScopeView(
            scope=scope,
            method_count=len(methods),
            methods=methods,
        )
        for scope in ORDERED_OPERATOR_SCOPES
        if (methods := classified_methods.get(scope))
    ]
    if node_methods := sorted(
        (method for method in tools if is_node_role_gateway_method(method)),
        key=str.lower,
    ):
        scope_groups.append(
            GatewayCapabilityMethodScopeView(
                scope=NODE_ROLE_GATEWAY_METHOD_SCOPE,
                method_count=len(node_methods),
                methods=node_methods,
            )
        )
    reserved_tools = [method for method in tools if is_reserved_admin_gateway_method(method)]
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
    return GatewayCapabilityMethodCatalogView(
        headline="Gateway method registry is staged",
        summary=summary,
        tool_count=len(tools),
        server_count=0,
        lane_count=0,
        classified_method_count=sum(group.method_count for group in scope_groups),
        reserved_admin_method_count=len(reserved_tools),
        reserved_admin_scope=(
            RESERVED_ADMIN_GATEWAY_METHOD_SCOPE if reserved_tools else None
        ),
        tools=tools,
        servers=[],
        reserved_admin_methods=reserved_tools,
        scopes=scope_groups,
    )


def authorize_operator_scopes_for_method(
    method: str,
    scopes: Iterable[str],
    plugin_scope: str | None = None,
) -> GatewayMethodAuthorization:
    normalized_scopes = [str(scope).strip() for scope in scopes if str(scope).strip()]
    if ADMIN_GATEWAY_METHOD_SCOPE in normalized_scopes:
        return GatewayMethodAuthorization(allowed=True)
    required_scope = (
        resolve_required_operator_scope_for_method(method, plugin_scope)
        or ADMIN_GATEWAY_METHOD_SCOPE
    )
    if required_scope == READ_GATEWAY_METHOD_SCOPE:
        if (
            READ_GATEWAY_METHOD_SCOPE in normalized_scopes
            or WRITE_GATEWAY_METHOD_SCOPE in normalized_scopes
        ):
            return GatewayMethodAuthorization(allowed=True)
        return GatewayMethodAuthorization(
            allowed=False,
            missing_scope=READ_GATEWAY_METHOD_SCOPE,
        )
    if required_scope in normalized_scopes:
        return GatewayMethodAuthorization(allowed=True)
    return GatewayMethodAuthorization(
        allowed=False,
        missing_scope=required_scope,
    )


def is_gateway_method_classified(
    method: str,
    plugin_scope: str | None = None,
) -> bool:
    if is_node_role_gateway_method(method):
        return True
    return resolve_required_operator_scope_for_method(method, plugin_scope) is not None


def classify_gateway_methods(
    methods: Iterable[str],
    *,
    plugin_method_scopes: Mapping[str, str] | None = None,
) -> dict[str, list[str]]:
    grouped_methods: dict[str, dict[str, str]] = {}
    normalized_plugin_scopes = {
        str(method_name).strip().lower(): str(scope).strip()
        for method_name, scope in (plugin_method_scopes or {}).items()
        if str(method_name).strip() and str(scope).strip()
    }
    for raw_method in methods:
        method = str(raw_method).strip()
        if not method:
            continue
        scope = resolve_gateway_method_scope_with_plugin_scope(
            method,
            normalized_plugin_scopes.get(method.lower()),
        )
        if scope is None:
            continue
        grouped_methods.setdefault(scope, {}).setdefault(method.lower(), method)
    return {
        scope: sorted(grouped_methods[scope].values(), key=str.lower)
        for scope in ORDERED_OPERATOR_SCOPES
        if scope in grouped_methods
    }
