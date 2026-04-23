from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from openzues.database import Database
from openzues.services.gateway_session_compaction import GatewaySessionCompactionService
from openzues.services.gateway_sessions import GatewaySessionsService
from openzues.services.session_keys import resolve_thread_session_keys


def _set_mission_updated_at(database: Database, *, session_key: str, updated_at: str) -> None:
    with sqlite3.connect(database.path) as connection:
        connection.execute(
            "UPDATE missions SET updated_at = ? WHERE session_key = ?",
            (updated_at, session_key),
        )
        connection.commit()


@pytest.mark.asyncio
async def test_message_payloads_surface_compaction_checkpoint_metadata(tmp_path: Path) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "openzues:thread:demo"
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )

    compaction_service = GatewaySessionCompactionService(database)
    compacted = await compaction_service.compact(
        session_key=session_key,
        max_lines=2,
        now_ms=1_700_000_000_123,
    )
    checkpoint_id = str(compacted["checkpointId"])

    message_row_id = await database.append_control_chat_message(
        role="user",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )
    message_row = await database.get_control_chat_message(message_row_id)
    assert message_row is not None

    sessions_service = GatewaySessionsService(database)
    message_payload = await sessions_service.build_message_event_payload(
        message_row=message_row,
        now_ms=1_700_000_000_456,
    )
    changed_payload = await sessions_service.build_message_changed_event_payload(
        message_row=message_row,
        now_ms=1_700_000_000_456,
    )

    assert message_payload is not None
    assert message_payload["sessionKey"] == session_key
    assert message_payload["compactionCheckpointCount"] == 1
    assert message_payload["latestCompactionCheckpoint"]["checkpointId"] == checkpoint_id
    assert message_payload["latestCompactionCheckpoint"]["sessionId"] == "demo"
    assert message_payload["message"]["content"][0]["text"] == "Delta line 1"

    assert changed_payload is not None
    assert changed_payload["sessionKey"] == session_key
    assert changed_payload["compactionCheckpointCount"] == 1
    assert changed_payload["latestCompactionCheckpoint"]["checkpointId"] == checkpoint_id
    assert changed_payload["latestCompactionCheckpoint"]["sessionId"] == "demo"
    assert changed_payload["phase"] == "message"


