from __future__ import annotations

from openzues.services.gateway_plugin_activation import (
    resolve_configured_channel_plugin_plan,
    resolve_manifest_activation_plan,
    resolve_manifest_activation_plugin_ids,
)


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


def test_resolve_manifest_activation_plan_projects_reason_entries() -> None:
    plugins = [
        {
            "id": "demo-channel",
            "providers": ["openai"],
            "channels": ["telegram"],
            "commandAliases": [
                {
                    "name": "demo",
                    "kind": "runtime-slash",
                    "cliCommand": "demo-tools",
                }
            ],
            "setup": {"providers": [{"id": "openai-codex"}]},
            "contracts": {"tools": ["custom-tool"]},
            "activation": {
                "onAgentHarnesses": ["codex"],
                "onCommands": ["demo-tools"],
                "onProviders": ["custom-provider"],
                "onChannels": ["telegram"],
                "onRoutes": ["webhook"],
                "onCapabilities": ["provider", "tool"],
            },
            "origin": "workspace",
        }
    ]

    assert resolve_manifest_activation_plan(
        plugins=plugins,
        trigger={"kind": "command", "command": "demo-tools"},
    ) == {
        "trigger": {"kind": "command", "command": "demo-tools"},
        "pluginIds": ["demo-channel"],
        "entries": [
            {
                "pluginId": "demo-channel",
                "origin": "workspace",
                "reasons": ["activation-command-hint", "manifest-command-alias"],
            }
        ],
        "diagnostics": [],
    }
    assert resolve_manifest_activation_plan(
        plugins=plugins,
        trigger={"kind": "provider", "provider": "openai-codex"},
    )["entries"][0]["reasons"] == ["manifest-setup-provider-owner"]
    assert resolve_manifest_activation_plan(
        plugins=plugins,
        trigger={"kind": "capability", "capability": "provider"},
    )["entries"][0]["reasons"] == [
        "activation-capability-hint",
        "activation-provider-hint",
        "manifest-provider-owner",
        "manifest-setup-provider-owner",
    ]


def test_resolve_configured_channel_plugin_plan_projects_activation_config() -> None:
    plugins = _activation_plugins()

    assert resolve_configured_channel_plugin_plan(
        plugins=plugins,
        config={
            "channels": {
                "telegram": {"enabled": True},
                "defaults": {"account": "primary"},
                "modelByChannel": {"telegram": "codex"},
            }
        },
    ) == {
        "scope": "configured-channels",
        "channelIds": ["telegram"],
        "pluginIds": ["demo-channel"],
        "entries": [
            {
                "channelId": "telegram",
                "sources": ["explicit-config"],
                "effective": True,
                "pluginIds": ["demo-channel"],
                "blockedReasons": [],
            }
        ],
        "diagnostics": [],
        "activationConfig": {
            "plugins": {
                "allow": ["demo-channel"],
                "entries": {"demo-channel": {"enabled": True}},
            }
        },
    }


def test_resolve_configured_channel_plugin_plan_respects_disabled_owner() -> None:
    plugins = _activation_plugins()

    assert resolve_configured_channel_plugin_plan(
        plugins=plugins,
        config={
            "plugins": {"entries": {"demo-channel": {"enabled": False}}},
            "channels": {"telegram": {"enabled": True}},
        },
    ) == {
        "scope": "configured-channels",
        "channelIds": ["telegram"],
        "pluginIds": [],
        "entries": [
            {
                "channelId": "telegram",
                "sources": ["explicit-config"],
                "effective": False,
                "pluginIds": [],
                "blockedReasons": ["plugin-disabled"],
            }
        ],
        "diagnostics": [],
    }


def test_resolve_configured_channel_plugin_plan_bypasses_allowlist_for_bundled_owner() -> None:
    plugins = [
        {
            "id": "bundled-telegram",
            "channels": ["telegram"],
            "origin": "bundled",
            "enabledByDefault": False,
        }
    ]

    assert resolve_configured_channel_plugin_plan(
        plugins=plugins,
        config={
            "plugins": {"allow": ["other-plugin"]},
            "channels": {"telegram": {"enabled": True}},
        },
    ) == {
        "scope": "configured-channels",
        "channelIds": ["telegram"],
        "pluginIds": ["bundled-telegram"],
        "entries": [
            {
                "channelId": "telegram",
                "sources": ["explicit-config"],
                "effective": True,
                "pluginIds": ["bundled-telegram"],
                "blockedReasons": [],
            }
        ],
        "diagnostics": [],
        "activationConfig": {
            "plugins": {
                "allow": ["bundled-telegram"],
                "entries": {"bundled-telegram": {"enabled": True}},
            }
        },
    }
