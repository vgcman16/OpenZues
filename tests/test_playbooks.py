from __future__ import annotations

from openzues.schemas import PlaybookRun
from openzues.services.playbooks import PlaybookService


class FakeManager:
    def __init__(self) -> None:
        self.exec_calls: list[dict] = []
        self.thread_calls: list[dict] = []
        self.turn_calls: list[dict] = []

    async def exec_command(
        self,
        instance_id: int,
        *,
        command: list[str],
        cwd: str | None,
        timeout_ms: int | None,
        tty: bool,
    ) -> dict:
        self.exec_calls.append(
            {
                "instance_id": instance_id,
                "command": command,
                "cwd": cwd,
                "timeout_ms": timeout_ms,
                "tty": tty,
            }
        )
        return {"exitCode": 0}

    async def start_thread(
        self,
        instance_id: int,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict:
        self.thread_calls.append({"instance_id": instance_id, "model": model, "cwd": cwd})
        return {"threadId": "thread_999"}

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
    ) -> dict:
        self.turn_calls.append({"instance_id": instance_id, "thread_id": thread_id, "text": text})
        return {"turnId": "turn_1"}

    async def start_review(self, instance_id: int, thread_id: str) -> dict:
        return {"review": True, "threadId": thread_id}


async def test_command_playbook_renders_variables() -> None:
    manager = FakeManager()
    service = PlaybookService()
    playbook = {
        "name": "Git branch check",
        "kind": "command",
        "instance_id": 7,
        "template": "git checkout {branch}",
        "cwd": "{cwd}",
        "timeout_ms": 10000,
    }
    run = PlaybookRun(cwd="C:/repo", variables={"branch": "main"})

    result = await service.execute(playbook, run, manager)

    assert result.rendered_template == "git checkout main"
    assert manager.exec_calls[0]["command"] == ["git", "checkout", "main"]
    assert manager.exec_calls[0]["cwd"] == "C:/repo"


async def test_playbook_merges_default_variables_before_runtime_overrides() -> None:
    manager = FakeManager()
    service = PlaybookService()
    playbook = {
        "name": "Branch check",
        "kind": "command",
        "instance_id": 7,
        "template": "git log {branch} --grep {goal}",
        "cwd": "{cwd}",
        "timeout_ms": 10000,
        "default_variables": {"branch": "main", "goal": "baseline"},
    }
    run = PlaybookRun(cwd="C:/repo", variables={"goal": "triage"})

    result = await service.execute(playbook, run, manager)

    assert result.rendered_template == "git log main --grep triage"
    assert manager.exec_calls[0]["command"] == ["git", "log", "main", "--grep", "triage"]


async def test_thread_turn_playbook_creates_thread_then_turn() -> None:
    manager = FakeManager()
    service = PlaybookService()
    playbook = {
        "name": "Open triage session",
        "kind": "thread_turn",
        "instance_id": 3,
        "template": "Investigate {issue}",
        "cwd": "C:/repo",
        "model": "gpt-5.4",
        "reasoning_effort": None,
        "collaboration_mode": None,
    }
    run = PlaybookRun(variables={"issue": "failing CI"})

    result = await service.execute(playbook, run, manager)

    assert result.thread_id == "thread_999"
    assert manager.thread_calls[0]["model"] == "gpt-5.4"
    assert manager.turn_calls[0]["text"] == "Investigate failing CI"
