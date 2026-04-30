from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from openzues.services.gateway_acp_spawn import RuntimeManagerAcpSpawnService


def _acp_thread_context() -> dict[str, object]:
    return {
        "requesterChannel": "slack",
        "requesterAccountId": "default",
        "requesterTo": "channel:C123",
        "requesterThreadId": "1710000000.000400",
    }


class FakeManager:
    def __init__(self) -> None:
        self.start_thread_calls: list[dict[str, object]] = []
        self.start_turn_calls: list[dict[str, object]] = []
        self.interrupt_turn_calls: list[dict[str, object]] = []

    async def list_views(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(id=7, connected=True, initialized=True),
        ]

    async def start_thread(
        self,
        instance_id: int,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, object]:
        self.start_thread_calls.append(
            {
                "instance_id": instance_id,
                "model": model,
                "cwd": cwd,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        return {"thread": {"id": "thread-acp-new"}}

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
    ) -> dict[str, object]:
        self.start_turn_calls.append(
            {
                "instance_id": instance_id,
                "thread_id": thread_id,
                "text": text,
                "cwd": cwd,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        return {"turn": {"id": "turn-acp-new"}}

    async def interrupt_turn(self, instance_id: int, thread_id: str) -> dict[str, object]:
        self.interrupt_turn_calls.append(
            {
                "instance_id": instance_id,
                "thread_id": thread_id,
            }
        )
        return {"ok": True}


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_starts_thread_and_turn() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager, default_model="gpt-5.4-mini")

    payload = await service.spawn(
        {
            "task": "Run this through ACP.",
            "agentId": "Codex",
            "cwd": "C:/workspace",
            "mode": "run",
            "thread": False,
        },
        {},
    )

    assert payload == {
        "status": "accepted",
        "childSessionKey": "agent:codex:acp:thread-acp-new",
        "runId": "turn-acp-new",
        "mode": "run",
        "runtimeThreadId": "thread-acp-new",
        "runtimeSessionId": "thread-acp-new",
        "note": (
            "initial ACP task queued in isolated session; "
            "follow-ups continue in the bound thread."
        ),
    }
    assert manager.start_thread_calls == [
        {
            "instance_id": 7,
            "model": "gpt-5.4-mini",
            "cwd": "C:/workspace",
            "reasoning_effort": None,
            "collaboration_mode": None,
        }
    ]
    assert manager.start_turn_calls == [
        {
            "instance_id": 7,
            "thread_id": "thread-acp-new",
            "text": "[Working directory: C:/workspace]\n\nRun this through ACP.",
            "cwd": "C:/workspace",
            "model": None,
            "reasoning_effort": None,
            "collaboration_mode": None,
        }
    ]


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_prefixes_cwd_like_openclaw() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)
    cwd = f"{Path.home()}\\openclaw-test"

    await service.spawn(
        {
            "task": "Run this through ACP.",
            "agentId": "codex",
            "cwd": cwd,
        },
        {},
    )

    assert manager.start_turn_calls[0]["text"] == (
        "[Working directory: ~\\openclaw-test]\n\nRun this through ACP."
    )


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_returns_openclaw_accepted_note_for_run_mode() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Run this through ACP.",
            "agentId": "codex",
            "mode": "run",
        },
        {},
    )

    assert payload["note"] == (
        "initial ACP task queued in isolated session; "
        "follow-ups continue in the bound thread."
    )


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_rejects_thread_session_without_channel_context() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Keep this ACP session alive in a provider thread.",
            "agentId": "codex",
            "mode": "session",
            "thread": True,
        },
        {},
    )

    assert payload == {
        "status": "error",
        "errorCode": "thread_binding_invalid",
        "error": "thread=true for ACP sessions requires a channel context.",
    }
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_returns_openclaw_accepted_note_for_session_mode() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Continue this ACP session.",
            "agentId": "codex",
            "resumeSessionId": "thread-existing",
            "mode": "session",
            "thread": True,
        },
        _acp_thread_context(),
    )

    assert payload["note"] == (
        "thread-bound ACP session stays active after this task; "
        "continue in-thread for follow-ups."
    )


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_binds_line_current_conversation() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Investigate flaky tests.",
            "agentId": "codex",
            "mode": "session",
            "thread": True,
        },
        {
            "requesterSessionKey": (
                "agent:main:line:direct:U1234567890abcdef1234567890abcdef"
            ),
            "requesterChannel": "line",
            "requesterAccountId": "default",
            "requesterTo": "line:user:U1234567890abcdef1234567890abcdef",
        },
    )

    assert payload["status"] == "accepted"
    assert payload["threadBinding"] == {
        "channel": "line",
        "accountId": "default",
        "to": "line:user:U1234567890abcdef1234567890abcdef",
    }
    assert payload["completionDelivery"] == {
        "mode": "thread",
        "channel": "line",
        "accountId": "default",
        "to": "line:user:U1234567890abcdef1234567890abcdef",
    }
    session_binding = payload["sessionBinding"]
    assert isinstance(session_binding, dict)
    assert session_binding["targetSessionKey"] == "agent:codex:acp:thread-acp-new"
    assert session_binding["targetKind"] == "session"
    assert session_binding["conversation"] == {
        "channel": "line",
        "accountId": "default",
        "conversationId": "U1234567890abcdef1234567890abcdef",
    }
    assert session_binding["status"] == "active"
    assert isinstance(session_binding["boundAt"], int)
    assert session_binding["metadata"]["placement"] == "current"
    assert session_binding["metadata"]["agentId"] == "codex"


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_resumes_existing_thread() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Continue this ACP session.",
            "agentId": "codex",
            "resumeSessionId": "thread-existing",
            "mode": "session",
            "thread": True,
        },
        _acp_thread_context(),
    )

    assert payload["status"] == "accepted"
    assert payload["childSessionKey"] == "agent:codex:acp:thread-existing"
    assert payload["runId"] == "turn-acp-new"
    assert payload["mode"] == "session"
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls[0]["thread_id"] == "thread-existing"


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_rejects_session_mode_without_thread() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Keep this ACP session alive.",
            "mode": "session",
            "thread": False,
        },
        {},
    )

    assert payload == {
        "status": "error",
        "errorCode": "thread_required",
        "error": (
            'mode="session" requires thread=true so the ACP session can stay '
            "bound to a thread."
        ),
    }
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_requires_target_agent_id() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Run this through ACP.",
            "mode": "run",
            "thread": False,
        },
        {},
    )

    assert payload == {
        "status": "error",
        "errorCode": "target_agent_required",
        "error": (
            "ACP target agent is not configured. Pass `agentId` in `sessions_spawn` "
            "or set `acp.defaultAgent` in config."
        ),
    }
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_runtime_manager_acp_cleanup_interrupts_active_thread() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    cancel_payload = await service.cancel_session(
        session_key="agent:main:acp:thread-cleanup",
        runtime_thread_id="thread-cleanup",
        runtime_session_id="thread-cleanup",
        reason="session-delete",
    )
    close_payload = await service.close_session(
        session_key="agent:main:acp:thread-cleanup",
        runtime_thread_id="thread-cleanup",
        runtime_session_id="thread-cleanup",
        reason="session-delete",
        discard_persistent_state=True,
        require_acp_session=False,
        allow_backend_unavailable=True,
    )

    assert cancel_payload == {"status": "ok", "cancelled": True}
    assert close_payload == {"status": "ok", "closed": True}
    assert manager.interrupt_turn_calls == [
        {
            "instance_id": 7,
            "thread_id": "thread-cleanup",
        }
    ]
