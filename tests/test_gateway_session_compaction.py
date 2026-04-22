from __future__ import annotations

from pathlib import Path

import pytest

from openzues.database import Database
from openzues.services.gateway_session_compaction import GatewaySessionCompactionService


async def _append_compactable_messages(database: Database, *, session_key: str) -> None:
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


@pytest.mark.asyncio
async def test_manual_compaction_checkpoint_uses_resolved_thread_session_id(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-session-compaction.db")
    await database.initialize()

    session_key = "launch:mode:workspace_affinity:task:77:operator:1:thread:thread-abc"
    await database.create_mission(
        name="Compaction thread mission",
        objective="Persist checkpoint metadata with the thread session id.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-abc",
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
    await _append_compactable_messages(database, session_key=session_key)

    service = GatewaySessionCompactionService(database)
    compacted = await service.compact(
        session_key=session_key,
        max_lines=2,
        now_ms=1_700_000_000_123,
    )
    checkpoint_payload = await service.get_checkpoint(
        session_key=session_key,
        checkpoint_id=str(compacted["checkpointId"]),
    )
    checkpoint = checkpoint_payload["checkpoint"]

    assert checkpoint["sessionId"] == "thread-abc"
    assert checkpoint["preCompaction"]["sessionId"] == "thread-abc"
    assert checkpoint["postCompaction"]["sessionId"] == "thread-abc"


@pytest.mark.asyncio
async def test_summary_compaction_checkpoint_falls_back_to_thread_suffix_session_id(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-session-compaction.db")
    await database.initialize()

    session_key = "openzues:thread:summary-thread"
    await _append_compactable_messages(database, session_key=session_key)

    service = GatewaySessionCompactionService(database)
    compacted = await service.compact(
        session_key=session_key,
        max_lines=None,
        now_ms=1_700_000_000_456,
    )
    checkpoints_payload = await service.list_checkpoints(session_key=session_key)
    checkpoint = checkpoints_payload["checkpoints"][0]

    assert checkpoint["checkpointId"] == compacted["checkpointId"]
    assert checkpoint["sessionId"] == "summary-thread"
    assert checkpoint["preCompaction"]["sessionId"] == "summary-thread"
    assert checkpoint["postCompaction"]["sessionId"] == "summary-thread"


@pytest.mark.asyncio
async def test_compaction_keeps_only_latest_25_checkpoints_like_openclaw(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gateway-session-compaction.db")
    await database.initialize()

    session_key = "openzues:thread:checkpoint-cap"
    service = GatewaySessionCompactionService(database)
    base_now_ms = 1_700_000_100_000

    for index in range(27):
        await _append_compactable_messages(database, session_key=session_key)
        compacted = await service.compact(
            session_key=session_key,
            max_lines=2,
            now_ms=base_now_ms + index,
        )
        assert compacted["compacted"] is True

    checkpoints_payload = await service.list_checkpoints(session_key=session_key)
    checkpoints = checkpoints_payload["checkpoints"]

    assert len(checkpoints) == 25
    assert await database.count_control_chat_compaction_checkpoints(session_key=session_key) == 25
    assert checkpoints[0]["createdAt"] == base_now_ms + 26
    assert checkpoints[-1]["createdAt"] == base_now_ms + 2
