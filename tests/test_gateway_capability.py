from __future__ import annotations

from openzues.schemas import InstanceView
from openzues.services.gateway_capability import (
    _build_browser_runtime_view,
    _build_callable_method_catalog,
    _catalog_item_name,
)


def _instance_view(
    *,
    instance_id: int,
    name: str,
    connected: bool = True,
    plugins: list[dict[str, object]] | None = None,
    mcp_servers: list[dict[str, object]] | None = None,
) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name=name,
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=connected,
        plugins=plugins or [],
        mcp_servers=mcp_servers or [],
    )


def test_gateway_capability_catalog_item_name_supports_nested_function_service_and_plugin_ids(
) -> None:
    assert _catalog_item_name({"function": {"name": "browser.request"}}) == "browser.request"
    assert (
        _catalog_item_name({"service": {"serviceId": "browser-control"}})
        == "browser-control"
    )
    assert _catalog_item_name({"plugin": {"pluginId": "browser"}}) == "browser"


def test_gateway_capability_callable_method_catalog_accepts_nested_function_tools_and_server_ids(
) -> None:
    instance = _instance_view(instance_id=7, name="Plugin Registry Lane")

    payload = _build_callable_method_catalog(
        [instance],
        {
            7: [
                {
                    "id": "plugin-control-plane",
                    "tools": [
                        {
                            "function": {"name": "browser.request"},
                            "scope": "operator.write",
                        },
                        {"toolName": "wizard.custom", "scope": "operator.read"},
                        {"method": "status"},
                    ],
                }
            ]
        },
    )

    assert payload.server_count == 1
    assert payload.servers == ["plugin-control-plane"]
    assert payload.tool_count == 3
    assert payload.classified_method_count == 3
    assert payload.reserved_admin_methods == ["wizard.custom"]
    assert [(scope.scope, scope.methods) for scope in payload.scopes] == [
        ("operator.admin", ["wizard.custom"]),
        ("operator.read", ["status"]),
        ("operator.write", ["browser.request"]),
    ]


def test_gateway_capability_browser_runtime_uses_plugin_ids_and_service_ids_from_status(
) -> None:
    instance = _instance_view(
        instance_id=11,
        name="Browser Runtime Lane",
        mcp_servers=[{"id": "browser-runtime"}],
    )

    payload = _build_browser_runtime_view(
        [instance],
        {
            11: [
                {
                    "id": "browser-runtime",
                    "pluginId": "browser",
                    "tools": [{"function": {"name": "browser.request"}}],
                    "services": [{"serviceId": "browser-control"}],
                }
            ]
        },
    )

    assert payload is not None
    assert payload.status == "ready"
    assert payload.methods == ["browser.request"]
    assert payload.services == ["browser-control"]
    assert payload.plugins == ["browser"]
    assert payload.servers == ["browser-runtime"]
