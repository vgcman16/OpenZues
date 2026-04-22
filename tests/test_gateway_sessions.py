from __future__ import annotations

from pathlib import Path

import pytest

from openzues.database import Database
from openzues.services.gateway_session_compaction import GatewaySessionCompactionService
from openzues.services.gateway_sessions import GatewaySessionsService


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
    assert message_payload["message"]["content"][0]["text"] == "Delta line 1"

    assert changed_payload is not None
    assert changed_payload["sessionKey"] == session_key
    assert changed_payload["compactionCheckpointCount"] == 1
    assert changed_payload["latestCompactionCheckpoint"]["checkpointId"] == checkpoint_id
    assert changed_payload["phase"] == "message"
