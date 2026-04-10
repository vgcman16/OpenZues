from __future__ import annotations

import asyncio
import json
import logging
import shlex
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

JsonDict = dict[str, Any]
EventCallback = Callable[[JsonDict], Awaitable[None]]
ServerRequestCallback = Callable[[JsonDict], Awaitable[None]]
STREAM_LIMIT_BYTES = 8 * 1024 * 1024


def split_args(raw_args: str | None) -> list[str]:
    if not raw_args:
        return []
    return shlex.split(raw_args, posix=False)


def extract_thread_id(payload: JsonDict) -> str | None:
    if "threadId" in payload and isinstance(payload["threadId"], str):
        return payload["threadId"]
    thread = payload.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"]
    turn = payload.get("turn")
    if isinstance(turn, dict):
        if isinstance(turn.get("threadId"), str):
            return turn["threadId"]
        nested_thread = turn.get("thread")
        if isinstance(nested_thread, dict) and isinstance(nested_thread.get("id"), str):
            return nested_thread["id"]
    item = payload.get("item")
    if isinstance(item, dict) and isinstance(item.get("threadId"), str):
        return item["threadId"]
    return None


def extract_turn_id(payload: JsonDict) -> str | None:
    if "turnId" in payload and isinstance(payload["turnId"], str):
        return payload["turnId"]
    turn = payload.get("turn")
    if isinstance(turn, dict) and isinstance(turn.get("id"), str):
        return turn["id"]
    item = payload.get("item")
    if isinstance(item, dict):
        if isinstance(item.get("turnId"), str):
            return item["turnId"]
        nested_turn = item.get("turn")
        if isinstance(nested_turn, dict) and isinstance(nested_turn.get("id"), str):
            return nested_turn["id"]
    return None


def _sandbox_policy_from_mode(value: str | None) -> JsonDict | None:
    if value == "read-only":
        return {"type": "readOnly"}
    if value == "workspace-write":
        return {"type": "workspaceWrite"}
    if value == "danger-full-access":
        return {"type": "dangerFullAccess"}
    return None


def _danger_full_access_policy() -> JsonDict:
    return {"type": "dangerFullAccess"}


@dataclass(slots=True)
class ConnectionInfo:
    connected: bool = False
    initialized: bool = False
    pid: int | None = None
    error: str | None = None
    client_user_agent: str | None = None


