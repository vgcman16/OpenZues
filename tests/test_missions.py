from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from openzues.database import Database
from openzues.schemas import (
    MissionCreate,
    MissionReflexRun,
    SwarmArtifactReferenceView,
    SwarmEnvelopeView,
    SwarmImplementationPlanView,
    SwarmIntegrationReportView,
    SwarmProductSpecView,
    SwarmWorkingSetView,
)
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.followups import mission_row_matches_payload
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.hub import BroadcastHub
from openzues.services.missions import (
    OPENCLAW_PARITY_CHECKPOINT_LEDGER,
    MissionService,
    _execution_stall_threshold_seconds,
    _uses_fast_parity_reporting_orbit_cutoff,
)
from openzues.services.swarm import build_initial_swarm_runtime


@pytest.fixture(autouse=True)
def _reset_external_skill_catalogs() -> None:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    yield
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)


def _write_fake_hermes_skill(
    repo_root: Path,
    *,
    relative_dir: str,
    name: str,
    description: str,
    category: str,
    tags: list[str],
    requires_toolsets: list[str] | None = None,
) -> Path:
    skill_dir = repo_root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "metadata:",
        "  hermes:",
        f"    category: {category}",
        f"    tags: [{', '.join(tags)}]",
    ]
    if requires_toolsets:
        lines.append(f"    requires_toolsets: [{', '.join(requires_toolsets)}]")
    lines.extend(
        [
            "---",
            "",
            f"# {name}",
            "",
            "## When to Use",
            "Use this Hermes skill when the workflow needs it.",
            "",
            "## Procedure",
            "1. Open the skill.",
            "2. Follow the workflow.",
        ]
    )
    skill_path.write_text("\n".join(lines), encoding="utf-8")
    return skill_path


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
        self.interrupt_calls: list[dict] = []
        self.fail_connect_for: set[int] = set()
        self.start_thread_error: Exception | None = None
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
        if self.start_thread_error is not None:
            raise self.start_thread_error
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

    async def interrupt_turn(self, instance_id: int, thread_id: str) -> dict[str, Any]:
        self.interrupt_calls.append(
            {
                "instance_id": instance_id,
                "thread_id": thread_id,
            }
        )
        runtime = await self.get(instance_id)
        runtime.threads = [{"id": thread_id, "status": {"type": "idle"}}]
        return {"ok": "true"}


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
async def test_run_now_uses_swarm_product_manager_prompt(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Swarm shipper",
            objective="Build the native swarm mission flow.",
            instance_id=7,
            cwd="C:/workspace",
            swarm_enabled=True,
            start_immediately=False,
        )
    )

    await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)

    assert stored is not None
    assert stored["swarm"] is not None
    assert stored["swarm"]["active_role"] == "product_manager"
    assert "delegation" not in stored["toolsets"]
    assert "Product Manager inside the OpenZues Swarm Constitution" in manager.turn_calls[0]["text"]
    assert "Return one raw JSON object only." in manager.turn_calls[0]["text"]


@pytest.mark.asyncio
async def test_create_reuses_saved_thread_from_session_key(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    await database.create_mission(
        name="Earlier parity run",
        objective="Ship the previous slice.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread_saved",
        session_key="launch:mode:workspace_affinity:task:7:operator:1",
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
        toolsets=["debugging"],
    )

    mission = await service.create(
        MissionCreate(
            name="OpenClaw parity continuation",
            objective="Land the next bounded parity slice.",
            instance_id=7,
            cwd="C:/workspace",
            session_key="launch:mode:workspace_affinity:task:7:operator:1",
            max_turns=2,
            start_immediately=False,
        )
    )
    stored = await database.get_mission(mission.id)

    assert stored is not None
    assert stored["thread_id"] == "thread_saved"
    assert stored["session_key"] == "launch:mode:workspace_affinity:task:7:operator:1"


@pytest.mark.asyncio
async def test_create_blocks_thread_reuse_when_conversation_target_changes(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    await database.create_mission(
        name="Earlier parity run",
        objective="Ship the previous slice.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread_saved",
        session_key="launch:mode:workspace_affinity:task:7:operator:1:channel:slack",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
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
        toolsets=["debugging"],
    )

    mission = await service.create(
        MissionCreate(
            name="OpenClaw parity continuation",
            objective="Land the next bounded parity slice.",
            instance_id=7,
            cwd="C:/workspace",
            session_key="launch:mode:workspace_affinity:task:7:operator:1:channel:slack",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "qa-room",
            },
            max_turns=2,
            start_immediately=False,
        )
    )
    stored = await database.get_mission(mission.id)

    assert stored is not None
    assert stored["thread_id"] is None
    assert stored["conversation_target"]["peer_id"] == "qa-room"


def test_followup_payload_matching_uses_session_key_when_thread_changes() -> None:
    payload = MissionCreate(
        name="Recover OpenClaw parity",
        objective=(
            "Continue the mission 'OpenClaw parity' from its existing thread. Start by "
            "reading the last checkpoint and failure context, fix the blocker, verify the "
            "path forward, and leave a cleaner checkpoint when done."
        ),
        instance_id=7,
        project_id=1,
        cwd="C:/workspace",
        thread_id="thread_new",
        session_key="launch:mode:workspace_affinity:task:7:project:1:operator:1",
        start_immediately=False,
    )

    assert mission_row_matches_payload(
        {
            "name": payload.name,
            "objective": payload.objective,
            "instance_id": 7,
            "project_id": 1,
            "thread_id": "thread_old",
            "session_key": "launch:mode:workspace_affinity:task:7:project:1:operator:1",
            "cwd": "C:/workspace",
        },
        payload,
        cwd="C:/workspace",
    )


def test_followup_payload_matching_prefers_conversation_target_before_session_key() -> None:
    payload = MissionCreate(
        name="Recover OpenClaw parity",
        objective=(
            "Continue the mission 'OpenClaw parity' from its existing thread. Start by "
            "reading the last checkpoint and failure context, fix the blocker, verify the "
            "path forward, and leave a cleaner checkpoint when done."
        ),
        instance_id=7,
        project_id=1,
        cwd="C:/workspace",
        thread_id="thread_new",
        session_key="launch:mode:workspace_affinity:task:7:project:1:operator:1",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        start_immediately=False,
    )

    assert mission_row_matches_payload(
        {
            "name": payload.name,
            "objective": payload.objective,
            "instance_id": 7,
            "project_id": 1,
            "thread_id": "thread_old",
            "session_key": "launch:mode:workspace_affinity:task:7:project:1:operator:1",
            "conversation_target": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            "cwd": "C:/workspace",
        },
        payload,
        cwd="C:/workspace",
    )


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
async def test_swarm_final_answer_advances_to_architect(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission = await service.create(
        MissionCreate(
            name="Swarm advancement",
            objective="Advance the structured swarm bus.",
            instance_id=7,
            cwd="C:/workspace",
            swarm_enabled=True,
            start_immediately=False,
        )
    )
    await service.run_now(mission.id)
    stored = await database.get_mission(mission.id)
    assert stored is not None

    payload = SwarmEnvelopeView(
        mission_id=mission.id,
        run_id=stored["swarm"]["run_id"],
        stage_index=1,
        from_role="product_manager",
        to_role="conductor",
        kind="product_spec",
        summary="Product framing is complete.",
        working_set=SwarmWorkingSetView(
            product_spec=SwarmProductSpecView(
                problem="Advance the structured swarm bus.",
                user_outcomes=[
                    "The conductor should route PM output to the Architect.",
                ],
                scope_in=["Structured bus handoffs"],
                scope_out=["Free chat"],
            )
        ),
    ).model_dump_json()

    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": stored["thread_id"],
            "params": {
                "threadId": stored["thread_id"],
                "turnId": "turn_pm",
                "item": {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": payload,
                },
            },
        },
    )

    mission_row = await database.get_mission(mission.id)
    checkpoints = await database.list_mission_checkpoints(mission.id)

    assert mission_row is not None
    assert mission_row["status"] == "active"
    assert mission_row["phase"] == "ready"
    assert mission_row["swarm"]["active_role"] == "architect"
    assert mission_row["swarm"]["stage_index"] == 2
    assert checkpoints[0]["kind"] == "swarm_payload"

    await service.run_now(mission.id)
    assert "Architect inside the OpenZues Swarm Constitution" in manager.turn_calls[-1]["text"]


