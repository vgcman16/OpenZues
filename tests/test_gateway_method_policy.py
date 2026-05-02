from __future__ import annotations

import re
from pathlib import Path

import pytest

from openzues.services.gateway_method_policy import (
    ADMIN_GATEWAY_METHOD_SCOPE,
    APPROVALS_GATEWAY_METHOD_SCOPE,
    EXPLICIT_GATEWAY_METHOD_SCOPE_GROUPS,
    NODE_ROLE_GATEWAY_METHOD_SCOPE,
    NODE_ROLE_GATEWAY_METHODS,
    ORDERED_OPERATOR_SCOPES,
    PAIRING_GATEWAY_METHOD_SCOPE,
    READ_GATEWAY_METHOD_SCOPE,
    TALK_SECRETS_GATEWAY_METHOD_SCOPE,
    WRITE_GATEWAY_METHOD_SCOPE,
    authorize_operator_scopes_for_method,
    classify_gateway_methods,
    is_gateway_method_classified,
    is_node_role_gateway_method,
    is_reserved_admin_gateway_method,
    list_known_gateway_events,
    list_known_gateway_methods,
    normalize_plugin_gateway_method_scope,
    resolve_gateway_method_scope,
    resolve_gateway_method_scope_with_plugin_scope,
    resolve_least_privilege_operator_scopes_for_method,
    resolve_required_operator_scope_for_method,
)

_OPENCLAW_MAIN_ROOT = Path(__file__).resolve().parents[2] / "openclaw-main"
_BASE_METHODS_BLOCK_PATTERN = re.compile(
    r"const BASE_METHODS = \[(.*?)\];\n\nexport function listGatewayMethods",
    re.DOTALL,
)
_GATEWAY_EVENTS_BLOCK_PATTERN = re.compile(
    r"export const GATEWAY_EVENTS = \[(.*?)\];",
    re.DOTALL,
)
_OPENCLAW_GATEWAY_UPDATE_AVAILABLE_PATTERN = re.compile(
    r'export const GATEWAY_EVENT_UPDATE_AVAILABLE = "([^"]+)"',
)
_HANDLER_METHOD_PATTERN = re.compile(
    r'^\s*"([^"]+)":\s*(?:async\b|[A-Za-z_][A-Za-z0-9_]*|\()',
    re.MULTILINE,
)


def _extract_handler_methods(*relative_parts: str) -> tuple[str, ...]:
    source_path = _OPENCLAW_MAIN_ROOT.joinpath(*relative_parts)
    if not source_path.exists():
        pytest.skip(f"OpenClaw source file is unavailable: {source_path}")
    return tuple(_HANDLER_METHOD_PATTERN.findall(source_path.read_text(encoding="utf-8")))


def _extract_runtime_handler_methods() -> dict[str, tuple[str, ...]]:
    methods_by_file: dict[str, tuple[str, ...]] = {}
    server_methods_root = _OPENCLAW_MAIN_ROOT / "src" / "gateway" / "server-methods"
    if not server_methods_root.exists():
        pytest.skip(f"OpenClaw source directory is unavailable: {server_methods_root}")
    for path in sorted(server_methods_root.glob("*.ts")):
        if path.name.endswith(".test.ts") or ".test." in path.name:
            continue
        methods = tuple(
            _HANDLER_METHOD_PATTERN.findall(path.read_text(encoding="utf-8"))
        )
        if methods:
            methods_by_file[path.name] = methods
    return methods_by_file


def _extract_base_gateway_methods() -> tuple[str, ...]:
    source_path = _OPENCLAW_MAIN_ROOT.joinpath("src", "gateway", "server-methods-list.ts")
    if not source_path.exists():
        pytest.skip(f"OpenClaw source file is unavailable: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")
    match = _BASE_METHODS_BLOCK_PATTERN.search(source_text)
    if match is None:
        pytest.fail(f"Could not parse OpenClaw gateway methods list from {source_path}")
    return tuple(re.findall(r'"([^"]+)"', match.group(1)))


