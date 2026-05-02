from __future__ import annotations

from typing import Any

from openzues.services.gateway_plugin_runtime import (
    build_plugin_runtime_executor_specs_from_active_registry,
)


async def _demo_executor(_tool_call_id: str, _args: dict[str, Any]) -> object:
    return {"ok": True}


def test_build_plugin_runtime_executor_specs_from_active_registry_projects_tools() -> None:
    registry = {
        "tools": [
            {
                "pluginId": "memory",
                "pluginName": "Memory",
                "source": "openclaw-plugin",
                "names": ["memory.search"],
                "description": "Search memory.",
                "executor": _demo_executor,
            },
            {
                "pluginId": "optional-pack",
                "pluginName": "Optional Pack",
                "source": "openclaw-plugin",
                "names": ["optional.tool"],
                "optional": True,
                "executor": _demo_executor,
            },
            {
                "pluginId": "core-shadow",
                "pluginName": "Core Shadow",
                "source": "openclaw-plugin",
                "names": ["agents_list"],
                "executor": _demo_executor,
            },
        ]
    }

    specs = build_plugin_runtime_executor_specs_from_active_registry(
        registry,
        existing_tool_names={"agents_list"},
        tool_allowlist=["group:plugins"],
    )

    assert [(spec.tool, spec.plugin_id, spec.optional) for spec in specs] == [
        ("memory.search", "memory", False),
        ("optional.tool", "optional-pack", True),
    ]
    assert specs[0].description == "Search memory."
    assert specs[0].source == "openclaw-plugin"


def test_build_plugin_runtime_executor_specs_from_active_registry_blocks_optional_tools() -> None:
    registry = {
        "tools": [
            {
                "pluginId": "optional-pack",
                "pluginName": "Optional Pack",
                "source": "openclaw-plugin",
                "names": ["optional.tool"],
                "optional": True,
                "executor": _demo_executor,
            }
        ]
    }

    specs = build_plugin_runtime_executor_specs_from_active_registry(
        registry,
        existing_tool_names=set(),
        tool_allowlist=[],
    )

    assert specs == ()


def test_active_registry_projection_blocks_plugin_id_conflicts() -> None:
    registry = {
        "tools": [
            {
                "pluginId": "agents_list",
                "pluginName": "Conflicting Plugin",
                "source": "openclaw-plugin",
                "names": ["conflict.extra"],
                "executor": _demo_executor,
            }
        ]
    }

    specs = build_plugin_runtime_executor_specs_from_active_registry(
        registry,
        existing_tool_names={"agents_list"},
        tool_allowlist=["group:plugins"],
    )

    assert specs == ()