@pytest.mark.asyncio
async def test_swarm_integration_payload_completes_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Swarm finish",
        objective="Finish the native swarm mission.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_swarm_finish",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode="swarm_constitution",
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
    swarm_runtime = build_initial_swarm_runtime(
        objective="Finish the native swarm mission.",
        mission_id=mission_id,
    ).model_copy(
        update={
            "stage_index": 8,
            "active_role": "integration_tester",
            "completed_roles": [
                "product_manager",
                "architect",
                "test_engineer",
                "backend_engineer",
                "frontend_engineer",
                "security_auditor",
                "refactorer",
            ],
            "pending_roles": ["integration_tester"],
        }
    )
    await database.update_mission(mission_id, swarm=swarm_runtime.model_dump(mode="json"))

    payload = SwarmEnvelopeView(
        mission_id=mission_id,
        run_id=swarm_runtime.run_id or "swarm-finish",
        stage_index=8,
        from_role="integration_tester",
        to_role="conductor",
        kind="integration_report",
        summary="Integration verification is green.",
        working_set=SwarmWorkingSetView(
            product_spec=SwarmProductSpecView(problem="Finish the native swarm mission."),
            integration_report=SwarmIntegrationReportView(
                headline="Integration verification is green.",
                verified_checks=["pytest tests/test_swarm.py -q"],
                failing_checks=[],
                blockers=[],
                recommended_action="Complete the mission.",
            ),
        ),
    ).model_dump_json()

    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": "thread_swarm_finish",
            "params": {
                "threadId": "thread_swarm_finish",
                "turnId": "turn_swarm_finish",
                "item": {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": payload,
                },
            },
        },
    )

    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "completed"
    assert mission["phase"] == "completed"
    assert mission["last_checkpoint"].startswith("Swarm pipeline completed.")
    assert checkpoints[0]["kind"] == "swarm_final"


@pytest.mark.asyncio
async def test_swarm_conflict_blocks_mission(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Swarm conflict",
        objective="Catch backend and frontend overlap.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_swarm_conflict",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode="swarm_constitution",
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
    swarm_runtime = build_initial_swarm_runtime(
        objective="Catch backend and frontend overlap.",
        mission_id=mission_id,
    ).model_copy(
        update={
            "stage_index": 5,
            "active_role": "frontend_engineer",
            "completed_roles": [
                "product_manager",
                "architect",
                "test_engineer",
                "backend_engineer",
            ],
            "pending_roles": [
                "frontend_engineer",
                "security_auditor",
                "refactorer",
                "integration_tester",
            ],
            "working_set": SwarmWorkingSetView(
                product_spec=SwarmProductSpecView(problem="Catch backend and frontend overlap."),
                backend_plan=SwarmImplementationPlanView(
                    headline="Backend touched the dashboard bridge.",
                    role="backend_engineer",
                    file_targets=[
                        SwarmArtifactReferenceView(
                            kind="file",
                            label="Shared app seam",
                            path="src/openzues/app.py",
                        )
                    ],
                ),
            ),
        }
    )
    await database.update_mission(mission_id, swarm=swarm_runtime.model_dump(mode="json"))

    payload = SwarmEnvelopeView(
        mission_id=mission_id,
        run_id=swarm_runtime.run_id or "swarm-conflict",
        stage_index=5,
        from_role="frontend_engineer",
        to_role="conductor",
        kind="frontend_plan",
        summary="Frontend wants the same shared app seam.",
        working_set=SwarmWorkingSetView(
            product_spec=SwarmProductSpecView(problem="Catch backend and frontend overlap."),
            backend_plan=swarm_runtime.working_set.backend_plan,
            frontend_plan=SwarmImplementationPlanView(
                headline="Frontend also touched the shared app seam.",
                role="frontend_engineer",
                file_targets=[
                    SwarmArtifactReferenceView(
                        kind="file",
                        label="Shared app seam",
                        path="src/openzues/app.py",
                    )
                ],
            ),
        ),
    ).model_dump_json()

    await service.handle_event(
        7,
        {
            "method": "item/completed",
            "threadId": "thread_swarm_conflict",
            "params": {
                "threadId": "thread_swarm_conflict",
                "turnId": "turn_swarm_conflict",
                "item": {
                    "type": "agentMessage",
                    "phase": "final_answer",
                    "text": payload,
                },
            },
        },
    )

    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["status"] == "blocked"
    assert mission["phase"] == "swarm_conflict"
    assert mission["last_error"].startswith("Swarm conflict:")
    assert mission["swarm"]["conflict"]["summary"].startswith("Backend and frontend")
    assert checkpoints[0]["kind"] == "swarm_conflict"


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
    assert view.delegation_brief.mode == "conductor_architect_planner_coder_auditor"
    assert view.delegation_brief.activation == "ready_now"
    role_names = [role.name for role in view.delegation_brief.roles]
    assert role_names == ["Architect", "Planner", "Coder", "Auditor"]


@pytest.mark.asyncio
async def test_get_view_surfaces_runtime_tool_evidence(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw parity watcher",
        objective="Verify the parity seam without pretending every tool already ran.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_tool_evidence",
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
        toolsets=["debugging", "delegation", "browser", "memory", "session_search"],
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_tool_evidence",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "command": (
                    'powershell.exe -Command "Get-Content src/openzues/services/setup.py"'
                ),
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_tool_evidence",
        method="item/completed",
        payload={
            "item": {
                "type": "collabAgentToolCall",
                "tool": "spawnAgent",
                "prompt": "Architect role. Map the next parity seam before edits.",
            }
        },
    )
    for index in range(260):
        await database.append_event(
            instance_id=7,
            thread_id="thread_tool_evidence",
            method="item/commandExecution/outputDelta",
            payload={
                "itemId": f"filler_{index}",
                "delta": f"filler output {index}",
            },
        )

    view = await service.get_view(mission_id)

    assert view.tool_evidence.proof_ready is False
    assert view.tool_evidence.observed_toolsets == ["debugging", "delegation"]
    assert view.tool_evidence.unproven_toolsets == ["memory", "session_search"]
    assert "Explicit proof is still missing" in view.tool_evidence.summary
    evidence_by_toolset = {item.toolset: item for item in view.tool_evidence.items}
    assert evidence_by_toolset["debugging"].status == "observed"
    assert evidence_by_toolset["delegation"].status == "observed"
    assert evidence_by_toolset["memory"].status == "unproven"