def _extract_gateway_event_methods() -> tuple[str, ...]:
    source_path = _OPENCLAW_MAIN_ROOT.joinpath("src", "gateway", "server-methods-list.ts")
    if not source_path.exists():
        pytest.skip(f"OpenClaw source file is unavailable: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")
    match = _GATEWAY_EVENTS_BLOCK_PATTERN.search(source_text)
    if match is None:
        pytest.fail(f"Could not parse OpenClaw gateway event list from {source_path}")
    events = re.findall(r'"([^"]+)"', match.group(1))
    if "GATEWAY_EVENT_UPDATE_AVAILABLE" in match.group(1):
        events_path = _OPENCLAW_MAIN_ROOT.joinpath("src", "gateway", "events.ts")
        if not events_path.exists():
            pytest.fail(f"OpenClaw gateway events source is unavailable: {events_path}")
        constant_match = _OPENCLAW_GATEWAY_UPDATE_AVAILABLE_PATTERN.search(
            events_path.read_text(encoding="utf-8")
        )
        if constant_match is None:
            pytest.fail(
                f"Could not parse GATEWAY_EVENT_UPDATE_AVAILABLE from {events_path}"
            )
        events.append(constant_match.group(1))
    return tuple(events)


def test_gateway_method_policy_mirrors_openclaw_operator_scope_groups() -> None:
    assert ORDERED_OPERATOR_SCOPES == (
        ADMIN_GATEWAY_METHOD_SCOPE,
        READ_GATEWAY_METHOD_SCOPE,
        WRITE_GATEWAY_METHOD_SCOPE,
        APPROVALS_GATEWAY_METHOD_SCOPE,
        PAIRING_GATEWAY_METHOD_SCOPE,
        TALK_SECRETS_GATEWAY_METHOD_SCOPE,
    )
    assert {
        scope: len(methods)
        for scope, methods in EXPLICIT_GATEWAY_METHOD_SCOPE_GROUPS.items()
    } == {
            APPROVALS_GATEWAY_METHOD_SCOPE: 9,
            PAIRING_GATEWAY_METHOD_SCOPE: 12,
            READ_GATEWAY_METHOD_SCOPE: 73,
            WRITE_GATEWAY_METHOD_SCOPE: 73,
            ADMIN_GATEWAY_METHOD_SCOPE: 25,
            TALK_SECRETS_GATEWAY_METHOD_SCOPE: 0,
        }
    assert resolve_gateway_method_scope("status") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.status") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.auth.list") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.auth.show") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.clipboard.read") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.doctor") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.diff.snapshot") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.diff.screenshot") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.verify") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.cookies.get") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.get") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.is") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.ios.device.list") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.network.request") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.network.requests") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.pdf") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.profiles") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.tabs") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.screenshot") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.session.current") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.session.list") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.snapshot") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.storage.get") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.stream.status") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("send") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.act") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.auth.delete") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.auth.login") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.auth.save") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.batch") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.back") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.chat") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.clipboard.copy") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.clipboard.paste") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.clipboard.write") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.close") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.cookies.clear") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.cookies.set") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.confirm") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.dashboard.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.dashboard.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.diff.url") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.deny") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.download") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.focus") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.forward") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.highlight") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.inspect") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.ios.swipe") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.ios.tap") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.open") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.navigate") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.network.har.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.network.har.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.profiler.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.profiler.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.record.restart") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.record.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.record.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.reload") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.set") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.storage.clear") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.storage.set") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.stream.disable") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.stream.enable") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.trace.start") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.trace.stop") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("browser.upload") == WRITE_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("exec.approval.resolve") == APPROVALS_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("node.pair.approve") == PAIRING_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("connect") == ADMIN_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("wizard.bootstrap") == ADMIN_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("update.release") == ADMIN_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("github_search") is None


def test_classify_gateway_methods_groups_mixed_catalog_in_operator_scope_order() -> None:
    classified = classify_gateway_methods(
        [
            "wizard.bootstrap",
            "status",
            "send",
            "exec.approval.list",
            "node.pair.request",
            "connect",
            "config.reload",
            "status",
            "update.release",
            "github_search",
            "",
        ]
    )

    assert classified == {
        ADMIN_GATEWAY_METHOD_SCOPE: [
            "config.reload",
            "connect",
            "update.release",
            "wizard.bootstrap",
        ],
        READ_GATEWAY_METHOD_SCOPE: ["status"],
        WRITE_GATEWAY_METHOD_SCOPE: ["send"],
        APPROVALS_GATEWAY_METHOD_SCOPE: ["exec.approval.list"],
        PAIRING_GATEWAY_METHOD_SCOPE: ["node.pair.request"],
    }
    assert is_reserved_admin_gateway_method("config.reload")
    assert is_reserved_admin_gateway_method("wizard.bootstrap")
    assert is_reserved_admin_gateway_method("update.release")
    assert not is_reserved_admin_gateway_method("connect")


