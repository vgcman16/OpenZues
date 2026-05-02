from __future__ import annotations

from collections.abc import Iterable, Mapping


def resolve_manifest_activation_plan(
    *,
    plugins: Iterable[Mapping[str, object]],
    trigger: Mapping[str, object],
    origin: str | None = None,
    only_plugin_ids: Iterable[str] | None = None,
) -> dict[str, object]:
    only_plugin_id_set = (
        {_normalize_plugin_id(plugin_id) for plugin_id in only_plugin_ids}
        if only_plugin_ids is not None
        else None
    )
    normalized_origin = _normalize_optional_string(origin)
    entries: list[dict[str, object]] = []
    for plugin in plugins:
        plugin_id = _normalize_plugin_id(plugin.get("id"))
        if not plugin_id:
            continue
        if (
            normalized_origin
            and _normalize_optional_string(plugin.get("origin")) != normalized_origin
        ):
            continue
        if only_plugin_id_set is not None and plugin_id not in only_plugin_id_set:
            continue
        reasons = _manifest_activation_trigger_reasons(plugin, trigger)
        if not reasons:
            continue
        entries.append(
            {
                "pluginId": plugin_id,
                "origin": _normalize_optional_string(plugin.get("origin")) or "config",
                "reasons": reasons,
            }
        )
    entries.sort(key=lambda entry: str(entry["pluginId"]))
    return {
        "trigger": dict(trigger),
        "pluginIds": [str(entry["pluginId"]) for entry in entries],
        "entries": entries,
        "diagnostics": [],
    }


