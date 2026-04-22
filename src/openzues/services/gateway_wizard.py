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
    optional: bool = False


@dataclass(slots=True)
class _GatewayWizardSession:
    base: dict[str, object]
    patch: dict[str, object] = field(default_factory=dict)
    completed_optional_fields: set[str] = field(default_factory=set)
    status: str = "running"
    error: str | None = None
    pending_step: _PendingWizardStep | None = None

    def merged_value(self, key: str) -> object:
        if key in self.patch:
            return self.patch[key]
        return self.base.get(key)


def _text_step(
    *,
    field: str,
    title: str,
    message: str,
    placeholder: str | None = None,
    initial_value: object = None,
    required: bool = True,
    input_type: str | None = None,
) -> _PendingWizardStep:
    step_id = str(uuid4())
    payload: dict[str, object] = {
        "id": step_id,
        "type": "text",
        "title": title,
        "message": message,
        "executor": "client",
    }
    if placeholder is not None:
        payload["placeholder"] = placeholder
    if not required:
        payload["required"] = False
    if input_type is not None:
        payload["inputType"] = input_type
    initial_text = _string_or_none(initial_value)
    if initial_text is not None:
        payload["initialvalue"] = initial_text
    return _PendingWizardStep(field=field, payload=payload, optional=not required)


def _select_step(
    *,
    field: str,
    title: str,
    message: str,
    options: list[dict[str, object]],
    initial_value: object = None,
) -> _PendingWizardStep:
    step_id = str(uuid4())
    payload: dict[str, object] = {
        "id": step_id,
        "type": "select",
        "title": title,
        "message": message,
        "options": [dict(option) for option in options],
        "executor": "client",
    }
    initial_text = _string_or_none(initial_value)
    if initial_text is not None:
        payload["initialvalue"] = initial_text
    return _PendingWizardStep(field=field, payload=payload)


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
            if pending.optional and _string_or_none(answer.get("value")) is None:
                session.patch.pop(pending.field, None)
                session.completed_optional_fields.add(pending.field)
            else:
                session.completed_optional_fields.discard(pending.field)
                session.patch[pending.field] = _coerce_answer_value(
                    pending.field,
                    answer.get("value"),
                )
                _apply_dependent_defaults(session, pending.field)
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
    mode = _normalized_mode_value(session.merged_value("mode"))
    if mode is None:
        return _select_step(
            field="mode",
            title="Setup Mode",
            message="Choose how you want the gateway wizard to stage setup.",
            options=[
                {
                    "value": "local",
                    "label": "Local",
                    "hint": "Use a local control plane and desktop lane.",
                },
                {
                    "value": "remote",
                    "label": "Remote",
                    "hint": "Stage the workspace spine first and bind a lane later.",
                },
            ],
            initial_value="local",
        )

    flow = _normalized_flow_value(session.merged_value("flow"))
    if mode == "local" and flow is None:
        return _select_step(
            field="flow",
            title="Setup Flow",
            message="Choose how deeply to stage the local bootstrap posture.",
            options=[
                {
                    "value": "quickstart",
                    "label": "QuickStart",
                    "hint": "Reuse the current control plane and tune the rest later.",
                },
                {
                    "value": "advanced",
                    "label": "Advanced",
                    "hint": "Stage the full local control plane posture before bootstrap.",
                },
            ],
            initial_value="quickstart",
        )

    project_path = _string_or_none(session.merged_value("project_path"))
    if project_path is None:
        return _text_step(
            field="project_path",
            title="Workspace",
            message="Enter the workspace path to stage for setup.",
            placeholder="C:/workspace",
        )

    operator_name = _string_or_none(session.merged_value("operator_name"))
    if operator_name is None:
        return _text_step(
            field="operator_name",
            title="Operator Name",
            message=(
                "Name the operator who should receive the remote ingress API key."
                if mode == "remote"
                else "Name the operator who should receive the local bootstrap access."
            ),
            placeholder="Remote Builder" if mode == "remote" else "Operator",
        )

    if mode == "remote":
        operator_email = _string_or_none(session.merged_value("operator_email"))
        if (
            operator_email is None
            and "operator_email" not in session.completed_optional_fields
        ):
            return _text_step(
                field="operator_email",
                title="Operator Email",
                message="Optionally add an email for the remote API key handoff.",
                placeholder="builder@example.com",
                required=False,
                input_type="email",
            )

        team_name = _string_or_none(session.merged_value("team_name"))
        if team_name is None and "team_name" not in session.completed_optional_fields:
            return _text_step(
                field="team_name",
                title="Operator Team",
                message="Optionally group the remote operator under a team label.",
                placeholder="Platform Ops",
                required=False,
            )

    task_name = _string_or_none(session.merged_value("task_name"))
    if task_name is None:
        return _text_step(
            field="task_name",
            title="Task Name",
            message="Name the recurring setup task.",
        )

    return None


def _coerce_answer_value(field: str, value: object) -> str:
    if field == "mode":
        normalized = _normalized_mode_value(value)
        if normalized is None:
            raise ValueError("mode must be local or remote")
        return normalized
    if field == "flow":
        normalized = _normalized_flow_value(value)
        if normalized is None:
            raise ValueError("flow must be quickstart or advanced")
        return normalized
    if field == "project_path":
        return _require_non_empty_text(value, label="workspace")
    if field == "operator_name":
        return _require_non_empty_text(value, label="operator name")
    if field == "task_name":
        return _require_non_empty_text(value, label="task name")
    return _require_non_empty_text(value, label=field)


def _normalized_mode_value(value: object) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"local", "remote"}:
        return lowered
    return None


def _normalized_flow_value(value: object) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"quickstart", "advanced"}:
        return lowered
    return None


def _apply_dependent_defaults(session: _GatewayWizardSession, field: str) -> None:
    if field != "mode":
        return
    mode = _normalized_mode_value(session.patch.get("mode"))
    if mode == "remote":
        session.patch["flow"] = "advanced"


def _status_payload(session: _GatewayWizardSession) -> dict[str, object]:
    payload: dict[str, object] = {"status": session.status}
    if session.error is not None:
        payload["error"] = session.error
    return payload
