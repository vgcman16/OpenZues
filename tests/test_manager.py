from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

import openzues.services.manager as manager_module
from openzues.database import Database
from openzues.services.codex_desktop import DesktopLaunchConfig
from openzues.services.hub import BroadcastHub
from openzues.services.manager import InstanceRuntime, RuntimeManager, compact_event_payload


def test_compact_event_payload_trims_catalog_updates() -> None:
    payload = {
        "data": [
            {
                "id": "connector_1",
                "name": "GitHub",
                "description": "Access repositories",
                "logoUrl": "https://example.com/logo.png",
                "isAccessible": True,
            },
            {
                "id": "connector_2",
                "name": "Slack",
                "description": "Read channel context",
                "logoUrl": "https://example.com/slack.png",
                "isAccessible": False,
            },
        ]
    }

    compact = compact_event_payload("app/list/updated", payload)

    assert compact["count"] == 2
    assert compact["truncated"] is False
    assert compact["data"] == [
        {
            "id": "connector_1",
            "name": "GitHub",
            "description": "Access repositories",
            "isAccessible": True,
        },
        {
            "id": "connector_2",
            "name": "Slack",
            "description": "Read channel context",
            "isAccessible": False,
        },
    ]


def test_compact_event_payload_keeps_thread_status_signal() -> None:
    payload = {
        "data": [
            {
                "id": "thread_1",
                "title": "Mission workspace",
                "status": {"type": "active", "reason": "running"},
                "updatedAt": "2026-04-10T09:00:00Z",
                "extra": "discard me",
            }
        ]
    }

    compact = compact_event_payload("thread/list/updated", payload)

    assert compact["data"] == [
        {
            "id": "thread_1",
            "title": "Mission workspace",
            "updatedAt": "2026-04-10T09:00:00Z",
            "status": {"type": "active"},
        }
    ]


def test_compact_event_payload_summarizes_account_updates() -> None:
    payload = {
        "account": {
            "type": "chatgpt",
            "email": "operator@example.com",
            "planType": "pro",
            "unused": "drop me",
        }
    }

    compact = compact_event_payload("account/updated", payload)

    assert compact["account"] == {
        "type": "chatgpt",
        "email": "operator@example.com",
        "planType": "pro",
    }


def test_compact_event_payload_truncates_long_server_logs() -> None:
    line = "<html>" + ("abcdef" * 90)

    compact = compact_event_payload("server/stderr", {"line": line})

    assert compact["line"].endswith("... [truncated]")
    assert compact["lineLength"] == len(line)


def test_compact_event_payload_strips_ansi_and_timestamp_from_server_logs() -> None:
    line = (
        "\x1b[2m2026-04-11T01:37:30.455301Z\x1b[0m "
        "\x1b[33mWARN\x1b[0m codex_core::plugins::manifest: ignoring interface.defaultPrompt"
    )

    compact = compact_event_payload("server/stderr", {"line": line})

    assert compact["line"] == (
        "WARN codex_core::plugins::manifest: ignoring interface.defaultPrompt"
    )


def test_compact_event_payload_drops_empty_catalog_items() -> None:
    compact = compact_event_payload("skill/list/updated", {"data": [{"name": "Checks"}, {}]})

    assert compact["data"] == [{"name": "Checks"}]


def test_compact_event_payload_clips_command_execution_items() -> None:
    long_command = "python -c \"" + ("print('openclaw parity seam') " * 20) + "\""
    long_output = "gateway parity trace " * 80

    compact = compact_event_payload(
        "item/completed",
        {
            "item": {
                "type": "commandExecution",
                "id": "cmd_1",
                "command": long_command,
                "aggregatedOutput": long_output,
                "status": "completed",
                "commandActions": [
                    {"type": "run", "command": long_command},
                    {"type": "run", "command": "rg -n gateway src/openzues"},
                    {"type": "run", "command": "pytest tests/test_gateway_bootstrap.py -q"},
                    {"type": "run", "command": "python -m compileall src/openzues"},
                ],
            }
        },
    )

    item = compact["item"]
    assert item["command"].endswith("... [truncated]")
    assert item["commandLength"] == len(long_command)
    assert item["aggregatedOutput"].endswith("... [truncated]")
    assert item["aggregatedOutputLength"] == len(long_output)
    assert item["commandActionCount"] == 4
    assert item["commandActionsTruncated"] is True
    assert len(item["commandActions"]) == 3