def resolve_manifest_activation_plans(
    *,
    plugins: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    plugin_rows = tuple(plugins)
    plans: list[dict[str, object]] = []
    for trigger in _manifest_activation_triggers(plugin_rows):
        plan = resolve_manifest_activation_plan(plugins=plugin_rows, trigger=trigger)
        entries = plan.get("entries")
        if isinstance(entries, list) and entries:
            plans.append(plan)
    return plans


def resolve_manifest_activation_plugin_ids(
    *,
    plugins: Iterable[Mapping[str, object]],
    trigger: Mapping[str, object],
    origin: str | None = None,
    only_plugin_ids: Iterable[str] | None = None,
) -> list[str]:
    plan = resolve_manifest_activation_plan(
        plugins=plugins,
        trigger=trigger,
        origin=origin,
        only_plugin_ids=only_plugin_ids,
    )
    plugin_ids = plan.get("pluginIds")
    if not isinstance(plugin_ids, list):
        return []
    return [str(plugin_id) for plugin_id in plugin_ids]


def resolve_configured_channel_plugin_plan(
    *,
    plugins: Iterable[Mapping[str, object]],
    config: Mapping[str, object],
) -> dict[str, object]:
    channel_ids = _configured_channel_ids(config)
    plugin_rows = tuple(plugins)
    plugins_by_id = {
        plugin_id: plugin
        for plugin in plugin_rows
        if (plugin_id := _normalize_plugin_id(plugin.get("id")))
    }
    entries: list[dict[str, object]] = []
    plugin_ids: list[str] = []
    for channel_id in channel_ids:
        candidate_owner_ids = resolve_manifest_activation_plugin_ids(
            plugins=plugin_rows,
            trigger={"kind": "channel", "channel": channel_id},
        )
        owner_ids: list[str] = []
        blocked_reasons: list[str] = []
        for candidate_owner_id in candidate_owner_ids:
            blocked_reason = _configured_channel_owner_block_reason(
                plugins_by_id.get(candidate_owner_id),
                config,
                channel_id=channel_id,
            )
            if blocked_reason is not None:
                blocked_reasons.append(blocked_reason)
                continue
            owner_ids.append(candidate_owner_id)
        plugin_ids.extend(owner_ids)
        entries.append(
            {
                "channelId": channel_id,
                "sources": ["explicit-config"],
                "effective": bool(owner_ids),
                "pluginIds": owner_ids,
                "blockedReasons": (
                    []
                    if owner_ids
                    else (_dedupe(blocked_reasons) or ["no-channel-owner"])
                ),
            }
        )
    scoped_plugin_ids = _dedupe(plugin_ids)
    payload: dict[str, object] = {
        "scope": "configured-channels",
        "channelIds": channel_ids,
        "pluginIds": scoped_plugin_ids,
        "entries": entries,
        "diagnostics": [],
    }
    if scoped_plugin_ids:
        payload["activationConfig"] = {
            "plugins": {
                "allow": scoped_plugin_ids,
                "entries": {
                    plugin_id: {"enabled": True} for plugin_id in scoped_plugin_ids
                },
            }
        }
    return payload


def _manifest_activation_triggers(
    plugins: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    triggers: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, field: str, value: object) -> None:
        normalized = _normalize_command_id(value)
        if not normalized:
            return
        key = (kind, normalized)
        if key in seen:
            return
        seen.add(key)
        triggers.append({"kind": kind, field: normalized})

    for plugin in plugins:
        activation = _mapping(plugin.get("activation"))
        for command in _string_items(activation.get("onCommands")):
            add("command", "command", command)
        for command in _activation_command_alias_ids(plugin):
            add("command", "command", command)
        for provider in _string_items(activation.get("onProviders")):
            add("provider", "provider", provider)
        for provider in _string_items(plugin.get("providers")):
            add("provider", "provider", provider)
        for provider in _activation_setup_provider_ids(plugin):
            add("provider", "provider", provider)
        for runtime in _string_items(activation.get("onAgentHarnesses")):
            add("agentHarness", "runtime", runtime)
        for channel in _string_items(activation.get("onChannels")):
            add("channel", "channel", channel)
        for channel in _string_items(plugin.get("channels")):
            add("channel", "channel", channel)
        for route in _string_items(activation.get("onRoutes")):
            add("route", "route", route)
        for capability in _manifest_activation_capability_triggers(plugin):
            add("capability", "capability", capability)
    return sorted(triggers, key=_activation_trigger_sort_key)


def _manifest_activation_trigger_reasons(
    plugin: Mapping[str, object],
    trigger: Mapping[str, object],
) -> list[str]:
    kind = _normalize_command_id(trigger.get("kind"))
    if kind == "command":
        expected = _normalize_command_id(trigger.get("command"))
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-command-hint"
                    if expected in _activation_command_hint_ids(plugin)
                    else None,
                    "manifest-command-alias"
                    if expected in _activation_command_alias_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if kind == "provider":
        expected = _normalize_provider_id(trigger.get("provider"))
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-provider-hint"
                    if expected in _activation_provider_hint_ids(plugin)
                    else None,
                    "manifest-provider-owner"
                    if expected in _manifest_provider_owner_ids(plugin)
                    else None,
                    "manifest-setup-provider-owner"
                    if expected in _activation_setup_provider_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if kind == "agentharness":
        expected = _normalize_command_id(trigger.get("runtime"))
        return (
            ["activation-agent-harness-hint"]
            if expected in _activation_agent_harness_ids(plugin)
            else []
        )
    if kind == "channel":
        expected = _normalize_command_id(trigger.get("channel"))
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-channel-hint"
                    if expected in _activation_channel_hint_ids(plugin)
                    else None,
                    "manifest-channel-owner"
                    if expected in _manifest_channel_owner_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if kind == "route":
        expected = _normalize_command_id(trigger.get("route"))
        return (
            ["activation-route-hint"]
            if expected in _activation_route_ids(plugin)
            else []
        )
    if kind == "capability":
        return _manifest_activation_capability_reasons(
            plugin,
            _normalize_command_id(trigger.get("capability")),
        )
    return []


def _manifest_activation_capability_reasons(
    plugin: Mapping[str, object],
    capability: str,
) -> list[str]:
    if capability == "provider":
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-capability-hint"
                    if capability in _activation_capability_ids(plugin)
                    else None,
                    "activation-provider-hint"
                    if _activation_provider_hint_ids(plugin)
                    else None,
                    "manifest-provider-owner"
                    if _manifest_provider_owner_ids(plugin)
                    else None,
                    "manifest-setup-provider-owner"
                    if _activation_setup_provider_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if capability == "channel":
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-capability-hint"
                    if capability in _activation_capability_ids(plugin)
                    else None,
                    "activation-channel-hint"
                    if _activation_channel_hint_ids(plugin)
                    else None,
                    "manifest-channel-owner"
                    if _manifest_channel_owner_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if capability == "tool":
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-capability-hint"
                    if capability in _activation_capability_ids(plugin)
                    else None,
                    "manifest-tool-contract"
                    if _contract_tool_ids(plugin)
                    else None,
                )
                if reason is not None
            ]
        )
    if capability == "hook":
        return _dedupe(
            [
                reason
                for reason in (
                    "activation-capability-hint"
                    if capability in _activation_capability_ids(plugin)
                    else None,
                    "manifest-hook-owner"
                    if _string_items(plugin.get("hooks"))
                    else None,
                )
                if reason is not None
            ]
        )
    return []


