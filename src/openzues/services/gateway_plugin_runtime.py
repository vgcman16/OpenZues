from __future__ import annotations

import json
import math
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from openzues.services.gateway_method_policy import (
    ADMIN_GATEWAY_METHOD_SCOPE,
    ORDERED_OPERATOR_SCOPES,
)

type GatewayPluginExecutor = Callable[[str, dict[str, Any]], Awaitable[object]]
type GatewayPluginSessionExtensionProjector = Callable[[dict[str, object]], object]

_PLUGIN_JSON_VALUE_MAX_DEPTH = 32
_PLUGIN_JSON_VALUE_MAX_NODES = 4096
_PLUGIN_JSON_VALUE_MAX_OBJECT_KEYS = 512
_PLUGIN_JSON_VALUE_MAX_STRING_LENGTH = 64 * 1024
_PLUGIN_JSON_VALUE_MAX_SERIALIZED_BYTES = 256 * 1024
_MISSING = object()
_CONTROL_UI_SURFACES = frozenset({"session", "tool", "run", "settings"})
_KNOWN_OPERATOR_SCOPES = frozenset(ORDERED_OPERATOR_SCOPES)


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
    parameters: Mapping[str, object] | None = None
    source: str = "plugin"


@dataclass(frozen=True, slots=True)
class GatewayPluginSessionExtensionSpec:
    plugin_id: str
    namespace: str
    description: str | None = None
    enabled: bool = True
    projector: GatewayPluginSessionExtensionProjector | None = None
    source: str = "plugin"


@dataclass(frozen=True, slots=True)
class GatewayPluginControlUiDescriptorSpec:
    plugin_id: str
    descriptor: Mapping[str, object]
    plugin_name: str | None = None
    enabled: bool = True
    source: str = "plugin"


type GatewayPluginRuntimeExecutorEntry = (
    GatewayPluginRuntimeExecutorSpec
    | Mapping[str, object]
    | tuple[str, GatewayPluginExecutor]
)
type GatewayPluginSessionExtensionEntry = (
    GatewayPluginSessionExtensionSpec | Mapping[str, object] | tuple[str, str]
)
type GatewayPluginControlUiDescriptorEntry = (
    GatewayPluginControlUiDescriptorSpec
    | Mapping[str, object]
    | tuple[str, Mapping[str, object]]
)


class GatewayPluginRuntimeExecutorRegistry(Protocol):
    def list_executors(self) -> Iterable[GatewayPluginRuntimeExecutorEntry]: ...


class GatewayPluginSessionExtensionRegistry(Protocol):
    def list_session_extensions(self) -> Iterable[GatewayPluginSessionExtensionEntry]: ...


class GatewayPluginControlUiDescriptorRegistry(Protocol):
    def list_control_ui_descriptors(
        self,
    ) -> Iterable[GatewayPluginControlUiDescriptorEntry]: ...


