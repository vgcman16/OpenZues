from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openzues.database import Database
from openzues.schemas import MissionView, OperatorCreate, RemoteMissionCreate, RemoteTaskTrigger
from openzues.services.access import AccessService
from openzues.services.hub import BroadcastHub
from openzues.services.remote_ops import RemoteOpsService


def make_mission_view(*, mission_id: int, name: str) -> MissionView:
    now = datetime.now(UTC)
    return MissionView(
        id=mission_id,
        name=name,
        objective="Keep shipping.",
        status="paused",
        instance_id=1,
        instance_name="Local Codex",
        project_id=None,
        project_label=None,
        task_blueprint_id=None,
        thread_id="thread_remote",
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
        in_progress=False,
        phase="ready",
        current_command=None,
        command_count=0,
        total_tokens=0,
        output_tokens=0,
        reasoning_tokens=0,
        last_commentary=None,
        suggested_action="Review the queue.",
        turns_started=0,
        turns_completed=0,
        failure_count=0,
        last_turn_id=None,
        last_error=None,
        last_checkpoint=None,
        last_reflex_kind=None,
        last_reflex_at=None,
        last_activity_at=now.isoformat(),
        checkpoints=[],
        created_at=now,
        updated_at=now,
    )


class FakeManager:
    async def list_views(self):
        return []

    async def get(self, instance_id: int):
        return object()


class FakeMissionService:
    def __init__(self) -> None:
        self.calls = []

    async def create(self, payload):
        self.calls.append(payload)
        return make_mission_view(mission_id=41, name=payload.name)


class FakeOpsMeshService:
    def __init__(self) -> None:
        self.calls = []

    async def run_task_blueprint_now(self, task_id: int, *, trigger: str = "manual"):
        self.calls.append((task_id, trigger))
        return make_mission_view(mission_id=52, name=f"Task {task_id} run")


@pytest.mark.asyncio
async def test_access_service_bootstraps_local_team_and_owner(tmp_path) -> None:
    database = Database(tmp_path / "access.db")
    await database.initialize()
    access = AccessService(database)

    await access.initialize()
    teams = await access.list_team_views()
    operators = await access.list_operator_views()

    assert teams[0].name == "Local Control"
    assert operators[0].role == "owner"
    assert operators[0].has_api_key is False


@pytest.mark.asyncio
async def test_remote_ops_service_triggers_task_and_reuses_idempotency_key(tmp_path) -> None:
    database = Database(tmp_path / "remote.db")
    await database.initialize()
    access = AccessService(database)
    await access.initialize()
    credential = await access.create_operator(
        OperatorCreate(
            name="Remote Builder",
            role="operator",
            issue_api_key=True,
        )
    )
    assert credential.api_key is not None
    auth = await access.authenticate_api_key(
        credential.api_key,
        permission="remote.task.trigger",
    )
    task_id = await database.create_task_blueprint(
        name="Nightly drift sweep",
        summary="Keep the workspace tight.",
        project_id=None,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Check for drift and leave a checkpoint.",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
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

    fake_missions = FakeMissionService()
    fake_ops_mesh = FakeOpsMeshService()
    service = RemoteOpsService(
        database,
        FakeManager(),
        fake_missions,
        fake_ops_mesh,
        BroadcastHub(),
    )

    first = await service.trigger_task_request(
        task_id,
        RemoteTaskTrigger(),
        auth=auth,
        source_ip="127.0.0.1",
        user_agent="pytest",
        idempotency_key="task-req-1",
    )
    second = await service.trigger_task_request(
        task_id,
        RemoteTaskTrigger(),
        auth=auth,
        source_ip="127.0.0.1",
        user_agent="pytest",
        idempotency_key="task-req-1",
    )

    assert first.status == "completed"
    assert first.kind == "task.trigger"
    assert first.target_kind == "task"
    assert first.target_id == task_id
    assert second.id == first.id
    assert fake_ops_mesh.calls == [(task_id, "remote")]
    remote_requests = await database.list_remote_requests()
    assert len(remote_requests) == 1
    assert remote_requests[0]["result"]["summary"].startswith("Triggered task")


@pytest.mark.asyncio
async def test_remote_ops_rejects_cross_kind_idempotency_reuse(tmp_path) -> None:
    database = Database(tmp_path / "remote-idempotency.db")
    await database.initialize()
    access = AccessService(database)
    await access.initialize()
    credential = await access.create_operator(
        OperatorCreate(
            name="Remote Builder",
            role="operator",
            issue_api_key=True,
        )
    )
    assert credential.api_key is not None
    mission_auth = await access.authenticate_api_key(
        credential.api_key,
        permission="remote.mission.create",
    )
    task_auth = await access.authenticate_api_key(
        credential.api_key,
        permission="remote.task.trigger",
    )
    task_id = await database.create_task_blueprint(
        name="Nightly drift sweep",
        summary="Keep the workspace tight.",
        project_id=None,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Check for drift and leave a checkpoint.",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
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

    service = RemoteOpsService(
        database,
        FakeManager(),
        FakeMissionService(),
        FakeOpsMeshService(),
        BroadcastHub(),
    )

    first = await service.create_mission_request(
        RemoteMissionCreate(
            name="Remote launch",
            objective="Create a mission from outside the browser.",
            instance_id=1,
            start_immediately=False,
        ),
        auth=mission_auth,
        source_ip="127.0.0.1",
        user_agent="pytest",
        idempotency_key="same-key",
    )

    with pytest.raises(ValueError, match="already bound"):
        await service.trigger_task_request(
            task_id,
            RemoteTaskTrigger(),
            auth=task_auth,
            source_ip="127.0.0.1",
            user_agent="pytest",
            idempotency_key="same-key",
        )

    assert first.kind == "mission.create"
    remote_requests = await database.list_remote_requests()
    assert len(remote_requests) == 1
