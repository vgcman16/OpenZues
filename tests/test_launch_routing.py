from __future__ import annotations

from pathlib import Path

import pytest

from openzues.database import Database
from openzues.schemas import ConversationTargetView, InstanceView
from openzues.services.launch_routing import LaunchRoutingService, _normalize_conversation_target


class FakeManager:
    def __init__(self, instances: list[InstanceView]) -> None:
        self.instances = {instance.id: instance for instance in instances}

    async def list_views(self) -> list[InstanceView]:
        return list(self.instances.values())

    async def get(self, instance_id: int) -> InstanceView | None:
        return self.instances.get(instance_id)


def test_normalize_conversation_target_preserves_punctuated_peer_id() -> None:
    normalized = _normalize_conversation_target(
        ConversationTargetView(
            channel="Slack",
            account_id="Workspace Bot",
            peer_kind="channel",
            peer_id="Deploy.Room+West",
            summary="ignored",
        )
    )

    assert normalized is not None
    assert normalized.channel == "slack"
    assert normalized.account_id == "workspace-bot"
    assert normalized.peer_kind == "channel"
    assert normalized.peer_id == "deploy.room+west"


def test_normalize_conversation_target_reuses_openclaw_account_id_rules() -> None:
    normalized = _normalize_conversation_target(
        ConversationTargetView(
            channel="Slack",
            account_id="__Ops__",
            peer_kind="channel",
            peer_id="Deploy.Room+West",
            summary="ignored",
        )
    )

    assert normalized is not None
    assert normalized.account_id == "__ops__"


@pytest.mark.asyncio
async def test_describe_preserves_reusable_thread_child_session_key(tmp_path: Path) -> None:
    database = Database(tmp_path / "launch-routing.db")
    await database.initialize()

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    instance = InstanceView(
        id=7,
        name="Workspace Lane",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=str(workspace_path),
        auto_connect=False,
        connected=True,
    )
    manager = FakeManager([instance])

    await database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="quickstart",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=None,
        preferred_project_id=None,
        team_id=None,
        operator_id=1,
        task_blueprint_id=77,
        default_cwd=str(workspace_path),
        model="gpt-5.4",
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

    await database.create_mission(
        name="Saved routed thread",
        objective="Preserve the child session key for the reusable thread.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-abc",
        session_key="launch:mode:workspace_affinity:task:77:operator:1:thread:thread-abc",
        cwd=str(workspace_path),
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

    route = await LaunchRoutingService(database, manager).describe()

    assert route.main_session_key == "launch:mode:workspace_affinity:task:77:operator:1"
    assert route.session_key == (
        "launch:mode:workspace_affinity:task:77:operator:1:thread:thread-abc"
    )
    assert route.last_route_policy == "session"
    assert route.conversation_reuse is not None
    assert route.conversation_reuse.reusable is True
    assert route.conversation_reuse.thread_id == "thread-abc"