@dataclass(frozen=True, slots=True)
class GatewayPluginRuntimeExecutorResolution:
    tool: str
    executor: GatewayPluginExecutor
    optional: bool = False
    plugin_id: str | None = None
    plugin_name: str | None = None
    parameters: Mapping[str, object] | None = None
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
        session_extensions: Iterable[GatewayPluginSessionExtensionEntry] | None = None,
        session_extension_registry: GatewayPluginSessionExtensionRegistry | None = None,
        control_ui_descriptors: Iterable[GatewayPluginControlUiDescriptorEntry] | None = None,
        control_ui_descriptor_registry: GatewayPluginControlUiDescriptorRegistry | None = None,
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
        self._registry_executors: list[GatewayPluginRuntimeExecutorSpec] = []
        for entry in registry_executors or ():
            registry_spec = _normalize_executor_spec(
                entry,
                owner_only_tools=self._owner_only,
            )
            if registry_spec is not None:
                self._registry_executors.append(registry_spec)
        self._executor_registry = executor_registry
        self._session_extensions: list[GatewayPluginSessionExtensionSpec] = []
        for session_entry in session_extensions or ():
            session_extension_spec = _normalize_session_extension_spec(session_entry)
            if session_extension_spec is not None:
                self._session_extensions.append(session_extension_spec)
        self._session_extension_registry = session_extension_registry
        self._control_ui_descriptors: list[GatewayPluginControlUiDescriptorSpec] = []
        for descriptor_entry in control_ui_descriptors or ():
            descriptor_spec = _normalize_control_ui_descriptor_spec(descriptor_entry)
            if descriptor_spec is not None:
                self._control_ui_descriptors.append(descriptor_spec)
        self._control_ui_descriptor_registry = control_ui_descriptor_registry

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
                parameters=spec.parameters,
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

    def control_ui_descriptors(self) -> tuple[dict[str, object], ...]:
        descriptors: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for spec in self._iter_control_ui_descriptor_specs():
            descriptor_id = cast(str, spec.descriptor["id"])
            key = (spec.plugin_id, descriptor_id)
            if key in seen:
                continue
            seen.add(key)
            payload = dict(spec.descriptor)
            payload["pluginId"] = spec.plugin_id
            if spec.plugin_name is not None:
                payload["pluginName"] = spec.plugin_name
            descriptors.append(payload)
        return tuple(descriptors)

    def has_session_extension(self, plugin_id: str, namespace: str) -> bool:
        return self._resolve_session_extension(plugin_id, namespace) is not None

    def project_session_extensions(
        self,
        *,
        session_key: str,
        session_id: str | None,
        plugin_extensions: Mapping[str, object] | None,
    ) -> tuple[dict[str, object], ...]:
        if not isinstance(plugin_extensions, Mapping):
            return ()
        projections: list[dict[str, object]] = []
        for spec in self._iter_session_extension_specs():
            state = _session_extension_state(
                plugin_extensions,
                plugin_id=spec.plugin_id,
                namespace=spec.namespace,
            )
            if state is _MISSING:
                continue
            projected = state
            if spec.projector is not None:
                try:
                    projected = spec.projector(
                        {
                            "sessionKey": session_key,
                            "sessionId": session_id,
                            "state": state,
                        }
                    )
                except Exception:
                    continue
            if not is_plugin_json_value(projected):
                continue
            projections.append(
                {
                    "pluginId": spec.plugin_id,
                    "namespace": spec.namespace,
                    "value": copy_plugin_json_value(projected),
                }
            )
        return tuple(projections)

    def _resolve_session_extension(
        self,
        plugin_id: str,
        namespace: str,
    ) -> GatewayPluginSessionExtensionSpec | None:
        normalized_plugin_id = str(plugin_id or "").strip()
        normalized_namespace = str(namespace or "").strip()
        if not normalized_plugin_id or not normalized_namespace:
            return None
        for spec in self._iter_session_extension_specs():
            if spec.plugin_id == normalized_plugin_id and spec.namespace == normalized_namespace:
                return spec
        return None

    def _iter_session_extension_specs(self) -> Iterable[GatewayPluginSessionExtensionSpec]:
        seen: set[tuple[str, str]] = set()
        for spec in self._session_extensions:
            if not spec.enabled:
                continue
            key = (spec.plugin_id, spec.namespace)
            if key in seen:
                continue
            seen.add(key)
            yield spec
        if self._session_extension_registry is None:
            return
        for entry in self._session_extension_registry.list_session_extensions():
            registry_spec = _normalize_session_extension_spec(entry)
            if registry_spec is None or not registry_spec.enabled:
                continue
            key = (registry_spec.plugin_id, registry_spec.namespace)
            if key in seen:
                continue
            seen.add(key)
            yield registry_spec

    def _iter_control_ui_descriptor_specs(
        self,
    ) -> Iterable[GatewayPluginControlUiDescriptorSpec]:
        for spec in self._control_ui_descriptors:
            if spec.enabled:
                yield spec
        if self._control_ui_descriptor_registry is None:
            return
        for entry in self._control_ui_descriptor_registry.list_control_ui_descriptors():
            descriptor_spec = _normalize_control_ui_descriptor_spec(entry)
            if descriptor_spec is not None and descriptor_spec.enabled:
                yield descriptor_spec


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
            parameters=_optional_mapping(entry.parameters),
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
        parameters=_optional_mapping(
            entry.get("parameters", entry.get("schema")),
        ),
        source=str(entry.get("source") or "plugin").strip() or "plugin",
    )


