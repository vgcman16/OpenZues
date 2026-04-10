from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from openzues.database import Database, utcnow
from openzues.schemas import InstanceView, TransportType
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.codex_rpc import CodexAppServerClient
from openzues.services.hub import BroadcastHub

logger = logging.getLogger(__name__)
RuntimeListener = Callable[[int, dict[str, Any]], Awaitable[None]]


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
    ) -> None:
        self.database = database
        self.hub = hub
        self.desktop_service = desktop_service
        self.instances: dict[int, InstanceRuntime] = {}
        self.event_listeners: list[RuntimeListener] = []
        self.server_request_listeners: list[RuntimeListener] = []

    def add_event_listener(self, listener: RuntimeListener) -> None:
        self.event_listeners.append(listener)

    def add_server_request_listener(self, listener: RuntimeListener) -> None:
        self.server_request_listeners.append(listener)

    async def load(self) -> None:
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
            if runtime.auto_connect:
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

    async def connect_instance(self, instance_id: int) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        (
            resolved_transport,
            resolved_command,
            resolved_args,
            resolved_websocket_url,
            transport_note,
        ) = self._resolve_connection(runtime)
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
        runtime.connected = False
        runtime.initialized = False
        runtime.pid = None
        await self.publish_snapshot("instance/disconnected", {"instanceId": instance_id})

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

    async def refresh_instance(self, instance_id: int) -> InstanceRuntime:
        runtime = await self.get(instance_id)
        client = runtime.client
        if client is None or not runtime.connected:
            return runtime
        runtime.auth_state = (
            await client.call("account/read", {"refreshToken": False})
        ).get("account")
        runtime.models = (
            await client.call("model/list", {"limit": 50, "includeHidden": False})
        ).get("data", [])
        runtime.collaboration_modes = (
            await client.call("collaborationMode/list", {})
        ).get("data", [])
        skills_params: dict[str, Any] = {"forceReload": False}
        if runtime.cwd:
            skills_params["cwds"] = [runtime.cwd]
        runtime.skills = (await client.call("skills/list", skills_params)).get("data", [])
        runtime.apps = (await client.call("app/list", {"limit": 50})).get("data", [])
        runtime.plugins = (await client.call("plugin/list", {})).get("data", [])
        runtime.mcp_servers = (
            await client.call("mcpServerStatus/list", {"limit": 50})
        ).get("data", [])
        runtime.config = (await client.call("config/read", {"includeLayers": False})).get("config")
        runtime.threads = (await client.call("thread/list", {"limit": 30})).get("data", [])
        runtime.loaded_thread_ids = (
            await client.call("thread/loaded/list", {})
        ).get("threadIds", [])
        runtime.unresolved_requests = await self.database.list_unresolved_server_requests(
            instance_id
        )
        runtime.last_event_at = utcnow()
        await self.publish_snapshot("instance/refreshed", {"instanceId": instance_id})
        return runtime

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
        await self.refresh_instance(instance_id)
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
        result = await runtime.client.start_turn(
            thread_id=thread_id,
            text=text,
            cwd=cwd,
            model=model,
            reasoning_effort=reasoning_effort,
            collaboration_mode=collaboration_mode,
        )
        await self.refresh_instance(instance_id)
        return result

    async def interrupt_turn(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        result = await runtime.client.interrupt_turn(thread_id=thread_id)
        await self.refresh_instance(instance_id)
        return result

    async def start_review(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        runtime = await self.get(instance_id)
        if runtime.client is None:
            raise RuntimeError("Instance is not connected.")
        result = await runtime.client.start_review(thread_id=thread_id)
        await self.refresh_instance(instance_id)
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
        await self.database.append_event(
            instance_id=instance_id,
            thread_id=event.get("threadId"),
            method=event["method"],
            payload=event["params"],
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
                "params": event["params"],
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
            asyncio.create_task(self.refresh_instance(instance_id))
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