@pytest.mark.asyncio
async def test_get_view_ignores_inspection_output_as_memory_tool_use(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Memory proof guard",
        objective="Verify the parity seam without overclaiming tool use.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_memory_guard",
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
        toolsets=["debugging", "memory"],
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_memory_guard",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "id": "call_memory_guard",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'src/openzues/services/gateway_capability.py"'
                ),
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_memory_guard",
        method="item/commandExecution/outputDelta",
        payload={
            "itemId": "call_memory_guard",
            "delta": (
                'memory_summary = "MemPalace is not staged through a tracked integration yet."'
            ),
        },
    )

    view = await service.get_view(mission_id)

    assert view.tool_evidence.observed_toolsets == ["debugging"]
    assert view.tool_evidence.unproven_toolsets == ["memory"]
    evidence_by_toolset = {item.toolset: item for item in view.tool_evidence.items}
    assert evidence_by_toolset["memory"].status == "unproven"


@pytest.mark.asyncio
async def test_get_view_counts_openzues_recall_as_memory_and_session_search(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recall proof guard",
        objective="Recover parity context through durable recall before the next slice.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_recall_guard",
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
        toolsets=["memory", "session_search"],
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_recall_guard",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "id": "call_recall_guard",
                "command": 'powershell.exe -Command "openzues recall parity --limit 3"',
            }
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_recall_guard",
        method="item/commandExecution/outputDelta",
        payload={
            "itemId": "call_recall_guard",
            "delta": "openzues recall returned the latest parity checkpoint trail.",
        },
    )

    view = await service.get_view(mission_id)

    assert view.tool_evidence.observed_toolsets == ["memory", "session_search"]
    assert view.tool_evidence.unproven_toolsets == []