def _normalize_session_extension_spec(
    entry: GatewayPluginSessionExtensionEntry,
) -> GatewayPluginSessionExtensionSpec | None:
    if isinstance(entry, GatewayPluginSessionExtensionSpec):
        plugin_id = _optional_string(entry.plugin_id)
        namespace = _optional_string(entry.namespace)
        if plugin_id is None or namespace is None:
            return None
        return GatewayPluginSessionExtensionSpec(
            plugin_id=plugin_id,
            namespace=namespace,
            description=_optional_string(entry.description),
            enabled=entry.enabled,
            projector=entry.projector if callable(entry.projector) else None,
            source=str(entry.source or "plugin").strip() or "plugin",
        )
    if isinstance(entry, tuple):
        if len(entry) != 2:
            return None
        plugin_id = _optional_string(entry[0])
        namespace = _optional_string(entry[1])
        if plugin_id is None or namespace is None:
            return None
        return GatewayPluginSessionExtensionSpec(plugin_id=plugin_id, namespace=namespace)
    plugin_id = _optional_string(entry.get("plugin_id", entry.get("pluginId")))
    namespace = _optional_string(entry.get("namespace"))
    if plugin_id is None or namespace is None:
        return None
    projector = entry.get("projector", entry.get("project"))
    return GatewayPluginSessionExtensionSpec(
        plugin_id=plugin_id,
        namespace=namespace,
        description=_optional_string(entry.get("description")),
        enabled=bool(entry.get("enabled", True)),
        projector=cast(GatewayPluginSessionExtensionProjector, projector)
        if callable(projector)
        else None,
        source=str(entry.get("source") or "plugin").strip() or "plugin",
    )


def _normalize_control_ui_descriptor_spec(
    entry: GatewayPluginControlUiDescriptorEntry,
) -> GatewayPluginControlUiDescriptorSpec | None:
    if isinstance(entry, GatewayPluginControlUiDescriptorSpec):
        plugin_id = _optional_string(entry.plugin_id)
        if plugin_id is None:
            return None
        descriptor = _normalize_control_ui_descriptor_payload(entry.descriptor)
        if descriptor is None:
            return None
        return GatewayPluginControlUiDescriptorSpec(
            plugin_id=plugin_id,
            plugin_name=_optional_string(entry.plugin_name),
            descriptor=descriptor,
            enabled=entry.enabled,
            source=str(entry.source or "plugin").strip() or "plugin",
        )
    if isinstance(entry, tuple):
        if len(entry) != 2:
            return None
        plugin_id = _optional_string(entry[0])
        if plugin_id is None:
            return None
        descriptor = _normalize_control_ui_descriptor_payload(entry[1])
        if descriptor is None:
            return None
        return GatewayPluginControlUiDescriptorSpec(
            plugin_id=plugin_id,
            descriptor=descriptor,
        )

    plugin_id = _optional_string(entry.get("plugin_id", entry.get("pluginId")))
    if plugin_id is None:
        return None
    raw_descriptor = entry.get("descriptor")
    descriptor_source = raw_descriptor if isinstance(raw_descriptor, Mapping) else entry
    descriptor = _normalize_control_ui_descriptor_payload(descriptor_source)
    if descriptor is None:
        return None
    return GatewayPluginControlUiDescriptorSpec(
        plugin_id=plugin_id,
        plugin_name=_optional_string(entry.get("plugin_name", entry.get("pluginName"))),
        descriptor=descriptor,
        enabled=bool(entry.get("enabled", True)),
        source=str(entry.get("source") or "plugin").strip() or "plugin",
    )


def _normalize_control_ui_descriptor_payload(
    descriptor: Mapping[str, object],
) -> Mapping[str, object] | None:
    descriptor_id = _optional_string(descriptor.get("id"))
    surface = _optional_string(descriptor.get("surface"))
    label = _optional_string(descriptor.get("label"))
    if (
        descriptor_id is None
        or surface not in _CONTROL_UI_SURFACES
        or label is None
    ):
        return None

    payload: dict[str, object] = {
        "id": descriptor_id,
        "surface": surface,
        "label": label,
    }
    if "description" in descriptor:
        normalized_description = _optional_string(descriptor.get("description"))
        if normalized_description is None:
            return None
        payload["description"] = normalized_description
    if "placement" in descriptor:
        normalized_placement = _optional_string(descriptor.get("placement"))
        if normalized_placement is None:
            return None
        payload["placement"] = normalized_placement
    if "requiredScopes" in descriptor:
        required_scopes = _normalize_control_ui_required_scopes(
            descriptor.get("requiredScopes")
        )
        if required_scopes is None:
            return None
        payload["requiredScopes"] = list(required_scopes)
    if "schema" in descriptor:
        schema = descriptor.get("schema")
        if not is_plugin_json_value(schema):
            return None
        payload["schema"] = copy_plugin_json_value(schema)
    return payload