def _matches_manifest_activation_trigger(
    plugin: Mapping[str, object],
    trigger: Mapping[str, object],
) -> bool:
    kind = _normalize_command_id(trigger.get("kind"))
    if kind == "command":
        return _normalize_command_id(trigger.get("command")) in _activation_command_ids(plugin)
    if kind == "provider":
        return _normalize_provider_id(trigger.get("provider")) in _activation_provider_ids(plugin)
    if kind == "agentharness":
        return _normalize_command_id(trigger.get("runtime")) in _activation_agent_harness_ids(
            plugin
        )
    if kind == "channel":
        return _normalize_command_id(trigger.get("channel")) in _activation_channel_ids(plugin)
    if kind == "route":
        return _normalize_command_id(trigger.get("route")) in _activation_route_ids(plugin)
    if kind == "capability":
        return _has_activation_capability(plugin, _normalize_command_id(trigger.get("capability")))
    return False


def _activation_agent_harness_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onAgentHarnesses"))
        if (normalized := _normalize_command_id(value))
    }


def _activation_command_hint_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onCommands"))
        if (normalized := _normalize_command_id(value))
    }


def _activation_command_alias_ids(plugin: Mapping[str, object]) -> set[str]:
    ids: set[str] = set()
    aliases = plugin.get("commandAliases")
    if not isinstance(aliases, list):
        return ids
    for alias in aliases:
        if isinstance(alias, str):
            value: object = alias
        elif isinstance(alias, Mapping):
            value = alias.get("cliCommand") or alias.get("name")
        else:
            continue
        normalized = _normalize_command_id(value)
        if normalized:
            ids.add(normalized)
    return ids


def _activation_command_ids(plugin: Mapping[str, object]) -> set[str]:
    return _activation_command_hint_ids(plugin) | _activation_command_alias_ids(plugin)


def _activation_provider_hint_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onProviders"))
        if (normalized := _normalize_provider_id(value))
    }


def _manifest_provider_owner_ids(plugin: Mapping[str, object]) -> set[str]:
    return {
        normalized
        for value in _string_items(plugin.get("providers"))
        if (normalized := _normalize_provider_id(value))
    }


def _activation_setup_provider_ids(plugin: Mapping[str, object]) -> set[str]:
    setup = _mapping(plugin.get("setup"))
    return {
        normalized
        for provider in _mapping_items(setup.get("providers"))
        if (normalized := _normalize_provider_id(provider.get("id")))
    }


def _activation_provider_ids(plugin: Mapping[str, object]) -> set[str]:
    return (
        _manifest_provider_owner_ids(plugin)
        | _activation_provider_hint_ids(plugin)
        | _activation_setup_provider_ids(plugin)
    )


def _activation_channel_hint_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onChannels"))
        if (normalized := _normalize_command_id(value))
    }


def _manifest_channel_owner_ids(plugin: Mapping[str, object]) -> set[str]:
    return {
        normalized
        for value in _string_items(plugin.get("channels"))
        if (normalized := _normalize_command_id(value))
    }


def _activation_channel_ids(plugin: Mapping[str, object]) -> set[str]:
    return _manifest_channel_owner_ids(plugin) | _activation_channel_hint_ids(plugin)


def _activation_route_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onRoutes"))
        if (normalized := _normalize_command_id(value))
    }


def _activation_capability_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onCapabilities"))
        if (normalized := _normalize_command_id(value))
    }


def _contract_tool_ids(plugin: Mapping[str, object]) -> set[str]:
    contracts = _mapping(plugin.get("contracts"))
    return {
        normalized
        for value in _string_items(contracts.get("tools"))
        if (normalized := _normalize_command_id(value))
    }


