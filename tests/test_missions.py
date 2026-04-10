from __future__ import annotations

import pytest

from openzues.database import Database
from openzues.schemas import MissionCreate
from openzues.services.hub import BroadcastHub
from openzues.services.missions import MissionService


class FakeRuntime:
    def __init__(self) -> None:
        self.name = "Local Codex Desktop"
        self.cwd = "C:/workspace"
        self.connected = False
        self.threads: list[dict] = []
        self.unresolved_requests: list[dict] = []


class FakeManager:
    def __init__(self) -> None:
        self.instances = {7: FakeRuntime()}
        self.thread_calls: list[dict] = []
        self.turn_calls: list[dict] = []

    async def get(self, instance_id: int) -> FakeRuntime:
        runtime = self.instances.get(instance_id)
        if runtime is None:
            raise KeyError(instance_id)
        return runtime

    async def connect_instance(self, instance_id: int) -> FakeRuntime:
        runtime = await self.get(instance_id)
        runtime.connected = True
        return runtime

    async def start_thread(
        self,
        instance_id: int,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict:
        self.thread_calls.append(
            {
                "instance_id": instance_id,
                "model": model,
                "cwd": cwd,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        runtime = await self.get(instance_id)
        runtime.threads = [{"id": "thread_auto", "status": {"type": "idle"}}]
        return {"thread": {"id": "thread_auto"}}

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
        self.turn_calls.append(
            {
                "instance_id": instance_id,
                "thread_id": thread_id,
                "text": text,
                "cwd": cwd,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        runtime = await self.get(instance_id)
        runtime.threads = [{"id": thread_id, "status": {"type": "active"}}]
        return {"turn": {"id": "turn_auto"}}


@pytest.mark.asyncio
async def test_run_now_creates_thread_and_turn(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Autonomous shipper",
            objective="Keep improving the dashboard.",
            instance_id=7,
            cwd="C:/workspace",
            max_turns=2,
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)

    assert manager.thread_calls[0]["model"] == "gpt-5.4"
    assert "Autonomous cycle: 1" in manager.turn_calls[0]["text"]
    assert stored is not None
    assert stored["thread_id"] == "thread_auto"
    assert stored["in_progress"] == 1


@pytest.mark.asyncio
async def test_final_answer_event_creates_checkpoint(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Checkpoint capture",
        objective="Remember final answers.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_memory",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
    )

    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": "thread_memory",
            "params": {
                "threadId": "thread_memory",
                "turnId": "turn_42",
                "item": {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": "Implemented the first milestone and verified the flow.",
                },
            },
        },
    )

    checkpoints = await database.list_mission_checkpoints(mission_id)
    mission = await database.get_mission(mission_id)

    assert checkpoints[0]["summary"].startswith("Implemented the first milestone")
    assert mission is not None
    assert mission["last_checkpoint"].startswith("Implemented the first milestone")


@pytest.mark.asyncio
async def test_server_request_blocks_mission_when_approval_is_required(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Approval aware",
        objective="Wait on risky actions.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_approval",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
    )

    await service.handle_server_request(
        7,
        {
            "requestId": "11",
            "threadId": "thread_approval",
            "method": "approval/request",
            "params": {"message": "Need approval"},
        },
    )

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "blocked"
    assert mission["last_error"] == "Waiting for approval: approval/request"


@pytest.mark.asyncio
async def test_second_mission_waits_behind_in_progress_instance_work(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    active_id = await database.create_mission(
        name="Already running",
        objective="Keep going.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_busy",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
    )
    await database.update_mission(active_id, in_progress=1)

    queued = await service.create(
        MissionCreate(
            name="Queued mission",
            objective="Wait your turn.",
            instance_id=7,
            cwd="C:/workspace",
            start_immediately=False,
        )
    )

    await service.run_now(queued.id)
    mission = await database.get_mission(queued.id)

    assert mission is not None
    assert mission["status"] == "blocked"
    assert mission["last_error"] == "Queued behind mission: Already running"