@dataclass(slots=True)
class CodexAppServerClient:
    transport: str
    command: str | None
    args: str | None
    websocket_url: str | None
    cwd: str | None
    event_callback: EventCallback
    server_request_callback: ServerRequestCallback
    process: asyncio.subprocess.Process | None = None
    websocket: ClientConnection | None = None
    _reader_task: asyncio.Task[None] | None = None
    _stderr_task: asyncio.Task[None] | None = None
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _pending: dict[int, asyncio.Future[Any]] = field(default_factory=dict)
    _next_id: int = 0
    _windows_sandbox_waiters: dict[str, asyncio.Future[None]] = field(default_factory=dict)
    _windows_sandbox_ready_modes: set[str] = field(default_factory=set)
    info: ConnectionInfo = field(default_factory=ConnectionInfo)

    def _execution_defaults(self) -> tuple[str | None, str | None, JsonDict | None]:
        approval_policy: str | None = None
        sandbox_mode: str | None = None
        sandbox_policy: JsonDict | None = None
        args = split_args(self.args)
        for index, token in enumerate(args):
            next_value = args[index + 1] if index + 1 < len(args) else None
            if token in {"-a", "--ask-for-approval"} and next_value:
                approval_policy = next_value
            elif token in {"-s", "--sandbox"} and next_value:
                sandbox_mode = next_value
                sandbox_policy = _sandbox_policy_from_mode(next_value)
        return approval_policy, sandbox_mode, sandbox_policy

    def _execution_policy_for_turns(self) -> JsonDict | None:
        _approval_policy, sandbox_mode, sandbox_policy = self._execution_defaults()
        if sys.platform.startswith("win") and sandbox_mode != "danger-full-access":
            return _danger_full_access_policy()
        return sandbox_policy

    async def connect(self) -> None:
        if self.info.connected:
            return
        self.info.error = None
        if self.transport == "stdio":
            command = self.command or "codex"
            args = split_args(self.args) if self.args is not None else ["app-server"]
            cwd = str(Path(self.cwd).expanduser()) if self.cwd else None
            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self.info.pid = self.process.pid
            assert self.process.stdout is not None
            assert self.process.stderr is not None
            self._raise_stream_limit(self.process.stdout)
            self._raise_stream_limit(self.process.stderr)
            self._reader_task = asyncio.create_task(self._stdio_reader_loop())
            self._stderr_task = asyncio.create_task(self._stderr_reader_loop())
        else:
            if not self.websocket_url:
                raise RuntimeError("WebSocket transport requires a websocket_url.")
            self.websocket = await websockets.connect(
                self.websocket_url,
                max_size=None,
                ping_interval=20,
            )
            self._reader_task = asyncio.create_task(self._websocket_reader_loop())

        self.info.connected = True
        result = await self.call(
            "initialize",
            {
                "clientInfo": {
                    "name": "openzues",
                    "title": "OpenZues",
                    "version": "0.1.0",
                },
                "capabilities": {
                    "experimentalApi": True,
                },
            },
        )
        self.info.client_user_agent = result.get("clientUserAgent") or result.get("userAgent")
        self.info.initialized = True
        await self.notify("initialized", {})
        try:
            await self.prepare_windows_sandbox(cwd=self.cwd)
        except Exception:
            logger.warning("Windows sandbox preparation failed", exc_info=True)

    async def close(self) -> None:
        self.info.connected = False
        self.info.initialized = False
        if self.websocket is not None:
            await self.websocket.close()
            self.websocket = None
        if self.process is not None:
            if self.process.stdin is not None:
                self.process.stdin.close()
            if self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            self.process = None
        for task in (self._reader_task, self._stderr_task):
            if task is not None:
                task.cancel()
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        for waiter in self._windows_sandbox_waiters.values():
            if not waiter.done():
                waiter.cancel()
        self._windows_sandbox_waiters.clear()
        self._windows_sandbox_ready_modes.clear()

    async def call(self, method: str, params: JsonDict | None = None, timeout: float = 30.0) -> Any:
        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending[request_id] = future
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
            "params": params or {},
        }
        await self._send_json(payload)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(request_id, None)

    async def notify(self, method: str, params: JsonDict | None = None) -> None:
        await self._send_json({"jsonrpc": "2.0", "method": method, "params": params or {}})

    async def respond(self, request_id: str, result: Any) -> None:
        await self._send_json({"jsonrpc": "2.0", "id": int(request_id), "result": result})

    async def prepare_windows_sandbox(self, *, cwd: str | None = None) -> None:
        if not sys.platform.startswith("win"):
            return
        _approval_policy, sandbox_mode, _sandbox_policy = self._execution_defaults()
        if sandbox_mode in {None, "danger-full-access"}:
            return
        for mode in ("elevated",):
            waiter = self._windows_sandbox_waiters.get(mode)
            if waiter is None or waiter.done():
                waiter = asyncio.get_running_loop().create_future()
                self._windows_sandbox_waiters[mode] = waiter
            self._windows_sandbox_ready_modes.discard(mode)
            params: JsonDict = {"mode": mode}
            if cwd:
                params["cwd"] = cwd
            await self.call("windowsSandbox/setupStart", params, timeout=120.0)
            await asyncio.wait_for(waiter, timeout=120.0)
            self._windows_sandbox_ready_modes.add(mode)

    async def start_thread(
        self,
        *,
        model: str,
        cwd: str | None = None,
        reasoning_effort: str | None = None,
        collaboration_mode: str | None = None,
    ) -> Any:
        params: JsonDict = {"model": model}
        approval_policy, sandbox_mode, _sandbox_policy = self._execution_defaults()
        await self.prepare_windows_sandbox(cwd=cwd or self.cwd)
        if cwd:
            params["cwd"] = cwd
        if approval_policy:
            params["approvalPolicy"] = approval_policy
        if sandbox_mode:
            params["sandbox"] = sandbox_mode
        return await self.call("thread/start", params)

    async def start_turn(
        self,
        *,
        thread_id: str,
        text: str,
        cwd: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        collaboration_mode: str | None = None,
    ) -> Any:
        params: JsonDict = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": text}],
        }
        approval_policy, _sandbox_mode, _sandbox_policy = self._execution_defaults()
        await self.prepare_windows_sandbox(cwd=cwd or self.cwd)
        sandbox_policy = self._execution_policy_for_turns()
        if cwd:
            params["cwd"] = cwd
        if model:
            params["model"] = model
        if reasoning_effort:
            params["effort"] = reasoning_effort
        if approval_policy:
            params["approvalPolicy"] = approval_policy
        if sandbox_policy:
            params["sandboxPolicy"] = sandbox_policy
        return await self.call("turn/start", params, timeout=60.0)

    async def interrupt_turn(self, *, thread_id: str, turn_id: str | None = None) -> Any:
        params: JsonDict = {"threadId": thread_id}
        if turn_id:
            params["turnId"] = turn_id
        return await self.call("turn/interrupt", params)

    async def start_review(self, *, thread_id: str) -> Any:
        return await self.call("review/start", {"threadId": thread_id})

    async def exec_command(
        self,
        *,
        command: list[str],
        cwd: str | None = None,
        timeout_ms: int | None = None,
        tty: bool = False,
    ) -> Any:
        params: JsonDict = {"command": command, "tty": tty}
        if cwd:
            params["cwd"] = cwd
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        await self.prepare_windows_sandbox(cwd=cwd or self.cwd)
        sandbox_policy = self._execution_policy_for_turns()
        if sandbox_policy:
            params["sandboxPolicy"] = sandbox_policy
        return await self.call("command/exec", params)

    async def _send_json(self, payload: JsonDict) -> None:
        message = json.dumps(payload, separators=(",", ":"))
        async with self._send_lock:
            if self.transport == "stdio":
                if self.process is None or self.process.stdin is None:
                    raise RuntimeError("Stdio transport is not available.")
                self.process.stdin.write(f"{message}\n".encode())
                await self.process.stdin.drain()
            else:
                if self.websocket is None:
                    raise RuntimeError("WebSocket transport is not available.")
                await self.websocket.send(message)

    async def _handle_incoming(self, payload: JsonDict) -> None:
        if "id" in payload and "method" not in payload:
            request_id = int(payload["id"])
            future = self._pending.get(request_id)
            if future is None or future.done():
                return
            if "error" in payload:
                message = payload["error"].get("message", "Unknown JSON-RPC error")
                future.set_exception(RuntimeError(message))
            else:
                future.set_result(payload.get("result", {}))
            return
        if "id" in payload and "method" in payload:
            params = dict(payload.get("params", {}))
            await self.server_request_callback(
                {
                    "requestId": str(payload["id"]),
                    "method": str(payload["method"]),
                    "params": params,
                    "threadId": extract_thread_id(params),
                }
            )
            return
        if "method" in payload:
            if payload["method"] == "windowsSandbox/setupCompleted":
                params = dict(payload.get("params", {}))
                mode = str(params.get("mode") or "")
                if mode:
                    waiter = self._windows_sandbox_waiters.get(mode)
                    if bool(params.get("success")):
                        self._windows_sandbox_ready_modes.add(mode)
                        if waiter is not None and not waiter.done():
                            waiter.set_result(None)
                    else:
                        error = str(
                            params.get("error") or f"Windows sandbox setup failed for {mode}."
                        )
                        if waiter is not None and not waiter.done():
                            waiter.set_exception(RuntimeError(error))
            params = dict(payload.get("params", {}))
            await self.event_callback(
                {
                    "method": str(payload["method"]),
                    "params": params,
                    "threadId": extract_thread_id(params),
                }
            )

    async def _stdio_reader_loop(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        try:
            while line := await self.process.stdout.readline():
                payload = json.loads(line.decode("utf-8"))
                await self._handle_incoming(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("App server stdio reader crashed")
            self.info.error = str(exc)
        finally:
            self.info.connected = False

    async def _stderr_reader_loop(self) -> None:
        assert self.process is not None
        assert self.process.stderr is not None
        try:
            while line := await self.process.stderr.readline():
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                await self.event_callback(
                    {
                        "method": "server/stderr",
                        "params": {"line": text},
                        "threadId": None,
                    }
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("App server stderr reader crashed")

    async def _websocket_reader_loop(self) -> None:
        assert self.websocket is not None
        try:
            async for message in self.websocket:
                payload = json.loads(message)
                await self._handle_incoming(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("App server websocket reader crashed")
            self.info.error = str(exc)
        finally:
            self.info.connected = False

    def _raise_stream_limit(self, stream: asyncio.StreamReader) -> None:
        limit = getattr(stream, "_limit", None)
        if isinstance(limit, int) and limit < STREAM_LIMIT_BYTES:
            cast(Any, stream)._limit = STREAM_LIMIT_BYTES
