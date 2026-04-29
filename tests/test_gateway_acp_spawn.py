from __future__ import annotations

from types import SimpleNamespace

import pytest

from openzues.services.gateway_acp_spawn import RuntimeManagerAcpSpawnService


class FakeManager:
    def __init__(self) -> None:
        self.start_thread_calls: list[dict[str, object]] = []
        self.start_turn_calls: list[dict[str, object]] = []

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


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_starts_thread_and_turn() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager, default_model="gpt-5.4-mini")

    payload = await service.spawn(
        {
            "task": "Run this through ACP.",
            "cwd": "C:/workspace",
            "mode": "run",
            "thread": False,
        },
        {},
    )

    assert payload == {
        "status": "accepted",
        "childSessionKey": "agent:main:acp:thread-acp-new",
        "runId": "turn-acp-new",
        "mode": "run",
        "runtimeThreadId": "thread-acp-new",
        "runtimeSessionId": "thread-acp-new",
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
            "text": "Run this through ACP.",
            "cwd": "C:/workspace",
            "model": None,
            "reasoning_effort": None,
            "collaboration_mode": None,
        }
    ]


@pytest.mark.asyncio
async def test_runtime_manager_acp_spawn_resumes_existing_thread() -> None:
    manager = FakeManager()
    service = RuntimeManagerAcpSpawnService(manager)

    payload = await service.spawn(
        {
            "task": "Continue this ACP session.",
            "resumeSessionId": "thread-existing",
            "mode": "session",
            "thread": True,
        },
        {},
    )

    assert payload["status"] == "accepted"
    assert payload["childSessionKey"] == "agent:main:acp:thread-existing"
    assert payload["runId"] == "turn-acp-new"
    assert payload["mode"] == "session"
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls[0]["thread_id"] == "thread-existing"
