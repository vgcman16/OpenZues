from __future__ import annotations

from openzues.services.gateway_plugin_activation import resolve_manifest_activation_plugin_ids


def _activation_plugins() -> list[dict[str, object]]:
    return [
        {
            "id": "memory-core",
            "commandAliases": [
                {"name": "dreaming", "kind": "runtime-slash", "cliCommand": "memory"}
            ],
            "providers": [],
            "channels": [],
            "hooks": [],
            "origin": "bundled",
        },
        {
            "id": "device-pair",
            "commandAliases": [{"name": "pair", "kind": "runtime-slash"}],
            "providers": [],
            "channels": [],
            "hooks": [],
            "origin": "bundled",
        },
        {
            "id": "openai",
            "providers": ["openai"],
            "activation": {"onAgentHarnesses": ["codex"]},
            "setup": {"providers": [{"id": "openai-codex"}]},
            "channels": [],
            "hooks": [],
            "origin": "bundled",
        },
        {
            "id": "demo-channel",
            "providers": [],
            "channels": ["telegram"],
            "hooks": ["before-agent-start"],
            "contracts": {"tools": ["web-search"]},
            "activation": {"onRoutes": ["webhook"], "onCommands": ["demo-tools"]},
            "origin": "workspace",
        },
    ]


def test_resolve_manifest_activation_plugin_ids_matches_command_triggers() -> None:
    plugins = _activation_plugins()

    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "command", "command": "memory"},
    ) == ["memory-core"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "command", "command": "pair"},
    ) == ["device-pair"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "command", "command": "demo-tools"},
    ) == ["demo-channel"]


def test_resolve_manifest_activation_plugin_ids_matches_runtime_manifest_triggers() -> None:
    plugins = _activation_plugins()

    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "provider", "provider": "openai-codex"},
    ) == ["openai"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "agentHarness", "runtime": "codex"},
    ) == ["openai"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "channel", "channel": "telegram"},
    ) == ["demo-channel"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "route", "route": "webhook"},
    ) == ["demo-channel"]


def test_resolve_manifest_activation_plugin_ids_matches_capabilities_and_scopes() -> None:
    plugins = _activation_plugins()

    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "capability", "capability": "provider"},
    ) == ["openai"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "capability", "capability": "tool"},
    ) == ["demo-channel"]
    assert resolve_manifest_activation_plugin_ids(
        plugins=plugins,
        trigger={"kind": "capability", "capability": "hook"},
        origin="workspace",
    ) == ["demo-channel"]
    assert (
        resolve_manifest_activation_plugin_ids(
            plugins=plugins,
            trigger={"kind": "provider", "provider": "openai"},
            only_plugin_ids=[],
        )
        == []
    )
