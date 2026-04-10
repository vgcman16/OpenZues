from __future__ import annotations

import pytest

from openzues.database import Database


@pytest.mark.asyncio
async def test_database_round_trip(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.initialize()

    instance_id = await database.create_instance(
        name="Local Codex",
        transport="stdio",
        command="codex",
        args="app-server",
        websocket_url=None,
        cwd=str(tmp_path),
        auto_connect=False,
    )
    await database.append_event(
        instance_id=instance_id,
        thread_id="thread_1",
        method="thread/started",
        payload={"ok": True},
    )

    instances = await database.list_instances()
    events = await database.list_events()

    assert instances[0]["name"] == "Local Codex"
    assert events[0]["payload"]["ok"] is True
