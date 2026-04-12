from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest

from openzues.database import Database
from openzues.schemas import MissionCreate, MissionReflexRun
from openzues.services.hub import BroadcastHub
from openzues.services.missions import MissionService


class FakeRuntime:
    def __init__(
        self,
        instance_id: int,
        *,
        transport: str = "desktop",
        cwd: str = "C:/workspace",
        name: str = "Local Codex Desktop",
    ) -> None:
        self.instance_id = instance_id
        self.name = name
        self.transport = transport
        self.cwd = cwd
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
        self.start_turn_error: Exception | None = None

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

    async def ensure_workspace_shell_instance(
        self,
        *,
        cwd: str,
        auto_connect: bool = True,
    ) -> FakeRuntime:
        runtime = self.instances.get(8)
        if runtime is None:
            runtime = FakeRuntime(
                8,
                transport="stdio",
                cwd=cwd,
                name=f"Workspace Shell: {cwd}",
            )
            self.instances[8] = runtime
        else:
            runtime.transport = "stdio"
            runtime.cwd = cwd
        if auto_connect:
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
        if self.start_turn_error is not None:
            raise self.start_turn_error
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
async def test_async_run_now_cleanup_ignores_deleted_mission(caplog, tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        BroadcastHub(),
        poll_interval_seconds=3600,
    )

    async def missing() -> None:
        raise ValueError("Unknown mission 99")

    task = asyncio.create_task(missing())
    with pytest.raises(ValueError):
        await task

    with caplog.at_level(logging.INFO):
        service._handle_run_now_result(99, task)  # type: ignore[arg-type]

    assert "Mission 99 was deleted before the async cycle finished." in caplog.text


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
    assert "Continuity relay:" in manager.turn_calls[0]["text"]
    assert "Mission charter:" in manager.turn_calls[0]["text"]
    assert "Objective gravity:" in manager.turn_calls[0]["text"]
    assert "Safest next handoff:" in manager.turn_calls[0]["text"]
    assert "Hermes tool policy:" in manager.turn_calls[0]["text"]
    assert "Active toolsets:" in manager.turn_calls[0]["text"]
    assert stored is not None
    assert stored["thread_id"] == "thread_auto_7"
    assert stored["in_progress"] == 1
    assert "safe" in stored["toolsets"]
    assert "terminal" in stored["toolsets"]


@pytest.mark.asyncio
async def test_run_now_blocks_when_executor_backend_is_unavailable(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "openzues.services.hermes_runtime_profile.shutil.which",
        lambda _command: None,
    )

    database = Database(tmp_path / "missions.db")
    await database.initialize()
    await database.upsert_hermes_runtime_profile(
        {"preferred_executor": "docker", "preferred_memory_provider": "openzues_recall"}
    )
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Docker-backed shipper",
            objective="Keep improving the backend.",
            instance_id=7,
            cwd="C:/workspace",
            max_turns=2,
            start_immediately=False,
        )
    )

    view = await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)

    assert manager.thread_calls == []
    assert view.status == "blocked"
    assert view.phase == "executor"
    assert stored is not None
    assert stored["status"] == "blocked"
    assert stored["phase"] == "executor"
    assert "Docker Backend" in str(stored["last_error"] or "")


@pytest.mark.asyncio
async def test_run_now_promotes_workspace_shell_to_stdio_lane(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    await database.upsert_hermes_runtime_profile(
        {
            "preferred_executor": "workspace_shell",
            "preferred_memory_provider": "openzues_recall",
        }
    )
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Workspace shell shipper",
            objective="Keep improving the dashboard from the repo shell.",
            instance_id=7,
            cwd="C:/workspace",
            max_turns=2,
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)

    assert manager.thread_calls[0]["instance_id"] == 8
    assert manager.turn_calls[0]["instance_id"] == 8
    assert stored is not None
    assert stored["instance_id"] == 8
    assert stored["thread_id"] == "thread_auto_8"
    assert manager.instances[8].transport == "stdio"
    assert manager.instances[8].connected is True


