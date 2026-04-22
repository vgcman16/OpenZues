from __future__ import annotations

import asyncio
import logging
import re
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
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
EVENT_TEXT_PREVIEW_LIMIT = 360
COMMAND_TEXT_PREVIEW_LIMIT = 240
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
LOG_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+")
START_TURN_TIMEOUT_CONFIRM_SECONDS = 12.0
REFRESH_TIMEOUT_BACKOFF_SECONDS = 30.0
REFRESH_SCHEDULE_DEBOUNCE_SECONDS = 2.0
FULL_REFRESH_METHODS = (
    "account/read",
    "model/list",
    "collaborationMode/list",
    "skills/list",
    "app/list",
    "plugin/list",
    "mcpServerStatus/list",
    "config/read",
    "thread/list",
    "thread/loaded/list",
)
THREAD_REFRESH_METHODS = ("thread/list", "thread/loaded/list")
MCP_RUNTIME_REFRESH_METHODS = (
    "skills/list",
    "app/list",
    "plugin/list",
    "mcpServerStatus/list",
    "config/read",
)
EVENT_REFRESH_METHODS: dict[str, tuple[str, ...]] = {
    "account/updated": ("account/read",),
    "mcpServer/oauthLogin/completed": MCP_RUNTIME_REFRESH_METHODS,
}


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


