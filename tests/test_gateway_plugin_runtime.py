from __future__ import annotations

from typing import Any

from openzues.services.gateway_method_policy import READ_GATEWAY_METHOD_SCOPE
from openzues.services.gateway_plugin_runtime import (
    GatewayPluginRuntimeService,
    build_plugin_runtime_control_ui_descriptor_specs_from_active_registry,
    build_plugin_runtime_executor_specs_from_active_registry,
    build_plugin_runtime_session_extension_specs_from_active_registry,
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


def test_active_registry_projection_includes_session_extensions_and_ui_descriptors() -> None:
    registry = {
        "sessionExtensions": [
            {
                "pluginId": "memory-core",
                "namespace": "focus",
                "description": "Focus state shown on session rows.",
                "source": "openclaw-plugin",
            },
            {
                "pluginId": "disabled-memory",
                "namespace": "hidden",
                "enabled": False,
                "source": "openclaw-plugin",
            },
        ],
        "controlUiDescriptors": [
            {
                "pluginId": "memory-core",
                "pluginName": "Memory Core",
                "source": "openclaw-plugin",
                "descriptor": {
                    "id": "memory-focus",
                    "surface": "session",
                    "label": "Memory Focus",
                    "description": "Session memory controls.",
                    "placement": "sidebar",
                    "requiredScopes": [READ_GATEWAY_METHOD_SCOPE],
                    "schema": {
                        "type": "object",
                        "properties": {"mode": {"type": "string"}},
                    },
                },
            },
            {
                "pluginId": "disabled-memory",
                "pluginName": "Disabled Memory",
                "enabled": False,
                "source": "openclaw-plugin",
                "descriptor": {
                    "id": "hidden-memory",
                    "surface": "session",
                    "label": "Hidden Memory",
                },
            },
        ],
    }

    session_specs = build_plugin_runtime_session_extension_specs_from_active_registry(
        registry
    )
    descriptor_specs = (
        build_plugin_runtime_control_ui_descriptor_specs_from_active_registry(registry)
    )
    service = GatewayPluginRuntimeService(
        session_extensions=session_specs,
        control_ui_descriptors=descriptor_specs,
    )

    assert [
        (spec.plugin_id, spec.namespace, spec.description, spec.enabled, spec.source)
        for spec in session_specs
    ] == [
        (
            "memory-core",
            "focus",
            "Focus state shown on session rows.",
            True,
            "openclaw-plugin",
        ),
        ("disabled-memory", "hidden", None, False, "openclaw-plugin"),
    ]
    assert [
        (
            spec.plugin_id,
            spec.plugin_name,
            spec.descriptor["id"],
            spec.enabled,
            spec.source,
        )
        for spec in descriptor_specs
    ] == [
        ("memory-core", "Memory Core", "memory-focus", True, "openclaw-plugin"),
        ("disabled-memory", "Disabled Memory", "hidden-memory", False, "openclaw-plugin"),
    ]

    assert service.has_session_extension("memory-core", "focus") is True
    assert service.has_session_extension("disabled-memory", "hidden") is False
    assert service.project_session_extensions(
        session_key="agent:main:main",
        session_id="session-1",
        plugin_extensions={
            "memory-core": {"focus": {"state": "active"}},
            "disabled-memory": {"hidden": {"state": "hidden"}},
        },
    ) == (
        {
            "pluginId": "memory-core",
            "namespace": "focus",
            "value": {"state": "active"},
        },
    )
    assert service.control_ui_descriptors() == (
        {
            "id": "memory-focus",
            "surface": "session",
            "label": "Memory Focus",
            "description": "Session memory controls.",
            "placement": "sidebar",
            "requiredScopes": [READ_GATEWAY_METHOD_SCOPE],
            "schema": {
                "type": "object",
                "properties": {"mode": {"type": "string"}},
            },
            "pluginId": "memory-core",
            "pluginName": "Memory Core",
        },
    )
