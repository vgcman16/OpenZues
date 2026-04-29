from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from openzues.services.gateway_plugin_runtime import (
    GatewayPluginRuntimeExecutorSpec,
    GatewayPluginRuntimeService,
)
from openzues.services.hermes_toolsets import (
    HermesToolsetSpec,
    expand_hermes_toolsets,
    iter_hermes_toolset_specs,
)

_PROFILE_OPTIONS: tuple[dict[str, str], ...] = (
    {"id": "minimal", "label": "Minimal"},
    {"id": "coding", "label": "Coding"},
    {"id": "messaging", "label": "Messaging"},
    {"id": "full", "label": "Full"},
)


class GatewayToolsCatalogService:
    def __init__(
        self,
        *,
        agent_id: str = "openzues",
        plugin_runtime_service: GatewayPluginRuntimeService | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._plugin_runtime_service = plugin_runtime_service

    def build_catalog(
        self,
        *,
        agent_id: str | None = None,
        include_plugins: bool = True,
    ) -> dict[str, Any]:
        if agent_id is not None and agent_id != self._agent_id:
            raise ValueError(f'unknown agent id "{agent_id}"')
        core_tools = [self._tool_payload(spec) for spec in _base_toolsets()]
        groups = [
            {
                "id": "openzues-toolsets",
                "label": "OpenZues Toolsets",
                "source": "core",
                "tools": core_tools,
            }
        ]
        if include_plugins and self._plugin_runtime_service is not None:
            groups.extend(
                _plugin_catalog_groups(
                    self._plugin_runtime_service.catalog_specs(),
                    existing_tool_names={str(tool["id"]) for tool in core_tools},
                )
            )
        return {
            "agentId": self._agent_id,
            "profiles": [dict(profile) for profile in _PROFILE_OPTIONS],
            "groups": groups,
        }

    def build_effective(
        self,
        *,
        agent_id: str,
        toolsets: Iterable[str] | None,
    ) -> dict[str, Any]:
        specs = _effective_tool_specs(toolsets)
        core_tools = [self._effective_tool_payload(spec) for spec in specs]
        plugin_groups = (
            _plugin_effective_groups(
                self._plugin_runtime_service.catalog_specs(),
                existing_tool_names={str(tool["id"]) for tool in core_tools},
            )
            if self._plugin_runtime_service is not None
            else []
        )
        groups: list[dict[str, Any]] = []
        if core_tools or not plugin_groups:
            groups.append(
                {
                    "id": "core",
                    "label": "Built-in tools",
                    "source": "core",
                    "tools": core_tools,
                }
            )
        groups.extend(plugin_groups)
        return {
            "agentId": agent_id,
            "profile": _effective_profile(specs),
            "groups": groups,
        }

    def _tool_payload(self, spec: HermesToolsetSpec) -> dict[str, Any]:
        return {
            "id": spec.name,
            "label": spec.name,
            "description": spec.summary,
            "source": "core",
            "defaultProfiles": _default_profiles(spec),
        }

    def _effective_tool_payload(self, spec: HermesToolsetSpec) -> dict[str, Any]:
        return {
            "id": spec.name,
            "label": spec.name,
            "description": spec.summary,
            "rawDescription": spec.summary,
            "source": "core",
        }


def _base_toolsets() -> tuple[HermesToolsetSpec, ...]:
    return tuple(
        spec
        for spec in iter_hermes_toolset_specs()
        if not spec.name.startswith("hermes-")
    )


def _effective_tool_specs(toolsets: Iterable[str] | None) -> tuple[HermesToolsetSpec, ...]:
    expanded = set(expand_hermes_toolsets(toolsets))
    return tuple(spec for spec in _base_toolsets() if spec.name in expanded)


def _effective_profile(specs: Iterable[HermesToolsetSpec]) -> str:
    resolved_specs = tuple(specs)
    if not resolved_specs:
        return "minimal"
    if any("messaging" in _default_profiles(spec) for spec in resolved_specs):
        return "messaging"
    return "coding"


def _default_profiles(spec: HermesToolsetSpec) -> list[str]:
    if spec.name in {"cronjob", "messaging", "tts", "clarify", "homeassistant"}:
        return ["messaging", "full"]
    return ["coding", "full"]


def _plugin_catalog_groups(
    specs: Iterable[GatewayPluginRuntimeExecutorSpec],
    *,
    existing_tool_names: set[str],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for spec in specs:
        if spec.tool in existing_tool_names:
            continue
        plugin_id = spec.plugin_id or spec.source or "plugin"
        group_id = f"plugin:{plugin_id}"
        group = groups.setdefault(
            group_id,
            {
                "id": group_id,
                "label": plugin_id,
                "source": "plugin",
                "pluginId": plugin_id,
                "tools": [],
            },
        )
        group["tools"].append(
            {
                "id": spec.tool,
                "label": spec.tool,
                "description": spec.description or "",
                "source": "plugin",
                "pluginId": plugin_id,
                "defaultProfiles": [],
            }
        )
        existing_tool_names.add(spec.tool)

    for group in groups.values():
        group["tools"] = sorted(group["tools"], key=lambda tool: str(tool.get("id") or ""))
    return sorted(groups.values(), key=lambda group: str(group.get("label") or ""))


def _plugin_effective_groups(
    specs: Iterable[GatewayPluginRuntimeExecutorSpec],
    *,
    existing_tool_names: set[str],
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for spec in specs:
        if spec.tool in existing_tool_names:
            continue
        plugin_id = spec.plugin_id or spec.source or "plugin"
        description = spec.description or ""
        tools.append(
            {
                "id": spec.tool,
                "label": spec.tool,
                "description": description,
                "rawDescription": description,
                "source": "plugin",
                "pluginId": plugin_id,
            }
        )
        existing_tool_names.add(spec.tool)
    if not tools:
        return []
    return [
        {
            "id": "plugin",
            "label": "Connected tools",
            "source": "plugin",
            "tools": sorted(tools, key=lambda tool: str(tool.get("label") or "")),
        }
    ]