def _has_activation_capability(plugin: Mapping[str, object], capability: str) -> bool:
    if capability in _activation_capability_ids(plugin):
        return True
    if capability == "provider":
        return bool(_activation_provider_ids(plugin))
    if capability == "channel":
        return bool(_activation_channel_ids(plugin))
    if capability == "tool":
        return bool(_contract_tool_ids(plugin))
    if capability == "hook":
        return bool(_string_items(plugin.get("hooks")))
    return False


def _manifest_activation_capability_triggers(plugin: Mapping[str, object]) -> list[str]:
    capabilities = [
        capability
        for capability in _activation_capability_ids(plugin)
        if capability in {"provider", "channel", "tool", "hook"}
    ]
    if _activation_provider_ids(plugin):
        capabilities.append("provider")
    if _activation_channel_ids(plugin):
        capabilities.append("channel")
    if _contract_tool_ids(plugin):
        capabilities.append("tool")
    if _string_items(plugin.get("hooks")):
        capabilities.append("hook")
    return _dedupe(capabilities)


def _activation_trigger_value(trigger: Mapping[str, object]) -> str:
    for key in ("command", "provider", "runtime", "channel", "route", "capability"):
        normalized = _normalize_command_id(trigger.get(key))
        if normalized:
            return normalized
    return ""


def _activation_trigger_sort_key(trigger: Mapping[str, object]) -> tuple[int, str, str]:
    kind = _normalize_optional_string(trigger.get("kind")) or ""
    order = {
        "command": 0,
        "provider": 1,
        "agentHarness": 2,
        "channel": 3,
        "route": 4,
        "capability": 5,
    }.get(kind, 99)
    return (order, kind, _activation_trigger_value(trigger))


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _configured_channel_ids(config: Mapping[str, object]) -> list[str]:
    channels = _mapping(config.get("channels"))
    channel_ids: list[str] = []
    for channel_id, value in channels.items():
        normalized_channel_id = _normalize_command_id(channel_id)
        if not normalized_channel_id or normalized_channel_id in {
            "defaults",
            "modelbychannel",
        }:
            continue
        if _configured_channel_enabled(value):
            channel_ids.append(normalized_channel_id)
    return _dedupe(channel_ids)


def _configured_channel_enabled(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    if value.get("enabled") is False:
        return False
    if value.get("enabled") is True:
        return True
    return any(
        key != "enabled" and _channel_config_value_present(config_value)
        for key, config_value in value.items()
    )


def _channel_config_value_present(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping | list | tuple | set):
        return bool(value)
    return True


def _configured_channel_owner_block_reason(
    plugin: Mapping[str, object] | None,
    config: Mapping[str, object],
    *,
    channel_id: str,
) -> str | None:
    if plugin is None:
        return "no-channel-owner"
    plugin_id = _normalize_plugin_id(plugin.get("id"))
    plugins = _mapping(config.get("plugins"))
    if plugins.get("enabled") is False:
        return "plugins-disabled"
    if plugin_id in _plugin_id_list(plugins.get("deny")):
        return "blocked-by-denylist"
    entries = _mapping(plugins.get("entries"))
    entry = _mapping(entries.get(plugin_id))
    if entry.get("enabled") is False:
        return "plugin-disabled"
    allow = _plugin_id_list(plugins.get("allow"))
    origin = _normalize_command_id(plugin.get("origin"))
    if (
        origin in {"config", "global"}
        and plugin_id not in allow
        and entry.get("enabled") is not True
    ):
        return "untrusted-plugin"
    allowlist_bypass = (
        origin == "bundled"
        and _configured_channel_enabled(_mapping(config.get("channels")).get(channel_id))
    )
    if allow and plugin_id not in allow and not allowlist_bypass:
        return "not-in-allowlist"
    return None


def _plugin_id_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        plugin_id
        for item in value
        if (plugin_id := _normalize_plugin_id(item))
    ]


def _mapping_items(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _normalize_plugin_id(value: object) -> str:
    return str(value or "").strip()


def _normalize_optional_string(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_command_id(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_provider_id(value: object) -> str:
    return _normalize_command_id(value)