@pytest.mark.asyncio
async def test_get_view_normalizes_openclaw_parity_toolsets(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective=(
            "Use C:/openclaw-main as the source of truth and C:/workspace as the target product. "
            "Resume from the verified checkpoint in "
            "`docs/openclaw-parity-checkpoint-2026-04-10.md` instead of rebuilding the full "
            "source inventory. Choose the next bounded missing seam named there, implement it end "
            "to end in production quality, run the focused verification for that seam, and leave "
            "a checkpoint that names what was completed, what remains, and the next best slice."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_tools",
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
        allow_failover=True,
        toolsets=["debugging", "delegation", "browser", "vision", "memory", "session_search"],
    )

    view = await service.get_view(mission_id)

    assert view.toolsets == ["debugging", "delegation", "memory", "session_search"]
    assert view.tool_evidence.expected_toolsets == [
        "debugging",
        "delegation",
        "memory",
        "session_search",
    ]
    assert "browser" not in view.toolsets
    assert "vision" not in view.toolsets


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
async def test_build_turn_prompt_emits_parity_tool_evidence_contract(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_contract",
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
        toolsets=["debugging", "delegation", "browser"],
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "OpenClaw parity proof contract:" in prompt
    assert "Tool evidence:" in prompt
    assert "Current tool proof gaps:" in prompt
    assert "declared tool families were actually exercised" in prompt
    assert "- memory: used MemPalace or Recall to recover prior context" in prompt
    assert (
        "- session_search: queried prior mission/checkpoint history before restating context"
        in prompt
    )
    assert "OpenClaw parity execution discipline:" in prompt
    assert "restart_safe" in prompt
    assert "continuity_auto" in prompt
    assert "Do not search the ledger for raw control-plane packet kinds" in prompt
    assert "Do not widen a ledger probe into a keyword cloud" in prompt
    assert ".openzues" in prompt
    assert ".codex" in prompt


@pytest.mark.asyncio
async def test_build_turn_prompt_compacts_parity_objective_and_skips_auto_local_skillbooks(
    tmp_path: Path,
) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    skill_path = _write_fake_hermes_skill(
        hermes_root,
        relative_dir="skills/gateway/openclaw-gateway-parity",
        name="OpenClaw Gateway Parity",
        description="Focused guidance for OpenClaw gateway parity seams.",
        category="gateway",
        tags=["openclaw", "parity", "gateway", "routing"],
        requires_toolsets=["debugging"],
    )
    configure_hermes_skill_catalog(hermes_root)

    database = Database(tmp_path / "missions.db")
    await database.initialize()
    project_root = tmp_path / "workspace"
    project_root.mkdir()
    (project_root / ".venv" / "Scripts").mkdir(parents=True)
    (project_root / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")
    await database.create_project(path=str(project_root), label="OpenZues Workspace")
    await database.create_skill_pin(
        project_id=1,
        name="Browser Verify",
        prompt_hint=(
            "Use this after meaningful UI changes or dashboard flows that need visual "
            "confirmation."
        ),
        source="agent-browser",
        enabled=True,
    )
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective=(
            "Use C:/openclaw-main as the source of truth and C:/workspace as the target product. "
            "First inventory the OpenClaw surface area across gateway, onboarding, CLI, channels, "
            "routing, voice, canvas, nodes, skills, browser, packaging, and companion apps. "
            "Then choose the highest-leverage missing parity slice in OpenZues, implement it end "
            "to end in production quality, run the relevant verification, and leave a checkpoint "
            "that names what was completed, what remains, and the next best slice.\n\n"
            "Continuous loop contract:\n"
            "- Keep chaining until parity is genuinely complete.\n\n"
            "Project skillbook:\n"
            f"- OpenClaw Gateway Parity: Read the linked Hermes SKILL.md first. Source: "
            f"{skill_path}.\n\n"
            "Hermes tool policy:\n"
            "- Active toolsets: debugging, delegation, browser.\n\n"
            "Hermes runtime posture prefers OpenZues Recall for memory and Docker Backend "
            "for execution."
        ),
        status="active",
        instance_id=7,
        project_id=1,
        thread_id="thread_parity_compaction",
        cwd=str(project_root),
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
        toolsets=["debugging", "delegation", "browser"],
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "docs/openclaw-parity-checkpoint-2026-04-10.md" in prompt
    assert r".\.venv\Scripts\python.exe -m openzues.cli recall --json" in prompt
    assert "First inventory the OpenClaw surface area" not in prompt
    assert "Project skillbook:" not in prompt
    assert str(skill_path) not in prompt
    assert "OpenClaw Gateway Parity" not in prompt
    assert "open that SKILL.md before you execute the related workflow" not in prompt
    assert "Browser Verify" in prompt


@pytest.mark.asyncio
async def test_build_turn_prompt_clamps_parity_inventory_drift_after_queue_yield(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_resume",
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
        toolsets=["debugging", "delegation"],
    )
    await database.update_mission(
        mission_id,
        command_count=59,
        last_checkpoint=(
            "Auto-yielded the lane after a long run of 38,347 tokens and 59 commands without "
            "a durable checkpoint."
        ),
        last_commentary=(
            "I am rebuilding context from the target workspace and mapping the highest-leverage "
            "missing parity seam again."
        ),
    )

    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = await service._build_turn_prompt(mission)

    assert "This mission already drifted into inventory churn or queue-yield." in prompt
    assert "Do not reopen global inventory on this turn." in prompt
    assert "Avoid root-level `Get-ChildItem`" in prompt


@pytest.mark.asyncio
async def test_build_queue_yield_checkpoint_includes_parity_resume_rule(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_queue",
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
        total_tokens=38347,
        command_count=59,
    )
    mission = await database.get_mission(mission_id)
    assert mission is not None

    summary = await service._build_queue_yield_checkpoint(mission_id, mission)

    assert "Resume rule: treat the source inventory as complete" in summary
    assert "Resume target: choose one missing parity seam" in summary


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
async def test_reconcile_uses_auto_reflex_for_in_progress_reporting_orbit(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_reporting_orbit", "status": {"type": "idle"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".venv" / "Scripts").mkdir(parents=True)
    (workspace / ".venv" / "Scripts" / "python.exe").write_text("", encoding="utf-8")

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_reporting_orbit",
        cwd=str(workspace),
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
        phase="reporting",
        command_count=12,
        turns_completed=1,
        current_command=None,
        last_checkpoint=None,
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["last_reflex_kind"] == "checkpoint_now"
    assert manager.turn_calls[0]["thread_id"] == "thread_reporting_orbit"
    assert (
        r".\.venv\Scripts\python.exe -m openzues.cli recall --json"
        in manager.turn_calls[0]["text"]
    )
    assert "Do not guess alternate Recall executable names" in manager.turn_calls[0]["text"]
    assert "If Recall succeeds, do not summarize it in commentary." in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "reflex_auto"


def test_parity_fast_reporting_orbit_cutoff_triggers_after_recall_anchor() -> None:
    mission = {
        "objective": "Keep iterating until OpenClaw parity is complete.",
        "current_command": None,
    }

    assert _uses_fast_parity_reporting_orbit_cutoff(
        mission,
        commentary_text="Recall is available and I'm narrowing that to the exact seam.",
        anchor_command=r".\.venv\Scripts\python.exe -m openzues.cli recall --json",
    )


def test_execution_stall_threshold_is_tighter_for_inspection_commands() -> None:
    assert _execution_stall_threshold_seconds("git status --short") == 60
    assert _execution_stall_threshold_seconds('powershell.exe -Command "pytest -q"') == 8 * 60


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
            'powershell.exe -Command "Get-Content src\\\\openzues\\\\web\\\\static\\\\app.css"'
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
async def test_reconcile_rebinds_commentary_orbiting_thread(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_orbit", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Orbiting parity mission",
        objective="Land the OpenClaw parity checkpoint instead of looping in commentary.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_orbit",
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
        phase="reporting",
        command_count=12,
        turns_completed=1,
        total_tokens=222631,
        last_turn_id="turn_orbit",
        current_command=None,
        last_commentary=(
            "I am still sequencing delegation and deciding whether this turn should stop."
        ),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_orbit",
        method="turn/started",
        payload={"threadId": "thread_orbit", "turnId": "turn_orbit"},
    )
    for delta in (
        "I",
        "am",
        "still",
        "deciding",
        "whether",
        "this",
        "turn",
        "should",
        "stop",
        "and",
        "land",
        "now",
    ):
        await database.append_event(
            instance_id=7,
            thread_id="thread_orbit",
            method="item/agentMessage/delta",
            payload={
                "threadId": "thread_orbit",
                "turnId": "turn_orbit",
                "itemId": "msg_orbit",
                "delta": delta,
            },
        )

    now = datetime.now(UTC) - timedelta(minutes=4)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = now + timedelta(seconds=offset * 20)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_orbit"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "commentary-orbit recovery" in manager.turn_calls[0]["text"]
    assert "Do not continue the abandoned narration" in manager.turn_calls[0]["text"]
    assert "emitted item must be a tool call or the checkpoint itself" in manager.turn_calls[0][
        "text"
    ]
    assert checkpoints[0]["kind"] == "orbit_rebind"
    assert "thread_orbit" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_reconcile_rebinds_low_signal_parity_orbit_early(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_parity_orbit", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw parity orbit mission",
        objective=(
            "Use the verified OpenClaw parity checkpoint in "
            "`docs/openclaw-parity-checkpoint-2026-04-10.md` and land the next bounded seam."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_orbit",
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
        phase="reporting",
        command_count=10,
        turns_completed=1,
        total_tokens=180000,
        last_turn_id="turn_parity_orbit",
        current_command=None,
        last_commentary="Waiting for the next checkpoint handoff.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_parity_orbit",
        method="turn/started",
        payload={"threadId": "thread_parity_orbit", "turnId": "turn_parity_orbit"},
    )
    for delta in (
        "Rebinding",
        " on",
        " the",
        " checkpoint",
        " seam now;",
        " checking for Recall/session-search first",
    ):
        await database.append_event(
            instance_id=7,
            thread_id="thread_parity_orbit",
            method="item/agentMessage/delta",
            payload={
                "threadId": "thread_parity_orbit",
                "turnId": "turn_parity_orbit",
                "itemId": "msg_parity_orbit",
                "delta": delta,
            },
        )

    now = datetime.now(UTC) - timedelta(minutes=2)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = now + timedelta(seconds=offset * 10)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_parity_orbit"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "commentary-orbit recovery" in manager.turn_calls[0]["text"]
    assert "emitted item must be a tool call or the checkpoint itself" in manager.turn_calls[0][
        "text"
    ]
    assert (
        "your next move must be a tool call or the checkpoint itself"
        in manager.turn_calls[0]["text"]
    )
    assert checkpoints[0]["kind"] == "orbit_rebind"
    assert "parity fast-cutoff guardrail" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_reconcile_rebinds_post_inspection_parity_orbit_early(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [
        {"id": "thread_parity_inspection_orbit", "status": {"type": "active"}}
    ]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw parity post-inspection orbit mission",
        objective=(
            "Use the verified OpenClaw parity checkpoint in "
            "`docs/openclaw-parity-checkpoint-2026-04-10.md` and land the next bounded seam."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_inspection_orbit",
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
        phase="reporting",
        command_count=10,
        turns_completed=1,
        total_tokens=180000,
        last_turn_id="turn_parity_inspection_orbit",
        current_command=None,
        last_commentary="Seam locked; now naming the next concrete move.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_parity_inspection_orbit",
        method="turn/started",
        payload={
            "threadId": "thread_parity_inspection_orbit",
            "turnId": "turn_parity_inspection_orbit",
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_parity_inspection_orbit",
        method="item/started",
        payload={
            "item": {
                "type": "commandExecution",
                "id": "call_parity_ledger",
                "command": (
                    "powershell.exe -Command "
                    "\"Get-Content -Raw docs/openclaw-parity-checkpoint-2026-04-10.md\""
                ),
            },
            "threadId": "thread_parity_inspection_orbit",
            "turnId": "turn_parity_inspection_orbit",
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_parity_inspection_orbit",
        method="item/commandExecution/outputDelta",
        payload={
            "threadId": "thread_parity_inspection_orbit",
            "turnId": "turn_parity_inspection_orbit",
            "itemId": "call_parity_ledger",
            "delta": "# OpenClaw Parity Checkpoint",
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_parity_inspection_orbit",
        method="item/completed",
        payload={
            "item": {
                "type": "commandExecution",
                "id": "call_parity_ledger",
                "command": (
                    "powershell.exe -Command "
                    "\"Get-Content -Raw docs/openclaw-parity-checkpoint-2026-04-10.md\""
                ),
            },
            "threadId": "thread_parity_inspection_orbit",
            "turnId": "turn_parity_inspection_orbit",
        },
    )
    for delta in (
        "Seam",
        " is",
        " explicit",
        " and",
        " the",
        " next",
        " operator",
        " move",
        " is",
        " being",
        " worded",
    ):
        await database.append_event(
            instance_id=7,
            thread_id="thread_parity_inspection_orbit",
            method="item/agentMessage/delta",
            payload={
                "threadId": "thread_parity_inspection_orbit",
                "turnId": "turn_parity_inspection_orbit",
                "itemId": "msg_parity_inspection_orbit",
                "delta": delta,
            },
        )

    now = datetime.now(UTC) - timedelta(minutes=2)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = now + timedelta(seconds=offset * 8)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_parity_inspection_orbit"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "commentary-orbit recovery" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "orbit_rebind"
    assert "parity fast-cutoff guardrail" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_reconcile_rebinds_stalled_executing_thread(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_exec_stall", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Stalled execution parity mission",
        objective="Land the OpenClaw parity checkpoint instead of hanging on a stale read.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_stall",
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
        command_count=18,
        turns_completed=2,
        total_tokens=310000,
        last_turn_id="turn_exec_stall",
        current_command=(
            'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
        ),
        last_commentary="I am still reading the parity checkpoint before deciding what to land.",
        last_activity_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stall",
        method="turn/started",
        payload={"threadId": "thread_exec_stall", "turnId": "turn_exec_stall"},
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stall",
        method="item/started",
        payload={
            "threadId": "thread_exec_stall",
            "turnId": "turn_exec_stall",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_stall",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'docs/openclaw-parity-checkpoint-2026-04-10.md"'
                ),
            },
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stall",
        method="item/commandExecution/outputDelta",
        payload={
            "threadId": "thread_exec_stall",
            "turnId": "turn_exec_stall",
            "itemId": "call_exec_stall",
            "delta": "OpenClaw parity checkpoint header",
        },
    )

    now = datetime.now(UTC) - timedelta(minutes=5)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = now + timedelta(seconds=offset * 20)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_exec_stall"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "stalled-execution recovery" in manager.turn_calls[0]["text"]
    assert "Do not keep rereading the same files" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "execution_rebind"
    assert "thread_exec_stall" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_reconcile_rebinds_long_running_inspection_execution(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [
        {"id": "thread_exec_inspection", "status": {"type": "active"}}
    ]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Long-running inspection parity mission",
        objective=(
            "Use the verified OpenClaw parity checkpoint in "
            "`docs/openclaw-parity-checkpoint-2026-04-10.md` and land the next bounded seam."
        ),
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_inspection",
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
        command_count=21,
        turns_completed=3,
        total_tokens=355000,
        last_turn_id="turn_exec_inspection",
        current_command=(
            'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
        ),
        last_commentary="I am still reviewing the parity ledger before choosing the next seam.",
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_inspection",
        method="turn/started",
        payload={
            "threadId": "thread_exec_inspection",
            "turnId": "turn_exec_inspection",
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_inspection",
        method="item/started",
        payload={
            "threadId": "thread_exec_inspection",
            "turnId": "turn_exec_inspection",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_inspection",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'docs/openclaw-parity-checkpoint-2026-04-10.md"'
                ),
            },
        },
    )
    for index in range(8):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_inspection",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_inspection",
                "turnId": "turn_exec_inspection",
                "itemId": "call_exec_inspection",
                "delta": f"Parity ledger line {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(minutes=5)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=offset * 35)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_exec_inspection"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "stalled-execution recovery" in manager.turn_calls[0]["text"]
    assert "inspection orbit disguised as execution" in manager.turn_calls[0]["text"]
    assert "emitted item must be a tool call or the checkpoint itself" in manager.turn_calls[0][
        "text"
    ]
    assert "stalled parity lane already spent its explanation budget" in manager.turn_calls[0][
        "text"
    ]
    assert checkpoints[0]["kind"] == "execution_rebind"
    assert "open-ended inspection output" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_detect_executing_stall_from_output_only_window(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Output-only inspection parity mission",
        objective="Catch parity-ledger inspection loops even after the start event falls out.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_output_only",
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
        command_count=24,
        turns_completed=3,
        total_tokens=389000,
        last_turn_id="turn_exec_output_only",
        current_command=(
            'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=30)).isoformat(),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_output_only",
        method="item/started",
        payload={
            "threadId": "thread_exec_output_only",
            "turnId": "turn_exec_output_only",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_output_only",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'docs/openclaw-parity-checkpoint-2026-04-10.md"'
                ),
            },
        },
    )
    for index in range(260):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_output_only",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_output_only",
                "turnId": "turn_exec_output_only",
                "itemId": "call_exec_output_only",
                "delta": f"Parity ledger line {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(minutes=9)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=2 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="notLoaded",
        last_activity_seconds=30,
    )

    assert signal is not None
    assert signal["mode"] == "long_running_inspection"
    assert signal["elapsed_lower_bound"] is True
    assert signal["output_delta_count"] >= 200
    assert signal["elapsed_seconds"] >= 180


@pytest.mark.asyncio
async def test_detect_executing_stall_cuts_repeated_parity_ledger_read_after_recovery(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recovered parity ledger replay mission",
        objective="Do not reread the full parity ledger after recovery already named the seam.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_repeated_ledger",
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
        command_count=22,
        turns_completed=3,
        total_tokens=401000,
        last_turn_id="turn_exec_repeated_ledger",
        current_command=(
            'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_before_recovery",
        turn_id="turn_before_recovery",
        kind="execution_rebind",
        summary="Mission rebound from a prior stalled parity-ledger read.",
    )
    for offset in range(3):
        await database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id="thread_after_recovery",
            turn_id=f"turn_after_recovery_{offset}",
            kind="restart_safe",
            summary=f"Restart-safe packet {offset + 1} after the recovery rebind.",
        )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_repeated_ledger",
        method="item/started",
        payload={
            "threadId": "thread_exec_repeated_ledger",
            "turnId": "turn_exec_repeated_ledger",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_repeated_ledger",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'docs/openclaw-parity-checkpoint-2026-04-10.md"'
                ),
            },
        },
    )
    for index in range(4):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_repeated_ledger",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_repeated_ledger",
                "turnId": "turn_exec_repeated_ledger",
                "itemId": "call_exec_repeated_ledger",
                "delta": f"Parity ledger line {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(seconds=50)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=15 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="active",
        last_activity_seconds=10,
    )

    assert signal is not None
    assert signal["mode"] == "repeated_parity_ledger_read"
    assert signal["output_delta_count"] == 4
    assert signal["elapsed_seconds"] >= 30


@pytest.mark.asyncio
async def test_detect_executing_stall_cuts_repeated_parity_select_string_after_recovery(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recovered parity ledger sweep mission",
        objective="Do not keep sweeping the parity ledger after recovery already named the seam.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_ledger_sweep",
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
        command_count=23,
        turns_completed=4,
        total_tokens=402500,
        last_turn_id="turn_exec_ledger_sweep",
        current_command=(
            "powershell.exe -Command "
            "\"$path='docs/openclaw-parity-checkpoint-2026-04-10.md'; "
            "Select-String -Path $path -Pattern 'Next best slice|Operator handoff' -Context 2,4\""
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_before_recovery",
        turn_id="turn_before_recovery",
        kind="execution_rebind",
        summary="Mission rebound from a prior stalled parity-ledger inspection.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_ledger_sweep",
        method="item/started",
        payload={
            "threadId": "thread_exec_ledger_sweep",
            "turnId": "turn_exec_ledger_sweep",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_ledger_sweep",
                "command": (
                    "powershell.exe -Command "
                    "\"$path='docs/openclaw-parity-checkpoint-2026-04-10.md'; "
                    "Select-String -Path $path -Pattern 'Next best slice|Operator handoff' "
                    "-Context 2,4\""
                ),
            },
        },
    )
    for index in range(4):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_ledger_sweep",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_ledger_sweep",
                "turnId": "turn_exec_ledger_sweep",
                "itemId": "call_exec_ledger_sweep",
                "delta": f"Parity ledger sweep line {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(seconds=55)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=15 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="active",
        last_activity_seconds=10,
    )

    assert signal is not None
    assert signal["mode"] == "repeated_parity_ledger_read"
    assert signal["output_delta_count"] == 4
    assert signal["elapsed_seconds"] >= 30


