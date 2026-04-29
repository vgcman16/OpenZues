from __future__ import annotations

from dataclasses import dataclass

import pytest

from openzues.services.gateway_sandbox_spawn import RuntimeManagerSandboxChatSendService


@dataclass(slots=True)
class _RuntimeView:
    id: int
    connected: bool = True
    initialized: bool = True


class _FakeRuntimeManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_views(self) -> list[_RuntimeView]:
        return [_RuntimeView(id=17)]

    async def start_thread(self, instance_id: int, **kwargs: object) -> dict[str, object]:
        self.calls.append(("start_thread", {"instance_id": instance_id, **kwargs}))
        return {"thread": {"id": "thread_sandbox_17"}}

    async def start_turn(self, instance_id: int, **kwargs: object) -> dict[str, object]:
        self.calls.append(("start_turn", {"instance_id": instance_id, **kwargs}))
        return {"turn": {"id": "turn_sandbox_17"}}


@pytest.mark.asyncio
async def test_runtime_manager_sandbox_chat_send_starts_workspace_write_turn() -> None:
    manager = _FakeRuntimeManager()
    service = RuntimeManagerSandboxChatSendService(manager)

    result = await service(
        session_key="agent:main:subagent:child",
        message="Do the sandboxed work.",
        idempotency_key="idem-1",
        thinking=None,
        deliver=None,
        timeout_ms=12_000,
        sandbox="require",
        sandbox_mode="workspace-write",
    )

    assert result == {
        "status": "ok",
        "runId": "turn_sandbox_17",
        "runtime": "codex-app-server",
        "runtimeId": 17,
        "runtimeThreadId": "thread_sandbox_17",
        "runtimeSessionId": "thread_sandbox_17",
        "sandboxed": True,
        "sandboxMode": "workspace-write",
        "sandboxPolicy": {"type": "workspaceWrite"},
    }
    assert manager.calls == [
        (
            "start_thread",
            {
                "instance_id": 17,
                "model": "gpt-5.4",
                "cwd": None,
                "reasoning_effort": None,
                "collaboration_mode": None,
                "sandbox_mode": "workspace-write",
            },
        ),
        (
            "start_turn",
            {
                "instance_id": 17,
                "thread_id": "thread_sandbox_17",
                "text": "Do the sandboxed work.",
                "cwd": None,
                "model": None,
                "reasoning_effort": None,
                "collaboration_mode": None,
                "sandbox_mode": "workspace-write",
            },
        ),
    ]


@pytest.mark.asyncio
async def test_runtime_manager_sandbox_chat_send_preserves_forbidden_when_unavailable() -> None:
    class EmptyRuntimeManager:
        async def list_views(self) -> list[_RuntimeView]:
            return []

    service = RuntimeManagerSandboxChatSendService(EmptyRuntimeManager())

    result = await service(
        session_key="agent:main:subagent:child",
        message="Do the sandboxed work.",
        idempotency_key="idem-1",
        thinking=None,
        deliver=None,
        timeout_ms=None,
        sandbox="require",
        sandbox_mode="workspace-write",
    )

    assert result == {
        "status": "forbidden",
        "error": (
            'sessions_spawn sandbox="require" needs a sandboxed target runtime. '
            'Pick a sandboxed agentId or use sandbox="inherit".'
        ),
    }