def test_gateway_method_policy_covers_openclaw_reserved_admin_registry_methods() -> None:
    source_path = _OPENCLAW_MAIN_ROOT.joinpath(
        "src",
        "gateway",
        "server-methods-list.ts",
    )
    if not source_path.exists():
        pytest.skip(f"OpenClaw source file is unavailable: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")

    reserved_methods = (
        "config.patch",
        "exec.approvals.node.set",
        "update.run",
        "wizard.status",
    )

    for method in reserved_methods:
        assert f'"{method}"' in source_text
        assert is_reserved_admin_gateway_method(method)
        assert resolve_gateway_method_scope(method) == ADMIN_GATEWAY_METHOD_SCOPE


def test_gateway_method_policy_covers_openclaw_wizard_registry_methods() -> None:
    wizard_methods = {
        method for method in _extract_base_gateway_methods() if method.startswith("wizard.")
    }

    assert wizard_methods == {
        "wizard.cancel",
        "wizard.next",
        "wizard.start",
        "wizard.status",
    }
    for method in wizard_methods:
        assert is_reserved_admin_gateway_method(method)
        assert resolve_gateway_method_scope(method) == ADMIN_GATEWAY_METHOD_SCOPE


def test_gateway_method_policy_covers_openclaw_config_handlers() -> None:
    config_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "config.ts")
    )

    assert config_methods == {
        "config.get",
        "config.schema",
        "config.schema.lookup",
        "config.set",
        "config.patch",
        "config.apply",
        "config.openFile",
    }
    assert {
        method
        for method in config_methods
        if resolve_gateway_method_scope(method) == READ_GATEWAY_METHOD_SCOPE
    } == {
        "config.get",
        "config.schema.lookup",
    }
    assert {
        method
        for method in config_methods
        if resolve_gateway_method_scope(method) == ADMIN_GATEWAY_METHOD_SCOPE
    } == {
        "config.apply",
        "config.openFile",
        "config.patch",
        "config.schema",
        "config.set",
    }


def test_gateway_method_policy_covers_openclaw_channels_handlers() -> None:
    channel_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "channels.ts")
    )

    assert channel_methods == {
        "channels.start",
        "channels.stop",
        "channels.logout",
        "channels.status",
    }
    assert {
        method
        for method in channel_methods
        if resolve_gateway_method_scope(method) == READ_GATEWAY_METHOD_SCOPE
    } == {"channels.status"}
    assert {
        method
        for method in channel_methods
        if resolve_gateway_method_scope(method) == ADMIN_GATEWAY_METHOD_SCOPE
    } == {
        "channels.logout",
        "channels.start",
        "channels.stop",
    }


def test_gateway_method_policy_covers_openclaw_chat_handlers() -> None:
    chat_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "chat.ts")
    )

    assert chat_methods == {
        "chat.abort",
        "chat.history",
        "chat.inject",
        "chat.send",
    }
    assert {
        method
        for method in chat_methods
        if resolve_gateway_method_scope(method) == READ_GATEWAY_METHOD_SCOPE
    } == {"chat.history"}
    assert {
        method
        for method in chat_methods
        if resolve_gateway_method_scope(method) == WRITE_GATEWAY_METHOD_SCOPE
    } == {
        "chat.abort",
        "chat.send",
    }
    assert {
        method
        for method in chat_methods
        if resolve_gateway_method_scope(method) == ADMIN_GATEWAY_METHOD_SCOPE
    } == {"chat.inject"}


def test_gateway_method_policy_classifies_all_openclaw_base_methods() -> None:
    methods = _extract_base_gateway_methods()
    unclassified = [
        method
        for method in methods
        if not is_node_role_gateway_method(method)
        and resolve_gateway_method_scope(method) is None
    ]

    assert unclassified == []