def _normalize_control_ui_required_scopes(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    scopes: list[str] = []
    for entry in value:
        scope = _optional_string(entry)
        if scope is None or scope not in _KNOWN_OPERATOR_SCOPES:
            return None
        scopes.append(scope)
    return tuple(scopes)


def build_plugin_runtime_executor_specs_from_active_registry(
    registry: Mapping[str, object],
    *,
    existing_tool_names: Iterable[str] = (),
    tool_allowlist: Iterable[str] = (),
) -> tuple[GatewayPluginRuntimeExecutorSpec, ...]:
    tools = registry.get("tools")
    if not isinstance(tools, list):
        return ()
    existing_normalized = {_normalize_tool_name(tool) for tool in existing_tool_names}
    allowlist = {_normalize_tool_name(tool) for tool in tool_allowlist}
    blocked_plugins: set[str] = set()
    specs: list[GatewayPluginRuntimeExecutorSpec] = []
    for entry in tools:
        if not isinstance(entry, Mapping):
            continue
        plugin_id = _optional_string(entry.get("pluginId", entry.get("plugin_id")))
        if plugin_id is None:
            continue
        plugin_key = _normalize_tool_name(plugin_id)
        if plugin_key in blocked_plugins:
            continue
        if plugin_key in existing_normalized:
            blocked_plugins.add(plugin_key)
            continue
        optional = bool(entry.get("optional", False))
        executor = entry.get("executor")
        if not callable(executor):
            continue
        for tool in _active_registry_tool_names(entry):
            tool_key = _normalize_tool_name(tool)
            if not tool_key:
                continue
            if optional and not _optional_tool_allowed(
                tool_key=tool_key,
                plugin_key=plugin_key,
                allowlist=allowlist,
            ):
                continue
            if tool_key in existing_normalized:
                continue
            existing_normalized.add(tool_key)
            specs.append(
                GatewayPluginRuntimeExecutorSpec(
                    tool=tool,
                    executor=cast(GatewayPluginExecutor, executor),
                    optional=optional,
                    plugin_id=plugin_id,
                    plugin_name=_optional_string(
                        entry.get("pluginName", entry.get("plugin_name"))
                    ),
                    description=_optional_string(entry.get("description")),
                    source=str(entry.get("source") or "plugin").strip() or "plugin",
                )
            )
    return tuple(specs)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _active_registry_tool_names(entry: Mapping[str, object]) -> tuple[str, ...]:
    raw_names = entry.get("names")
    names = [str(name).strip() for name in raw_names] if isinstance(raw_names, list) else []
    single_name = _optional_string(entry.get("name", entry.get("tool")))
    if single_name is not None:
        names.append(single_name)
    return tuple(name for name in names if name)


def _normalize_tool_name(value: object) -> str:
    return str(value or "").strip().lower()


def _optional_tool_allowed(
    *,
    tool_key: str,
    plugin_key: str,
    allowlist: set[str],
) -> bool:
    if not allowlist:
        return False
    return tool_key in allowlist or plugin_key in allowlist or "group:plugins" in allowlist


def _optional_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _plugin_requester_is_owner(requester: object) -> bool:
    caller_scopes = getattr(requester, "caller_scopes", None)
    if caller_scopes is None:
        return True
    return ADMIN_GATEWAY_METHOD_SCOPE in caller_scopes


def _session_extension_state(
    plugin_extensions: Mapping[str, object],
    *,
    plugin_id: str,
    namespace: str,
) -> object:
    plugin_state = plugin_extensions.get(plugin_id)
    if not isinstance(plugin_state, Mapping):
        return _MISSING
    if namespace not in plugin_state:
        return _MISSING
    return plugin_state[namespace]


def copy_plugin_json_value(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def is_plugin_json_value(value: object) -> bool:
    if not _is_plugin_json_value_within_limits(
        value,
        depth=0,
        state={"nodes": 0},
    ):
        return False
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        return False
    return len(encoded) <= _PLUGIN_JSON_VALUE_MAX_SERIALIZED_BYTES


def _is_plugin_json_value_within_limits(
    value: object,
    *,
    depth: int,
    state: dict[str, int],
) -> bool:
    state["nodes"] = state.get("nodes", 0) + 1
    if state["nodes"] > _PLUGIN_JSON_VALUE_MAX_NODES or depth > _PLUGIN_JSON_VALUE_MAX_DEPTH:
        return False
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, str):
        return len(value) <= _PLUGIN_JSON_VALUE_MAX_STRING_LENGTH
    if isinstance(value, int) and not isinstance(value, bool):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(
            _is_plugin_json_value_within_limits(entry, depth=depth + 1, state=state)
            for entry in value
        )
    if not isinstance(value, Mapping):
        return False
    if len(value) > _PLUGIN_JSON_VALUE_MAX_OBJECT_KEYS:
        return False
    for key, entry in value.items():
        if not isinstance(key, str) or len(key) > _PLUGIN_JSON_VALUE_MAX_STRING_LENGTH:
            return False
        if not _is_plugin_json_value_within_limits(entry, depth=depth + 1, state=state):
            return False
    return True
