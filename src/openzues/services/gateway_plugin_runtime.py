from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from openzues.services.gateway_method_policy import ADMIN_GATEWAY_METHOD_SCOPE

type GatewayPluginExecutor = Callable[[str, dict[str, Any]], Awaitable[object]]


@dataclass(frozen=True, slots=True)
class GatewayPluginRuntimeExecutorSpec:
    tool: str
    executor: GatewayPluginExecutor
    enabled: bool = True
    owner_only: bool = False
    optional: bool = False
    plugin_id: str | None = None
    plugin_name: str | None = None
    description: str | None = None
    source: str = "plugin"


type GatewayPluginRuntimeExecutorEntry = (
    GatewayPluginRuntimeExecutorSpec
    | Mapping[str, object]
    | tuple[str, GatewayPluginExecutor]
)


class GatewayPluginRuntimeExecutorRegistry(Protocol):
    def list_executors(self) -> Iterable[GatewayPluginRuntimeExecutorEntry]: ...


@dataclass(frozen=True, slots=True)
class GatewayPluginRuntimeExecutorResolution:
    tool: str
    executor: GatewayPluginExecutor
    optional: bool = False
    plugin_id: str | None = None
    plugin_name: str | None = None
    source: str = "plugin"


class GatewayPluginRuntimeService:
    def __init__(
        self,
        *,
        executors: Mapping[str, GatewayPluginExecutor]
        | Iterable[tuple[str, GatewayPluginExecutor]]
        | None = None,
        registry_executors: Iterable[GatewayPluginRuntimeExecutorEntry] | None = None,
        executor_registry: GatewayPluginRuntimeExecutorRegistry | None = None,
        owner_only: Iterable[str] = (),
    ) -> None:
        self._owner_only = {
            str(tool or "").strip()
            for tool in owner_only
            if str(tool or "").strip()
        }
        self._configured_executors: list[GatewayPluginRuntimeExecutorSpec] = []
        if executors is not None:
            items = executors.items() if isinstance(executors, Mapping) else executors
            for tool, executor in items:
                spec = _normalize_executor_spec(
                    (tool, executor),
                    owner_only_tools=self._owner_only,
                )
                if spec is not None:
                    self._configured_executors.append(spec)
        self._registry_executors = [
            spec
            for entry in registry_executors or ()
            if (
                spec := _normalize_executor_spec(
                    entry,
                    owner_only_tools=self._owner_only,
                )
            )
            is not None
        ]
        self._executor_registry = executor_registry

    def resolve_executor(
        self,
        tool: str,
        requester: object,
        args: Mapping[str, object],
    ) -> GatewayPluginRuntimeExecutorResolution | None:
        del args
        normalized_tool = str(tool or "").strip()
        if not normalized_tool:
            return None
        for spec in self._iter_ordered_specs():
            if not spec.enabled:
                continue
            if spec.tool != normalized_tool:
                continue
            if spec.owner_only and not _plugin_requester_is_owner(requester):
                return None
            return GatewayPluginRuntimeExecutorResolution(
                tool=normalized_tool,
                executor=spec.executor,
                optional=spec.optional,
                plugin_id=spec.plugin_id,
                plugin_name=spec.plugin_name,
                source=spec.source,
            )
        return None

    def _iter_ordered_specs(self) -> Iterable[GatewayPluginRuntimeExecutorSpec]:
        seen_tools: set[str] = set()
        for spec in self._configured_executors:
            if not spec.enabled:
                continue
            if spec.tool in seen_tools:
                continue
            seen_tools.add(spec.tool)
            yield spec
        for spec in self._registry_executors:
            if not spec.enabled:
                continue
            if spec.tool in seen_tools:
                continue
            seen_tools.add(spec.tool)
            yield spec
        if self._executor_registry is None:
            return
        for entry in self._executor_registry.list_executors():
            registry_spec = _normalize_executor_spec(
                entry,
                owner_only_tools=self._owner_only,
            )
            if (
                registry_spec is None
                or not registry_spec.enabled
                or registry_spec.tool in seen_tools
            ):
                continue
            seen_tools.add(registry_spec.tool)
            yield registry_spec

    def catalog_specs(
        self,
        *,
        include_owner_only: bool = False,
    ) -> tuple[GatewayPluginRuntimeExecutorSpec, ...]:
        return tuple(
            spec
            for spec in self._iter_ordered_specs()
            if include_owner_only or not spec.owner_only
        )


def _normalize_executor_spec(
    entry: GatewayPluginRuntimeExecutorEntry,
    *,
    owner_only_tools: set[str],
) -> GatewayPluginRuntimeExecutorSpec | None:
    if isinstance(entry, GatewayPluginRuntimeExecutorSpec):
        normalized_tool = str(entry.tool or "").strip()
        if not normalized_tool:
            return None
        return GatewayPluginRuntimeExecutorSpec(
            tool=normalized_tool,
            executor=entry.executor,
            enabled=entry.enabled,
            owner_only=entry.owner_only or normalized_tool in owner_only_tools,
            optional=entry.optional,
            plugin_id=_optional_string(entry.plugin_id),
            plugin_name=_optional_string(entry.plugin_name),
            description=_optional_string(entry.description),
            source=str(entry.source or "plugin").strip() or "plugin",
        )
    if isinstance(entry, tuple):
        if len(entry) != 2:
            return None
        raw_tool, raw_executor = entry
        normalized_tool = str(raw_tool or "").strip()
        if not normalized_tool or not callable(raw_executor):
            return None
        return GatewayPluginRuntimeExecutorSpec(
            tool=normalized_tool,
            executor=raw_executor,
            owner_only=normalized_tool in owner_only_tools,
        )
    mapping_tool = entry.get("tool") or entry.get("name")
    mapping_executor = entry.get("executor")
    normalized_tool = str(mapping_tool or "").strip()
    if not normalized_tool or not callable(mapping_executor):
        return None
    owner_only = bool(entry.get("owner_only", entry.get("ownerOnly", False)))
    return GatewayPluginRuntimeExecutorSpec(
        tool=normalized_tool,
        executor=cast(GatewayPluginExecutor, mapping_executor),
        enabled=bool(entry.get("enabled", True)),
        owner_only=owner_only or normalized_tool in owner_only_tools,
        optional=bool(entry.get("optional", False)),
        plugin_id=_optional_string(entry.get("plugin_id", entry.get("pluginId"))),
        plugin_name=_optional_string(entry.get("plugin_name", entry.get("pluginName"))),
        description=_optional_string(entry.get("description")),
        source=str(entry.get("source") or "plugin").strip() or "plugin",
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _plugin_requester_is_owner(requester: object) -> bool:
    caller_scopes = getattr(requester, "caller_scopes", None)
    if caller_scopes is None:
        return True
    return ADMIN_GATEWAY_METHOD_SCOPE in caller_scopes
