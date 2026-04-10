from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openzues.database import Database
from openzues.schemas import MissionCreate, MissionReflexRun
from openzues.services.hub import BroadcastHub
from openzues.services.missions import MissionService


class FakeRuntime:
    def __init__(self, instance_id: int) -> None:
        self.instance_id = instance_id
        self.name = "Local Codex Desktop"
        self.cwd = "C:/workspace"
        self.connected = False
        self.threads: list[dict] = []
        self.unresolved_requests: list[dict] = []
        self.models: list[dict] = []
        self.last_event_at: str | None = None


class FakeManager:
    def __init__(self) -> None:
        self.instances = {7: FakeRuntime(7)}
        self.thread_calls: list[dict] = []
        self.turn_calls: list[dict] = []
        self.fail_connect_for: set[int] = set()

    async def get(self, instance_id: int) -> FakeRuntime:
        runtime = self.instances.get(instance_id)
        if runtime is None:
            raise KeyError(instance_id)
        return runtime

    async def connect_instance(self, instance_id: int) -> FakeRuntime:
        if instance_id in self.fail_connect_for:
            raise RuntimeError(f"offline lane {instance_id}")
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
        thread_id = f"thread_auto_{instance_id}"
        runtime.threads = [{"id": thread_id, "status": {"type": "idle"}}]
        return {"thread": {"id": thread_id}}

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
        return {"turn": {"id": f"turn_auto_{instance_id}"}}


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
    assert stored["thread_id"] == "thread_auto_7"
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
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
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
async def test_token_and_commentary_events_update_mission_telemetry(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Telemetry",
        objective="Track runtime signals.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_metrics",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )

    await service.handle_event(
        7,
        {
            "method": "thread/tokenUsage/updated",
            "threadId": "thread_metrics",
            "params": {
                "threadId": "thread_metrics",
                "tokenUsage": {
                    "total": {
                        "totalTokens": 1200,
                        "outputTokens": 220,
                        "reasoningOutputTokens": 90,
                    }
                },
            },
        },
    )
    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": "thread_metrics",
            "params": {
                "threadId": "thread_metrics",
                "turnId": "turn_metrics",
                "item": {
                    "type": "agentMessage",
                    "phase": "commentary",
                    "text": "I am verifying the main workflow now.",
                },
            },
        },
    )

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["total_tokens"] == 1200
    assert mission["output_tokens"] == 220
    assert mission["reasoning_tokens"] == 90
    assert mission["last_commentary"] == "I am verifying the main workflow now."


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
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
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
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
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


@pytest.mark.asyncio
async def test_fire_reflex_injects_turn_into_existing_thread(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_reflex", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Reflex target",
        objective="Keep the run moving.",
        status="paused",
        instance_id=7,
        project_id=None,
        thread_id="thread_reflex",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )

    await service.fire_reflex(
        mission_id,
        MissionReflexRun(
            kind="resume_handoff",
            title="Resume from handoff",
            prompt="Pick up from the checkpoint and land the next smallest verified slice.",
        ),
    )

    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["in_progress"] == 1
    assert manager.turn_calls[0]["thread_id"] == "thread_reflex"
    assert "next smallest verified slice" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "reflex"
    assert checkpoints[0]["summary"] == "Resume from handoff"


@pytest.mark.asyncio
async def test_reconcile_uses_auto_reflex_for_orbiting_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_auto_reflex", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Orbiting mission",
        objective="Keep shipping.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_auto_reflex",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        mission_id,
        command_count=12,
        turns_completed=1,
        last_checkpoint=None,
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["last_reflex_kind"] == "checkpoint_now"
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_reflex"
    assert "Stop broadening the task." in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "reflex_auto"


@pytest.mark.asyncio
async def test_reconcile_auto_recovers_failed_mission_with_checkpoint(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_recover", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recoverable mission",
        objective="Keep moving.",
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_recover",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        mission_id,
        failure_count=1,
        last_checkpoint="The previous milestone mostly landed.",
        last_error="tests failed",
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["last_reflex_kind"] == "recovery_triangle"
    assert "recovery is still within budget" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "recovery"


@pytest.mark.asyncio
async def test_reconcile_fails_over_offline_mission_to_idle_instance(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].name = "Primary Lane"
    manager.instances[7].connected = False
    manager.instances[7].models = [{"id": "gpt-5.4"}]
    manager.fail_connect_for.add(7)
    manager.instances[8] = FakeRuntime(8)
    manager.instances[8].name = "Recovery Lane"
    manager.instances[8].connected = True
    manager.instances[8].models = [{"id": "gpt-5.4"}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Lane transplant",
        objective="Keep building even if one lane drops offline.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_primary",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_primary",
        turn_id="turn_primary",
        kind="final_answer",
        summary="Verified the last stable slice before the lane dropped.",
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["instance_id"] == 8
    assert mission["thread_id"] == "thread_auto_8"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert manager.thread_calls[0]["instance_id"] == 8
    assert manager.turn_calls[0]["instance_id"] == 8
    assert (
        "taking over an OpenZues autonomous mission after lane failover"
        in manager.turn_calls[0]["text"]
    )
    assert "Recent checkpoint trail:" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "failover"
    assert "Primary Lane" in checkpoints[0]["summary"]
    assert "Recovery Lane" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_recent_reflex_cooldown_prevents_immediate_repeat(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_cooldown", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Cooling mission",
        objective="Keep moving.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_cooldown",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        mission_id,
        command_count=12,
        turns_completed=1,
        last_reflex_kind="checkpoint_now",
        last_reflex_at=datetime.now(UTC).isoformat(),
    )

    await service._reconcile_mission(mission_id)

    assert manager.turn_calls[0]["text"].startswith(
        "You are running inside an OpenZues autonomous mission."
    )