def test_compact_event_payload_clips_long_delta_events() -> None:
    delta = "checkpoint detail " * 60

    compact = compact_event_payload(
        "item/commandExecution/outputDelta",
        {
            "threadId": "thread_1",
            "turnId": "turn_1",
            "itemId": "cmd_1",
            "delta": delta,
        },
    )

    assert compact["delta"].endswith("... [truncated]")
    assert compact["deltaLength"] == len(delta)


def test_compact_event_payload_clips_user_message_content() -> None:
    long_text = "recovery packet detail " * 80

    compact = compact_event_payload(
        "item/completed",
        {
            "item": {
                "type": "userMessage",
                "id": "msg_1",
                "content": [
                    {"type": "text", "text": long_text},
                    {"type": "text", "text": "second note"},
                    {"type": "text", "text": "third note"},
                ],
            }
        },
    )

    item = compact["item"]
    assert item["contentCount"] == 3
    assert item["contentTruncated"] is True
    assert len(item["content"]) == 2
    assert item["content"][0]["text"].endswith("... [truncated]")
    assert item["content"][0]["textLength"] == len(long_text)


def test_resolve_connection_stages_windows_codex_stdio_launch(monkeypatch, tmp_path) -> None:
    class StubDesktopService:
        def resolve_launch(self) -> DesktopLaunchConfig:
            return DesktopLaunchConfig(
                command="C:/runtime/codex.exe",
                args="-a never -s danger-full-access app-server",
                note="staged from desktop package",
                version="0.119.0",
            )

    database = Database(tmp_path / "manager.db")
    manager = RuntimeManager(database, BroadcastHub(), desktop_service=StubDesktopService())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Workspace Shell",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
    )

    monkeypatch.setattr(manager_module.sys, "platform", "win32")

    transport, command, args, websocket_url, note = manager._resolve_connection(runtime)

    assert transport == "stdio"
    assert command == "C:/runtime/codex.exe"
    assert args == "-a never -s danger-full-access app-server"
    assert websocket_url is None
    assert note == "staged from desktop package (0.119.0)"


def test_resolve_connection_keeps_custom_stdio_args_when_staging_codex(
    monkeypatch,
    tmp_path,
) -> None:
    class StubDesktopService:
        def resolve_launch(self) -> DesktopLaunchConfig:
            return DesktopLaunchConfig(
                command="C:/runtime/codex.exe",
                args="-a never -s danger-full-access app-server",
                note="staged from desktop package",
                version=None,
            )

    database = Database(tmp_path / "manager.db")
    manager = RuntimeManager(database, BroadcastHub(), desktop_service=StubDesktopService())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Workspace Shell",
        transport="stdio",
        command=r"C:\Program Files\WindowsApps\OpenAI.Codex_26.409\app\resources\codex.exe",
        args="--log-level debug app-server",
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
    )

    monkeypatch.setattr(manager_module.sys, "platform", "win32")

    transport, command, args, websocket_url, note = manager._resolve_connection(runtime)

    assert transport == "stdio"
    assert command == "C:/runtime/codex.exe"
    assert args == "--log-level debug app-server"
    assert websocket_url is None
    assert note == "staged from desktop package"