def _catalog_item_name(item: object) -> str | None:
    if isinstance(item, str):
        name = item.strip()
        return name or None
    if not isinstance(item, dict):
        return None
    for key in ("name", "id", "uri", "method", "title", "serviceId"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    nested_service = item.get("service")
    if isinstance(nested_service, dict):
        for key in ("name", "id", "uri", "title"):
            raw = nested_service.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return None


def _catalog_names(value: Any) -> list[str]:
    if isinstance(value, dict):
        return _ordered_names([str(key) for key in value])
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            if name := _catalog_item_name(item):
                names.append(name)
        return _ordered_names(names)
    return []


def _should_stage_windows_codex_command(command: str | None, default_command: str | None) -> bool:
    raw = str(command or "").strip().strip('"')
    if not raw:
        return False
    normalized = raw.replace("/", "\\").lower()
    name = Path(raw).name.lower()
    if name not in {"codex", "codex.exe"}:
        return False
    default_value = str(default_command or "").strip().strip('"')
    normalized_default = default_value.replace("/", "\\").lower()
    return (
        normalized in {"codex", "codex.exe"}
        or (normalized_default and normalized == normalized_default)
        or "\\windowsapps\\" in normalized
    )


def _summarize_mcp_server_status(item: dict[str, Any]) -> dict[str, Any]:
    summary = _pick_fields(item, ("name", "status", "source", "authStatus"))
    for key in ("tools", "resources", "resourceTemplates", "services"):
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


def _upsert_thread_summary(
    existing_threads: list[dict[str, Any]],
    thread_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    thread_id = thread_summary.get("id")
    if not isinstance(thread_id, str):
        return list(existing_threads)
    updated_threads: list[dict[str, Any]] = []
    replaced = False
    for existing in existing_threads:
        if existing.get("id") == thread_id:
            updated_threads.append(thread_summary)
            replaced = True
        else:
            updated_threads.append(existing)
    if not replaced:
        updated_threads.append(thread_summary)
    return updated_threads


def _merge_thread_summaries(
    preferred_threads: list[dict[str, Any]],
    fallback_threads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_threads = list(preferred_threads)
    seen_ids = {
        str(thread.get("id"))
        for thread in preferred_threads
        if isinstance(thread.get("id"), str)
    }
    for thread in fallback_threads:
        thread_id = thread.get("id")
        if not isinstance(thread_id, str) or thread_id in seen_ids:
            continue
        merged_threads.append(thread)
        seen_ids.add(thread_id)
    return merged_threads


def _patch_thread_summary(
    existing_threads: list[dict[str, Any]],
    thread_id: str,
    patch: dict[str, Any],
) -> list[dict[str, Any]]:
    existing = next(
        (
            thread
            for thread in existing_threads
            if isinstance(thread, dict) and thread.get("id") == thread_id
        ),
        None,
    )
    merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {"id": thread_id}
    for key, value in patch.items():
        if key == "status" and isinstance(value, dict):
            status = merged.get("status")
            merged_status = dict(status) if isinstance(status, dict) else {}
            merged_status.update(value)
            merged["status"] = merged_status
            continue
        merged[key] = value
    return _upsert_thread_summary(existing_threads, merged)


def _add_loaded_thread_id(loaded_thread_ids: list[str], thread_id: str) -> list[str]:
    ordered = [item for item in loaded_thread_ids if isinstance(item, str) and item != thread_id]
    ordered.append(thread_id)
    return ordered


def _seed_runtime_thread_status(
    runtime: InstanceRuntime,
    thread_id: str,
    *,
    status_type: str,
    turn_id: str | None = None,
) -> None:
    status_patch: dict[str, Any] = {"type": status_type}
    if turn_id:
        status_patch["turnId"] = turn_id
        status_patch["activeTurnId"] = turn_id
    runtime.threads = _patch_thread_summary(
        runtime.threads,
        thread_id,
        {"status": status_patch},
    )
    status = next(
        (
            thread.get("status")
            for thread in runtime.threads
            if isinstance(thread, dict) and thread.get("id") == thread_id
        ),
        None,
    )
    if isinstance(status, dict) and not turn_id:
        status.pop("turnId", None)
        status.pop("activeTurnId", None)
    runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)


def _summarize_named_items(
    items: list[dict[str, Any]],
    *,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [summary for item in items if (summary := _pick_fields(item, keys))]


def _sanitize_log_line(line: str) -> str:
    cleaned = ANSI_ESCAPE_RE.sub("", line).strip()
    return LOG_TIMESTAMP_RE.sub("", cleaned)


def _clip_event_text(text: str, *, limit: int) -> tuple[str, int | None]:
    if len(text) <= limit:
        return text, None
    return f"{text[:limit]}... [truncated]", len(text)


def _compact_command_actions(actions: Any) -> list[dict[str, Any]] | None:
    if not isinstance(actions, list):
        return None
    compacted: list[dict[str, Any]] = []
    for action in actions[:3]:
        if not isinstance(action, dict):
            continue
        summary = _pick_fields(action, ("type", "command", "label", "path"))
        command = summary.get("command")
        if isinstance(command, str):
            clipped, original_length = _clip_event_text(
                command,
                limit=COMMAND_TEXT_PREVIEW_LIMIT,
            )
            summary["command"] = clipped
            if original_length is not None:
                summary["commandLength"] = original_length
        if summary:
            compacted.append(summary)
    return compacted


def _compact_message_content(
    content: Any,
) -> tuple[list[dict[str, Any]], int, bool] | None:
    if not isinstance(content, list):
        return None
    compacted: list[dict[str, Any]] = []
    for entry in content[:2]:
        if not isinstance(entry, dict):
            continue
        summary = _pick_fields(entry, ("type", "mimeType", "source", "url"))
        text = entry.get("text")
        if isinstance(text, str):
            clipped, original_length = _clip_event_text(
                text,
                limit=EVENT_TEXT_PREVIEW_LIMIT,
            )
            summary["text"] = clipped
            if original_length is not None:
                summary["textLength"] = original_length
        if summary:
            compacted.append(summary)
    return compacted, len(content), len(content) > len(compacted)


def _compact_event_item(item: dict[str, Any]) -> dict[str, Any]:
    compact_item = dict(item)
    item_type = str(item.get("type") or "")
    if item_type == "commandExecution":
        command = item.get("command")
        if isinstance(command, str):
            clipped, original_length = _clip_event_text(
                command,
                limit=COMMAND_TEXT_PREVIEW_LIMIT,
            )
            compact_item["command"] = clipped
            if original_length is not None:
                compact_item["commandLength"] = original_length
        aggregated_output = item.get("aggregatedOutput")
        if isinstance(aggregated_output, str):
            clipped, original_length = _clip_event_text(
                aggregated_output,
                limit=EVENT_TEXT_PREVIEW_LIMIT,
            )
            compact_item["aggregatedOutput"] = clipped
            if original_length is not None:
                compact_item["aggregatedOutputLength"] = original_length
        compact_actions = _compact_command_actions(item.get("commandActions"))
        if compact_actions is not None:
            compact_item["commandActions"] = compact_actions
            compact_item["commandActionCount"] = len(item.get("commandActions") or [])
            compact_item["commandActionsTruncated"] = len(item.get("commandActions") or []) > len(
                compact_actions
            )
        return compact_item

    if item_type in {"agentMessage", "userMessage"}:
        text = item.get("text")
        if isinstance(text, str):
            clipped, original_length = _clip_event_text(
                text,
                limit=EVENT_TEXT_PREVIEW_LIMIT,
            )
            compact_item["text"] = clipped
            if original_length is not None:
                compact_item["textLength"] = original_length
        compact_content = _compact_message_content(item.get("content"))
        if compact_content is not None:
            entries, content_count, truncated = compact_content
            compact_item["content"] = entries
            compact_item["contentCount"] = content_count
            if truncated:
                compact_item["contentTruncated"] = True
        return compact_item

    return compact_item


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

    if method in {"item/started", "item/completed"}:
        item = payload.get("item")
        if isinstance(item, dict):
            compact["item"] = _compact_event_item(item)
        return compact

    if method.endswith("/delta") or method.endswith("outputDelta"):
        for field in ("delta", "text"):
            value = payload.get(field)
            if not isinstance(value, str):
                continue
            clipped, original_length = _clip_event_text(
                value,
                limit=EVENT_TEXT_PREVIEW_LIMIT,
            )
            compact[field] = clipped
            if original_length is not None:
                compact[f"{field}Length"] = original_length
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


def _ordered_refresh_methods(
    methods: set[str] | tuple[str, ...] | list[str] | None,
) -> tuple[str, ...]:
    requested = set(methods or FULL_REFRESH_METHODS)
    return tuple(method for method in FULL_REFRESH_METHODS if method in requested)


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
    refresh_backoff_until: dict[str, float] = field(default_factory=dict)
    refresh_method_locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    refresh_task: asyncio.Task[None] | None = None
    refresh_pending: bool = False
    refresh_pending_methods: set[str] = field(default_factory=set)

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
        method = "mcpServerStatus/list"
        if refresh and self._refresh_call_in_backoff(runtime, method):
            return [dict(item) for item in runtime.mcp_server_status]
        async with self._refresh_method_lock(runtime, method):
            if refresh and self._refresh_call_in_backoff(runtime, method):
                return [dict(item) for item in runtime.mcp_server_status]
            try:
                raw_status = (await client.call(method, {"limit": limit})).get("data", [])
            except TimeoutError:
                self._mark_refresh_backoff(runtime, method)
                logger.warning(
                    "Instance refresh kept cached data for %s on instance %s after timeout; "
                    "backing off for %.0fs",
                    method,
                    runtime.instance_id,
                    REFRESH_TIMEOUT_BACKOFF_SECONDS,
                )
                return [dict(item) for item in runtime.mcp_server_status]
            except Exception:
                logger.warning(
                    "Instance refresh kept cached data for %s on instance %s",
                    method,
                    runtime.instance_id,
                    exc_info=True,
                )
                return [dict(item) for item in runtime.mcp_server_status]
            self._clear_refresh_backoff(runtime, method)
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
        refresh_task = self._cancel_refresh_task(runtime)
        if refresh_task is not None:
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
        if runtime.client is not None:
            await runtime.client.close()
            runtime.client = None
        runtime.connected = False
        runtime.initialized = False
        runtime.pid = None
        await self.publish_snapshot("instance/disconnected", {"instanceId": instance_id})

    async def delete_instance(self, instance_id: int) -> None:
        runtime = await self.get(instance_id)
        refresh_task = self._cancel_refresh_task(runtime)
        if refresh_task is not None:
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
        if runtime.client is not None:
            await runtime.client.close()
        self.instances.pop(instance_id, None)
        await self.database.delete_instance(instance_id)
        await self.publish_snapshot("instance/deleted", {"instanceId": instance_id})

    async def close(self) -> None:
        refresh_tasks: list[asyncio.Task[None]] = []
        for runtime in self.instances.values():
            refresh_task = self._cancel_refresh_task(runtime)
            if refresh_task is not None:
                refresh_tasks.append(refresh_task)
        for refresh_task in refresh_tasks:
            try:
                await refresh_task
            except asyncio.CancelledError:
                pass
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
                auto_connect=auto_connect,
            )
        else:
            if not matching.cwd:
                matching.cwd = normalized_cwd
            if matching.auto_connect != auto_connect:
                matching.auto_connect = auto_connect
                await self.database.update_instance_auto_connect(
                    matching.instance_id,
                    auto_connect=auto_connect,
                )

        if auto_connect and not matching.connected:
            matching = await self.connect_instance(matching.instance_id)
        return matching

    async def refresh_instance(
        self,
        instance_id: int,
        methods: tuple[str, ...] | None = None,
    ) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        client = runtime.client
        if client is None or not runtime.connected:
            return runtime
        requested_methods = set(_ordered_refresh_methods(methods))

        if "account/read" in requested_methods:
            account_payload = await self._safe_refresh_call(
                runtime,
                "account/read",
                {"refreshToken": False},
            )
            if isinstance(account_payload, dict):
                runtime.auth_state = _summarize_account(account_payload.get("account"))

        if "model/list" in requested_methods:
            model_payload = await self._safe_refresh_call(
                runtime,
                "model/list",
                {"limit": 50, "includeHidden": False},
            )
            if isinstance(model_payload, dict):
                raw_models = model_payload.get("data", [])
                runtime.models = _summarize_models(
                    [item for item in raw_models if isinstance(item, dict)]
                )

        if "collaborationMode/list" in requested_methods:
            mode_payload = await self._safe_refresh_call(runtime, "collaborationMode/list", {})
            if isinstance(mode_payload, dict):
                raw_modes = mode_payload.get("data", [])
                runtime.collaboration_modes = _summarize_named_items(
                    [item for item in raw_modes if isinstance(item, dict)],
                    keys=("name", "mode", "model", "reasoning_effort"),
                )

        if "skills/list" in requested_methods:
            skills_params: dict[str, Any] = {"forceReload": False}
            if runtime.cwd:
                skills_params["cwds"] = [runtime.cwd]
            skills_payload = await self._safe_refresh_call(runtime, "skills/list", skills_params)
            if isinstance(skills_payload, dict):
                raw_skills = skills_payload.get("data", [])
                runtime.skills = _summarize_named_items(
                    [item for item in raw_skills if isinstance(item, dict)],
                    keys=("name", "description"),
                )

        if "app/list" in requested_methods:
            apps_payload = await self._safe_refresh_call(runtime, "app/list", {"limit": 50})
            if isinstance(apps_payload, dict):
                raw_apps = apps_payload.get("data", [])
                runtime.apps = _summarize_named_items(
                    [item for item in raw_apps if isinstance(item, dict)],
                    keys=("id", "name", "description", "isAccessible", "isEnabled"),
                )

        if "plugin/list" in requested_methods:
            plugins_payload = await self._safe_refresh_call(runtime, "plugin/list", {})
            if isinstance(plugins_payload, dict):
                raw_plugins = plugins_payload.get("data", [])
                runtime.plugins = _summarize_named_items(
                    [item for item in raw_plugins if isinstance(item, dict)],
                    keys=("name", "enabled"),
                )

        if "mcpServerStatus/list" in requested_methods:
            raw_mcp_servers = await self.list_mcp_server_status(instance_id, limit=50, refresh=True)
            runtime.mcp_servers = _summarize_named_items(
                [item for item in raw_mcp_servers if isinstance(item, dict)],
                keys=("name", "status", "source", "authStatus"),
            )

        if "config/read" in requested_methods:
            config_payload = await self._safe_refresh_call(
                runtime,
                "config/read",
                {"includeLayers": False},
            )
            if isinstance(config_payload, dict):
                raw_config = config_payload.get("config")
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

        if "thread/list" in requested_methods:
            thread_payload = await self._safe_refresh_call(runtime, "thread/list", {"limit": 30})
            if isinstance(thread_payload, dict):
                raw_threads = thread_payload.get("data", [])
                runtime.threads = _summarize_threads(
                    [item for item in raw_threads if isinstance(item, dict)]
                )

        if "thread/loaded/list" in requested_methods:
            loaded_threads_payload = await self._safe_refresh_call(
                runtime,
                "thread/loaded/list",
                {},
            )
            if isinstance(loaded_threads_payload, dict):
                runtime.loaded_thread_ids = loaded_threads_payload.get("threadIds", [])

        runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
            instance_id
        )
        runtime.last_event_at = utcnow()
        await self.publish_snapshot("instance/refreshed", {"instanceId": instance_id})
        return runtime

    async def _safe_refresh_call(
        self,
        runtime: InstanceRuntime,
        method: str,
        params: dict[str, Any],
    ) -> Any | None:
        client = runtime.client
        if client is None:
            return None
        if self._refresh_call_in_backoff(runtime, method):
            return None
        async with self._refresh_method_lock(runtime, method):
            if self._refresh_call_in_backoff(runtime, method):
                return None
            try:
                response = await client.call(method, params)
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                self._mark_refresh_backoff(runtime, method)
                logger.warning(
                    "Instance refresh kept cached data for %s on instance %s after timeout; "
                    "backing off for %.0fs",
                    method,
                    runtime.instance_id,
                    REFRESH_TIMEOUT_BACKOFF_SECONDS,
                )
                return None
            except Exception:
                logger.warning(
                    "Instance refresh kept cached data for %s on instance %s",
                    method,
                    runtime.instance_id,
                    exc_info=True,
                )
                return None
            self._clear_refresh_backoff(runtime, method)
            return response

    def _refresh_call_in_backoff(self, runtime: InstanceRuntime, method: str) -> bool:
        retry_at = runtime.refresh_backoff_until.get(method)
        if retry_at is None:
            return False
        return retry_at > asyncio.get_running_loop().time()

    def _mark_refresh_backoff(
        self,
        runtime: InstanceRuntime,
        method: str,
        *,
        seconds: float = REFRESH_TIMEOUT_BACKOFF_SECONDS,
    ) -> None:
        runtime.refresh_backoff_until[method] = asyncio.get_running_loop().time() + seconds

    def _clear_refresh_backoff(self, runtime: InstanceRuntime, method: str) -> None:
        runtime.refresh_backoff_until.pop(method, None)

    def _refresh_method_lock(self, runtime: InstanceRuntime, method: str) -> asyncio.Lock:
        lock = runtime.refresh_method_locks.get(method)
        if lock is None:
            lock = asyncio.Lock()
            runtime.refresh_method_locks[method] = lock
        return lock

    async def _refresh_instance_safely(
        self,
        instance_id: int,
        methods: tuple[str, ...] | None = None,
    ) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        try:
            return await self.refresh_instance(instance_id, methods=methods)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Instance refresh failed for %s", instance_id, exc_info=True)
            return runtime

    async def _drain_refresh_instance(self, instance_id: int) -> None:
        try:
            while True:
                runtime = await self.get(instance_id)
                runtime.refresh_pending = False
                scheduled_methods = self._consume_scheduled_refresh_methods(runtime)
                await self._refresh_instance_safely(instance_id, methods=scheduled_methods)
                runtime = await self.get(instance_id)
                if not runtime.refresh_pending:
                    break
                await asyncio.sleep(REFRESH_SCHEDULE_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            raise
        except KeyError:
            return
        finally:
            final_runtime = self.instances.get(instance_id)
            if final_runtime is not None:
                final_runtime.refresh_task = None
                final_runtime.refresh_pending = False

    def _schedule_refresh_instance(
        self,
        instance_id: int,
        methods: tuple[str, ...] | None = None,
    ) -> None:
        runtime = self.instances.get(instance_id)
        if runtime is None:
            return
        runtime.refresh_pending = True
        runtime.refresh_pending_methods.update(_ordered_refresh_methods(methods))
        if runtime.refresh_task is not None and not runtime.refresh_task.done():
            return
        runtime.refresh_task = asyncio.create_task(self._drain_refresh_instance(instance_id))

    def _consume_scheduled_refresh_methods(self, runtime: InstanceRuntime) -> tuple[str, ...]:
        methods = _ordered_refresh_methods(runtime.refresh_pending_methods)
        runtime.refresh_pending_methods.clear()
        return methods

    def _cancel_refresh_task(self, runtime: InstanceRuntime) -> asyncio.Task[None] | None:
        task = runtime.refresh_task
        if task is not None and not task.done():
            task.cancel()
            active_task: asyncio.Task[None] | None = task
        else:
            active_task = None
        runtime.refresh_task = None
        runtime.refresh_pending = False
        runtime.refresh_pending_methods.clear()
        return active_task

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
        prior_threads = list(runtime.threads)
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

            runtime.threads = _merge_thread_summaries(
                _summarize_threads([item for item in raw_threads if isinstance(item, dict)]),
                prior_threads,
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
        runtime.threads = _merge_thread_summaries(
            _summarize_threads([item for item in raw_threads if isinstance(item, dict)]),
            runtime.threads,
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
        known_thread_ids = {
            str(thread.get("id"))
            for thread in runtime.threads
            if isinstance(thread, dict) and isinstance(thread.get("id"), str)
        }
        attempts = 2
        last_error: Exception | None = None
        result: dict[str, Any] | None = None
        for attempt in range(attempts):
            if runtime.client is None:
                raise RuntimeError("Instance is not connected.")
            try:
                result = await runtime.client.start_thread(
                    model=model,
                    cwd=cwd,
                    reasoning_effort=reasoning_effort,
                    collaboration_mode=collaboration_mode,
                )
                break
            except TimeoutError as exc:
                last_error = exc
                await self._refresh_runtime_threads(runtime)
                recovered_thread = next(
                    (
                        str(thread.get("id"))
                        for thread in runtime.threads
                        if isinstance(thread, dict)
                        and isinstance(thread.get("id"), str)
                        and str(thread.get("id")) not in known_thread_ids
                    ),
                    None,
                )
                if recovered_thread is not None:
                    _seed_runtime_thread_status(
                        runtime,
                        recovered_thread,
                        status_type="idle",
                    )
                    return {
                        "thread": {"id": recovered_thread},
                        "threadId": recovered_thread,
                        "recoveredFrom": "timeout",
                    }
                if attempt == attempts - 1:
                    raise
                logger.warning(
                    "Thread launch timed out for instance %s; reconnecting and retrying once.",
                    instance_id,
                )
                await self.disconnect_instance(instance_id)
                runtime = await self.connect_instance(instance_id)
        if result is None:
            assert last_error is not None
            raise last_error
        thread_id = None
        thread = result.get("thread") if isinstance(result, dict) else None
        if isinstance(thread, dict) and isinstance(thread.get("id"), str):
            thread_id = thread["id"]
        elif isinstance(result, dict) and isinstance(result.get("threadId"), str):
            thread_id = result["threadId"]
        if thread_id is not None:
            runtime.threads = _upsert_thread_summary(
                runtime.threads,
                {"id": thread_id, "status": {"type": "idle"}},
            )
            runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)
            await self._wait_for_thread_visibility(runtime, thread_id)
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
            except TimeoutError as exc:
                last_error = exc
                result = await self._confirm_timed_out_start_turn(
                    runtime,
                    instance_id,
                    thread_id,
                )
                if result is not None:
                    logger.warning(
                        "Recovered timed-out turn start for thread %s on instance %s.",
                        thread_id,
                        instance_id,
                    )
                    break
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as exc:
                last_error = exc
                if "thread not found" not in str(exc).lower() or attempt == attempts - 1:
                    raise
                await self._wait_for_thread_visibility(runtime, thread_id)
                await asyncio.sleep(0.5 * (attempt + 1))
        if result is None:
            assert last_error is not None
            raise last_error
        turn_id = extract_turn_id(result)
        _seed_runtime_thread_status(
            runtime,
            thread_id,
            status_type="active",
            turn_id=turn_id,
        )
        return result

    async def _confirm_timed_out_start_turn(
        self,
        runtime: InstanceRuntime,
        instance_id: int,
        thread_id: str,
        *,
        timeout_seconds: float = START_TURN_TIMEOUT_CONFIRM_SECONDS,
    ) -> dict[str, Any] | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        observed_active = False
        prior_threads = list(runtime.threads)
        while loop.time() < deadline:
            await self._refresh_runtime_threads(runtime)
            runtime.threads = _merge_thread_summaries(runtime.threads, prior_threads)
            turn_id = self._turn_id_from_runtime(runtime, thread_id)
            if turn_id is None:
                turn_id = await self._turn_id_from_events(instance_id, thread_id)
            thread_status = self._thread_status_from_runtime(runtime, thread_id)
            if thread_status == "active":
                observed_active = True
            if turn_id is not None:
                return {
                    "threadId": thread_id,
                    "turn": {"id": turn_id},
                    "recoveredFrom": "timeout",
                }
            if observed_active:
                return {
                    "threadId": thread_id,
                    "recoveredFrom": "timeout",
                }
            await asyncio.sleep(0.5)
        return None

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
        _seed_runtime_thread_status(runtime, thread_id, status_type="idle")
        return result

    async def start_review(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        result = await runtime.client.start_review(thread_id=thread_id)
        _seed_runtime_thread_status(runtime, thread_id, status_type="active")
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

    def _apply_runtime_thread_event(
        self,
        runtime: InstanceRuntime,
        method: str,
        params: dict[str, Any],
    ) -> None:
        if method == "thread/started":
            thread = params.get("thread")
            if isinstance(thread, dict):
                summaries = _summarize_threads([thread])
                if summaries:
                    summary = summaries[0]
                    thread_id = summary.get("id")
                    if isinstance(thread_id, str):
                        runtime.threads = _upsert_thread_summary(runtime.threads, summary)
                        runtime.loaded_thread_ids = _add_loaded_thread_id(
                            runtime.loaded_thread_ids,
                            thread_id,
                        )
            return

        thread_id = params.get("threadId")
        if not isinstance(thread_id, str) or not thread_id:
            return

        if method == "thread/archived":
            runtime.loaded_thread_ids = [
                item for item in runtime.loaded_thread_ids if item != thread_id
            ]
            runtime.threads = _patch_thread_summary(
                runtime.threads,
                thread_id,
                {"status": {"type": "archived"}},
            )
            return

        if method == "thread/unarchived":
            runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)
            runtime.threads = _patch_thread_summary(
                runtime.threads,
                thread_id,
                {"status": {"type": "idle"}},
            )
            return

        if method == "thread/name/updated":
            patch: dict[str, Any] = {}
            for key in ("name", "title"):
                value = params.get(key)
                if isinstance(value, str) and value.strip():
                    patch[key] = value
            if patch:
                runtime.threads = _patch_thread_summary(runtime.threads, thread_id, patch)
            return

        if method == "thread/status/changed":
            status = params.get("status")
            if not isinstance(status, dict):
                return
            status_patch = _pick_fields(status, ("type", "turnId", "activeTurnId"))
            status_type = status_patch.get("type")
            if status_type != "active":
                status_patch.pop("turnId", None)
                status_patch.pop("activeTurnId", None)
            runtime.threads = _patch_thread_summary(
                runtime.threads,
                thread_id,
                {"status": status_patch},
            )
            runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)
            return

        if method == "turn/started":
            turn = params.get("turn")
            turn_id = None
            if isinstance(turn, dict):
                raw_turn_id = turn.get("id")
                if isinstance(raw_turn_id, str) and raw_turn_id:
                    turn_id = raw_turn_id
            active_status_patch: dict[str, Any] = {"type": "active"}
            if turn_id is not None:
                active_status_patch["turnId"] = turn_id
                active_status_patch["activeTurnId"] = turn_id
            runtime.threads = _patch_thread_summary(
                runtime.threads,
                thread_id,
                {"status": active_status_patch},
            )
            runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)
            return

        if method == "turn/completed":
            turn = params.get("turn")
            turn_status = None
            if isinstance(turn, dict):
                raw_status = turn.get("status")
                if isinstance(raw_status, str) and raw_status:
                    turn_status = raw_status
            completed_status_patch: dict[str, Any] = {}
            if turn_status == "failed":
                completed_status_patch["type"] = "systemError"
            elif turn_status:
                completed_status_patch["type"] = "idle"
            runtime.threads = _patch_thread_summary(
                runtime.threads,
                thread_id,
                {"status": completed_status_patch},
            )
            status = next(
                (
                    thread.get("status")
                    for thread in runtime.threads
                    if isinstance(thread, dict) and thread.get("id") == thread_id
                ),
                None,
            )
            if isinstance(status, dict):
                status.pop("turnId", None)
                status.pop("activeTurnId", None)
            runtime.loaded_thread_ids = _add_loaded_thread_id(runtime.loaded_thread_ids, thread_id)

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
        event_params = event.get("params")
        if isinstance(event_params, dict):
            self._apply_runtime_thread_event(runtime, event["method"], event_params)
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
        if event["method"] in EVENT_REFRESH_METHODS:
            self._schedule_refresh_instance(
                instance_id,
                methods=EVENT_REFRESH_METHODS.get(event["method"]),
            )
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
        if (
            runtime.transport == "stdio"
            and sys.platform.startswith("win")
            and self.desktop_service is not None
            and _should_stage_windows_codex_command(
                runtime.command,
                self.default_stdio_command,
            )
        ):
            launch = self.desktop_service.resolve_launch()
            launch_note = (
                launch.note if launch.version is None else f"{launch.note} ({launch.version})"
            )
            resolved_args = runtime.args
            if not str(resolved_args or "").strip() or str(resolved_args).strip() == str(
                self.default_stdio_args
            ).strip():
                resolved_args = launch.args
            return ("stdio", launch.command, resolved_args, None, launch_note)
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
