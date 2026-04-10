from __future__ import annotations

import pytest

from openzues.services import codex_rpc
from openzues.services.codex_rpc import CodexAppServerClient, extract_thread_id, split_args


def test_split_args_handles_basic_invocation() -> None:
    assert split_args("app-server --config local") == ["app-server", "--config", "local"]


def test_extract_thread_id_from_nested_turn_payload() -> None:
    payload = {"turn": {"thread": {"id": "thread_123"}}}
    assert extract_thread_id(payload) == "thread_123"


async def _noop_callback(_payload: dict) -> None:
    return None


@pytest.mark.asyncio
async def test_start_thread_uses_enum_sandbox_and_approval_policy(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    recorded: dict[str, object] = {}
    monkeypatch.setattr(codex_rpc.sys, "platform", "linux")

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        recorded["method"] = method
        recorded["params"] = params or {}
        recorded["timeout"] = timeout
        return {"thread": {"id": "thread_123"}}

    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.start_thread(model="gpt-5.4", cwd="C:/workspace")

    assert recorded["method"] == "thread/start"
    assert recorded["params"] == {
        "model": "gpt-5.4",
        "cwd": "C:/workspace",
        "approvalPolicy": "never",
        "sandbox": "workspace-write",
    }
    assert recorded["timeout"] == 60.0


@pytest.mark.asyncio
async def test_start_thread_uses_danger_full_access_on_windows(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    recorded: dict[str, object] = {}

    async def fake_prepare(
        self: CodexAppServerClient,
        *,
        cwd: str | None = None,
        sandbox_mode: str | None = None,
    ) -> None:
        recorded["prepare_cwd"] = cwd
        recorded["prepare_sandbox_mode"] = sandbox_mode

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        recorded["method"] = method
        recorded["params"] = params or {}
        recorded["timeout"] = timeout
        return {"thread": {"id": "thread_123"}}

    monkeypatch.setattr(codex_rpc.sys, "platform", "win32")
    monkeypatch.setattr(CodexAppServerClient, "prepare_windows_sandbox", fake_prepare)
    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.start_thread(model="gpt-5.4", cwd="C:/workspace")

    assert recorded["prepare_cwd"] == "C:/workspace"
    assert recorded["prepare_sandbox_mode"] == "danger-full-access"
    assert recorded["method"] == "thread/start"
    assert recorded["params"] == {
        "model": "gpt-5.4",
        "cwd": "C:/workspace",
        "approvalPolicy": "never",
        "sandbox": "danger-full-access",
    }
    assert recorded["timeout"] == 60.0


@pytest.mark.asyncio
async def test_start_turn_uses_object_sandbox_policy(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    recorded: dict[str, object] = {}
    monkeypatch.setattr(codex_rpc.sys, "platform", "linux")

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        recorded["method"] = method
        recorded["params"] = params or {}
        recorded["timeout"] = timeout
        return {"turn": {"id": "turn_123"}}

    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.start_turn(
        thread_id="thread_123",
        text="Build the moderation queue.",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort="high",
    )

    assert recorded["method"] == "turn/start"
    assert recorded["params"] == {
        "threadId": "thread_123",
        "input": [{"type": "text", "text": "Build the moderation queue."}],
        "cwd": "C:/workspace",
        "model": "gpt-5.4",
        "effort": "high",
        "approvalPolicy": "never",
        "sandboxPolicy": {"type": "workspaceWrite"},
    }
    assert recorded["timeout"] == 60.0


@pytest.mark.asyncio
async def test_prepare_windows_sandbox_uses_elevated_mode(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    calls: list[tuple[str, dict | None]] = []

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        calls.append((method, params))
        if method == "windowsSandbox/setupStart" and params is not None:
            waiter = self._windows_sandbox_waiters[str(params["mode"])]
            if not waiter.done():
                waiter.set_result(None)
        return {}

    monkeypatch.setattr(codex_rpc.sys, "platform", "win32")
    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.prepare_windows_sandbox(cwd="C:/workspace")

    assert calls == [
        ("windowsSandbox/setupStart", {"mode": "elevated", "cwd": "C:/workspace"}),
    ]


@pytest.mark.asyncio
async def test_prepare_windows_sandbox_skips_danger_full_access(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    calls: list[tuple[str, dict | None]] = []

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        calls.append((method, params))
        return {}

    monkeypatch.setattr(codex_rpc.sys, "platform", "win32")
    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.prepare_windows_sandbox(
        cwd="C:/workspace",
        sandbox_mode="danger-full-access",
    )

    assert calls == []


@pytest.mark.asyncio
async def test_start_turn_uses_danger_full_access_on_windows(monkeypatch) -> None:
    client = CodexAppServerClient(
        transport="stdio",
        command="codex",
        args="-a never -s workspace-write app-server",
        websocket_url=None,
        cwd="C:/workspace",
        event_callback=_noop_callback,
        server_request_callback=_noop_callback,
    )
    recorded: dict[str, object] = {}

    async def fake_prepare(
        self: CodexAppServerClient,
        *,
        cwd: str | None = None,
        sandbox_mode: str | None = None,
    ) -> None:
        return None

    async def fake_call(
        self: CodexAppServerClient,
        method: str,
        params: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        recorded["method"] = method
        recorded["params"] = params or {}
        recorded["timeout"] = timeout
        return {"turn": {"id": "turn_123"}}

    monkeypatch.setattr(codex_rpc.sys, "platform", "win32")
    monkeypatch.setattr(CodexAppServerClient, "prepare_windows_sandbox", fake_prepare)
    monkeypatch.setattr(CodexAppServerClient, "call", fake_call)

    await client.start_turn(
        thread_id="thread_123",
        text="Run a shell command.",
        cwd="C:/workspace",
        model="gpt-5.4",
    )

    assert recorded["method"] == "turn/start"
    assert recorded["params"] == {
        "threadId": "thread_123",
        "input": [{"type": "text", "text": "Run a shell command."}],
        "cwd": "C:/workspace",
        "model": "gpt-5.4",
        "approvalPolicy": "never",
        "sandboxPolicy": {"type": "dangerFullAccess"},
    }