def test_known_gateway_method_registry_covers_openclaw_base_registry() -> None:
    registry_methods = set(list_known_gateway_methods())
    base_methods = set(_extract_base_gateway_methods())
    openzues_only_methods = registry_methods - base_methods

    assert base_methods.issubset(registry_methods)
    assert openzues_only_methods == {
        "browser.act",
        "browser.auth.delete",
        "browser.auth.list",
        "browser.auth.login",
        "browser.auth.save",
        "browser.auth.show",
        "browser.batch",
        "browser.back",
        "browser.chat",
        "browser.clipboard.copy",
        "browser.clipboard.paste",
        "browser.clipboard.read",
        "browser.clipboard.write",
        "browser.close",
        "browser.confirm",
        "browser.cookies.clear",
        "browser.console",
        "browser.cookies.get",
        "browser.cookies.set",
        "browser.dashboard.start",
        "browser.dashboard.stop",
        "browser.diff.snapshot",
        "browser.diff.screenshot",
        "browser.diff.url",
        "browser.doctor",
        "browser.deny",
        "browser.download",
        "browser.errors",
        "browser.focus",
        "browser.forward",
        "browser.get",
        "browser.highlight",
        "browser.inspect",
        "browser.ios.device.list",
        "browser.ios.swipe",
        "browser.ios.tap",
        "browser.is",
        "browser.navigate",
        "browser.network.har.start",
        "browser.network.har.stop",
        "browser.network.request",
        "browser.network.requests",
        "browser.open",
        "browser.pdf",
        "browser.profiles",
        "browser.profiler.start",
        "browser.profiler.stop",
        "browser.record.restart",
        "browser.record.start",
        "browser.record.stop",
        "browser.reload",
        "browser.screenshot",
        "browser.set",
        "browser.session.current",
        "browser.session.list",
        "browser.snapshot",
        "browser.start",
        "browser.status",
        "browser.stop",
        "browser.storage.clear",
        "browser.storage.get",
        "browser.storage.set",
        "browser.stream.disable",
        "browser.stream.enable",
        "browser.stream.status",
        "browser.tabs",
        "browser.trace.start",
        "browser.trace.stop",
        "browser.upload",
        "browser.verify",
        "chat.inject",
        "config.openFile",
        "connect",
        "poll",
        "push.test",
        "sessions.get",
        "sessions.resolve",
        "sessions.steer",
        "sessions.usage",
        "sessions.usage.logs",
        "sessions.usage.timeseries",
        "web.login.start",
        "web.login.wait",
    }


def test_known_gateway_event_registry_matches_openclaw_event_catalog() -> None:
    assert list_known_gateway_events() == _extract_gateway_event_methods()


def test_gateway_method_policy_classifies_all_openclaw_runtime_handlers() -> None:
    missing_by_file = {
        file_name: sorted(
            method
            for method in methods
            if not is_node_role_gateway_method(method)
            and resolve_gateway_method_scope(method) is None
        )
        for file_name, methods in _extract_runtime_handler_methods().items()
    }
    missing_by_file = {
        file_name: methods for file_name, methods in missing_by_file.items() if methods
    }

    assert missing_by_file == {}


def test_openclaw_gateway_events_are_not_treated_as_registry_methods() -> None:
    registry_methods = set(list_known_gateway_methods())
    base_methods = set(_extract_base_gateway_methods())
    gateway_events = set(_extract_gateway_event_methods())
    event_only_methods = gateway_events - base_methods

    assert {
        "connect.challenge",
        "device.pair.requested",
        "device.pair.resolved",
        "exec.approval.requested",
        "exec.approval.resolved",
        "node.invoke.request",
        "node.pair.requested",
        "node.pair.resolved",
        "plugin.approval.requested",
        "plugin.approval.resolved",
        "session.message",
        "session.tool",
        "sessions.changed",
        "update.available",
        "voicewake.changed",
    }.issubset(event_only_methods)
    assert registry_methods.isdisjoint(event_only_methods)


def test_normalize_plugin_gateway_method_scope_matches_openclaw_reserved_admin_policy() -> None:
    unchanged = normalize_plugin_gateway_method_scope(
        "browser.request",
        READ_GATEWAY_METHOD_SCOPE,
    )
    assert unchanged.scope == READ_GATEWAY_METHOD_SCOPE
    assert unchanged.coerced_to_reserved_admin is False

    reserved_missing_scope = normalize_plugin_gateway_method_scope("wizard.status", None)
    assert reserved_missing_scope.scope is None
    assert reserved_missing_scope.coerced_to_reserved_admin is False

    reserved_admin = normalize_plugin_gateway_method_scope(
        "config.patch",
        ADMIN_GATEWAY_METHOD_SCOPE,
    )
    assert reserved_admin.scope == ADMIN_GATEWAY_METHOD_SCOPE
    assert reserved_admin.coerced_to_reserved_admin is False

    reserved_coerced = normalize_plugin_gateway_method_scope(
        "exec.approvals.node.set",
        READ_GATEWAY_METHOD_SCOPE,
    )
    assert reserved_coerced.scope == ADMIN_GATEWAY_METHOD_SCOPE
    assert reserved_coerced.coerced_to_reserved_admin is True


