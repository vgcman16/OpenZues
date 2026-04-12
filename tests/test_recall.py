from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.services.hub import BroadcastHub
from openzues.services.missions import MissionService
from openzues.services.recall import RecallService
from openzues.settings import Settings


class _RecallRuntime:
    def __init__(self, name: str) -> None:
        self.name = name


class _RecallManager:
    def __init__(self) -> None:
        self.instances = {7: _RecallRuntime("Local Codex Desktop")}


@pytest.mark.asyncio
async def test_recall_service_search_prioritizes_checkpoint_matches(tmp_path) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    project_id = await database.create_project(path=str(tmp_path), label="Memory Workspace")
    mission_service = MissionService(database, _RecallManager(), BroadcastHub())
    recall = RecallService(mission_service)

    target_id = await database.create_mission(
        name="ForumForge Inbox + Queue Build",
        objective="Ship the forum migration with durable recall.",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-forum",
        session_key="forum-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=3,
        use_builtin_agents=False,
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
    await database.update_mission(
        target_id,
        last_checkpoint="Verified the forum migration recall through MemPalace.",
        last_commentary="The forum migration slice is green and checkpointed.",
    )
    await database.append_mission_checkpoint(
        mission_id=target_id,
        thread_id="thread-forum",
        turn_id=None,
        kind="continuity_auto",
        summary="Forum migration handoff captured for durable recall and restart safety.",
    )

    other_id = await database.create_mission(
        name="Clean UI Shell",
        objective="Polish the dashboard shell.",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-ui",
        session_key="ui-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=False,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["safe"],
    )
    await database.append_mission_checkpoint(
        mission_id=other_id,
        thread_id="thread-ui",
        turn_id=None,
        kind="continuity_auto",
        summary="UI cleanup checkpoint captured.",
    )

    payload = await recall.search("forum migration", limit=5)

    assert payload.mode == "query"
    assert payload.total_matches >= 1
    assert payload.items[0].mission_id == target_id
    assert "forum migration" in payload.items[0].excerpt.lower()
    assert payload.items[0].continuity_path == f"/api/missions/{target_id}/continuity"
    assert payload.items[0].toolsets == ["memory", "session_search"]


@pytest.mark.asyncio
async def test_recall_service_recent_returns_latest_items(tmp_path) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    project_id = await database.create_project(path=str(tmp_path), label="Recent Workspace")
    mission_service = MissionService(database, _RecallManager(), BroadcastHub())
    recall = RecallService(mission_service)

    first_id = await database.create_mission(
        name="Earlier Slice",
        objective="Land the earlier checkpoint.",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-earlier",
        session_key="earlier-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=False,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["safe"],
    )
    await database.append_mission_checkpoint(
        mission_id=first_id,
        thread_id="thread-earlier",
        turn_id=None,
        kind="continuity_auto",
        summary="Earlier checkpoint captured.",
    )

    latest_id = await database.create_mission(
        name="Latest Slice",
        objective="Land the latest checkpoint.",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-latest",
        session_key="latest-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=False,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["safe", "memory"],
    )
    await database.update_mission(
        latest_id,
        last_checkpoint="Latest checkpoint captured for restart safety.",
    )

    payload = await recall.search(limit=5)

    assert payload.mode == "recent"
    assert payload.items[0].mission_id == latest_id
    assert payload.items[0].match_source in {"checkpoint", "summary"}
    assert payload.items[0].continuity_path == f"/api/missions/{latest_id}/continuity"


@pytest.mark.asyncio
async def test_recall_service_prefers_mempalace_when_profile_prefers_it(tmp_path) -> None:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    await database.upsert_hermes_runtime_profile(
        {
            "preferred_memory_provider": "mempalace",
            "preferred_executor": "codex_desktop",
        }
    )
    project_id = await database.create_project(path=str(tmp_path), label="Recall Workspace")
    mission_service = MissionService(database, _RecallManager(), BroadcastHub())
    recall = RecallService(mission_service, database)

    proof_id = await database.create_mission(
        name="MemPalace Direct Proof: Recall Workspace",
        objective="MemPalace control-plane proof contract:",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-proof",
        session_key="proof-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=1,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=False,
        auto_recover=False,
        auto_recover_limit=0,
        reflex_cooldown_seconds=900,
        allow_failover=False,
        toolsets=["memory", "session_search"],
    )
    await database.update_mission(
        proof_id,
        last_checkpoint="Verified the memory can be recalled through MemPalace.",
    )

    generic_id = await database.create_mission(
        name="Generic Slice",
        objective="Land the latest generic checkpoint.",
        status="completed",
        instance_id=7,
        project_id=project_id,
        thread_id="thread-generic",
        session_key="generic-session",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=False,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["safe"],
    )
    await database.update_mission(
        generic_id,
        last_checkpoint="Generic checkpoint captured later in time.",
    )

    payload = await recall.search(limit=5)

    assert payload.preferred_memory_provider == "mempalace"
    assert payload.preferred_memory_provider_label == "MemPalace"
    assert "Preferred provider: MemPalace." in payload.summary
    assert payload.items[0].mission_id == proof_id


def test_recall_api_and_dashboard_surface_saved_results(tmp_path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)

    with TestClient(api_app, client=("testclient", 50000)) as client:
        database = api_app.state.database
        project_id = asyncio.run(
            database.create_project(path=str(tmp_path), label="Recall Workspace")
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="MemPalace Direct Proof: Recall Workspace",
                objective="MemPalace control-plane proof contract:",
                status="completed",
                instance_id=7,
                project_id=project_id,
                thread_id="thread-proof",
                session_key="recall-proof",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=1,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=False,
                auto_recover=False,
                auto_recover_limit=0,
                reflex_cooldown_seconds=900,
                allow_failover=False,
                toolsets=["memory", "session_search"],
            )
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                last_checkpoint=(
                    "Control-plane proof verified live MemPalace recall for Recall Workspace."
                ),
            )
        )
        asyncio.run(
            database.append_mission_checkpoint(
                mission_id=mission_id,
                thread_id="thread-proof",
                turn_id=None,
                kind="continuity_auto",
                summary="Control-plane proof verified live MemPalace recall for Recall Workspace.",
            )
        )

        recall_payload = client.get(
            "/api/recall",
            params={"query": "Recall Workspace"},
        ).json()
        assert recall_payload["headline"].startswith("Recall found")
        assert recall_payload["items"][0]["mission_id"] == mission_id
        assert recall_payload["items"][0]["continuity_path"] == (
            f"/api/missions/{mission_id}/continuity"
        )

        dashboard_payload = client.get("/api/dashboard").json()
        assert dashboard_payload["recall"]["headline"]
        assert any(
            item["mission_id"] == mission_id
            for item in dashboard_payload["recall"]["items"]
        )