@pytest.mark.asyncio
async def test_create_reuses_duplicate_inflight_thread_bound_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    first = await service.create(
        MissionCreate(
            name="Harden Checkout",
            objective=(
                "Continue from the latest checkpoint in the mission 'Ship checkout'. "
                "First read the existing handoff in the thread, verify what is already true, "
                "close the biggest gaps, and leave a stronger checkpoint with validation."
            ),
            instance_id=7,
            project_id=None,
            cwd="C:/workspace",
            thread_id="thread_checkout",
            start_immediately=False,
        )
    )

    second = await service.create(
        MissionCreate(
            name="Harden Checkout",
            objective=(
                "Continue from the latest checkpoint in the mission 'Ship checkout'. "
                "First read the existing handoff in the thread, verify what is already true, "
                "close the biggest gaps, and leave a stronger checkpoint with validation."
            ),
            instance_id=7,
            project_id=None,
            cwd="C:/workspace",
            thread_id="thread_checkout",
            start_immediately=False,
        )
    )

    missions = await database.list_missions()

    assert first.id == second.id
    assert len(missions) == 1


@pytest.mark.asyncio
async def test_create_reuses_thread_bound_hardener_even_if_source_mission_shifts(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    first = await service.create(
        MissionCreate(
            name="Harden OpenZues Workspace",
            objective=(
                "Continue from the latest checkpoint in the mission "
                "'OpenClaw Total Parity Program'. First read the existing handoff in the "
                "thread, verify what is already true, close the biggest gaps, and leave a "
                "stronger checkpoint with validation."
            ),
            instance_id=7,
            project_id=None,
            cwd="C:/workspace",
            thread_id="thread_source",
            start_immediately=False,
        )
    )

    second = await service.create(
        MissionCreate(
            name="Harden OpenZues Workspace",
            objective=(
                "Continue from the latest checkpoint in the mission "
                "'Harden OpenZues Workspace'. First read the existing handoff in the thread, "
                "verify what is already true, close the biggest gaps, and leave a stronger "
                "checkpoint with validation."
            ),
            instance_id=7,
            project_id=None,
            cwd="C:/workspace",
            thread_id="thread_source",
            start_immediately=False,
        )
    )

    missions = await database.list_missions()

    assert first.id == second.id
    assert len(missions) == 1


@pytest.mark.asyncio
async def test_create_reuses_inflight_task_blueprint_mission_without_thread_id(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    task_id = await database.create_task_blueprint(
        name="OpenClaw Total Parity Program",
        summary="Keep parity moving.",
        project_id=None,
        instance_id=7,
        cadence_minutes=180,
        enabled=True,
        payload={
            "objective_template": "Ship the next parity slice.",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "collaboration_mode": None,
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )

    first = await service.create(
        MissionCreate(
            name="OpenClaw Total Parity Program",
            objective="Keep iterating until parity is complete.",
            instance_id=7,
            project_id=None,
            task_blueprint_id=task_id,
            cwd="C:/workspace",
            thread_id=None,
            start_immediately=False,
        )
    )

    second = await service.create(
        MissionCreate(
            name="OpenClaw Total Parity Program",
            objective="Keep iterating until parity is complete.",
            instance_id=7,
            project_id=None,
            task_blueprint_id=task_id,
            cwd="C:/workspace",
            thread_id=None,
            start_immediately=False,
        )
    )

    missions = await database.list_missions()

    assert first.id == second.id
    assert len(missions) == 1


@pytest.mark.asyncio
async def test_run_now_includes_auto_skillbook_for_looping_frontend_work(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Frontend polish loop",
            objective=(
                "Keep improving the frontend chat interface until the UI feels cleaner, "
                "more polished, and more autonomous."
            ),
            instance_id=7,
            cwd="C:/workspace",
            max_turns=2,
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)

    prompt = manager.turn_calls[0]["text"]
    assert "Mission skillbook:" in prompt
    assert "Superhuman Skill" in prompt
    assert "Loop Skill" in prompt
    assert "Front-end / UX UI Pro Skill" in prompt


@pytest.mark.asyncio
async def test_run_now_includes_contract_guard_for_setup_bootstrap_work(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Setup parity",
            objective=(
                "Close the onboarding and gateway bootstrap setup seam so QuickStart, API, "
                "CLI, and dashboard flows stay aligned."
            ),
            instance_id=7,
            cwd="C:/workspace",
            max_turns=2,
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)

    prompt = manager.turn_calls[0]["text"]
    assert "Mission skillbook:" in prompt
    assert "Control Plane Contract Guard" in prompt
    assert "tests/test_app.py tests/test_database.py tests/test_manager.py" in prompt


@pytest.mark.asyncio
async def test_pause_clears_in_progress_so_lane_is_released(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Pause me",
            objective="Stop cleanly.",
            instance_id=7,
            cwd="C:/workspace",
            start_immediately=False,
        )
    )
    await database.update_mission(mission.id, in_progress=1, phase="thinking", status="active")

    paused = await service.pause(mission.id)
    stored = await database.get_mission(mission.id)

    assert paused.status == "paused"
    assert paused.in_progress is False
    assert stored is not None
    assert stored["in_progress"] == 0


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
    assert mission["status"] == "completed"
    assert mission["phase"] == "completed"
    assert mission["in_progress"] == 0


@pytest.mark.asyncio
async def test_shared_thread_event_updates_active_mission_owner(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    completed_id = await database.create_mission(
        name="Finished parity slice",
        objective="Leave the validated checkpoint intact.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread_shared",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=3,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    active_id = await database.create_mission(
        name="Shared hardener",
        objective="Continue from the checkpoint on the same thread.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_shared",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        completed_id,
        last_checkpoint="Finished parity slice.",
    )
    await database.update_mission(
        active_id,
        in_progress=1,
    )

    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": "thread_shared",
            "params": {
                "threadId": "thread_shared",
                "turnId": "turn_shared",
                "item": {
                    "type": "agentMessage",
                    "phase": "commentary",
                    "text": "Hardener is validating the checkpoint.",
                },
            },
        },
    )

    completed = await database.get_mission(completed_id)
    active = await database.get_mission(active_id)

    assert completed is not None
    assert active is not None
    assert completed["last_commentary"] is None
    assert active["last_commentary"] == "Hardener is validating the checkpoint."


@pytest.mark.asyncio
async def test_turn_completed_after_final_answer_does_not_launch_another_cycle(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_final", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Stop on handoff",
        objective="Do not relaunch after a final answer.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_final",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
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
            "threadId": "thread_final",
            "params": {
                "threadId": "thread_final",
                "turnId": "turn_final",
                "item": {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": "Completed the requested slice and verified it.",
                },
            },
        },
    )
    await service.handle_event(
        7,
        {
            "method": "turn/completed",
            "threadId": "thread_final",
            "params": {
                "threadId": "thread_final",
                "turnId": "turn_final",
                "turn": {"id": "turn_final"},
            },
        },
    )
    await asyncio.sleep(0)

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "completed"
    assert mission["phase"] == "completed"
    assert mission["turns_completed"] == 1
    assert manager.turn_calls == []


@pytest.mark.asyncio
async def test_turn_completed_without_final_answer_creates_continuity_snapshot(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Relay memory",
        objective="Keep state durable between turns.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_relay",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
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
        phase="reporting",
        in_progress=1,
        command_count=5,
        total_tokens=52200,
        last_commentary="I verified the scheduler path and I am packaging the next handoff.",
    )

    await service.handle_event(
        7,
        {
            "method": "turn/completed",
            "threadId": "thread_relay",
            "params": {
                "threadId": "thread_relay",
                "turnId": "turn_relay",
                "turn": {"id": "turn_relay"},
            },
        },
    )

    checkpoints = await database.list_mission_checkpoints(mission_id)
    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["last_checkpoint"] is None
    assert mission["turns_completed"] == 1
    kinds = {checkpoint["kind"] for checkpoint in checkpoints}
    assert "continuity_auto" in kinds
    assert "restart_safe" in kinds
    restart_safe = next(
        checkpoint for checkpoint in checkpoints if checkpoint["kind"] == "restart_safe"
    )
    assert "Restart-safe recovery packet (turn_boundary)" in restart_safe["summary"]
    continuity = next(
        checkpoint for checkpoint in checkpoints if checkpoint["kind"] == "continuity_auto"
    )
    assert "turn_boundary" in continuity["summary"]
    assert "Next handoff:" in continuity["summary"]


@pytest.mark.asyncio
async def test_turn_completed_normalizes_blank_error_payload(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Normalize mission turn failure",
        objective="Keep failure summaries useful even when Codex sends an empty error.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_error",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(mission_id, in_progress=1, phase="thinking")

    await service.handle_event(
        7,
        {
            "method": "turn/completed",
            "threadId": "thread_error",
            "params": {
                "threadId": "thread_error",
                "turnId": "turn_error",
                "turn": {"id": "turn_error", "error": RuntimeError("")},
            },
        },
    )

    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "failed"
    assert mission["phase"] == "failed"
    assert mission["last_error"] == (
        "RuntimeError: Codex reported turn failure without detailed error output."
    )
    assert checkpoints[0]["kind"] == "error"
    assert checkpoints[0]["summary"] == mission["last_error"]


@pytest.mark.asyncio
async def test_restart_safe_snapshot_uses_recent_thread_trace(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Crash journal",
        objective="Keep enough evidence to recover after a sudden outage.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_journal",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
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
        in_progress=1,
        phase="executing",
        current_command='powershell.exe -Command "pytest -q"',
        total_tokens=53200,
        command_count=6,
        last_commentary="I am verifying the current slice before I checkpoint it.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_journal",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "command": 'powershell.exe -Command "pytest -q"',
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_journal",
        method="item/commandExecution/outputDelta",
        payload={"delta": "12 passed, 0 failed"},
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    appended = await service._maybe_append_restart_safe_snapshot(
        mission_id,
        mission,
        force=True,
        reason="test_recovery",
    )
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert appended is True
    assert checkpoints[0]["kind"] == "restart_safe"
    assert "Recent live trace:" in checkpoints[0]["summary"]
    assert "Command started:" in checkpoints[0]["summary"]
    assert "Output: 12 passed, 0 failed" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_restart_safe_snapshot_prefers_green_evidence_over_stale_blocker_commentary(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Parity hardener",
        objective="Verify the branch, clear the blocker, and checkpoint it.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_green",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        mission_id,
        in_progress=1,
        phase="thinking",
        total_tokens=42000,
        command_count=4,
        last_commentary=(
            "The repo is not fully green yet: one route-selection regression is still live "
            "in the current worktree."
        ),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_green",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "command": 'powershell.exe -Command "pytest tests/test_app.py -q"',
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_green",
        method="item/commandExecution/outputDelta",
        payload={"delta": "1 passed, 67 deselected in 2.03s"},
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    appended = await service._maybe_append_restart_safe_snapshot(
        mission_id,
        mission,
        force=True,
        reason="evidence_test",
    )
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert appended is True
    assert "Current focus: Recent verification looks green:" in checkpoints[0]["summary"]
    assert "Earlier blocker language may already be stale" in checkpoints[0]["summary"]


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
async def test_get_view_surfaces_live_thread_telemetry(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_live", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Live telemetry",
        objective="Show whether the thread is still moving.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_live",
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
    await database.update_mission(mission_id, in_progress=1)
    await database.append_event(
        instance_id=7,
        thread_id="thread_live",
        method="item/started",
        payload={"item": {"type": "commandExecution", "command": "Get-Date"}},
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_live",
        method="item/commandExecution/outputDelta",
        payload={"delta": "Saturday"},
    )

    view = await service.get_view(mission_id)

    assert view.live_telemetry.streaming is True
    assert view.live_telemetry.thread_status == "active"
    assert view.live_telemetry.recent_event_count_30s >= 2
    assert view.live_telemetry.recent_output_delta_count_30s >= 1
    assert view.live_telemetry.token_rollup_pending is True


@pytest.mark.asyncio
async def test_get_view_softens_stale_blocker_commentary(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Commentary drift",
        objective="Keep the operator story aligned with evidence.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_commentary",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        mission_id,
        in_progress=1,
        phase="thinking",
        command_count=8,
        last_commentary=(
            "The repo is not fully green yet: one route-selection regression is still live "
            "in the current worktree."
        ),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_commentary",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "command": 'powershell.exe -Command "Get-Content src/openzues/services/setup.py"',
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_commentary",
        method="item/commandExecution/outputDelta",
        payload={"delta": "async def inspect(self) -> SetupStatusView:"},
    )

    view = await service.get_view(mission_id)

    assert view.commentary_summary is not None
    assert "not been reconfirmed" in view.commentary_summary
    assert view.last_commentary != view.commentary_summary


@pytest.mark.asyncio
async def test_get_view_surfaces_adaptive_delegation_brief(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw parity hardener",
        objective=(
            "Verify the current parity slice, design the next gateway seam, plan the work, "
            "implement the bounded change, and audit the result."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_agents",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        mission_id,
        turns_started=2,
        command_count=5,
        in_progress=1,
        last_commentary="Checking whether the current parity seam is complete before broadening.",
    )

    view = await service.get_view(mission_id)

    assert view.delegation_brief.enabled is True
    assert (
        view.delegation_brief.mode
        == "conductor_architect_planner_coder_auditor"
    )
    assert view.delegation_brief.activation == "ready_now"
    role_names = [role.name for role in view.delegation_brief.roles]
    assert role_names == ["Architect", "Planner", "Coder", "Auditor"]


@pytest.mark.asyncio
async def test_build_turn_prompt_emits_agent_stack_roles(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Design and ship gateway doctor",
        objective=(
            "Brainstorm a cleaner gateway doctor surface, design the seam, plan the slice, "
            "build it, and audit the result."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_prompt",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "Built-in agent stack:" in prompt
    assert "The main lane is the conductor" in prompt
    assert "Brainstormer:" in prompt
    assert "Architect:" in prompt
    assert "Planner:" in prompt
    assert "Coder:" in prompt
    assert "Auditor:" in prompt


@pytest.mark.asyncio
async def test_build_turn_prompt_emits_contract_seam_guardrails(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Gateway dashboard contract seam",
        objective=(
            "Finish the gateway doctor dashboard contract by aligning the schema, API payload, "
            "CLI view, and shared fixtures before checkpointing."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_contract",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "Contract seam guard:" in prompt
    assert "shared test fixtures" in prompt
    assert "tests/test_app.py" in prompt


@pytest.mark.asyncio
async def test_build_turn_prompt_includes_mempalace_protocol_for_project_memory(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    project_id = await database.create_project(path=str(tmp_path), label="Memory Workspace")
    await database.create_integration(
        name="MemPalace",
        kind="mempalace",
        project_id=project_id,
        base_url="python -m mempalace.mcp_server",
        auth_scheme="none",
        vault_secret_id=None,
        secret_label=None,
        secret_value=None,
        notes="Use the MCP tools for recall before answering historical questions.",
        enabled=True,
    )
    mission_id = await database.create_mission(
        name="Ship with memory",
        objective="Land the next slice without losing prior project decisions.",
        status="active",
        instance_id=7,
        project_id=project_id,
        thread_id="thread_memory_protocol",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "MemPalace memory protocol:" in prompt
    assert "query MemPalace first instead of guessing" in prompt
    assert "write it back through MemPalace" in prompt


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
    manager.instances[7].unresolved_requests = [
        {
            "request_id": "11",
            "thread_id": "thread_approval",
            "method": "approval/request",
        }
    ]

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
    assert mission["in_progress"] == 0
    assert mission["last_error"] == "Queued behind mission: Already running"


@pytest.mark.asyncio
async def test_stale_queued_blocker_does_not_deadlock_next_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    stale_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until parity is complete.",
        status="blocked",
        instance_id=7,
        project_id=None,
        thread_id=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort="high",
        collaboration_mode=None,
        max_turns=8,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
    )
    await database.update_mission(
        stale_id,
        phase="queued",
        in_progress=1,
        last_error="Queued behind mission: OpenClaw Total Parity Program",
    )

    follower = await service.create(
        MissionCreate(
            name="OpenClaw Total Parity Program",
            objective="Keep iterating until parity is complete.",
            instance_id=7,
            cwd="C:/workspace",
            start_immediately=False,
        )
    )

    await service.run_now(follower.id)
    mission = await database.get_mission(follower.id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["in_progress"] == 1
    assert mission["last_error"] is None
    assert manager.thread_calls[0]["instance_id"] == 7


@pytest.mark.asyncio
async def test_run_now_normalizes_blank_start_turn_error(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.start_turn_error = RuntimeError("")
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Recover useful lane errors",
            objective="Fail with a useful summary when the runtime returns a blank error.",
            instance_id=7,
            cwd="C:/workspace",
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)
    checkpoints = await database.list_mission_checkpoints(mission.id)

    assert stored is not None
    assert stored["status"] == "failed"
    assert stored["phase"] == "failed"
    assert stored["last_error"] == (
        "RuntimeError: Codex runtime failed to start the turn without a detailed error."
    )
    assert checkpoints[0]["kind"] == "error"
    assert checkpoints[0]["summary"] == stored["last_error"]


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
async def test_reconcile_uses_scope_realign_reflex_for_drifting_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_scope", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Moderation queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_scope",
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
        phase="executing",
        current_command=(
            'powershell.exe -Command "Get-Content '
            'src\\\\openzues\\\\web\\\\static\\\\app.css"'
        ),
        last_commentary="Polishing gradients and chat bubble spacing in the dashboard shell.",
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["last_reflex_kind"] == "scope_realign"
    assert "Restate the charter" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "reflex_auto"


@pytest.mark.asyncio
async def test_reconcile_creates_background_continuity_snapshot_for_hot_live_turn(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_live_hot", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Hot live mission",
        objective="Keep building while preserving thread memory.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_live_hot",
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
        in_progress=1,
        phase="executing",
        command_count=8,
        total_tokens=340000,
        current_command='powershell.exe -Command "Get-Content src\\\\openzues\\\\app.py"',
        last_commentary="I am validating the existing scheduler path before editing it.",
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["in_progress"] == 1
    assert mission["last_checkpoint"] is None
    assert manager.turn_calls == []
    assert checkpoints[0]["kind"] == "continuity_auto"
    assert "live_orbit" in checkpoints[0]["summary"]
    assert "Current command:" in checkpoints[0]["summary"]

    await service._reconcile_mission(mission_id)
    repeated_checkpoints = await database.list_mission_checkpoints(mission_id)

    assert len([item for item in repeated_checkpoints if item["kind"] == "continuity_auto"]) == 1


@pytest.mark.asyncio
async def test_reconcile_auto_yields_stale_hot_mission_and_releases_queue(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_hot", "status": {"type": "notLoaded"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    hot_id = await database.create_mission(
        name="Hot lane owner",
        objective="Keep shipping until a checkpoint lands.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_hot",
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
        hot_id,
        in_progress=1,
        phase="thinking",
        total_tokens=770089,
        command_count=4,
        last_activity_at=(datetime.now(UTC) - timedelta(minutes=11)).isoformat(),
    )

    queued_id = await database.create_mission(
        name="Queued follower",
        objective="Pick up once the lane is free.",
        status="blocked",
        instance_id=7,
        project_id=None,
        thread_id=None,
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
        queued_id,
        phase="queued",
        last_error="Queued behind mission: Hot lane owner",
    )

    await service._reconcile_mission(hot_id)
    hot = await database.get_mission(hot_id)
    hot_checkpoints = await database.list_mission_checkpoints(hot_id)

    assert hot is not None
    assert hot["status"] == "paused"
    assert hot["in_progress"] == 0
    assert hot["last_checkpoint"].startswith(
        "Auto-yielded the lane after a long run of 770,089 tokens"
    )
    assert hot_checkpoints[0]["kind"] == "queue_yield"

    await service._reconcile_mission(queued_id)
    queued = await database.get_mission(queued_id)

    assert queued is not None
    assert queued["status"] == "active"
    assert queued["in_progress"] == 1
    assert queued["last_error"] is None
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["text"].startswith(
        "You are running inside an OpenZues autonomous mission."
    )


@pytest.mark.asyncio
async def test_yield_for_queue_is_idempotent_once_checkpoint_exists(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Yield once",
        objective="Cool the lane once.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_once",
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
        total_tokens=64000,
        command_count=7,
        last_activity_at=(datetime.now(UTC) - timedelta(minutes=9)).isoformat(),
    )

    await service.yield_for_queue(mission_id)
    await service.yield_for_queue(mission_id)

    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "paused"
    assert len([item for item in checkpoints if item["kind"] == "queue_yield"]) == 1


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
async def test_reconcile_rebinds_stale_thread_before_failing_again(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = []
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Stale thread mission",
        objective="Keep shipping after a stale thread disappears.",
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_stale",
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
        thread_id="thread_stale",
        turn_id="turn_stale",
        kind="final_answer",
        summary="The last stable milestone mostly landed before the thread vanished.",
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_stale",
        turn_id="turn_stale",
        kind="restart_safe",
        summary="Restart-safe recovery packet (turn_boundary) after 9 commands and 52,200 tokens.",
    )
    await database.update_mission(
        mission_id,
        last_error="thread not found: thread_stale",
        last_checkpoint="The last stable milestone mostly landed before the thread vanished.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_stale",
        method="item/commandExecution/outputDelta",
        payload={"delta": "Recovered 3 route bindings before the thread vanished."},
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "stale-thread recovery" in manager.turn_calls[0]["text"]
    assert "Crash-safe relay packets:" in manager.turn_calls[0]["text"]
    assert "Recent persisted live trace:" in manager.turn_calls[0]["text"]
    assert "Recovered 3 route bindings before the thread vanished." in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "thread_rebind"
    assert "thread_stale" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_live_event_clears_stale_thread_failure_state(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Live thread proof",
        objective="Recover status when a real event arrives on the thread.",
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_live",
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
        last_error="thread not found: thread_live",
        phase="failed",
        in_progress=0,
    )

    await service.handle_event(
        7,
        {
            "method": "item/started",
            "threadId": "thread_live",
            "params": {
                "threadId": "thread_live",
                "turnId": "turn_live",
                "item": {
                    "type": "commandExecution",
                    "command": 'powershell.exe -Command "Get-Date"',
                },
            },
        },
    )

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["last_error"] is None
    assert mission["phase"] == "executing"
    assert mission["in_progress"] == 1


@pytest.mark.asyncio
async def test_live_event_clears_approval_block_after_autopilot_resume(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Approval resume",
        objective="Recover immediately after a safe approval is resolved.",
        status="blocked",
        instance_id=7,
        project_id=None,
        thread_id="thread_approval_live",
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
        phase="approval",
        last_error="Waiting for approval: item/commandExecution/requestApproval",
        in_progress=0,
    )

    await service.handle_event(
        7,
        {
            "method": "item/started",
            "threadId": "thread_approval_live",
            "params": {
                "threadId": "thread_approval_live",
                "turnId": "turn_after_approval",
                "item": {
                    "type": "commandExecution",
                    "command": 'powershell.exe -Command "rg -n foo src"',
                },
            },
        },
    )

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["last_error"] is None
    assert mission["phase"] == "executing"
    assert mission["in_progress"] == 1


@pytest.mark.asyncio
async def test_reconcile_clears_stale_thread_error_when_runtime_thread_is_alive(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_live", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Healed by runtime",
        objective="Trust a live runtime thread over a stale failure marker.",
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_live",
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
        last_error="thread not found: thread_live",
        phase="failed",
        in_progress=0,
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "active"
    assert mission["last_error"] is None
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1


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
    assert "Continuity relay packet:" in manager.turn_calls[0]["text"]
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