@pytest.mark.asyncio
async def test_detect_executing_stall_cuts_parity_ledger_keyword_sweep_after_recovery(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recovered parity ledger keyword sweep mission",
        objective="Do not widen parity recovery into a generic ledger keyword sweep.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_keyword_sweep",
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
        command_count=26,
        turns_completed=4,
        total_tokens=410200,
        last_turn_id="turn_exec_keyword_sweep",
        current_command=(
            "powershell.exe -Command "
            "\"Select-String -Path 'docs/openclaw-parity-checkpoint-2026-04-10.md' "
            "-Pattern 'continuity_auto|remaining|Next|OpenClaw|parity|resume|seam' "
            "-Context 1,2\""
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_before_recovery",
        turn_id="turn_before_recovery",
        kind="orbit_rebind",
        summary=(
            "Mission rebound from commentary orbit and should not reopen generic "
            "ledger sweeps."
        ),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_keyword_sweep",
        method="item/started",
        payload={
            "threadId": "thread_exec_keyword_sweep",
            "turnId": "turn_exec_keyword_sweep",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_keyword_sweep",
                "command": (
                    "powershell.exe -Command "
                    "\"Select-String -Path 'docs/openclaw-parity-checkpoint-2026-04-10.md' "
                    "-Pattern 'continuity_auto|remaining|Next|OpenClaw|parity|resume|seam' "
                    "-Context 1,2\""
                ),
            },
        },
    )
    for index in range(4):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_keyword_sweep",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_keyword_sweep",
                "turnId": "turn_exec_keyword_sweep",
                "itemId": "call_exec_keyword_sweep",
                "delta": f"Keyword sweep line {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(seconds=35)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=8 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="active",
        last_activity_seconds=10,
    )

    assert signal is not None
    assert signal["mode"] == "parity_ledger_keyword_sweep"
    assert signal["output_delta_count"] == 4
    assert signal["elapsed_seconds"] >= 20