@pytest.mark.asyncio
async def test_handle_event_updates_runtime_threads_without_scheduling_refresh(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    await manager.handle_event(
        1,
        {
            "method": "thread/started",
            "threadId": "thread_live",
            "params": {
                "thread": {
                    "id": "thread_live",
                    "status": {"type": "idle"},
                    "name": "Parity Thread",
                    "updatedAt": "2026-04-14T21:35:07Z",
                }
            },
        },
    )
    await manager.handle_event(
        1,
        {
            "method": "turn/started",
            "threadId": "thread_live",
            "params": {
                "threadId": "thread_live",
                "turn": {"id": "turn_live", "status": "inProgress"},
            },
        },
    )
    await manager.handle_event(
        1,
        {
            "method": "turn/completed",
            "threadId": "thread_live",
            "params": {
                "threadId": "thread_live",
                "turn": {"id": "turn_live", "status": "completed"},
            },
        },
    )

    assert runtime.threads == [
        {
            "id": "thread_live",
            "name": "Parity Thread",
            "updatedAt": "2026-04-14T21:35:07Z",
            "status": {"type": "idle"},
        }
    ]
    assert runtime.loaded_thread_ids == ["thread_live"]
    assert scheduled == []


@pytest.mark.asyncio
async def test_handle_event_schedules_refresh_for_account_updates(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    await manager.handle_event(
        1,
        {
            "method": "account/updated",
            "threadId": None,
            "params": {
                "account": {
                    "type": "chatgpt",
                    "email": "operator@example.com",
                }
            },
        },
    )

    assert scheduled == [(1, ("account/read",))]


class FakeInterruptClient:
    def __init__(
        self,
        *,
        thread_list: list[dict[str, object]] | None = None,
        interrupt_error: Exception | None = None,
    ) -> None:
        self.calls: list[dict[str, str]] = []
        self.thread_list = thread_list or []
        self.interrupt_error = interrupt_error

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        assert method == "thread/list"
        return {"data": self.thread_list}

    async def interrupt_turn(self, *, thread_id: str, turn_id: str | None = None) -> dict[str, str]:
        if self.interrupt_error is not None:
            raise self.interrupt_error
        self.calls.append({"thread_id": thread_id, "turn_id": turn_id or ""})
        return {"ok": "true"}


class FakeTurnClient:
    def __init__(self) -> None:
        self.turn_attempts = 0
        self.thread_list_calls = 0

    async def start_turn(
        self,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        self.turn_attempts += 1
        if self.turn_attempts == 1:
            raise RuntimeError(f"thread not found: {thread_id}")
        return {"turn": {"id": "turn_retry_ok"}}

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        assert method == "thread/list"
        self.thread_list_calls += 1
        return {"data": [{"id": "thread_retry", "status": {"type": "idle"}}]}


class FakeSuccessfulTurnClient:
    async def start_turn(
        self,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        del thread_id, text, cwd, model, reasoning_effort, collaboration_mode
        return {"turn": {"id": "turn_ok"}}


class FakeTimeoutTurnClient:
    def __init__(self) -> None:
        self.turn_attempts = 0
        self.thread_list_calls = 0

    async def start_turn(
        self,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        del thread_id, text, cwd, model, reasoning_effort, collaboration_mode
        self.turn_attempts += 1
        raise TimeoutError()

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        del params, timeout
        assert method == "thread/list"
        self.thread_list_calls += 1
        return {"data": [{"id": "thread_timeout", "status": {"type": "active"}}]}


class FakeStartThreadRetryClient:
    def __init__(self) -> None:
        self.start_attempts = 0

    async def start_thread(
        self,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        del model, cwd, reasoning_effort, collaboration_mode
        self.start_attempts += 1
        if self.start_attempts == 1:
            raise TimeoutError()
        return {"thread": {"id": "thread_retry_ok"}}


class FakeImmediateStartThreadClient:
    def __init__(self) -> None:
        self.thread_list_calls = 0

    async def start_thread(
        self,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        del model, cwd, reasoning_effort, collaboration_mode
        return {"thread": {"id": "thread_live"}}

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        del params, timeout
        assert method == "thread/list"
        self.thread_list_calls += 1
        return {"data": [{"id": "thread_live", "status": {"type": "idle"}}]}


class FakeStartThreadRecoveredClient:
    def __init__(self) -> None:
        self.start_attempts = 0
        self.thread_list_calls = 0

    async def start_thread(
        self,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, dict[str, str]]:
        del model, cwd, reasoning_effort, collaboration_mode
        self.start_attempts += 1
        raise TimeoutError()

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        del params, timeout
        assert method == "thread/list"
        self.thread_list_calls += 1
        return {"data": [{"id": "thread_recovered", "status": {"type": "idle"}}]}


class FakeMcpStatusClient:
    def __init__(self, payload: list[dict[str, object]]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict | None]] = []

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, list[dict[str, object]]]:
        self.calls.append((method, params))
        assert method == "mcpServerStatus/list"
        return {"data": self.payload}


class FakeReviewClient:
    async def start_review(self, *, thread_id: str) -> dict[str, str]:
        del thread_id
        return {"ok": "true"}


class FakeRefreshClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        del params, timeout
        self.calls.append(method)
        if method in {"app/list", "plugin/list"}:
            raise TimeoutError()
        if method == "account/read":
            return {"account": {"type": "chatgpt", "email": "operator@example.com"}}
        if method == "model/list":
            return {"data": [{"id": "gpt-5.4", "displayName": "GPT-5.4"}]}
        if method == "collaborationMode/list":
            return {"data": [{"name": "default", "mode": "default"}]}
        if method == "skills/list":
            return {"data": [{"name": "Browser Verify", "description": "Verify UI flows."}]}
        if method == "config/read":
            return {"config": {"model": "gpt-5.4", "approvalPolicy": "never"}}
        if method == "thread/list":
            return {"data": [{"id": "thread_live", "status": {"type": "active"}}]}
        if method == "thread/loaded/list":
            return {"threadIds": ["thread_live"]}
        if method == "mcpServerStatus/list":
            return {"data": []}
        raise AssertionError(f"Unexpected method {method}")


class FakeTimeoutBackoffClient:
    def __init__(self, method: str) -> None:
        self.method = method
        self.calls: list[str] = []

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        del params, timeout
        self.calls.append(method)
        assert method == self.method
        raise TimeoutError()


class FakeSlowTimeoutBackoffClient:
    def __init__(self, method: str) -> None:
        self.method = method
        self.calls: list[str] = []

    async def call(
        self,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]:
        del params, timeout
        self.calls.append(method)
        assert method == self.method
        await asyncio.sleep(0.01)
        raise TimeoutError()


@pytest.mark.asyncio
async def test_interrupt_turn_uses_latest_active_turn_from_events(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient(thread_list=[{"id": "thread_123", "status": {"type": "active"}}])
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    await database.append_event(
        instance_id=1,
        thread_id="thread_123",
        method="turn/started",
        payload={"threadId": "thread_123", "turnId": "turn_123"},
    )
    manager.refresh_instance = AsyncMock(return_value=runtime)  # type: ignore[method-assign]

    result = await manager.interrupt_turn(1, "thread_123")

    assert client.calls == [{"thread_id": "thread_123", "turn_id": "turn_123"}]
    assert result == {"ok": "true"}


@pytest.mark.asyncio
async def test_interrupt_turn_returns_noop_when_no_active_turn(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    result = await manager.interrupt_turn(1, "thread_missing")

    assert client.calls == []
    assert result == {"ok": False, "reason": "no_active_turn", "threadId": "thread_missing"}


@pytest.mark.asyncio
async def test_interrupt_turn_ignores_stale_event_when_thread_is_idle(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient(thread_list=[{"id": "thread_idle", "status": {"type": "idle"}}])
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    await database.append_event(
        instance_id=1,
        thread_id="thread_idle",
        method="turn/started",
        payload={"threadId": "thread_idle", "turnId": "turn_stale"},
    )

    result = await manager.interrupt_turn(1, "thread_idle")

    assert client.calls == []
    assert result == {"ok": False, "reason": "no_active_turn", "threadId": "thread_idle"}


@pytest.mark.asyncio
async def test_interrupt_turn_returns_timeout_payload_when_interrupt_unconfirmed(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient(
        thread_list=[{"id": "thread_busy", "status": {"type": "active", "turnId": "turn_busy"}}],
        interrupt_error=TimeoutError(),
    )
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    result = await manager.interrupt_turn(1, "thread_busy")

    assert result == {
        "ok": False,
        "reason": "interrupt_timeout",
        "threadId": "thread_busy",
        "turnId": "turn_busy",
    }


@pytest.mark.asyncio
async def test_start_turn_retries_after_thread_not_found(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeTurnClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    result = await manager.start_turn(
        1,
        thread_id="thread_retry",
        text="Continue building.",
        cwd="C:/workspace",
        model=None,
        reasoning_effort=None,
        collaboration_mode=None,
    )

    assert result == {"turn": {"id": "turn_retry_ok"}}
    assert client.turn_attempts == 2
    assert client.thread_list_calls >= 1
    assert runtime.threads == [
        {
            "id": "thread_retry",
            "status": {
                "type": "active",
                "turnId": "turn_retry_ok",
                "activeTurnId": "turn_retry_ok",
            },
        }
    ]


@pytest.mark.asyncio
async def test_start_turn_seeds_runtime_state_without_scheduling_refresh(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=FakeSuccessfulTurnClient(),  # type: ignore[arg-type]
        connected=True,
        threads=[{"id": "thread_live", "status": {"type": "idle"}}],
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    result = await manager.start_turn(
        1,
        thread_id="thread_live",
        text="Continue building.",
        cwd="C:/workspace",
        model=None,
        reasoning_effort=None,
        collaboration_mode=None,
    )

    assert result == {"turn": {"id": "turn_ok"}}
    assert runtime.threads == [
        {
            "id": "thread_live",
            "status": {"type": "active", "turnId": "turn_ok", "activeTurnId": "turn_ok"},
        }
    ]
    assert runtime.loaded_thread_ids == ["thread_live"]
    assert scheduled == []


@pytest.mark.asyncio
async def test_start_turn_recovers_when_runtime_started_turn_after_timeout(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeTimeoutTurnClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    await database.append_event(
        instance_id=1,
        thread_id="thread_timeout",
        method="turn/started",
        payload={"threadId": "thread_timeout", "turn": {"id": "turn_late"}},
    )

    result = await manager.start_turn(
        1,
        thread_id="thread_timeout",
        text="Continue building.",
        cwd="C:/workspace",
        model=None,
        reasoning_effort=None,
        collaboration_mode=None,
    )

    assert result["turn"]["id"] == "turn_late"
    assert result["recoveredFrom"] == "timeout"
    assert client.turn_attempts == 1
    assert client.thread_list_calls >= 1
    assert runtime.threads == [
        {
            "id": "thread_timeout",
            "status": {"type": "active", "turnId": "turn_late", "activeTurnId": "turn_late"},
        }
    ]


@pytest.mark.asyncio
async def test_start_turn_timeout_recovery_preserves_existing_runtime_threads(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeTimeoutTurnClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        threads=[{"id": "thread_main", "status": {"type": "idle"}}],
    )
    manager.instances[1] = runtime
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    await database.append_event(
        instance_id=1,
        thread_id="thread_timeout",
        method="turn/started",
        payload={"threadId": "thread_timeout", "turn": {"id": "turn_late"}},
    )

    result = await manager.start_turn(
        1,
        thread_id="thread_timeout",
        text="Continue building.",
        cwd="C:/workspace",
        model=None,
        reasoning_effort=None,
        collaboration_mode=None,
    )

    assert result["turn"]["id"] == "turn_late"
    assert result["recoveredFrom"] == "timeout"
    assert runtime.threads == [
        {
            "id": "thread_timeout",
            "status": {"type": "active", "turnId": "turn_late", "activeTurnId": "turn_late"},
        },
        {"id": "thread_main", "status": {"type": "idle"}},
    ]


@pytest.mark.asyncio
async def test_start_thread_reconnects_and_retries_after_timeout(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeStartThreadRetryClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime
    manager.disconnect_instance = AsyncMock()  # type: ignore[method-assign]
    manager.connect_instance = AsyncMock(return_value=runtime)  # type: ignore[method-assign]
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    result = await manager.start_thread(
        1,
        model="gpt-5.4",
        cwd="C:/workspace",
        reasoning_effort="high",
        collaboration_mode=None,
    )

    assert result == {"thread": {"id": "thread_retry_ok"}}
    assert client.start_attempts == 2
    manager.disconnect_instance.assert_awaited_once_with(1)
    manager.connect_instance.assert_awaited_once_with(1)
    assert runtime.threads == [{"id": "thread_retry_ok", "status": {"type": "idle"}}]


@pytest.mark.asyncio
async def test_start_thread_marks_loaded_thread_without_scheduling_refresh(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeImmediateStartThreadClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    result = await manager.start_thread(
        1,
        model="gpt-5.4",
        cwd="C:/workspace",
        reasoning_effort="high",
        collaboration_mode=None,
    )

    assert result == {"thread": {"id": "thread_live"}}
    assert client.thread_list_calls >= 1
    assert runtime.threads == [{"id": "thread_live", "status": {"type": "idle"}}]
    assert runtime.loaded_thread_ids == ["thread_live"]
    assert scheduled == []


@pytest.mark.asyncio
async def test_start_thread_preserves_existing_runtime_threads_when_seeding_new_thread(
    tmp_path,
) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeStartThreadRetryClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        threads=[{"id": "thread_main", "status": {"type": "active", "turnId": "turn_main"}}],
    )
    manager.instances[1] = runtime
    manager.disconnect_instance = AsyncMock()  # type: ignore[method-assign]
    manager.connect_instance = AsyncMock(return_value=runtime)  # type: ignore[method-assign]
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    result = await manager.start_thread(
        1,
        model="gpt-5.4",
        cwd="C:/workspace",
        reasoning_effort="high",
        collaboration_mode=None,
    )

    assert result == {"thread": {"id": "thread_retry_ok"}}
    assert runtime.threads == [
        {"id": "thread_main", "status": {"type": "active", "turnId": "turn_main"}},
        {"id": "thread_retry_ok", "status": {"type": "idle"}},
    ]


@pytest.mark.asyncio
async def test_start_thread_recovers_when_timeout_created_thread_anyway(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeStartThreadRecoveredClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime
    manager._schedule_refresh_instance = (  # type: ignore[method-assign]
        lambda _instance_id, methods=None: None
    )

    result = await manager.start_thread(
        1,
        model="gpt-5.4",
        cwd="C:/workspace",
        reasoning_effort="high",
        collaboration_mode=None,
    )

    assert result["thread"]["id"] == "thread_recovered"
    assert result["recoveredFrom"] == "timeout"
    assert client.start_attempts == 1
    assert client.thread_list_calls >= 1
    assert runtime.threads == [{"id": "thread_recovered", "status": {"type": "idle"}}]


@pytest.mark.asyncio
async def test_interrupt_turn_updates_runtime_state_without_scheduling_refresh(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeInterruptClient(
        thread_list=[{"id": "thread_busy", "status": {"type": "active", "turnId": "turn_busy"}}]
    )
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        threads=[
            {
                "id": "thread_busy",
                "status": {"type": "active", "turnId": "turn_busy", "activeTurnId": "turn_busy"},
            }
        ],
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    result = await manager.interrupt_turn(1, "thread_busy")

    assert result == {"ok": "true"}
    assert runtime.threads == [{"id": "thread_busy", "status": {"type": "idle"}}]
    assert runtime.loaded_thread_ids == ["thread_busy"]
    assert scheduled == []


@pytest.mark.asyncio
async def test_start_review_marks_runtime_active_without_scheduling_refresh(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=FakeReviewClient(),  # type: ignore[arg-type]
        connected=True,
        threads=[{"id": "thread_review", "status": {"type": "idle"}}],
    )
    manager.instances[1] = runtime

    scheduled: list[tuple[int, tuple[str, ...] | None]] = []

    def capture_schedule(instance_id: int, methods=None) -> None:
        scheduled.append((instance_id, methods))

    manager._schedule_refresh_instance = capture_schedule  # type: ignore[method-assign]

    result = await manager.start_review(1, "thread_review")

    assert result == {"ok": "true"}
    assert runtime.threads == [{"id": "thread_review", "status": {"type": "active"}}]
    assert runtime.loaded_thread_ids == ["thread_review"]
    assert scheduled == []


@pytest.mark.asyncio
async def test_list_mcp_server_status_summarizes_tool_catalogs(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeMcpStatusClient(
        [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": {
                    "mempalace_status": {},
                    "mempalace_search": {},
                    "mempalace_diary_write": {},
                },
                "resources": [{"name": "Memory Journal"}],
                "resourceTemplates": [{"uri": "mempalace://entries/{id}"}],
                "services": [{"service": {"id": "browser-control"}}],
            }
        ]
    )
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    payload = await manager.list_mcp_server_status(1)

    assert payload == [
        {
            "name": "MemPalace MCP Server",
            "source": "mempalace",
            "status": "ready",
            "authStatus": "ready",
            "tools": [
                "mempalace_status",
                "mempalace_search",
                "mempalace_diary_write",
            ],
            "resources": ["Memory Journal"],
            "resourceTemplates": ["mempalace://entries/{id}"],
            "services": ["browser-control"],
        }
    ]
    assert runtime.mcp_server_status == payload


@pytest.mark.asyncio
async def test_refresh_instance_keeps_cached_catalogs_when_optional_reads_timeout(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeRefreshClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        apps=[{"id": "cached_app", "name": "Cached App"}],
        plugins=[{"name": "cached-plugin", "enabled": True}],
    )
    manager.instances[1] = runtime

    refreshed = await manager.refresh_instance(1)

    assert refreshed.auth_state == {"type": "chatgpt", "email": "operator@example.com"}
    assert refreshed.models == [{"id": "gpt-5.4", "displayName": "GPT-5.4"}]
    assert refreshed.skills == [{"name": "Browser Verify", "description": "Verify UI flows."}]
    assert refreshed.apps == [{"id": "cached_app", "name": "Cached App"}]
    assert refreshed.plugins == [{"name": "cached-plugin", "enabled": True}]
    assert refreshed.threads == [{"id": "thread_live", "status": {"type": "active"}}]
    assert refreshed.loaded_thread_ids == ["thread_live"]
    assert "app/list" in client.calls
    assert "plugin/list" in client.calls


@pytest.mark.asyncio
async def test_refresh_instance_can_target_thread_only_methods(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeRefreshClient()
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        apps=[{"id": "cached_app", "name": "Cached App"}],
        plugins=[{"name": "cached-plugin", "enabled": True}],
    )
    manager.instances[1] = runtime

    refreshed = await manager.refresh_instance(1, methods=manager_module.THREAD_REFRESH_METHODS)

    assert refreshed.threads == [{"id": "thread_live", "status": {"type": "active"}}]
    assert refreshed.loaded_thread_ids == ["thread_live"]
    assert refreshed.apps == [{"id": "cached_app", "name": "Cached App"}]
    assert refreshed.plugins == [{"name": "cached-plugin", "enabled": True}]
    assert client.calls == ["thread/list", "thread/loaded/list"]


@pytest.mark.asyncio
async def test_safe_refresh_call_backs_off_after_timeout(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeTimeoutBackoffClient("thread/list")
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    first = await manager._safe_refresh_call(runtime, "thread/list", {"limit": 30})
    second = await manager._safe_refresh_call(runtime, "thread/list", {"limit": 30})

    assert first is None
    assert second is None
    assert client.calls == ["thread/list"]
    assert "thread/list" in runtime.refresh_backoff_until


@pytest.mark.asyncio
async def test_list_mcp_server_status_backs_off_after_timeout(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeTimeoutBackoffClient("mcpServerStatus/list")
    cached_status = [{"name": "Cached MCP", "status": "ready"}]
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        mcp_server_status=cached_status,
    )
    manager.instances[1] = runtime

    first = await manager.list_mcp_server_status(1, refresh=True)
    second = await manager.list_mcp_server_status(1, refresh=True)

    assert first == cached_status
    assert second == cached_status
    assert client.calls == ["mcpServerStatus/list"]
    assert "mcpServerStatus/list" in runtime.refresh_backoff_until


@pytest.mark.asyncio
async def test_safe_refresh_call_coalesces_concurrent_timeouts(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeSlowTimeoutBackoffClient("thread/list")
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
    )
    manager.instances[1] = runtime

    first, second = await asyncio.gather(
        manager._safe_refresh_call(runtime, "thread/list", {"limit": 30}),
        manager._safe_refresh_call(runtime, "thread/list", {"limit": 30}),
    )

    assert first is None
    assert second is None
    assert client.calls == ["thread/list"]
    assert "thread/list" in runtime.refresh_backoff_until


@pytest.mark.asyncio
async def test_schedule_refresh_instance_coalesces_repeated_requests(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    monkeypatch.setattr(manager_module, "REFRESH_SCHEDULE_DEBOUNCE_SECONDS", 0.01)
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
    )
    manager.instances[1] = runtime

    call_count = 0

    async def fake_refresh(
        instance_id: int,
        methods: tuple[str, ...] | None = None,
    ) -> InstanceRuntime:
        nonlocal call_count
        del methods
        assert instance_id == 1
        call_count += 1
        await asyncio.sleep(0.01)
        return runtime

    manager.refresh_instance = fake_refresh  # type: ignore[method-assign]

    manager._schedule_refresh_instance(1)
    manager._schedule_refresh_instance(1)
    manager._schedule_refresh_instance(1)
    await asyncio.sleep(0.005)
    manager._schedule_refresh_instance(1)
    await asyncio.sleep(0.05)

    assert call_count == 2
    assert runtime.refresh_task is None
    assert runtime.refresh_pending is False


@pytest.mark.asyncio
async def test_schedule_refresh_instance_merges_targeted_method_requests(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    monkeypatch.setattr(manager_module, "REFRESH_SCHEDULE_DEBOUNCE_SECONDS", 0.01)
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
    )
    manager.instances[1] = runtime

    calls: list[tuple[str, ...]] = []

    async def fake_refresh(
        instance_id: int,
        methods: tuple[str, ...] | None = None,
    ) -> InstanceRuntime:
        assert instance_id == 1
        calls.append(methods or ())
        await asyncio.sleep(0.01)
        return runtime

    manager.refresh_instance = fake_refresh  # type: ignore[method-assign]

    manager._schedule_refresh_instance(1, methods=manager_module.THREAD_REFRESH_METHODS)
    manager._schedule_refresh_instance(1, methods=("account/read",))
    await asyncio.sleep(0.05)

    assert calls == [("account/read", "thread/list", "thread/loaded/list")]
    assert runtime.refresh_task is None
    assert runtime.refresh_pending is False
    assert runtime.refresh_pending_methods == set()


@pytest.mark.asyncio
async def test_list_mcp_server_status_coalesces_concurrent_timeouts(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    client = FakeSlowTimeoutBackoffClient("mcpServerStatus/list")
    cached_status = [{"name": "Cached MCP", "status": "ready"}]
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        client=client,  # type: ignore[arg-type]
        connected=True,
        mcp_server_status=cached_status,
    )
    manager.instances[1] = runtime

    first, second = await asyncio.gather(
        manager.list_mcp_server_status(1, refresh=True),
        manager.list_mcp_server_status(1, refresh=True),
    )

    assert first == cached_status
    assert second == cached_status
    assert client.calls == ["mcpServerStatus/list"]
    assert "mcpServerStatus/list" in runtime.refresh_backoff_until


@pytest.mark.asyncio
async def test_close_awaits_cancelled_refresh_tasks(tmp_path) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())
    runtime = InstanceRuntime(
        instance_id=1,
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
    )
    cancelled = asyncio.Event()

    async def fake_refresh_task() -> None:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    runtime.refresh_task = asyncio.create_task(fake_refresh_task())
    manager.instances[1] = runtime

    await asyncio.sleep(0)
    await manager.close()

    assert cancelled.is_set()
    assert runtime.refresh_task is None


@pytest.mark.asyncio
async def test_ensure_workspace_shell_instance_persists_auto_connect_requested(
    tmp_path,
    monkeypatch,
) -> None:
    database = Database(tmp_path / "manager.db")
    await database.initialize()
    manager = RuntimeManager(database, BroadcastHub())

    async def fake_connect_instance(instance_id: int) -> InstanceRuntime:
        runtime = await manager.get(instance_id)
        runtime.connected = True
        runtime.initialized = True
        return runtime

    monkeypatch.setattr(manager, "connect_instance", fake_connect_instance)

    runtime = await manager.ensure_workspace_shell_instance(cwd="C:/workspace", auto_connect=True)
    row = await database.get_instance(runtime.instance_id)

    assert runtime.auto_connect is True
    assert runtime.connected is True
    assert row is not None
    assert bool(row["auto_connect"]) is True
