from __future__ import annotations

from collections.abc import Iterable
from typing import Any

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
    def __init__(self, *, agent_id: str = "openzues") -> None:
        self._agent_id = agent_id

    def build_catalog(
        self,
        *,
        agent_id: str | None = None,
        include_plugins: bool = True,
    ) -> dict[str, Any]:
        del include_plugins
        if agent_id is not None and agent_id != self._agent_id:
            raise ValueError(f'unknown agent id "{agent_id}"')
        return {
            "agentId": self._agent_id,
            "profiles": [dict(profile) for profile in _PROFILE_OPTIONS],
            "groups": [
                {
                    "id": "openzues-toolsets",
                    "label": "OpenZues Toolsets",
                    "source": "core",
                    "tools": [self._tool_payload(spec) for spec in _base_toolsets()],
                }
            ],
        }

    def build_effective(
        self,
        *,
        agent_id: str,
        toolsets: Iterable[str] | None,
    ) -> dict[str, Any]:
        specs = _effective_tool_specs(toolsets)
        return {
            "agentId": agent_id,
            "profile": _effective_profile(specs),
            "groups": [
                {
                    "id": "core",
                    "label": "Built-in tools",
                    "source": "core",
                    "tools": [self._effective_tool_payload(spec) for spec in specs],
                }
            ],
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
