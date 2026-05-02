from __future__ import annotations

from collections.abc import Iterable, Mapping


def resolve_manifest_activation_plugin_ids(
    *,
    plugins: Iterable[Mapping[str, object]],
    trigger: Mapping[str, object],
    origin: str | None = None,
    only_plugin_ids: Iterable[str] | None = None,
) -> list[str]:
    only_plugin_id_set = (
        {_normalize_plugin_id(plugin_id) for plugin_id in only_plugin_ids}
        if only_plugin_ids is not None
        else None
    )
    normalized_origin = _normalize_optional_string(origin)
    plugin_ids: set[str] = set()
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
        if _matches_manifest_activation_trigger(plugin, trigger):
            plugin_ids.add(plugin_id)
    return sorted(plugin_ids)


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


def _activation_command_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    ids = {
        normalized
        for value in _string_items(activation.get("onCommands"))
        if (normalized := _normalize_command_id(value))
    }
    for alias in _mapping_items(plugin.get("commandAliases")):
        value = alias.get("cliCommand") or alias.get("name")
        normalized = _normalize_command_id(value)
        if normalized:
            ids.add(normalized)
    return ids


def _activation_provider_ids(plugin: Mapping[str, object]) -> set[str]:
    ids = {
        normalized
        for value in _string_items(plugin.get("providers"))
        if (normalized := _normalize_provider_id(value))
    }
    activation = _mapping(plugin.get("activation"))
    for value in _string_items(activation.get("onProviders")):
        normalized = _normalize_provider_id(value)
        if normalized:
            ids.add(normalized)
    setup = _mapping(plugin.get("setup"))
    for provider in _mapping_items(setup.get("providers")):
        normalized = _normalize_provider_id(provider.get("id"))
        if normalized:
            ids.add(normalized)
    return ids


def _activation_channel_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    values = [*_string_items(plugin.get("channels")), *_string_items(activation.get("onChannels"))]
    return {
        normalized for value in values if (normalized := _normalize_command_id(value))
    }


def _activation_route_ids(plugin: Mapping[str, object]) -> set[str]:
    activation = _mapping(plugin.get("activation"))
    return {
        normalized
        for value in _string_items(activation.get("onRoutes"))
        if (normalized := _normalize_command_id(value))
    }


def _has_activation_capability(plugin: Mapping[str, object], capability: str) -> bool:
    activation = _mapping(plugin.get("activation"))
    if capability in {
        _normalize_command_id(value)
        for value in _string_items(activation.get("onCapabilities"))
    }:
        return True
    if capability == "provider":
        return bool(_activation_provider_ids(plugin))
    if capability == "channel":
        return bool(_activation_channel_ids(plugin))
    if capability == "tool":
        contracts = _mapping(plugin.get("contracts"))
        return bool(_string_items(contracts.get("tools")))
    if capability == "hook":
        return bool(_string_items(plugin.get("hooks")))
    return False


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


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