def test_plugin_scope_resolution_honors_methods_and_reserved_prefixes() -> None:
    assert (
        resolve_gateway_method_scope_with_plugin_scope(
            "browser.request",
            WRITE_GATEWAY_METHOD_SCOPE,
        )
        == WRITE_GATEWAY_METHOD_SCOPE
    )
    assert (
        resolve_gateway_method_scope_with_plugin_scope(
            "wizard.custom",
            READ_GATEWAY_METHOD_SCOPE,
        )
        == ADMIN_GATEWAY_METHOD_SCOPE
    )
    assert resolve_gateway_method_scope_with_plugin_scope("browser.request", None) is None


def test_gateway_authorization_helpers_match_openclaw_operator_scope_behavior() -> None:
    assert resolve_required_operator_scope_for_method("status") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_required_operator_scope_for_method(
        "browser.request",
        WRITE_GATEWAY_METHOD_SCOPE,
    ) == (
        WRITE_GATEWAY_METHOD_SCOPE
    )
    assert resolve_required_operator_scope_for_method(
        "wizard.custom",
        READ_GATEWAY_METHOD_SCOPE,
    ) == (
        ADMIN_GATEWAY_METHOD_SCOPE
    )

    assert resolve_least_privilege_operator_scopes_for_method("status") == [
        READ_GATEWAY_METHOD_SCOPE
    ]
    assert resolve_least_privilege_operator_scopes_for_method("node.pending.drain") == []
    assert resolve_least_privilege_operator_scopes_for_method(
        "browser.request",
        WRITE_GATEWAY_METHOD_SCOPE,
    ) == [
        WRITE_GATEWAY_METHOD_SCOPE
    ]

    assert (
        authorize_operator_scopes_for_method("health", [READ_GATEWAY_METHOD_SCOPE]).allowed
        is True
    )
    assert (
        authorize_operator_scopes_for_method("health", [WRITE_GATEWAY_METHOD_SCOPE]).allowed
        is True
    )
    assert (
        authorize_operator_scopes_for_method("config.patch", [ADMIN_GATEWAY_METHOD_SCOPE]).allowed
        is True
    )

    write_auth = authorize_operator_scopes_for_method("send", [READ_GATEWAY_METHOD_SCOPE])
    assert write_auth.allowed is False
    assert write_auth.missing_scope == WRITE_GATEWAY_METHOD_SCOPE

    approvals_auth = authorize_operator_scopes_for_method(
        "exec.approval.resolve",
        [WRITE_GATEWAY_METHOD_SCOPE],
    )
    assert approvals_auth.allowed is False
    assert approvals_auth.missing_scope == APPROVALS_GATEWAY_METHOD_SCOPE

    plugin_auth = authorize_operator_scopes_for_method(
        "browser.request",
        [WRITE_GATEWAY_METHOD_SCOPE],
        WRITE_GATEWAY_METHOD_SCOPE,
    )
    assert plugin_auth.allowed is True

    reserved_plugin_auth = authorize_operator_scopes_for_method(
        "config.plugin.inspect",
        [READ_GATEWAY_METHOD_SCOPE],
        READ_GATEWAY_METHOD_SCOPE,
    )
    assert reserved_plugin_auth.allowed is False
    assert reserved_plugin_auth.missing_scope == ADMIN_GATEWAY_METHOD_SCOPE

    unknown_auth = authorize_operator_scopes_for_method(
        "unknown.method",
        [READ_GATEWAY_METHOD_SCOPE],
    )
    assert unknown_auth.allowed is False
    assert unknown_auth.missing_scope == ADMIN_GATEWAY_METHOD_SCOPE

    assert is_gateway_method_classified("node.pending.drain") is True
    assert is_gateway_method_classified("browser.request", WRITE_GATEWAY_METHOD_SCOPE) is True
    assert is_gateway_method_classified("unknown.method") is False