@pytest.mark.asyncio
async def test_detect_executing_stall_cuts_parity_context_sweep_after_recovery(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recovered parity context sweep mission",
        objective="Do not rediscover parity context by sweeping session artifacts after recovery.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_context_sweep",
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
        command_count=24,
        turns_completed=4,
        total_tokens=403100,
        last_turn_id="turn_exec_context_sweep",
        current_command=(
            "powershell.exe -Command "
            "\"Get-ChildItem -Force -Name .,.openzues,.zues,docs,.codex,logs,artifacts,"
            "sessions,session,mission-control 2>$null\""
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_before_recovery",
        turn_id="turn_before_recovery",
        kind="thread_rebind",
        summary="Mission rebound from a stale recovery thread.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_context_sweep",
        method="item/started",
        payload={
            "threadId": "thread_exec_context_sweep",
            "turnId": "turn_exec_context_sweep",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_context_sweep",
                "command": (
                    "powershell.exe -Command "
                    "\"Get-ChildItem -Force -Name .,.openzues,.zues,docs,.codex,logs,"
                    "artifacts,sessions,session,mission-control 2>$null\""
                ),
            },
        },
    )
    for index in range(6):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_context_sweep",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_context_sweep",
                "turnId": "turn_exec_context_sweep",
                "itemId": "call_exec_context_sweep",
                "delta": f"Recovery context artifact {index + 1}",
            },
        )

    started_at = datetime.now(UTC) - timedelta(seconds=40)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=5 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="active",
        last_activity_seconds=10,
    )

    assert signal is not None
    assert signal["mode"] == "parity_context_sweep"
    assert signal["output_delta_count"] == 6
    assert signal["elapsed_seconds"] >= 25


