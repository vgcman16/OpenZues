from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from openzues.database import Database, utcnow
from openzues.schemas import InstanceView, TransportType
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.codex_rpc import CodexAppServerClient, extract_turn_id
from openzues.services.hub import BroadcastHub

logger = logging.getLogger(__name__)
RuntimeListener = Callable[[int, dict[str, Any]], Awaitable[None]]

CATALOG_SAMPLE_LIMIT = 8
LOG_LINE_PREVIEW_LIMIT = 360
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
LOG_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+")


def _pick_fields(item: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: value for key in keys if (value := item.get(key)) not in (None, "", [], {})}


def _ordered_names(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        name = str(item).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _catalog_names(value: Any) -> list[str]:
    if isinstance(value, dict):
        return _ordered_names([str(key) for key in value])
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
                continue
            if not isinstance(item, dict):
                continue
            for key in ("name", "id", "uri", "method", "title"):
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    names.append(raw)
                    break
        return _ordered_names(names)
    return []


def _summarize_mcp_server_status(item: dict[str, Any]) -> dict[str, Any]:
    summary = _pick_fields(item, ("name", "status", "source", "authStatus"))
    for key in ("tools", "resources", "resourceTemplates"):
        names = _catalog_names(item.get(key))
        if names:
            summary[key] = names
    return summary


def _summarize_account(account: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(account, dict):
        return None
    return _pick_fields(account, ("type", "email", "planType"))


def _summarize_models(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _pick_fields(
            item,
            (
                "id",
                "model",
                "displayName",
                "description",
                "defaultReasoningEffort",
                "isDefault",
            ),
        )
        for item in items
    ]


def _summarize_threads(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized: list[dict[str, Any]] = []
    for item in items:
        summary = _pick_fields(item, ("id", "title", "name", "updatedAt"))
        status = item.get("status")
        if isinstance(status, dict):
            summary["status"] = _pick_fields(status, ("type", "turnId", "activeTurnId"))
        summarized.append(summary)
    return summarized


def _summarize_named_items(
    items: list[dict[str, Any]],
    *,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [summary for item in items if (summary := _pick_fields(item, keys))]


def _sanitize_log_line(line: str) -> str:
    cleaned = ANSI_ESCAPE_RE.sub("", line).strip()
    return LOG_TIMESTAMP_RE.sub("", cleaned)


def compact_event_payload(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    compact = dict(payload)

    if method in {"server/stderr", "server/stdout"}:
        line = payload.get("line")
        if isinstance(line, str):
            clean_line = _sanitize_log_line(line)
            compact["line"] = clean_line
            if len(clean_line) > LOG_LINE_PREVIEW_LIMIT:
                compact["line"] = f"{clean_line[:LOG_LINE_PREVIEW_LIMIT]} ... [truncated]"
                compact["lineLength"] = len(clean_line)
        return compact

    if method == "account/updated":
        compact["account"] = _summarize_account(payload.get("account"))
        return compact

    data = payload.get("data")
    if isinstance(data, list) and (
        method.endswith("/updated") or method.endswith("/list") or len(data) > 12
    ):
        sample = data[:CATALOG_SAMPLE_LIMIT]
        if method.startswith("model/"):
            compact["data"] = _summarize_models([item for item in sample if isinstance(item, dict)])
        elif method.startswith("thread/"):
            compact["data"] = _summarize_threads(
                [item for item in sample if isinstance(item, dict)]
            )
        else:
            compact["data"] = _summarize_named_items(
                [item for item in sample if isinstance(item, dict)],
                keys=(
                    "id",
                    "name",
                    "displayName",
                    "description",
                    "status",
                    "type",
                    "method",
                    "isAccessible",
                    "isEnabled",
                ),
            )
        compact["count"] = len(data)
        compact["truncated"] = len(data) > CATALOG_SAMPLE_LIMIT
        return compact

    thread_ids = payload.get("threadIds")
    if isinstance(thread_ids, list) and len(thread_ids) > 12:
        compact["threadIds"] = [str(item) for item in thread_ids[:CATALOG_SAMPLE_LIMIT]]
        compact["count"] = len(thread_ids)
        compact["truncated"] = len(thread_ids) > CATALOG_SAMPLE_LIMIT

    return compact


@dataclass(slots=True)
class InstanceRuntime:
    instance_id: int
    name: str
    transport: str
    command: str | None
    args: str | None
    websocket_url: str | None
    cwd: str | None
    auto_connect: bool
    client: CodexAppServerClient | None = None
    connected: bool = False
    initialized: bool = False
    resolved_transport: str | None = None
    resolved_command: str | None = None
    resolved_args: str | None = None
    transport_note: str | None = None
    pid: int | None = None
    error: str | None = None
    client_user_agent: str | None = None
    auth_state: dict[str, Any] | None = None
    models: list[dict[str, Any]] = field(default_factory=list)
    collaboration_modes: list[dict[str, Any]] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    apps: list[dict[str, Any]] = field(default_factory=list)
    plugins: list[dict[str, Any]] = field(default_factory=list)
    mcp_servers: list[dict[str, Any]] = field(default_factory=list)
    mcp_server_status: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] | None = None
    threads: list[dict[str, Any]] = field(default_factory=list)
    loaded_thread_ids: list[str] = field(default_factory=list)
    unresolved_requests: list[dict[str, Any]] = field(default_factory=list)
    last_event_at: str | None = None

    def view(self) -> InstanceView:
        return InstanceView(
            id=self.instance_id,
            name=self.name,
            transport=cast(TransportType, self.transport),
            command=self.command,
            args=self.args,
            websocket_url=self.websocket_url,
            cwd=self.cwd,
            auto_connect=self.auto_connect,
            connected=self.connected,
            resolved_transport=cast(Literal["stdio", "websocket"] | None, self.resolved_transport),
            resolved_command=self.resolved_command,
            resolved_args=self.resolved_args,
            transport_note=self.transport_note,
            initialized=self.initialized,
            pid=self.pid,
            error=self.error,
            client_user_agent=self.client_user_agent,
            auth_state=self.auth_state,
            models=self.models,
            collaboration_modes=self.collaboration_modes,
            skills=self.skills,
            apps=self.apps,
            plugins=self.plugins,
            mcp_servers=self.mcp_servers,
            config=self.config,
            threads=self.threads,
            loaded_thread_ids=self.loaded_thread_ids,
            unresolved_requests=self.unresolved_requests,
            last_event_at=self.last_event_at,
        )


class RuntimeManager:
    def __init__(
        self,
        database: Database,
        hub: BroadcastHub,
        desktop_service: CodexDesktopService | None = None,
        *,
        default_stdio_command: str = "codex",
        default_stdio_args: str = "app-server",
    ) -> None:
        self.database = database
        self.hub = hub
        self.desktop_service = desktop_service
        self.default_stdio_command = default_stdio_command
        self.default_stdio_args = default_stdio_args
        self.instances: dict[int, InstanceRuntime] = {}
        self.event_listeners: list[RuntimeListener] = []
        self.server_request_listeners: list[RuntimeListener] = []

    def add_event_listener(self, listener: RuntimeListener) -> None:
        self.event_listeners.append(listener)

    def add_server_request_listener(self, listener: RuntimeListener) -> None:
        self.server_request_listeners.append(listener)

    async def load(self, *, auto_connect: bool = True) -> None:
        rows = await self.database.list_instances()
        for row in rows:
            runtime = InstanceRuntime(
                instance_id=int(row["id"]),
                name=row["name"],
                transport=row["transport"],
                command=row["command"],
                args=row["args"],
                websocket_url=row["websocket_url"],
                cwd=row["cwd"],
                auto_connect=bool(row["auto_connect"]),
            )
            self._apply_static_resolution(runtime)
            runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
                runtime.instance_id
            )
            self.instances[runtime.instance_id] = runtime
        for runtime in self.instances.values():
            if runtime.auto_connect and auto_connect:
                asyncio.create_task(self.connect_instance(runtime.instance_id))

    async def create_instance(
        self,
        *,
        name: str,
        transport: str,
        command: str | None,
        args: str | None,
        websocket_url: str | None,
        cwd: str | None,
        auto_connect: bool,
    ) -> InstanceRuntime:
        instance_id = await self.database.create_instance(
            name=name,
            transport=transport,
            command=command,
            args=args,
            websocket_url=websocket_url,
            cwd=cwd,
            auto_connect=auto_connect,
        )
        runtime = InstanceRuntime(
            instance_id=instance_id,
            name=name,
            transport=transport,
            command=command,
            args=args,
            websocket_url=websocket_url,
            cwd=cwd,
            auto_connect=auto_connect,
        )
        self._apply_static_resolution(runtime)
        self.instances[instance_id] = runtime
        await self.publish_snapshot("instance/created", {"instanceId": instance_id})
        if auto_connect:
            await self.connect_instance(instance_id)
        return runtime

    async def list_views(self) -> list[InstanceView]:
        return [runtime.view() for runtime in self.instances.values()]

    async def get(self, instance_id: int) -> InstanceRuntime:
        runtime = self.instances.get(instance_id)
        if runtime is None:
            raise KeyError(f"Unknown instance {instance_id}")
        return runtime

    async def list_mcp_server_status(
        self,
        instance_id: int,
        *,
        limit: int = 50,
        refresh: bool = True,
    ) -> list[dict[str, Any]]:
        runtime = await self.get(instance_id)
        client = runtime.client
        if client is None or not runtime.connected:
            return [dict(item) for item in runtime.mcp_server_status]
        if runtime.mcp_server_status and not refresh:
            return [dict(item) for item in runtime.mcp_server_status]
        raw_status = (await client.call("mcpServerStatus/list", {"limit": limit})).get("data", [])
        runtime.mcp_server_status = [
            _summarize_mcp_server_status(item) for item in raw_status if isinstance(item, dict)
        ]
        return [dict(item) for item in runtime.mcp_server_status]

    async def connect_instance(self, instance_id: int) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        try:
            (
                resolved_transport,
                resolved_command,
                resolved_args,
                resolved_websocket_url,
                transport_note,
            ) = self._resolve_connection(runtime)
        except Exception as exc:
            runtime.connected = False
            runtime.initialized = False
            runtime.error = str(exc)
            await self.publish_snapshot(
                "instance/error",
                {"instanceId": instance_id, "error": str(exc)},
            )
            return runtime
        runtime.resolved_transport = resolved_transport
        runtime.resolved_command = resolved_command
        runtime.resolved_args = resolved_args
        runtime.transport_note = transport_note
        if runtime.client is None:
            runtime.client = CodexAppServerClient(
                transport=resolved_transport,
                command=resolved_command,
                args=resolved_args,
                websocket_url=resolved_websocket_url,
                cwd=runtime.cwd,
                event_callback=lambda event: self.handle_event(runtime.instance_id, event),
                server_request_callback=lambda request: self.handle_server_request(
                    runtime.instance_id,
                    request,
                ),
            )
        else:
            runtime.client.transport = resolved_transport
            runtime.client.command = resolved_command
            runtime.client.args = resolved_args
            runtime.client.websocket_url = resolved_websocket_url
        try:
            await runtime.client.connect()
            runtime.connected = runtime.client.info.connected
            runtime.initialized = runtime.client.info.initialized
            runtime.pid = runtime.client.info.pid
            runtime.client_user_agent = runtime.client.info.client_user_agent
            runtime.error = runtime.client.info.error
            await self.refresh_instance(instance_id)
            await self.publish_snapshot("instance/connected", {"instanceId": instance_id})
        except Exception as exc:
            runtime.connected = False
            runtime.error = str(exc)
            await self.publish_snapshot(
                "instance/error",
                {"instanceId": instance_id, "error": str(exc)},
            )
        return runtime

    async def disconnect_instance(self, instance_id: int) -> None:
        runtime = await self.get(instance_id)
        if runtime.client is not None:
            await runtime.client.close()
            runtime.client = None
        runtime.connected = False
        runtime.initialized = False
        runtime.pid = None
        await self.publish_snapshot("instance/disconnected", {"instanceId": instance_id})

    async def delete_instance(self, instance_id: int) -> None:
        runtime = await self.get(instance_id)
        if runtime.client is not None:
            await runtime.client.close()
        self.instances.pop(instance_id, None)
        await self.database.delete_instance(instance_id)
        await self.publish_snapshot("instance/deleted", {"instanceId": instance_id})

    async def close(self) -> None:
        for runtime in self.instances.values():
            if runtime.client is not None:
                await runtime.client.close()
                runtime.client = None
            runtime.connected = False
            runtime.initialized = False
            runtime.pid = None

    async def quick_connect_desktop(
        self,
        *,
        name: str = "Local Codex Desktop",
        cwd: str | None = None,
    ) -> InstanceRuntime:
        runtime = next(
            (instance for instance in self.instances.values() if instance.transport == "desktop"),
            None,
        )
        if runtime is None:
            runtime = await self.create_instance(
                name=name,
                transport="desktop",
                command=None,
                args=None,
                websocket_url=None,
                cwd=cwd,
                auto_connect=False,
            )
        elif cwd and not runtime.cwd:
            runtime.cwd = cwd
        return await self.connect_instance(runtime.instance_id)

    async def ensure_workspace_shell_instance(
        self,
        *,
        cwd: str,
        auto_connect: bool = True,
    ) -> InstanceRuntime:
        normalized_cwd = str(cwd).strip()
        if not normalized_cwd:
            raise ValueError("Workspace shell executor needs a concrete cwd.")

        matching = next(
            (
                instance
                for instance in self.instances.values()
                if instance.transport == "stdio"
                and str(instance.cwd or "").strip().lower() == normalized_cwd.lower()
            ),
            None,
        )
        if matching is None:
            matching = await self.create_instance(
                name=f"Workspace Shell: {normalized_cwd}",
                transport="stdio",
                command=self.default_stdio_command,
                args=self.default_stdio_args,
                websocket_url=None,
                cwd=normalized_cwd,
                auto_connect=False,
            )
        elif not matching.cwd:
            matching.cwd = normalized_cwd

        if auto_connect and not matching.connected:
            matching = await self.connect_instance(matching.instance_id)
        return matching

    async def refresh_instance(self, instance_id: int) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        client = runtime.client
        if client is None or not runtime.connected:
            return runtime
        account = (await client.call("account/read", {"refreshToken": False})).get("account")
        runtime.auth_state = _summarize_account(account)
        raw_models = (await client.call("model/list", {"limit": 50, "includeHidden": False})).get(
            "data", []
        )
        runtime.models = _summarize_models([item for item in raw_models if isinstance(item, dict)])
        raw_modes = (await client.call("collaborationMode/list", {})).get("data", [])
        runtime.collaboration_modes = _summarize_named_items(
            [item for item in raw_modes if isinstance(item, dict)],
            keys=("name", "mode", "model", "reasoning_effort"),
        )
        skills_params: dict[str, Any] = {"forceReload": False}
        if runtime.cwd:
            skills_params["cwds"] = [runtime.cwd]
        raw_skills = (await client.call("skills/list", skills_params)).get("data", [])
        runtime.skills = _summarize_named_items(
            [item for item in raw_skills if isinstance(item, dict)],
            keys=("name", "description"),
        )
        raw_apps = (await client.call("app/list", {"limit": 50})).get("data", [])
        runtime.apps = _summarize_named_items(
            [item for item in raw_apps if isinstance(item, dict)],
            keys=("id", "name", "description", "isAccessible", "isEnabled"),
        )
        raw_plugins = (await client.call("plugin/list", {})).get("data", [])
        runtime.plugins = _summarize_named_items(
            [item for item in raw_plugins if isinstance(item, dict)],
            keys=("name", "enabled"),
        )
        raw_mcp_servers = await self.list_mcp_server_status(instance_id, limit=50, refresh=True)
        runtime.mcp_servers = _summarize_named_items(
            [item for item in raw_mcp_servers if isinstance(item, dict)],
            keys=("name", "status", "source", "authStatus"),
        )
        raw_config = (await client.call("config/read", {"includeLayers": False})).get("config")
        runtime.config = (
            _pick_fields(
                raw_config,
                (
                    "model",
                    "model_reasoning_effort",
                    "profile",
                    "sandbox",
                    "approvalPolicy",
                    "approval_policy",
                ),
            )
            if isinstance(raw_config, dict)
            else None
        )
        raw_threads = (await client.call("thread/list", {"limit": 30})).get("data", [])
        runtime.threads = _summarize_threads(
            [item for item in raw_threads if isinstance(item, dict)]
        )
        runtime.loaded_thread_ids = (await client.call("thread/loaded/list", {})).get(
            "threadIds", []
        )
        runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
            instance_id
        )
        runtime.last_event_at = utcnow()
        await self.publish_snapshot("instance/refreshed", {"instanceId": instance_id})
        return runtime

    async def _refresh_instance_safely(self, instance_id: int) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        try:
            return await self.refresh_instance(instance_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Instance refresh failed for %s", instance_id, exc_info=True)
            return runtime

    def _schedule_refresh_instance(self, instance_id: int) -> None:
        asyncio.create_task(self._refresh_instance_safely(instance_id))

    async def _wait_for_thread_visibility(
        self,
        runtime: InstanceRuntime,
        thread_id: str,
        *,
        timeout_seconds: float = 12.0,
    ) -> bool:
        client = runtime.client
        if client is None:
            return False

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            try:
                raw_threads = (await client.call("thread/list", {"limit": 30})).get("data", [])
            except Exception:
                logger.debug(
                    "Thread visibility poll failed for %s on instance %s",
                    thread_id,
                    runtime.instance_id,
                    exc_info=True,
                )
                await asyncio.sleep(0.4)
                continue

            runtime.threads = _summarize_threads(
                [item for item in raw_threads if isinstance(item, dict)]
            )
            if any(thread.get("id") == thread_id for thread in runtime.threads):
                return True
            await asyncio.sleep(0.4)
        return False

    async def _refresh_runtime_threads(self, runtime: InstanceRuntime) -> None:
        client = runtime.client
        if client is None:
            return
        try:
            raw_threads = (await client.call("thread/list", {"limit": 30})).get("data", [])
        except Exception:
            logger.debug(
                "Live thread refresh failed for instance %s",
                runtime.instance_id,
                exc_info=True,
            )
            return
        runtime.threads = _summarize_threads(
            [item for item in raw_threads if isinstance(item, dict)]
        )

    async def start_thread(
        self,
        instance_id: int,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        result = await runtime.client.start_thread(
            model=model,
            cwd=cwd,
            reasoning_effort=reasoning_effort,
            collaboration_mode=collaboration_mode,
        )
        thread_id = None
        thread = result.get("thread") if isinstance(result, dict) else None
        if isinstance(thread, dict) and isinstance(thread.get("id"), str):
            thread_id = thread["id"]
        elif isinstance(result, dict) and isinstance(result.get("threadId"), str):
            thread_id = result["threadId"]
        if thread_id is not None:
            runtime.threads = [{"id": thread_id, "status": {"type": "idle"}}]
            await self._wait_for_thread_visibility(runtime, thread_id)
        self._schedule_refresh_instance(instance_id)
        return result

    async def start_turn(
        self,
        instance_id: int,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        attempts = 3
        last_error: Exception | None = None
        result: dict[str, Any] | None = None
        for attempt in range(attempts):
            try:
                result = await runtime.client.start_turn(
                    thread_id=thread_id,
                    text=text,
                    cwd=cwd,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    collaboration_mode=collaboration_mode,
                )
                break
            except Exception as exc:
                last_error = exc
                if "thread not found" not in str(exc).lower() or attempt == attempts - 1:
                    raise
                await self._wait_for_thread_visibility(runtime, thread_id)
                await asyncio.sleep(0.5 * (attempt + 1))
        if result is None:
            assert last_error is not None
            raise last_error
        self._schedule_refresh_instance(instance_id)
        return result

    async def interrupt_turn(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        await self._refresh_runtime_threads(runtime)
        turn_id = self._turn_id_from_runtime(runtime, thread_id)
        thread_status = self._thread_status_from_runtime(runtime, thread_id)
        if thread_status == "idle" and turn_id is None:
            return {"ok": False, "reason": "no_active_turn", "threadId": thread_id}
        if turn_id is None:
            turn_id = await self._turn_id_from_events(instance_id, thread_id)
        if turn_id is None:
            return {"ok": False, "reason": "no_active_turn", "threadId": thread_id}
        try:
            result = await runtime.client.interrupt_turn(thread_id=thread_id, turn_id=turn_id)
        except TimeoutError:
            await self._refresh_runtime_threads(runtime)
            refreshed_turn_id = self._turn_id_from_runtime(runtime, thread_id)
            refreshed_status = self._thread_status_from_runtime(runtime, thread_id)
            if refreshed_status == "idle" or refreshed_turn_id is None:
                return {"ok": False, "reason": "no_active_turn", "threadId": thread_id}
            logger.warning(
                "Interrupt timed out for thread %s on instance %s",
                thread_id,
                instance_id,
                exc_info=True,
            )
            return {
                "ok": False,
                "reason": "interrupt_timeout",
                "threadId": thread_id,
                "turnId": turn_id,
            }
        except RuntimeError as exc:
            if "thread not found" in str(exc).lower():
                return {"ok": False, "reason": "no_active_turn", "threadId": thread_id}
            raise
        self._schedule_refresh_instance(instance_id)
        return result

    async def start_review(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        result = await runtime.client.start_review(thread_id=thread_id)
        self._schedule_refresh_instance(instance_id)
        return result

    async def exec_command(
        self,
        instance_id: int,
        *,
        command: list[str],
        cwd: str | None,
        timeout_ms: int | None,
        tty: bool,
    ) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        return await runtime.client.exec_command(
            command=command,
            cwd=cwd,
            timeout_ms=timeout_ms,
            tty=tty,
        )

    async def resolve_request(self, instance_id: int, request_id: str, result: Any) -> None:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        await runtime.client.respond(request_id, result)
        await self.database.resolve_server_request(
            instance_id=instance_id,
            request_id=request_id,
            status="resolved",
        )
        runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
            instance_id
        )
        await self.publish_snapshot(
            "serverRequest/resolved",
            {"instanceId": instance_id, "requestId": request_id},
        )

    async def handle_server_request(self, instance_id: int, request: dict[str, Any]) -> None:
        await self.database.upsert_server_request(
            instance_id=instance_id,
            request_id=request["requestId"],
            thread_id=request.get("threadId"),
            method=request["method"],
            payload=request["params"],
            status="pending",
        )
        runtime = await self.get(instance_id)
        runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
            instance_id
        )
        await self.publish_snapshot(
            "serverRequest/created",
            {
                "instanceId": instance_id,
                "requestId": request["requestId"],
                "method": request["method"],
            },
        )
        for listener in self.server_request_listeners:
            try:
                await listener(instance_id, request)
            except Exception:
                logger.exception("Runtime server request listener crashed")

    async def handle_event(self, instance_id: int, event: dict[str, Any]) -> None:
        compact_payload = compact_event_payload(event["method"], event["params"])
        await self.database.append_event(
            instance_id=instance_id,
            thread_id=event.get("threadId"),
            method=event["method"],
            payload=compact_payload,
        )
        runtime = await self.get(instance_id)
        runtime.last_event_at = utcnow()
        if runtime.client is not None:
            runtime.connected = runtime.client.info.connected
            runtime.initialized = runtime.client.info.initialized
            runtime.pid = runtime.client.info.pid
            runtime.error = runtime.client.info.error
        await self.hub.publish(
            {
                "type": "codex_event",
                "instanceId": instance_id,
                "method": event["method"],
                "threadId": event.get("threadId"),
                "params": compact_payload,
                "createdAt": runtime.last_event_at,
            }
        )
        if event["method"] in {
            "thread/started",
            "thread/archived",
            "thread/unarchived",
            "thread/name/updated",
            "thread/status/changed",
            "turn/completed",
            "account/updated",
            "mcpServer/oauthLogin/completed",
        }:
            self._schedule_refresh_instance(instance_id)
        for listener in self.event_listeners:
            try:
                await listener(instance_id, event)
            except Exception:
                logger.exception("Runtime event listener crashed")

    async def publish_snapshot(self, event_type: str, payload: dict[str, Any]) -> None:
        await self.hub.publish({"type": event_type, **payload, "createdAt": utcnow()})

    def _apply_static_resolution(self, runtime: InstanceRuntime) -> None:
        if runtime.transport == "stdio":
            runtime.resolved_transport = "stdio"
            runtime.resolved_command = runtime.command
            runtime.resolved_args = runtime.args
            runtime.transport_note = None
        elif runtime.transport == "websocket":
            runtime.resolved_transport = "websocket"
            runtime.resolved_command = None
            runtime.resolved_args = None
            runtime.transport_note = runtime.websocket_url

    def _resolve_connection(
        self,
        runtime: InstanceRuntime,
    ) -> tuple[str, str | None, str | None, str | None, str | None]:
        if runtime.transport == "desktop":
            if self.desktop_service is None:
                raise RuntimeError("Desktop transport is not configured.")
            launch = self.desktop_service.resolve_launch()
            note = launch.note if launch.version is None else f"{launch.note} ({launch.version})"
            return ("stdio", launch.command, launch.args, None, note)
        return (
            runtime.transport,
            runtime.command,
            runtime.args,
            runtime.websocket_url,
            runtime.transport_note,
        )

    def _turn_id_from_runtime(self, runtime: InstanceRuntime, thread_id: str) -> str | None:
        for thread in runtime.threads:
            if thread.get("id") != thread_id:
                continue
            status = thread.get("status")
            if not isinstance(status, dict):
                continue
            for key in ("turnId", "activeTurnId"):
                value = status.get(key)
                if isinstance(value, str):
                    return value
        return None

    def _thread_status_from_runtime(self, runtime: InstanceRuntime, thread_id: str) -> str | None:
        for thread in runtime.threads:
            if thread.get("id") != thread_id:
                continue
            status = thread.get("status")
            if isinstance(status, dict) and isinstance(status.get("type"), str):
                return status["type"]
        return None

    async def _turn_id_from_events(self, instance_id: int, thread_id: str) -> str | None:
        active_turn_id: str | None = None
        for event in await self.database.list_events(500):
            if int(event.get("instance_id") or 0) != instance_id:
                continue
            if event.get("thread_id") != thread_id:
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            turn_id = extract_turn_id(payload)
            if event.get("method") == "turn/started" and turn_id:
                active_turn_id = turn_id
            elif event.get("method") == "turn/completed" and turn_id == active_turn_id:
                active_turn_id = None
        return active_turn_id