@pytest.mark.asyncio
async def test_session_payload_caps_compaction_checkpoint_count_at_25(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "openzues:thread:checkpoint-cap"
    compaction_service = GatewaySessionCompactionService(database)
    base_now_ms = 1_700_000_200_000

    for index in range(27):
        await database.append_control_chat_message(
            role="user",
            content=f"Alpha line {index}\nAlpha follow-up {index}",
            mission_id=None,
            session_key=session_key,
        )
        await database.append_control_chat_message(
            role="assistant",
            content=f"Bravo line {index}",
            mission_id=None,
            session_key=session_key,
        )
        await database.append_control_chat_message(
            role="assistant",
            content=f"Charlie line {index}\nCharlie follow-up {index}",
            mission_id=None,
            session_key=session_key,
        )
        compacted = await compaction_service.compact(
            session_key=session_key,
            max_lines=2,
            now_ms=base_now_ms + index,
        )
        assert compacted["compacted"] is True

    payload = await GatewaySessionsService(database).build_session_payload_for_key(
        session_key=session_key,
        now_ms=base_now_ms + 100,
    )

    assert payload is not None
    assert payload["compactionCheckpointCount"] == 25
    assert payload["latestCompactionCheckpoint"]["createdAt"] == base_now_ms + 26


@pytest.mark.asyncio
async def test_build_snapshot_discovers_mission_and_transcript_sessions_without_metadata(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    mission_only_key = "launch:mode:saved_lane:task:9:operator:1:thread:mission-only"
    transcript_only_key = (
        "launch:mode:workspace_affinity:task:88:operator:1:thread:transcript-only"
    )

    await database.create_mission(
        name="Mission-only session",
        objective="Mission-only objective",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="mission-only",
        session_key=mission_only_key,
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
    await database.append_control_chat_message(
        role="assistant",
        content="Transcript-only payload",
        mission_id=None,
        session_key=transcript_only_key,
        created_at="2024-01-02T03:04:05Z",
    )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=True,
        include_unknown=False,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_000_123,
    )

    sessions_by_key = {session["key"]: session for session in snapshot["sessions"]}

    assert snapshot["count"] == 2
    assert set(sessions_by_key) == {mission_only_key, transcript_only_key}
    assert sessions_by_key[mission_only_key]["sessionId"] == "mission-only"
    assert sessions_by_key[mission_only_key]["subject"] == "Mission-only objective"
    assert sessions_by_key[transcript_only_key]["sessionId"] == "transcript-only"
    assert sessions_by_key[transcript_only_key]["subject"] == "Operator control chat"


@pytest.mark.asyncio
async def test_build_snapshot_includes_current_main_session_without_persisted_rows(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=True,
        include_unknown=False,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_000_234,
    )

    assert snapshot["count"] == 1
    assert snapshot["defaults"]["mainSessionKey"] == "launch:mode:workspace_affinity"
    assert snapshot["sessions"] == [
        {
            "key": "launch:mode:workspace_affinity",
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": 1_700_000_000_234,
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "contextTokens": None,
        }
    ]


@pytest.mark.asyncio
async def test_build_snapshot_sorts_discovered_sessions_by_updated_at_desc(tmp_path: Path) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    newer_key = "launch:mode:workspace_affinity:task:5:operator:1:thread:newer"
    older_key = "launch:mode:workspace_affinity:task:5:operator:1:thread:older"

    await database.append_control_chat_message(
        role="assistant",
        content="Newer transcript payload",
        mission_id=None,
        session_key=newer_key,
        created_at="2025-05-02T00:00:00Z",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Older transcript payload",
        mission_id=None,
        session_key=older_key,
        created_at="2024-05-02T00:00:00Z",
    )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=False,
        include_unknown=False,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_000_456,
    )

    assert [session["key"] for session in snapshot["sessions"]] == [newer_key, older_key]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_limit", [0, -3, 1.9])
async def test_build_snapshot_clamps_limit_to_positive_integer_like_openclaw(
    tmp_path: Path,
    raw_limit: object,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    newer_key = "launch:mode:workspace_affinity:task:6:operator:1:thread:newer"
    older_key = "launch:mode:workspace_affinity:task:6:operator:1:thread:older"

    await database.append_control_chat_message(
        role="assistant",
        content="Newer transcript payload",
        mission_id=None,
        session_key=newer_key,
        created_at="2025-05-02T00:00:00Z",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Older transcript payload",
        mission_id=None,
        session_key=older_key,
        created_at="2024-05-02T00:00:00Z",
    )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=False,
        include_unknown=False,
        limit=raw_limit,  # type: ignore[arg-type]
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_000_567,
    )

    assert snapshot["count"] == 1
    assert [session["key"] for session in snapshot["sessions"]] == [newer_key]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_active_minutes", [0, -2, 1.9])
async def test_build_snapshot_clamps_active_minutes_to_positive_integer_like_openclaw(
    tmp_path: Path,
    raw_active_minutes: object,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    now_ms = 1_700_000_120_000
    fresh_key = "launch:mode:workspace_affinity:task:7:operator:1:thread:fresh"
    stale_key = "launch:mode:workspace_affinity:task:7:operator:1:thread:stale"

    await database.append_control_chat_message(
        role="assistant",
        content="Fresh transcript payload",
        mission_id=None,
        session_key=fresh_key,
        created_at="2023-11-14T22:14:50Z",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Stale transcript payload",
        mission_id=None,
        session_key=stale_key,
        created_at="2023-11-14T22:14:19Z",
    )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=False,
        include_unknown=False,
        limit=None,
        active_minutes=raw_active_minutes,  # type: ignore[arg-type]
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=now_ms,
    )

    assert snapshot["count"] == 1
    assert [session["key"] for session in snapshot["sessions"]] == [fresh_key]


@pytest.mark.asyncio
async def test_resolve_key_prefers_structural_session_id_match_over_fresher_fuzzy_duplicate(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_id = "run-dup"
    structural_key = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity",
        thread_id=session_id,
    ).session_key
    fuzzy_key = "agent:main:other"

    await database.create_mission(
        name="Structural duplicate",
        objective="Keep the structural session key for duplicate session ids.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id=session_id,
        session_key=structural_key,
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
    await database.create_mission(
        name="Fuzzy duplicate",
        objective="A newer fuzzy duplicate should not outrank the structural match.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id=session_id,
        session_key=fuzzy_key,
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
    _set_mission_updated_at(
        database,
        session_key=structural_key,
        updated_at="2025-01-01T00:00:00Z",
    )
    _set_mission_updated_at(
        database,
        session_key=fuzzy_key,
        updated_at="2026-01-01T00:00:00Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=session_id,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": structural_key}


@pytest.mark.asyncio
async def test_resolve_key_rejects_ambiguous_structural_session_id_duplicates(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_id = "sid"
    structural_key_a = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity:task:1",
        thread_id=session_id,
    ).session_key
    structural_key_b = resolve_thread_session_keys(
        base_session_key="launch:mode:saved_lane:task:2",
        thread_id=session_id,
    ).session_key
    fuzzy_key = "agent:main:other"

    for session_key, name in (
        (structural_key_a, "Structural duplicate A"),
        (structural_key_b, "Structural duplicate B"),
        (fuzzy_key, "Fuzzy duplicate"),
    ):
        await database.create_mission(
            name=name,
            objective="Keep duplicate session-id resolution deterministic.",
            status="completed",
            instance_id=7,
            project_id=None,
            thread_id=session_id,
            session_key=session_key,
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

    _set_mission_updated_at(
        database,
        session_key=structural_key_a,
        updated_at="2025-01-01T00:00:00Z",
    )
    _set_mission_updated_at(
        database,
        session_key=structural_key_b,
        updated_at="2025-01-01T00:00:00Z",
    )
    _set_mission_updated_at(
        database,
        session_key=fuzzy_key,
        updated_at="2026-01-01T00:00:00Z",
    )

    with pytest.raises(ValueError, match="unknown sessionId"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=session_id,
            label=None,
            agent_id=None,
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_accepts_session_key_passed_via_session_id_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "launch:mode:workspace_affinity:task:42:operator:1:thread:key-target"
    await database.append_control_chat_message(
        role="assistant",
        content="Transcript-only payload",
        mission_id=None,
        session_key=session_key,
        created_at="2025-01-02T03:04:05Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=session_key,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": session_key}


@pytest.mark.asyncio
async def test_resolve_key_session_id_prefilters_spawned_by_before_duplicate_preference(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_id = "shared-thread"
    structural_key = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity:task:7:operator:1",
        thread_id=session_id,
    ).session_key
    fuzzy_key = "agent:main:other"

    for session_key, name in (
        (structural_key, "Structural session"),
        (fuzzy_key, "Requester-visible duplicate"),
    ):
        await database.create_mission(
            name=name,
            objective="Resolve sessionId duplicates after applying spawnedBy filters.",
            status="completed",
            instance_id=7,
            project_id=None,
            thread_id=session_id,
            session_key=session_key,
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

    await database.upsert_gateway_session_metadata(
        session_key=structural_key,
        metadata={"spawnedBy": "controller-other"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=fuzzy_key,
        metadata={"spawnedBy": "controller"},
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=session_id,
        label=None,
        agent_id=None,
        spawned_by="controller",
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": fuzzy_key}


@pytest.mark.asyncio
async def test_resolve_key_by_key_accepts_parent_session_key_for_spawned_by_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    parent_key = "agent:main:main"
    child_key = "launch:mode:workspace_affinity:task:91:operator:1:thread:child-parent-filter"
    await database.append_control_chat_message(
        role="assistant",
        content="Child transcript payload",
        mission_id=None,
        session_key=child_key,
        created_at="2026-01-02T03:04:05Z",
    )
    await database.upsert_gateway_session_metadata(
        session_key=child_key,
        metadata={"parentSessionKey": parent_key},
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=child_key,
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=parent_key,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": child_key}


@pytest.mark.asyncio
async def test_resolve_key_by_key_prefers_latest_controller_owner_over_stale_spawned_by(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    old_parent_key = "agent:main:subagent:old-parent"
    new_parent_key = "agent:main:subagent:new-parent"
    child_key = "agent:main:subagent:moved-child"
    await database.append_control_chat_message(
        role="assistant",
        content="Moved child transcript payload",
        mission_id=None,
        session_key=child_key,
        created_at="2026-01-02T03:04:05Z",
    )
    await database.upsert_gateway_session_metadata(
        session_key=child_key,
        metadata={
            "spawnedBy": old_parent_key,
            "controllerSessionKey": new_parent_key,
            "requesterSessionKey": new_parent_key,
        },
    )

    with pytest.raises(ValueError, match="unknown session key"):
        await GatewaySessionsService(database).resolve_key(
            key=child_key,
            session_id=None,
            label=None,
            agent_id=None,
            spawned_by=old_parent_key,
            include_global=True,
            include_unknown=True,
        )

    payload = await GatewaySessionsService(database).resolve_key(
        key=child_key,
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=new_parent_key,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": child_key}


@pytest.mark.asyncio
async def test_owner_alias_metadata_is_canonicalized_for_filters_snapshot_and_child_sessions(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    parent_key = "agent:main:main"
    latest_owner_child_key = "agent:main:subagent:latest-owner-alias"
    fallback_owner_child_key = "agent:main:subagent:fallback-owner-alias"

    for session_key, content in (
        (parent_key, "Parent transcript payload"),
        (latest_owner_child_key, "Latest-owner child transcript payload"),
        (fallback_owner_child_key, "Fallback-owner child transcript payload"),
    ):
        await database.append_control_chat_message(
            role="assistant",
            content=content,
            mission_id=None,
            session_key=session_key,
            created_at="2026-01-02T03:04:05Z",
        )

    await database.upsert_gateway_session_metadata(
        session_key=parent_key,
        metadata={},
    )
    await database.upsert_gateway_session_metadata(
        session_key=latest_owner_child_key,
        metadata={
            "controllerSessionKey": " MAIN ",
            "requesterSessionKey": "main",
        },
    )
    await database.upsert_gateway_session_metadata(
        session_key=fallback_owner_child_key,
        metadata={
            "spawnedBy": " main ",
            "parentSessionKey": " MAIN ",
        },
    )

    service = GatewaySessionsService(database)

    assert await service.resolve_key(
        key=latest_owner_child_key,
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=parent_key,
        include_global=True,
        include_unknown=True,
    ) == {"ok": True, "key": latest_owner_child_key}
    assert await service.resolve_key(
        key=fallback_owner_child_key,
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=parent_key,
        include_global=True,
        include_unknown=True,
    ) == {"ok": True, "key": fallback_owner_child_key}

    snapshot = await service.build_snapshot(
        include_global=True,
        include_unknown=True,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=parent_key,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_002_345,
    )
    latest_owner_payload = await service.build_session_payload_for_key(
        session_key=latest_owner_child_key,
        now_ms=1_700_000_002_345,
    )
    fallback_owner_payload = await service.build_session_payload_for_key(
        session_key=fallback_owner_child_key,
        now_ms=1_700_000_002_345,
    )
    parent_payload = await service.build_session_payload_for_key(
        session_key=parent_key,
        now_ms=1_700_000_002_345,
    )

    assert {session["key"] for session in snapshot["sessions"]} == {
        latest_owner_child_key,
        fallback_owner_child_key,
    }
    assert latest_owner_payload is not None
    assert fallback_owner_payload is not None
    assert parent_payload is not None
    assert latest_owner_payload["spawnedBy"] == parent_key
    assert latest_owner_payload["parentSessionKey"] == parent_key
    assert fallback_owner_payload["spawnedBy"] == parent_key
    assert fallback_owner_payload["parentSessionKey"] == parent_key
    assert set(parent_payload["childSessions"]) == {
        latest_owner_child_key,
        fallback_owner_child_key,
    }


@pytest.mark.asyncio
async def test_resolve_key_session_id_prefilters_visibility_before_duplicate_preference(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_id = "shared-main-thread"
    global_key = "launch:mode:workspace_affinity"
    visible_key = resolve_thread_session_keys(
        base_session_key="launch:mode:saved_lane:task:9:operator:1",
        thread_id=session_id,
    ).session_key

    for session_key, name in (
        (global_key, "Hidden global duplicate"),
        (visible_key, "Visible duplicate"),
    ):
        await database.create_mission(
            name=name,
            objective="Resolve sessionId duplicates after applying visibility filters.",
            status="completed",
            instance_id=7,
            project_id=None,
            thread_id=session_id,
            session_key=session_key,
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

    _set_mission_updated_at(
        database,
        session_key=global_key,
        updated_at="2026-01-01T00:00:00Z",
    )
    _set_mission_updated_at(
        database,
        session_key=visible_key,
        updated_at="2025-01-01T00:00:00Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=session_id,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=False,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": visible_key}


@pytest.mark.asyncio
async def test_resolve_key_rejects_multiple_primary_selectors_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    with pytest.raises(
        ValueError,
        match=r"Provide either key, sessionId, or label \(not multiple\)",
    ):
        await GatewaySessionsService(database).resolve_key(
            key="launch:mode:workspace_affinity",
            session_id="thread-abc",
            label=None,
            agent_id=None,
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_requires_a_nonblank_primary_selector_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    with pytest.raises(ValueError, match="Either key, sessionId, or label is required"):
        await GatewaySessionsService(database).resolve_key(
            key="   ",
            session_id="\n\t",
            label="  ",
            agent_id=None,
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_requires_primary_selector_even_with_spawned_by_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    with pytest.raises(ValueError, match="Either key, sessionId, or label is required"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=None,
            label=None,
            agent_id=None,
            spawned_by="controller",
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_requires_primary_selector_even_with_agent_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    with pytest.raises(ValueError, match="Either key, sessionId, or label is required"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=None,
            label=None,
            agent_id="main",
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_key_lookup_ignores_include_global_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    global_key = "launch:mode:workspace_affinity"

    payload = await GatewaySessionsService(database).resolve_key(
        key=global_key,
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=False,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": global_key}


@pytest.mark.asyncio
async def test_resolve_key_key_lookup_ignores_include_unknown_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    await database.append_control_chat_message(
        role="assistant",
        content="Unknown session transcript",
        mission_id=None,
        session_key="unknown",
        created_at="2026-01-02T03:04:05Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key="unknown",
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=True,
        include_unknown=False,
    )

    assert payload == {"ok": True, "key": "unknown"}


@pytest.mark.asyncio
async def test_resolve_key_key_lookup_ignores_agent_filter_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    await database.append_control_chat_message(
        role="assistant",
        content="Unknown session transcript",
        mission_id=None,
        session_key="unknown",
        created_at="2026-01-02T03:04:05Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key="unknown",
        session_id=None,
        label=None,
        agent_id="main",
        spawned_by=None,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": "unknown"}


@pytest.mark.asyncio
async def test_resolve_key_key_lookup_allows_legacy_launch_session_with_agent_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "launch:mode:workspace_affinity:task:77:operator:1:thread:legacy-key"
    await database.append_control_chat_message(
        role="assistant",
        content="Legacy launch session transcript",
        mission_id=None,
        session_key=session_key,
        created_at="2026-01-02T03:04:05Z",
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=session_key,
        session_id=None,
        label=None,
        agent_id="main",
        spawned_by=None,
        include_global=True,
        include_unknown=True,
    )

    assert payload == {"ok": True, "key": session_key}


@pytest.mark.asyncio
async def test_key_lookup_accepts_default_agent_request_key_alias_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    stored_key = "agent:main:thread:worker-123"
    await database.append_control_chat_message(
        role="assistant",
        content="Agent thread transcript",
        mission_id=None,
        session_key=stored_key,
        created_at="2026-01-02T03:04:05Z",
    )

    service = GatewaySessionsService(database)
    payload = await service.resolve_key(
        key="thread:worker-123",
        session_id=None,
        label=None,
        agent_id=None,
        spawned_by=None,
        include_global=True,
        include_unknown=True,
    )
    session_payload = await service.build_session_payload_for_key(
        session_key="thread:worker-123",
        now_ms=1_700_000_000_987,
    )

    assert payload == {"ok": True, "key": stored_key}
    assert session_payload is not None
    assert session_payload["key"] == stored_key
    assert session_payload["sessionId"] == "worker-123"


@pytest.mark.asyncio
async def test_resolve_key_session_id_lookup_rejects_legacy_launch_session_for_agent_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "launch:mode:workspace_affinity:task:77:operator:1:thread:legacy-thread"
    await database.create_mission(
        name="Legacy launch session",
        objective="Reject non-agent sessions when agentId filtering is requested.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="legacy-thread",
        session_key=session_key,
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

    with pytest.raises(ValueError, match="unknown sessionId"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id="legacy-thread",
            label=None,
            agent_id="main",
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_label_lookup_rejects_legacy_launch_session_for_agent_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "launch:mode:workspace_affinity:task:77:operator:1:thread:legacy-label"
    await database.append_control_chat_message(
        role="assistant",
        content="Legacy launch session transcript",
        mission_id=None,
        session_key=session_key,
        created_at="2026-01-02T03:04:05Z",
    )
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "legacy-label"},
    )

    with pytest.raises(ValueError, match="unknown session label"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=None,
            label="legacy-label",
            agent_id="main",
            spawned_by=None,
            include_global=True,
            include_unknown=True,
        )


@pytest.mark.asyncio
async def test_resolve_key_label_lookup_skips_hidden_metadata_matches(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    visible_key = "launch:mode:workspace_affinity:task:88:operator:1:thread:visible"
    await database.upsert_gateway_session_metadata(
        session_key="unknown",
        metadata={"label": "shared-label"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=visible_key,
        metadata={"label": "shared-label"},
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=None,
        label="shared-label",
        agent_id=None,
        spawned_by=None,
        include_global=False,
        include_unknown=False,
    )

    assert payload == {"ok": True, "key": visible_key}


@pytest.mark.asyncio
async def test_resolve_key_label_lookup_trims_whitespace_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    visible_key = "launch:mode:workspace_affinity:task:88:operator:1:thread:visible"
    await database.upsert_gateway_session_metadata(
        session_key=visible_key,
        metadata={"label": "shared-label"},
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=None,
        label="  shared-label  ",
        agent_id=None,
        spawned_by=None,
        include_global=False,
        include_unknown=False,
    )

    assert payload == {"ok": True, "key": visible_key}


@pytest.mark.asyncio
async def test_resolve_key_label_lookup_accepts_parent_session_key_for_spawned_by_filter(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    parent_key = "agent:main:main"
    visible_key = "launch:mode:workspace_affinity:task:88:operator:1:thread:visible"
    await database.upsert_gateway_session_metadata(
        session_key=visible_key,
        metadata={"label": "shared-label", "parentSessionKey": parent_key},
    )

    payload = await GatewaySessionsService(database).resolve_key(
        key=None,
        session_id=None,
        label="shared-label",
        agent_id=None,
        spawned_by=parent_key,
        include_global=False,
        include_unknown=False,
    )

    assert payload == {"ok": True, "key": visible_key}


@pytest.mark.asyncio
async def test_resolve_key_rejects_ambiguous_visible_label_matches(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    key_a = "launch:mode:workspace_affinity:task:1:operator:1:thread:alpha"
    key_b = "launch:mode:workspace_affinity:task:2:operator:1:thread:beta"
    await database.upsert_gateway_session_metadata(
        session_key=key_a,
        metadata={"label": "shared-label"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=key_b,
        metadata={"label": "shared-label"},
    )

    with pytest.raises(ValueError, match="multiple sessions found with label: shared-label"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=None,
            label="shared-label",
            agent_id=None,
            spawned_by=None,
            include_global=False,
            include_unknown=False,
        )


@pytest.mark.asyncio
async def test_resolve_key_rejects_too_long_label_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    with pytest.raises(ValueError, match=r"invalid label: too long \(max 512\)"):
        await GatewaySessionsService(database).resolve_key(
            key=None,
            session_id=None,
            label="x" * 513,
            agent_id=None,
            spawned_by=None,
            include_global=False,
            include_unknown=False,
        )


@pytest.mark.asyncio
async def test_build_snapshot_label_filter_trims_whitespace_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    visible_key = "launch:mode:workspace_affinity:task:88:operator:1:thread:visible"
    await database.upsert_gateway_session_metadata(
        session_key=visible_key,
        metadata={"label": "shared-label"},
    )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=False,
        include_unknown=False,
        limit=None,
        active_minutes=None,
        label="  shared-label  ",
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_000_789,
    )

    assert snapshot["count"] == 1
    assert snapshot["sessions"][0]["key"] == visible_key


@pytest.mark.asyncio
async def test_build_snapshot_agent_filter_only_returns_strict_agent_sessions(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    strict_agent_key = "agent:main:thread:agent-visible"
    legacy_launch_key = "launch:mode:workspace_affinity:task:77:operator:1:thread:legacy-visible"
    for session_key, created_at in (
        (strict_agent_key, "2026-01-02T03:04:05Z"),
        (legacy_launch_key, "2026-01-02T03:05:06Z"),
    ):
        await database.append_control_chat_message(
            role="assistant",
            content=f"Transcript for {session_key}",
            mission_id=None,
            session_key=session_key,
            created_at=created_at,
        )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=True,
        include_unknown=True,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id="main",
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_001_000,
    )

    assert snapshot["count"] == 1
    assert [session["key"] for session in snapshot["sessions"]] == [strict_agent_key]


@pytest.mark.asyncio
async def test_build_snapshot_hides_cron_run_alias_session_keys_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    cron_key = "agent:main:cron:job-1"
    cron_run_key = "agent:main:cron:job-1:run:run-abc"
    for session_key, created_at in (
        (cron_key, "2026-01-02T03:04:05Z"),
        (cron_run_key, "2026-01-02T03:05:06Z"),
    ):
        await database.append_control_chat_message(
            role="assistant",
            content=f"Transcript for {session_key}",
            mission_id=None,
            session_key=session_key,
            created_at=created_at,
        )

    snapshot = await GatewaySessionsService(database).build_snapshot(
        include_global=False,
        include_unknown=False,
        limit=None,
        active_minutes=None,
        label=None,
        spawned_by=None,
        agent_id=None,
        search=None,
        include_derived_titles=False,
        include_last_message=False,
        now_ms=1_700_000_001_234,
    )

    keys = [session["key"] for session in snapshot["sessions"]]
    assert cron_key in keys
    assert cron_run_key not in keys


@pytest.mark.asyncio
async def test_build_session_payload_for_unsuffixed_session_uses_thread_kind_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    session_key = "agent:main:cron:job-1"
    await database.append_control_chat_message(
        role="assistant",
        content="Transcript for agent cron base session",
        mission_id=None,
        session_key=session_key,
        created_at="2026-01-02T03:04:05Z",
    )

    payload = await GatewaySessionsService(database).build_session_payload_for_key(
        session_key=session_key,
        now_ms=1_700_000_001_456,
    )

    assert payload is not None
    assert payload["key"] == session_key
    assert payload["kind"] == "thread"
    assert payload["displayName"] == "OpenZues Control Chat Thread"


@pytest.mark.asyncio
async def test_session_payload_and_changed_event_surface_child_sessions_with_latest_owner(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-sessions.db")
    await database.initialize()

    old_parent_key = "agent:main:subagent:old-parent"
    new_parent_key = "agent:main:subagent:new-parent"
    moved_child_key = "agent:main:subagent:moved-child"
    dashboard_child_key = "agent:main:dashboard:child"

    for session_key, content in (
        (old_parent_key, "Old parent transcript"),
        (new_parent_key, "New parent transcript"),
        (moved_child_key, "Moved child transcript"),
        (dashboard_child_key, "Dashboard child transcript"),
    ):
        await database.append_control_chat_message(
            role="assistant",
            content=content,
            mission_id=None,
            session_key=session_key,
            created_at="2026-01-02T03:04:05Z",
        )

    await database.upsert_gateway_session_metadata(
        session_key=old_parent_key,
        metadata={},
    )
    await database.upsert_gateway_session_metadata(
        session_key=new_parent_key,
        metadata={},
    )
    await database.upsert_gateway_session_metadata(
        session_key=moved_child_key,
        metadata={
            "spawnedBy": old_parent_key,
            "controllerSessionKey": new_parent_key,
            "requesterSessionKey": new_parent_key,
        },
    )
    await database.upsert_gateway_session_metadata(
        session_key=dashboard_child_key,
        metadata={"parentSessionKey": new_parent_key},
    )

    service = GatewaySessionsService(database)
    new_parent_payload = await service.build_session_payload_for_key(
        session_key=new_parent_key,
        now_ms=1_700_000_001_789,
    )
    old_parent_payload = await service.build_session_payload_for_key(
        session_key=old_parent_key,
        now_ms=1_700_000_001_789,
    )
    moved_child_payload = await service.build_session_payload_for_key(
        session_key=moved_child_key,
        now_ms=1_700_000_001_789,
    )
    changed_payload = await service.build_changed_event_payload(
        session_key=new_parent_key,
        reason="patched",
        now_ms=1_700_000_001_789,
    )

    assert new_parent_payload is not None
    assert old_parent_payload is not None
    assert moved_child_payload is not None
    assert set(new_parent_payload["childSessions"]) == {moved_child_key, dashboard_child_key}
    assert "childSessions" not in old_parent_payload
    assert moved_child_payload["spawnedBy"] == new_parent_key
    assert moved_child_payload["parentSessionKey"] == new_parent_key
    assert set(changed_payload["childSessions"]) == {moved_child_key, dashboard_child_key}