@pytest.mark.asyncio
async def test_detect_executing_stall_ignores_stale_parity_window_after_later_command(
    tmp_path,
) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    ledger_command = (
        'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
    )
    pytest_command = (
        'powershell.exe -Command ".venv\\Scripts\\python.exe -m pytest tests/test_missions.py '
        '-q -k repeated_parity_ledger_read"'
    )

    mission_id = await database.create_mission(
        name="Recovered parity ledger replay mission",
        objective="Ignore stale parity ledger windows once the lane has already moved on.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_stale_ledger",
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
        command_count=22,
        turns_completed=3,
        total_tokens=401000,
        last_turn_id="turn_exec_stale_ledger",
        current_command=ledger_command,
        last_activity_at=(datetime.now(UTC) - timedelta(seconds=10)).isoformat(),
    )
    await database.append_mission_checkpoint(
        mission_id=mission_id,
        thread_id="thread_before_recovery",
        turn_id="turn_before_recovery",
        kind="execution_rebind",
        summary="Mission rebound from a prior stalled parity-ledger read.",
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/started",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_repeated_ledger",
                "command": ledger_command,
            },
        },
    )
    for index in range(4):
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec_stale_ledger",
            method="item/commandExecution/outputDelta",
            payload={
                "threadId": "thread_exec_stale_ledger",
                "turnId": "turn_exec_stale_ledger",
                "itemId": "call_exec_repeated_ledger",
                "delta": f"Parity ledger line {index + 1}",
            },
        )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/started",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_pytest",
                "command": pytest_command,
            },
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/commandExecution/outputDelta",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "itemId": "call_exec_pytest",
            "delta": "1 passed in 0.50s",
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/completed",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_pytest",
                "command": pytest_command,
            },
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/started",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "item": {
                "type": "reasoning",
                "id": "reasoning_after_pytest",
            },
        },
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_stale_ledger",
        method="item/started",
        payload={
            "threadId": "thread_exec_stale_ledger",
            "turnId": "turn_exec_stale_ledger",
            "item": {
                "type": "agentMessage",
                "id": "commentary_after_pytest",
                "phase": "commentary",
            },
        },
    )

    started_at = datetime.now(UTC) - timedelta(seconds=55)
    with sqlite3.connect(database.path) as connection:
        event_ids = [
            row[0]
            for row in connection.execute("SELECT id FROM events ORDER BY id ASC").fetchall()
        ]
        for offset, event_id in enumerate(event_ids):
            created_at = started_at + timedelta(seconds=5 * offset)
            connection.execute(
                "UPDATE events SET created_at = ? WHERE id = ?",
                (created_at.isoformat(), event_id),
            )
        connection.commit()

    mission = await database.get_mission(mission_id)
    assert mission is not None
    signal = await service._detect_executing_stall(
        mission,
        thread_status="active",
        last_activity_seconds=10,
    )

    assert signal is None


