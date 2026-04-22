from __future__ import annotations

from pathlib import Path

import pytest

from openzues.database import Database
from openzues.schemas import ConversationTargetView, InstanceView
from openzues.services.hub import BroadcastHub
from openzues.services.ops_mesh import OpsMeshService
from openzues.services.session_keys import build_launch_session_key
from openzues.services.vault import VaultService
from openzues.settings import Settings


def make_vault(database: Database, tmp_path: Path) -> VaultService:
    return VaultService(
        database,
        Settings(
            data_dir=tmp_path / "data",
            db_path=tmp_path / "data" / "openzues-test.db",
        ),
    )


class FakeManager:
    async def list_views(self) -> list[InstanceView]:
        return []

    async def get(self, instance_id: int) -> None:  # noqa: ARG002
        return None


class FakeMissionService:
    async def list_views(self) -> list[object]:
        return []


def test_build_launch_session_key_canonicalizes_channel_account_and_peer_identity() -> None:
    session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="Slack",
            account_id="Workspace Bot",
            peer_kind="channel",
            peer_id="Deploy.Room+West",
        ),
    )

    assert (
        session_key
        == "launch:mode:workspace_affinity:channel:slack:account:workspace-bot:"
        "peer:channel:deploy.room+west"
    )


@pytest.mark.asyncio
async def test_ops_mesh_matches_routes_after_account_id_canonicalization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Deploy Room",
        kind="webhook",
        target="https://example.invalid/deploy",
        events=["mission/*"],
        conversation_target={
            "channel": "Slack",
            "account_id": "Workspace Bot",
            "peer_kind": "channel",
            "peer_id": "Deploy.Room+West",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_notification_route(
        name="Workspace Account",
        kind="webhook",
        target="https://example.invalid/account",
        events=["mission/*"],
        conversation_target={
            "channel": "Slack",
            "account_id": "Workspace Bot",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )

    mission_id = await database.create_mission(
        name="Deploy parity slice",
        objective="Ship the next routed parity seam.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_route",
        session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=7,
            project_id=None,
            operator_id=1,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="workspace-bot",
                peer_kind="channel",
                peer_id="deploy.room+west",
            ),
        ),
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy.room+west",
        },
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
        toolsets=[],
    )

    deliveries: list[tuple[str, str]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, secret_token
        deliveries.append(
            (
                str(route.get("name") or ""),
                str(event.get("routeMatch") or ""),
            )
        )

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert deliveries == [
        ("Deploy Room", "peer"),
        ("Workspace Account", "account"),
    ]
