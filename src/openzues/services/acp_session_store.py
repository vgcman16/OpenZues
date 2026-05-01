from __future__ import annotations

import time
import uuid
from collections.abc import Callable

DEFAULT_MAX_SESSIONS = 5_000
DEFAULT_IDLE_TTL_MS = 24 * 60 * 60 * 1_000
AcpAbortCallback = Callable[[], object]
AcpSession = dict[str, object]


class InMemoryAcpSessionStore:
    def __init__(
        self,
        *,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        idle_ttl_ms: int = DEFAULT_IDLE_TTL_MS,
        now: Callable[[], int | float] | None = None,
    ) -> None:
        self.max_sessions = max(1, max_sessions)
        self.idle_ttl_ms = max(1_000, idle_ttl_ms)
        self._now = now or (lambda: int(time.time() * 1000))
        self._sessions: dict[str, AcpSession] = {}
        self._run_id_to_session_id: dict[str, str] = {}

    def _now_ms(self) -> int:
        return int(self._now())

    def _touch_session(self, session: AcpSession, now_ms: int | None = None) -> None:
        session["lastTouchedAt"] = self._now_ms() if now_ms is None else now_ms

    def _remove_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        active_run_id = session.get("activeRunId")
        if isinstance(active_run_id, str):
            self._run_id_to_session_id.pop(active_run_id, None)
        abort = session.get("abort")
        if callable(abort):
            abort()
        del self._sessions[session_id]
        return True

    def _reap_idle_sessions(self, now_ms: int) -> None:
        idle_before = now_ms - self.idle_ttl_ms
        for session_id, session in list(self._sessions.items()):
            if session.get("activeRunId") or session.get("abort"):
                continue
            last_touched_at = session.get("lastTouchedAt")
            if isinstance(last_touched_at, int | float) and last_touched_at > idle_before:
                continue
            self._remove_session(session_id)

    def _evict_oldest_idle_session(self) -> bool:
        oldest_session_id: str | None = None
        oldest_last_touched_at = float("inf")
        for session_id, session in self._sessions.items():
            if session.get("activeRunId") or session.get("abort"):
                continue
            last_touched_at = session.get("lastTouchedAt")
            if not isinstance(last_touched_at, int | float):
                continue
            if last_touched_at >= oldest_last_touched_at:
                continue
            oldest_last_touched_at = float(last_touched_at)
            oldest_session_id = session_id
        if oldest_session_id is None:
            return False
        return self._remove_session(oldest_session_id)

    def create_session(
        self,
        *,
        session_key: str,
        cwd: str,
        session_id: str | None = None,
    ) -> AcpSession:
        now_ms = self._now_ms()
        resolved_session_id = session_id or str(uuid.uuid4())
        existing_session = self._sessions.get(resolved_session_id)
        if existing_session is not None:
            existing_session["sessionKey"] = session_key
            existing_session["cwd"] = cwd
            self._touch_session(existing_session, now_ms)
            return existing_session
        self._reap_idle_sessions(now_ms)
        if len(self._sessions) >= self.max_sessions and not self._evict_oldest_idle_session():
            raise RuntimeError(
                f"ACP session limit reached (max {self.max_sessions}). "
                "Close idle ACP clients and retry."
            )
        session: AcpSession = {
            "sessionId": resolved_session_id,
            "sessionKey": session_key,
            "cwd": cwd,
            "createdAt": now_ms,
            "lastTouchedAt": now_ms,
            "abort": None,
            "activeRunId": None,
        }
        self._sessions[resolved_session_id] = session
        return session

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def get_session(self, session_id: str) -> AcpSession | None:
        session = self._sessions.get(session_id)
        if session is not None:
            self._touch_session(session)
        return session

    def get_session_by_run_id(self, run_id: str) -> AcpSession | None:
        session_id = self._run_id_to_session_id.get(run_id)
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session is not None:
            self._touch_session(session)
        return session

    def set_active_run(
        self,
        session_id: str,
        run_id: str,
        abort: AcpAbortCallback,
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session["activeRunId"] = run_id
        session["abort"] = abort
        self._run_id_to_session_id[run_id] = session_id
        self._touch_session(session)

    def clear_active_run(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        active_run_id = session.get("activeRunId")
        if isinstance(active_run_id, str):
            self._run_id_to_session_id.pop(active_run_id, None)
        session["activeRunId"] = None
        session["abort"] = None
        self._touch_session(session)

    def cancel_active_run(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None or not callable(session.get("abort")):
            return False
        abort = session["abort"]
        if callable(abort):
            abort()
        active_run_id = session.get("activeRunId")
        if isinstance(active_run_id, str):
            self._run_id_to_session_id.pop(active_run_id, None)
        session["activeRunId"] = None
        session["abort"] = None
        self._touch_session(session)
        return True

    def clear_all_sessions_for_test(self) -> None:
        for session in self._sessions.values():
            abort = session.get("abort")
            if callable(abort):
                abort()
        self._sessions.clear()
        self._run_id_to_session_id.clear()


def create_in_memory_session_store(
    *,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
    idle_ttl_ms: int = DEFAULT_IDLE_TTL_MS,
    now: Callable[[], int | float] | None = None,
) -> InMemoryAcpSessionStore:
    return InMemoryAcpSessionStore(
        max_sessions=max_sessions,
        idle_ttl_ms=idle_ttl_ms,
        now=now,
    )


default_acp_session_store = create_in_memory_session_store()
