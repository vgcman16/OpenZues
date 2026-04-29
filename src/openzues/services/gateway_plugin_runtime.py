from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from openzues.services.gateway_method_policy import ADMIN_GATEWAY_METHOD_SCOPE

type GatewayPluginExecutor = Callable[[str, dict[str, Any]], Awaitable[object]]


@dataclass(frozen=True, slots=True)
class GatewayPluginRuntimeExecutorResolution:
    tool: str
    executor: GatewayPluginExecutor


class GatewayPluginRuntimeService:
    def __init__(
        self,
        *,
        executors: Mapping[str, GatewayPluginExecutor]
        | Iterable[tuple[str, GatewayPluginExecutor]]
        | None = None,
        owner_only: Iterable[str] = (),
    ) -> None:
        self._executors: dict[str, GatewayPluginExecutor] = {}
        if executors is not None:
            items = executors.items() if isinstance(executors, Mapping) else executors
            for tool, executor in items:
                normalized_tool = str(tool or "").strip()
                if not normalized_tool:
                    continue
                self._executors[normalized_tool] = executor
        self._owner_only = {
            str(tool or "").strip()
            for tool in owner_only
            if str(tool or "").strip()
        }

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
        executor = self._executors.get(normalized_tool)
        if executor is None:
            return None
        if normalized_tool in self._owner_only and not _plugin_requester_is_owner(requester):
            return None
        return GatewayPluginRuntimeExecutorResolution(
            tool=normalized_tool,
            executor=executor,
        )


def _plugin_requester_is_owner(requester: object) -> bool:
    caller_scopes = getattr(requester, "caller_scopes", None)
    if caller_scopes is None:
        return True
    return ADMIN_GATEWAY_METHOD_SCOPE in caller_scopes
