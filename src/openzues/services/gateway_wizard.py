from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if isinstance(value, (int, float, bool)):
        normalized = str(value).strip()
        return normalized or None
    return None


def _require_non_empty_text(value: object, *, label: str) -> str:
    normalized = _string_or_none(value)
    if normalized is None:
        raise ValueError(f"{label} must be a non-empty string")
    return normalized


@dataclass(slots=True)
class _PendingWizardStep:
    field: str
    payload: dict[str, object]


@dataclass(slots=True)
class _GatewayWizardSession:
    base: dict[str, object]
    patch: dict[str, object] = field(default_factory=dict)
    status: str = "running"
    error: str | None = None
    pending_step: _PendingWizardStep | None = None

    def merged_value(self, key: str) -> object:
        if key in self.patch:
            return self.patch[key]
        return self.base.get(key)


class GatewayWizardService:
    def __init__(
        self,
        *,
        load_session,
        save_session,
    ) -> None:
        self._load_session = load_session
        self._save_session = save_session
        self._sessions: dict[str, _GatewayWizardSession] = {}

    async def start(
        self,
        *,
        mode: str | None = None,
        workspace: str | None = None,
    ) -> dict[str, object]:
        if any(session.status == "running" for session in self._sessions.values()):
            raise ValueError("wizard already running")
        base = await self._load_session()
        session = _GatewayWizardSession(base=dict(base))
        if mode is not None:
            session.patch["mode"] = mode
            if mode == "remote":
                session.patch["flow"] = "advanced"
        if workspace is not None:
            session.patch["project_path"] = workspace
        session_id = str(uuid4())
        self._sessions[session_id] = session
        result = await self._advance(session_id, session)
        if result.get("done") is True:
            self._sessions.pop(session_id, None)
        return {"sessionId": session_id, **result}

    async def next(
        self,
        *,
        session_id: str,
        answer: dict[str, object] | None = None,
    ) -> dict[str, object]:
        session = self._require_session(session_id)
        if answer is not None:
            if session.status != "running":
                raise ValueError("wizard not running")
            pending = session.pending_step
            step_id = _require_non_empty_text(answer.get("stepId"), label="stepId")
            if pending is None or str(pending.payload.get("id") or "") != step_id:
                raise ValueError("wizard: no pending step")
            session.pending_step = None
            session.patch[pending.field] = _coerce_answer_value(
                pending.field,
                answer.get("value"),
            )
        result = await self._advance(session_id, session)
        if result.get("done") is True:
            self._sessions.pop(session_id, None)
        return result

    async def cancel(self, *, session_id: str) -> dict[str, object]:
        session = self._require_session(session_id)
        session.status = "cancelled"
        session.error = "cancelled"
        session.pending_step = None
        self._sessions.pop(session_id, None)
        return _status_payload(session)

    async def status(self, *, session_id: str) -> dict[str, object]:
        session = self._require_session(session_id)
        return _status_payload(session)

    def _require_session(self, session_id: str) -> _GatewayWizardSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("wizard not found")
        return session

    async def _advance(
        self,
        session_id: str,
        session: _GatewayWizardSession,
    ) -> dict[str, object]:
        if session.pending_step is not None:
            return {
                "done": False,
                "step": dict(session.pending_step.payload),
                "status": session.status,
            }
        if session.status != "running":
            return {"done": True, **_status_payload(session)}

        next_step = _build_next_step(session)
        if next_step is not None:
            session.pending_step = next_step
            return {
                "done": False,
                "step": dict(next_step.payload),
                "status": session.status,
            }

        try:
            await self._save_session(dict(session.patch))
        except Exception as exc:
            session.status = "error"
            session.error = str(exc)
            return {"done": True, **_status_payload(session)}

        session.status = "done"
        session.error = None
        return {"done": True, "status": session.status}


def _build_next_step(session: _GatewayWizardSession) -> _PendingWizardStep | None:
    project_path = _string_or_none(session.merged_value("project_path"))
    if project_path is None:
        step_id = str(uuid4())
        return _PendingWizardStep(
            field="project_path",
            payload={
                "id": step_id,
                "type": "text",
                "title": "Workspace",
                "message": "Enter the workspace path to stage for setup.",
                "placeholder": "C:/workspace",
                "executor": "client",
            },
        )

    task_name = _string_or_none(session.merged_value("task_name"))
    if task_name is None:
        step_id = str(uuid4())
        return _PendingWizardStep(
            field="task_name",
            payload={
                "id": step_id,
                "type": "text",
                "title": "Task Name",
                "message": "Name the recurring setup task.",
                "executor": "client",
            },
        )

    return None


def _coerce_answer_value(field: str, value: object) -> str:
    if field == "project_path":
        return _require_non_empty_text(value, label="workspace")
    if field == "task_name":
        return _require_non_empty_text(value, label="task name")
    return _require_non_empty_text(value, label=field)


def _status_payload(session: _GatewayWizardSession) -> dict[str, object]:
    payload: dict[str, object] = {"status": session.status}
    if session.error is not None:
        payload["error"] = session.error
    return payload
