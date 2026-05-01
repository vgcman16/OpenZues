from __future__ import annotations

import pytest


def test_acp_session_store_creates_updates_and_touches_sessions() -> None:
    from openzues.services.acp_session_store import create_in_memory_session_store

    now = 1000

    def clock() -> int:
        return now

    store = create_in_memory_session_store(now=clock)

    session = store.create_session(
        session_key="agent:main:main",
        cwd=r"C:\work",
        session_id="session-1",
    )
    assert session["sessionId"] == "session-1"
    assert session["createdAt"] == 1000
    assert session["lastTouchedAt"] == 1000

    now = 1500
    updated = store.create_session(
        session_key="agent:main:other",
        cwd=r"C:\work\other",
        session_id="session-1",
    )

    assert updated is session
    assert updated["sessionKey"] == "agent:main:other"
    assert updated["cwd"] == r"C:\work\other"
    assert updated["createdAt"] == 1000
    assert updated["lastTouchedAt"] == 1500


def test_acp_session_store_tracks_and_clears_active_runs() -> None:
    from openzues.services.acp_session_store import create_in_memory_session_store

    store = create_in_memory_session_store()
    session = store.create_session(
        session_key="agent:main:main",
        cwd=r"C:\work",
        session_id="session-1",
    )
    aborts: list[str] = []

    store.set_active_run("session-1", "run-1", lambda: aborts.append("run-1"))

    assert session["activeRunId"] == "run-1"
    assert store.get_session_by_run_id("run-1") is session

    store.clear_active_run("session-1")

    assert session["activeRunId"] is None
    assert store.get_session_by_run_id("run-1") is None
    assert aborts == []


def test_acp_session_store_cancel_active_run_aborts_and_unindexes() -> None:
    from openzues.services.acp_session_store import create_in_memory_session_store

    store = create_in_memory_session_store()
    session = store.create_session(
        session_key="agent:main:main",
        cwd=r"C:\work",
        session_id="session-1",
    )
    aborts: list[str] = []

    store.set_active_run("session-1", "run-1", lambda: aborts.append("run-1"))

    assert store.cancel_active_run("session-1") is True
    assert session["activeRunId"] is None
    assert store.get_session_by_run_id("run-1") is None
    assert aborts == ["run-1"]
    assert store.cancel_active_run("session-1") is False


def test_acp_session_store_reaps_idle_sessions_before_limit() -> None:
    from openzues.services.acp_session_store import create_in_memory_session_store

    now = 0

    def clock() -> int:
        return now

    store = create_in_memory_session_store(max_sessions=1, idle_ttl_ms=1000, now=clock)
    store.create_session(session_key="agent:old", cwd=r"C:\old", session_id="old")

    now = 2001
    new_session = store.create_session(session_key="agent:new", cwd=r"C:\new", session_id="new")

    assert new_session["sessionId"] == "new"
    assert store.has_session("old") is False
    assert store.has_session("new") is True


def test_acp_session_store_refuses_limit_when_all_sessions_active() -> None:
    from openzues.services.acp_session_store import create_in_memory_session_store

    store = create_in_memory_session_store(max_sessions=1)
    store.create_session(session_key="agent:main", cwd=r"C:\work", session_id="session-1")
    store.set_active_run("session-1", "run-1", lambda: None)

    with pytest.raises(RuntimeError, match="ACP session limit reached"):
        store.create_session(
            session_key="agent:other",
            cwd=r"C:\other",
            session_id="session-2",
        )