@pytest.mark.asyncio
async def test_handle_event_tracks_active_command_from_overlapping_runtime_events(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    service = MissionService(database, None, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Concurrent command parity mission",
        objective="Track the command that is actually emitting output.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_overlap",
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
        phase="thinking",
        last_turn_id="turn_overlap",
    )

    recall_command = (
        'powershell.exe -Command "Get-Content -Path src/openzues/services/recall.py '
        '-TotalCount 220"'
    )
    ledger_command = (
        'powershell.exe -Command "Get-Content -Path '
        "docs/openclaw-parity-checkpoint-2026-04-10.md | Select-String -Pattern "
        '\'[restart_safe]\' -Context 2,3"'
    )

    first_start = {
        "method": "item/started",
        "threadId": "thread_overlap",
        "params": {
            "threadId": "thread_overlap",
            "turnId": "turn_overlap",
            "item": {
                "type": "commandExecution",
                "id": "call_first",
                "command": recall_command,
            },
        },
    }
    await database.append_event(
        instance_id=7,
        thread_id="thread_overlap",
        method=first_start["method"],
        payload=first_start["params"],
    )
    await service.handle_event(7, first_start)

    second_start = {
        "method": "item/started",
        "threadId": "thread_overlap",
        "params": {
            "threadId": "thread_overlap",
            "turnId": "turn_overlap",
            "item": {
                "type": "commandExecution",
                "id": "call_second",
                "command": ledger_command,
            },
        },
    }
    await database.append_event(
        instance_id=7,
        thread_id="thread_overlap",
        method=second_start["method"],
        payload=second_start["params"],
    )
    await service.handle_event(7, second_start)

    first_output = {
        "method": "item/commandExecution/outputDelta",
        "threadId": "thread_overlap",
        "params": {
            "threadId": "thread_overlap",
            "turnId": "turn_overlap",
            "itemId": "call_first",
            "delta": "from openzues.services.missions import MissionService",
        },
    }
    await database.append_event(
        instance_id=7,
        thread_id="thread_overlap",
        method=first_output["method"],
        payload=first_output["params"],
    )
    await service.handle_event(7, first_output)

    mission = await database.get_mission(mission_id)
    assert mission is not None
    assert mission["phase"] == "executing"
    assert mission["current_command"] == recall_command

    first_complete = {
        "method": "item/completed",
        "threadId": "thread_overlap",
        "params": {
            "threadId": "thread_overlap",
            "turnId": "turn_overlap",
            "item": {
                "type": "commandExecution",
                "id": "call_first",
                "command": recall_command,
            },
        },
    }
    await database.append_event(
        instance_id=7,
        thread_id="thread_overlap",
        method=first_complete["method"],
        payload=first_complete["params"],
    )
    await service.handle_event(7, first_complete)

    mission = await database.get_mission(mission_id)
    assert mission is not None
    assert mission["phase"] == "executing"
    assert mission["current_command"] == ledger_command


@pytest.mark.asyncio
async def test_reconcile_rebinds_not_loaded_executing_thread(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [
        {
            "id": "thread_exec_not_loaded",
            "status": {"type": "notLoaded"},
        }
    ]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Stalled execution parity mission",
        objective="Land the OpenClaw parity checkpoint instead of hanging on a stale read.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec_not_loaded",
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
        command_count=18,
        turns_completed=2,
        total_tokens=310000,
        last_turn_id="turn_exec_not_loaded",
        current_command=(
            'powershell.exe -Command "Get-Content docs/openclaw-parity-checkpoint-2026-04-10.md"'
        ),
        last_commentary="I am still reading the parity checkpoint before deciding what to land.",
        last_activity_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_not_loaded",
        method="turn/started",
        payload={"threadId": "thread_exec_not_loaded", "turnId": "turn_exec_not_loaded"},
    )
    await database.append_event(
        instance_id=7,
        thread_id="thread_exec_not_loaded",
        method="item/started",
        payload={
            "threadId": "thread_exec_not_loaded",
            "turnId": "turn_exec_not_loaded",
            "item": {
                "type": "commandExecution",
                "id": "call_exec_not_loaded",
                "command": (
                    'powershell.exe -Command "Get-Content '
                    'docs/openclaw-parity-checkpoint-2026-04-10.md"'
                ),
            },
        },
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.interrupt_calls[0]["thread_id"] == "thread_exec_not_loaded"
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "stalled-execution recovery" in manager.turn_calls[0]["text"]
    assert "no longer reporting as a live runtime thread" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "execution_rebind"
    assert "thread_exec_not_loaded" in checkpoints[0]["summary"]


@pytest.mark.asyncio
async def test_reconcile_rebinds_untracked_in_progress_thread_without_command(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [
        {
            "id": "thread_silent_not_loaded",
            "status": {"type": "notLoaded"},
        }
    ]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Silent parity recovery mission",
        objective="Resume the next parity seam without getting stranded mid-turn.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_silent_not_loaded",
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
        phase="thinking",
        command_count=10,
        total_tokens=78141,
        current_command=None,
        last_commentary=(
            "Recall is not available here; I'm moving straight to the ledger and the next "
            "concrete seam."
        ),
        last_activity_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    )

    await service._reconcile_mission(mission_id)
    mission = await database.get_mission(mission_id)
    checkpoints = await database.list_mission_checkpoints(mission_id)

    assert mission is not None
    assert mission["thread_id"] == "thread_auto_7"
    assert mission["status"] == "active"
    assert mission["phase"] == "thinking"
    assert mission["in_progress"] == 1
    assert manager.thread_calls[0]["instance_id"] == 7
    assert manager.turn_calls[0]["thread_id"] == "thread_auto_7"
    assert "stale-thread recovery" in manager.turn_calls[0]["text"]
    assert "live thread stopped reporting" in manager.turn_calls[0]["text"]
    assert checkpoints[0]["kind"] == "thread_rebind"
    assert "thread_silent_not_loaded" in checkpoints[0]["summary"]


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
async def test_stale_thread_recovery_prompt_is_compact_for_openclaw_parity(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective=(
            "Use C:/openclaw-main as the source of truth and C:/OpenZues as the target product. "
            "First inventory the OpenClaw surface area across gateway, onboarding, CLI, channels, "
            "routing, voice, canvas, nodes, skills, browser, packaging, and companion apps. "
            "Then choose the highest-leverage missing parity slice in OpenZues, implement it end "
            "to end in production quality, run the relevant verification, and leave a checkpoint "
            "that names what was completed, what remains, and the next best slice."
        ),
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_parity_stale",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort="high",
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
        allow_failover=True,
    )
    mission = await database.get_mission(mission_id)
    assert mission is not None

    prompt = service._build_stale_thread_recovery_prompt(
        mission,
        stale_thread_id="thread_parity_stale",
        new_thread_id="thread_parity_recovered",
        stale_error="thread not found: thread_parity_stale",
        checkpoints=[
            {
                "kind": "restart_safe",
                "summary": (
                    "Restart-safe recovery packet after 4 commands. Current focus: Rebuilding "
                    "context first: I'm reading the Hermes workflow guidance, the current "
                    "OpenZues worktree state, and any existing parity checkpoint."
                ),
            },
            {
                "kind": "final_answer",
                "summary": (
                    "Persistent setup launch handoff landed. Next step: move into routing and "
                    "session-key policy parity."
                ),
            },
        ],
        trace_lines=[
            "Output: hermes sessions list",
            "Output: hermes cron create 30m",
        ],
    )

    assert "stale-thread recovery" in prompt
    assert f"Treat `{OPENCLAW_PARITY_CHECKPOINT_LEDGER}` as the recovery ledger." in prompt
    assert "Give at most two short commentary sentences before the first tool call." in prompt
    assert "emitted item must be a tool call or the checkpoint itself" in prompt
    assert "If Recall returns a usable anchor, do not summarize it in commentary." in prompt
    assert "If Recall succeeds, do not paraphrase the recovered context in commentary." in prompt
    assert "The next emitted item after Recall must be a bounded tool call" in prompt
    assert "does not count as session search" in prompt
    assert "list_mcp_resources" in prompt
    assert "do not satisfy the first-tool-call recovery rule" in prompt
    assert "Built-in agent stack:" not in prompt
    assert "Crash-safe relay packets:" not in prompt
    assert "Recent persisted live trace:" not in prompt
    assert "Hermes workflow guidance" not in prompt
    assert "Relevant checkpoint trail:" in prompt
    assert "Persistent setup launch handoff landed." in prompt
    assert "First inventory the OpenClaw surface area" not in prompt


@pytest.mark.asyncio
async def test_run_now_blocks_mission_when_thread_launch_times_out(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.start_thread_error = TimeoutError()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Resume from the parity checkpoint and lock the next bounded seam.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort="high",
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
        allow_failover=True,
    )

    view = await service.run_now(mission_id)
    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["status"] == "blocked"
    assert mission["phase"] == "launch"
    assert "Thread launch timed out" in str(mission["last_error"])
    assert view.status == "blocked"
    assert view.phase == "launch"


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
async def test_live_event_clears_turn_start_timeout_failure_state(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Late turn start proof",
        objective="Recover when the runtime starts a turn after the RPC times out.",
        status="failed",
        instance_id=7,
        project_id=None,
        thread_id="thread_late",
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
        last_error="TimeoutError: Codex runtime failed to start the turn without a detailed error.",
        phase="failed",
        in_progress=0,
    )

    await service.handle_event(
        7,
        {
            "method": "item/started",
            "threadId": "thread_late",
            "params": {
                "threadId": "thread_late",
                "turnId": "turn_late",
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
async def test_reconcile_clears_turn_start_timeout_failure_when_thread_is_alive(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    manager.instances[7].connected = True
    manager.instances[7].threads = [{"id": "thread_live", "status": {"type": "active"}}]
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="Recovered late-start mission",
        objective="Trust a live runtime thread over a transient turn-start timeout.",
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
        last_error="TimeoutError: Codex runtime failed to start the turn without a detailed error.",
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
    assert manager.turn_calls == []


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


@pytest.mark.asyncio
async def test_handle_event_clears_superseded_orphan_command(tmp_path) -> None:
    database = Database(tmp_path / "missions.db")
    await database.initialize()
    manager = FakeManager()
    service = MissionService(database, manager, BroadcastHub(), poll_interval_seconds=3600)

    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_exec",
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
        phase="executing",
        last_turn_id="turn_exec",
        current_command="Select-String -Path docs/openclaw-parity-checkpoint-2026-04-10.md",
    )

    async def emit(method: str, payload: dict[str, Any]) -> None:
        await database.append_event(
            instance_id=7,
            thread_id="thread_exec",
            method=method,
            payload=payload,
        )
        await service.handle_event(
            7,
            {
                "threadId": "thread_exec",
                "method": method,
                "params": payload,
            },
        )

    await emit(
        "item/started",
        {
            "threadId": "thread_exec",
            "turnId": "turn_exec",
            "item": {
                "type": "commandExecution",
                "id": "call_old",
                "command": "Select-String -Path docs/openclaw-parity-checkpoint-2026-04-10.md",
                "status": "inProgress",
            },
        },
    )
    await emit(
        "item/started",
        {
            "threadId": "thread_exec",
            "turnId": "turn_exec",
            "item": {
                "type": "commandExecution",
                "id": "call_new",
                "command": "git status --short",
                "status": "inProgress",
            },
        },
    )
    await emit(
        "item/completed",
        {
            "threadId": "thread_exec",
            "turnId": "turn_exec",
            "item": {
                "type": "commandExecution",
                "id": "call_new",
                "command": "git status --short",
                "status": "completed",
            },
        },
    )
    await emit(
        "item/commandExecution/outputDelta",
        {
            "threadId": "thread_exec",
            "turnId": "turn_exec",
            "itemId": "call_old",
            "delta": "\r\n",
        },
    )

    mission = await database.get_mission(mission_id)

    assert mission is not None
    assert mission["current_command"] is None
    assert mission["phase"] == "thinking"
