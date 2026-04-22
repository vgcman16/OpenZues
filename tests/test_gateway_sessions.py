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