def test_node_role_gateway_methods_match_openclaw_node_only_registry() -> None:
    assert NODE_ROLE_GATEWAY_METHOD_SCOPE == "node.role"
    assert NODE_ROLE_GATEWAY_METHODS == (
        "node.invoke.result",
        "node.event",
        "node.pending.drain",
        "node.canvas.capability.refresh",
        "node.pending.pull",
        "node.pending.ack",
        "skills.bins",
    )
    assert is_node_role_gateway_method("skills.bins")
    assert is_node_role_gateway_method("node.pending.pull")
    assert not is_node_role_gateway_method("status")


def test_gateway_method_policy_covers_openclaw_node_and_voice_handlers() -> None:
    node_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "nodes.ts")
    )
    node_pending_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "nodes-pending.ts")
    )
    voicewake_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "voicewake.ts")
    )

    extracted_methods = node_methods | node_pending_methods | voicewake_methods
    assert extracted_methods == {
        "node.pair.request",
        "node.pair.list",
        "node.pair.approve",
        "node.pair.reject",
        "node.pair.remove",
        "node.pair.verify",
        "node.rename",
        "node.list",
        "node.describe",
        "node.canvas.capability.refresh",
        "node.pending.pull",
        "node.pending.ack",
        "node.invoke",
        "node.invoke.result",
        "node.event",
        "node.pending.drain",
        "node.pending.enqueue",
        "voicewake.get",
        "voicewake.set",
    }

    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == READ_GATEWAY_METHOD_SCOPE
    } == {
        "node.describe",
        "node.list",
        "voicewake.get",
    }
    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == WRITE_GATEWAY_METHOD_SCOPE
    } == {
        "node.invoke",
        "node.pending.enqueue",
        "voicewake.set",
    }
    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == PAIRING_GATEWAY_METHOD_SCOPE
    } == {
        "node.pair.approve",
        "node.pair.list",
        "node.pair.remove",
        "node.pair.reject",
        "node.pair.request",
        "node.pair.verify",
        "node.rename",
    }
    assert {method for method in extracted_methods if is_node_role_gateway_method(method)} == {
        "node.canvas.capability.refresh",
        "node.event",
        "node.invoke.result",
        "node.pending.ack",
        "node.pending.drain",
        "node.pending.pull",
    }


def test_gateway_method_policy_covers_openclaw_talk_and_tts_handlers() -> None:
    talk_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "talk.ts")
    )
    tts_methods = set(
        _extract_handler_methods("src", "gateway", "server-methods", "tts.ts")
    )

    extracted_methods = talk_methods | tts_methods
    assert extracted_methods == {
        "talk.config",
        "talk.mode",
        "talk.realtime.relayAudio",
        "talk.realtime.relayMark",
        "talk.realtime.relayStop",
        "talk.realtime.relayToolResult",
        "talk.realtime.session",
        "talk.speak",
        "tts.status",
        "tts.enable",
        "tts.disable",
        "tts.convert",
        "tts.setProvider",
        "tts.setPersona",
        "tts.providers",
        "tts.personas",
    }

    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == READ_GATEWAY_METHOD_SCOPE
    } == {
        "talk.config",
        "tts.personas",
        "tts.providers",
        "tts.status",
    }
    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == WRITE_GATEWAY_METHOD_SCOPE
    } == {
        "talk.mode",
        "talk.realtime.relayAudio",
        "talk.realtime.relayMark",
        "talk.realtime.relayStop",
        "talk.realtime.relayToolResult",
        "talk.realtime.session",
        "talk.speak",
        "tts.convert",
        "tts.disable",
        "tts.enable",
        "tts.setProvider",
        "tts.setPersona",
    }
    assert {
        method
        for method in extracted_methods
        if resolve_gateway_method_scope(method) == TALK_SECRETS_GATEWAY_METHOD_SCOPE
    } == set()


def test_gateway_method_policy_covers_openclaw_tts_persona_handlers() -> None:
    assert resolve_gateway_method_scope("tts.personas") == READ_GATEWAY_METHOD_SCOPE
    assert resolve_gateway_method_scope("tts.setPersona") == WRITE_GATEWAY_METHOD_SCOPE
