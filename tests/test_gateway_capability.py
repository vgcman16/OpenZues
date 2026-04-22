from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from openzues.schemas import InstanceView
from openzues.services.gateway_capability import (
    GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS,
    GatewayCapabilityService,
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


class _FakeMcpStatusClient:
    def __init__(self, response: object) -> None:
        self._response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call(self, method: str, params: dict[str, object]) -> object:
        self.calls.append((method, params))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


@dataclass(slots=True)
class _FakeCapabilityRuntime:
    connected: bool = True
    client: _FakeMcpStatusClient | None = None
    mcp_server_status: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.mcp_server_status is None:
            self.mcp_server_status = []


class _FakeCapabilityManager:
    def __init__(self, runtimes: dict[int, _FakeCapabilityRuntime]) -> None:
        self.instances = runtimes


def _gateway_capability_service(
    manager: _FakeCapabilityManager,
) -> GatewayCapabilityService:
    service = GatewayCapabilityService.__new__(GatewayCapabilityService)
    service.manager = manager
    return service


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


def test_gateway_capability_callable_method_catalog_accepts_wrapped_inner_tool_catalogs(
) -> None:
    instance = _instance_view(instance_id=8, name="Wrapped Tool Lane")

    payload = _build_callable_method_catalog(
        [instance],
        {
            8: [
                {
                    "id": "plugin-control-plane",
                    "tools": {
                        "items": [
                            {
                                "function": {"name": "browser.request"},
                                "scope": "operator.write",
                            },
                            {"toolName": "wizard.custom", "scope": "operator.read"},
                            {"method": "status"},
                        ]
                    },
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


def test_gateway_capability_callable_method_catalog_accepts_wrapped_inner_string_tool_catalogs(
) -> None:
    instance = _instance_view(instance_id=9, name="Wrapped String Tool Lane")

    payload = _build_callable_method_catalog(
        [instance],
        {
            9: [
                {
                    "id": "plugin-control-plane",
                    "tools": {
                        "items": [
                            "browser.request",
                            "wizard.custom",
                            "status",
                        ]
                    },
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


def test_gateway_capability_browser_runtime_accepts_wrapped_inner_string_catalogs() -> None:
    instance = _instance_view(
        instance_id=13,
        name="Wrapped Browser Runtime String Lane",
        mcp_servers=[{"id": "browser-runtime"}],
    )

    payload = _build_browser_runtime_view(
        [instance],
        {
            13: [
                {
                    "id": "browser-runtime",
                    "pluginId": "browser",
                    "tools": {"items": ["browser.request"]},
                    "services": {"items": ["browser-control"]},
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


def test_gateway_capability_browser_runtime_accepts_wrapped_inner_service_catalogs() -> None:
    instance = _instance_view(
        instance_id=12,
        name="Wrapped Browser Runtime Lane",
        mcp_servers=[{"id": "browser-runtime"}],
    )

    payload = _build_browser_runtime_view(
        [instance],
        {
            12: [
                {
                    "id": "browser-runtime",
                    "pluginId": "browser",
                    "tools": {
                        "items": [{"function": {"name": "browser.request"}}],
                    },
                    "services": {
                        "data": [{"service": {"id": "browser-control"}}],
                    },
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


@pytest.mark.asyncio
async def test_gateway_capability_refresh_mcp_status_prefers_live_raw_status_over_cached_summary(
) -> None:
    client = _FakeMcpStatusClient(
        {
            "data": [
                {
                    "id": "plugin-control-plane",
                    "pluginId": "browser",
                    "tools": [
                        {
                            "function": {"name": "browser.request"},
                            "scope": "operator.write",
                        }
                    ],
                    "services": [{"serviceId": "browser-control"}],
                }
            ]
        }
    )
    service = _gateway_capability_service(
        _FakeCapabilityManager(
            {
                7: _FakeCapabilityRuntime(
                    connected=True,
                    client=client,
                    mcp_server_status=[
                        {
                            "id": "plugin-control-plane",
                            "tools": ["browser.request"],
                            "services": ["browser-control"],
                        }
                    ],
                )
            }
        )
    )

    status_entries = await service._refresh_mcp_server_status(7)
    payload = _build_callable_method_catalog(
        [_instance_view(instance_id=7, name="Browser Lane")],
        {7: status_entries},
    )

    assert client.calls == [("mcpServerStatus/list", {"limit": 50})]
    assert status_entries == [
        {
            "id": "plugin-control-plane",
            "pluginId": "browser",
            "tools": [
                {
                    "function": {"name": "browser.request"},
                    "scope": "operator.write",
                }
            ],
            "services": [{"serviceId": "browser-control"}],
        }
    ]
    assert payload.servers == ["plugin-control-plane"]
    assert [(scope.scope, scope.methods) for scope in payload.scopes] == [
        ("operator.write", ["browser.request"])
    ]


@pytest.mark.parametrize(
    ("response",),
    [
        (
            [
                {
                    "id": "plugin-control-plane",
                    "pluginId": "browser",
                    "tools": ["browser.request"],
                }
            ],
        ),
        (
            {
                "items": [
                    {
                        "id": "plugin-control-plane",
                        "pluginId": "browser",
                        "tools": ["browser.request"],
                    }
                ]
            },
        ),
        (
            {
                "servers": [
                    {
                        "id": "plugin-control-plane",
                        "pluginId": "browser",
                        "tools": ["browser.request"],
                    }
                ]
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_gateway_capability_refresh_mcp_status_accepts_array_like_wrappers(
    response: object,
) -> None:
    client = _FakeMcpStatusClient(response)
    service = _gateway_capability_service(
        _FakeCapabilityManager(
            {
                9: _FakeCapabilityRuntime(
                    connected=True,
                    client=client,
                    mcp_server_status=[],
                )
            }
        )
    )

    status_entries = await service._refresh_mcp_server_status(9)

    assert client.calls == [("mcpServerStatus/list", {"limit": 50})]
    assert status_entries == [
        {
            "id": "plugin-control-plane",
            "pluginId": "browser",
            "tools": ["browser.request"],
        }
    ]


@pytest.mark.asyncio
async def test_gateway_capability_refresh_mcp_status_falls_back_to_cached_summary_on_error(
) -> None:
    service = _gateway_capability_service(
        _FakeCapabilityManager(
            {
                11: _FakeCapabilityRuntime(
                    connected=True,
                    client=_FakeMcpStatusClient(
                        TimeoutError(
                            f"timed out after {GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS}s"
                        )
                    ),
                    mcp_server_status=[
                        {
                            "id": "plugin-control-plane",
                            "tools": ["browser.request"],
                            "services": ["browser-control"],
                        }
                    ],
                )
            }
        )
    )

    status_entries = await service._refresh_mcp_server_status(11)

    assert status_entries == [
        {
            "id": "plugin-control-plane",
            "tools": ["browser.request"],
            "services": ["browser-control"],
        }
    ]


@pytest.mark.asyncio
async def test_gateway_capability_load_mcp_status_catalog_keeps_cached_offline_lane_status(
) -> None:
    service = _gateway_capability_service(
        _FakeCapabilityManager(
            {
                12: _FakeCapabilityRuntime(
                    connected=False,
                    client=None,
                    mcp_server_status=[
                        {
                            "id": "browser-runtime",
                            "pluginId": "browser",
                            "tools": ["browser.request"],
                            "services": ["browser-control"],
                        }
                    ],
                )
            }
        )
    )
    instance = _instance_view(instance_id=12, name="Offline Browser Lane", connected=False)

    status_by_instance = await service._load_mcp_server_status_catalog([instance])
    payload = _build_browser_runtime_view([instance], status_by_instance)

    assert status_by_instance == {
        12: [
            {
                "id": "browser-runtime",
                "pluginId": "browser",
                "tools": ["browser.request"],
                "services": ["browser-control"],
            }
        ]
    }
    assert payload is not None
    assert payload.status == "info"
    assert payload.methods == ["browser.request"]
    assert payload.services == ["browser-control"]
    assert payload.plugins == ["browser"]
    assert payload.servers == ["browser-runtime"]
    assert len(payload.lanes) == 1
    lane = payload.lanes[0]
    assert lane.instance_id == 12
    assert lane.instance_name == "Offline Browser Lane"
    assert lane.connected is False
    assert lane.level == "info"
    assert lane.ready is False
    assert lane.method_count == 1
    assert lane.service_count == 1
    assert lane.methods == ["browser.request"]
    assert lane.services == ["browser-control"]
    assert lane.plugins == ["browser"]
    assert lane.servers == ["browser-runtime"]
    assert lane.summary == "Offline Browser Lane shows browser runtime signals on an offline lane."


@pytest.mark.parametrize(("response",), [([],), ({"items": []},), ({"servers": []},)])
@pytest.mark.asyncio
async def test_gateway_capability_refresh_mcp_status_preserves_empty_live_catalogs(
    response: object,
) -> None:
    service = _gateway_capability_service(
        _FakeCapabilityManager(
            {
                13: _FakeCapabilityRuntime(
                    connected=True,
                    client=_FakeMcpStatusClient(response),
                    mcp_server_status=[
                        {
                            "id": "stale-plugin-control-plane",
                            "tools": ["browser.request"],
                        }
                    ],
                )
            }
        )
    )

    status_entries = await service._refresh_mcp_server_status(13)

    assert status_entries == []
