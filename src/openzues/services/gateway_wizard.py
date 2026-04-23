from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from uuid import uuid4

_DEFAULT_SETUP_INSTANCE_NAME = "Local Codex Desktop"


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


def _instance_id_or_none(value: object) -> int | None:
    raw = value.get("id") if isinstance(value, dict) else getattr(value, "id", None)
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def _instance_name_or_none(value: object) -> str | None:
    raw = value.get("name") if isinstance(value, dict) else getattr(value, "name", None)
    return _string_or_none(raw)


def _instance_connected(value: object) -> bool:
    raw = value.get("connected") if isinstance(value, dict) else getattr(value, "connected", False)
    return bool(raw)


def _instance_option_label(value: object, *, name: str) -> str:
    status = "connected" if _instance_connected(value) else "offline"
    return f"{name} ({status})"


@dataclass(slots=True)
class _PendingWizardStep:
    field: str
    payload: dict[str, object]
    optional: bool = False
    transient: bool = False


@dataclass(slots=True)
class _GatewayWizardSession:
    base: dict[str, object]
    patch: dict[str, object] = field(default_factory=dict)
    persisted_patch: dict[str, object] = field(default_factory=dict)
    completed_optional_fields: set[str] = field(default_factory=set)
    completed_transient_fields: set[str] = field(default_factory=set)
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
        "field": field,
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
        payload["initialValue"] = initial_text
    return _PendingWizardStep(field=field, payload=payload, optional=not required)


def _select_step(
    *,
    field: str,
    title: str,
    message: str,
    options: list[dict[str, object]],
    initial_value: object = None,
    required: bool = True,
) -> _PendingWizardStep:
    step_id = str(uuid4())
    payload: dict[str, object] = {
        "id": step_id,
        "field": field,
        "type": "select",
        "title": title,
        "message": message,
        "options": [dict(option) for option in options],
        "executor": "client",
    }
    if not required:
        payload["required"] = False
    initial_text = _string_or_none(initial_value)
    if initial_text is not None:
        payload["initialValue"] = initial_text
    return _PendingWizardStep(field=field, payload=payload, optional=not required)


def _note_step(
    *,
    field: str,
    title: str,
    message: str,
) -> _PendingWizardStep:
    step_id = str(uuid4())
    return _PendingWizardStep(
        field=field,
        payload={
            "id": step_id,
            "field": field,
            "type": "note",
            "title": title,
            "message": message,
            "executor": "client",
        },
        transient=True,
    )


class GatewayWizardService:
    def __init__(
        self,
        *,
        load_session,
        save_session,
        list_instances=None,
    ) -> None:
        self._load_session = load_session
        self._save_session = save_session
        self._list_instances = list_instances
        self._sessions: dict[str, _GatewayWizardSession] = {}

    async def start(
        self,
        *,
        mode: str | None = None,
        flow: str | None = None,
        workspace: str | None = None,
    ) -> dict[str, object]:
        if any(session.status == "running" for session in self._sessions.values()):
            raise ValueError("wizard already running")
        base = await self._load_session()
        session = _GatewayWizardSession(base=dict(base))
        base_mode = _normalized_mode_value(base.get("mode"))
        normalized_mode = _normalized_mode_value(mode)
        normalized_flow = _normalized_flow_value(flow)
        if normalized_mode is not None:
            session.patch["mode"] = normalized_mode
            if normalized_mode == "remote":
                session.patch["flow"] = "advanced"
                session.patch["instance_mode"] = "existing"
                if base_mode != "remote":
                    session.patch["instance_id"] = None
                    session.patch["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME
        if normalized_flow is not None and normalized_mode != "remote":
            session.patch["flow"] = normalized_flow
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
            if pending.transient:
                session.completed_transient_fields.add(pending.field)
            elif pending.optional and _string_or_none(answer.get("value")) is None:
                _clear_optional_step_state(session, pending)
                session.completed_optional_fields.add(pending.field)
            else:
                previous_value = session.merged_value(pending.field)
                if pending.optional:
                    session.completed_optional_fields.add(pending.field)
                else:
                    session.completed_optional_fields.discard(pending.field)
                session.patch[pending.field] = _coerce_answer_value(
                    pending.field,
                    answer.get("value"),
                )
                _apply_dependent_defaults(
                    session,
                    pending.field,
                    previous_value=previous_value,
                    pending_step=pending,
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

    async def _persist_progress(
        self,
        session: _GatewayWizardSession,
    ) -> dict[str, object] | None:
        next_patch = dict(session.patch)
        if next_patch == session.persisted_patch:
            return None
        try:
            await self._save_session(next_patch)
        except Exception as exc:
            session.status = "error"
            session.error = str(exc)
            session.pending_step = None
            return {"done": True, **_status_payload(session)}
        session.persisted_patch = next_patch
        return None

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

        instance_options = await self._load_instance_options()
        _normalize_remote_instance_selection(session, instance_options=instance_options)
        next_step = _build_next_step(session, instance_options=instance_options)
        persist_result = await self._persist_progress(session)
        if persist_result is not None:
            return persist_result
        if next_step is not None:
            session.pending_step = next_step
            return {
                "done": False,
                "step": dict(next_step.payload),
                "status": session.status,
            }

        session.status = "done"
        session.error = None
        return {"done": True, "status": session.status}

    async def _load_instance_options(self) -> list[dict[str, object]]:
        if self._list_instances is None:
            return []
        instances = self._list_instances()
        if inspect.isawaitable(instances):
            instances = await instances
        options: list[dict[str, object]] = []
        for instance in instances or []:
            instance_id = _instance_id_or_none(instance)
            instance_name = _instance_name_or_none(instance)
            if instance_id is None or instance_name is None:
                continue
            options.append(
                {
                    "value": str(instance_id),
                    "label": _instance_option_label(instance, name=instance_name),
                    "instanceName": instance_name,
                }
            )
        return sorted(options, key=lambda option: str(option["label"]).lower())


def _build_next_step(
    session: _GatewayWizardSession,
    *,
    instance_options: list[dict[str, object]] | None = None,
) -> _PendingWizardStep | None:
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

        lane_step = _build_remote_lane_step(
            session,
            instance_options=instance_options or [],
        )
        if lane_step is not None:
            return lane_step

        note_step = _build_remote_lane_note_step(
            session,
            instance_options=instance_options or [],
        )
        if note_step is not None:
            return note_step

    task_name = _string_or_none(session.merged_value("task_name"))
    if task_name is None:
        return _text_step(
            field="task_name",
            title="Task Name",
            message="Name the recurring setup task.",
        )

    return None


def _coerce_answer_value(field: str, value: object) -> str | int:
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
    if field == "instance_id":
        normalized = _require_non_empty_text(value, label="saved lane")
        try:
            instance_id = int(normalized)
        except ValueError as exc:
            raise ValueError("saved lane must be a numeric id") from exc
        if instance_id <= 0:
            raise ValueError("saved lane must be a numeric id")
        return instance_id
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


def _build_remote_lane_step(
    session: _GatewayWizardSession,
    *,
    instance_options: list[dict[str, object]],
) -> _PendingWizardStep | None:
    if not instance_options or "instance_id" in session.completed_optional_fields:
        return None
    option_values = {
        _string_or_none(option.get("value"))
        for option in instance_options
    }
    current_id = _string_or_none(session.merged_value("instance_id"))
    initial_value = current_id if current_id in option_values else ""
    return _select_step(
        field="instance_id",
        title="Saved Lane",
        message="Optionally pin the first remote launch to a saved lane now, or leave it flexible.",
        options=[
            {
                "value": "",
                "label": "Bind at launch time",
                "instanceName": _DEFAULT_SETUP_INSTANCE_NAME,
            },
            *instance_options,
        ],
        initial_value=initial_value,
        required=False,
    )


def _build_remote_lane_note_step(
    session: _GatewayWizardSession,
    *,
    instance_options: list[dict[str, object]],
) -> _PendingWizardStep | None:
    if instance_options or "remote_lane_note" in session.completed_transient_fields:
        return None
    return _note_step(
        field="remote_lane_note",
        title="Lane Binding Can Wait",
        message=(
            "No saved lane is staged yet. Remote setup can still save the workspace, "
            "operator access, and recurring task now, then bind a lane when the first "
            "launch is ready."
        ),
    )


def _clear_optional_step_state(
    session: _GatewayWizardSession,
    pending_step: _PendingWizardStep,
) -> None:
    session.patch[pending_step.field] = None
    if pending_step.field == "instance_id":
        session.patch["instance_mode"] = "existing"
        session.patch["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME


def _find_step_option(
    pending_step: _PendingWizardStep | None,
    value: object,
) -> dict[str, object] | None:
    if pending_step is None:
        return None
    selected_value = _string_or_none(value)
    if selected_value is None:
        return None
    raw_options = pending_step.payload.get("options")
    if not isinstance(raw_options, list):
        return None
    for option in raw_options:
        if not isinstance(option, dict):
            continue
        if _string_or_none(option.get("value")) == selected_value:
            return option
    return None


def _apply_dependent_defaults(
    session: _GatewayWizardSession,
    field: str,
    *,
    previous_value: object = None,
    pending_step: _PendingWizardStep | None = None,
) -> None:
    if field == "mode":
        mode = _normalized_mode_value(session.patch.get("mode"))
        if mode == "remote":
            session.patch["flow"] = "advanced"
            session.patch["instance_mode"] = "existing"
            if _normalized_mode_value(previous_value) != "remote":
                session.patch["instance_id"] = None
                session.patch["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME
        return
    if field != "instance_id":
        return
    session.patch["instance_mode"] = "existing"
    selected_option = _find_step_option(pending_step, session.patch.get("instance_id"))
    selected_name = _string_or_none(
        selected_option.get("instanceName") if selected_option is not None else None
    )
    session.patch["instance_name"] = selected_name or _DEFAULT_SETUP_INSTANCE_NAME


def _normalize_remote_instance_selection(
    session: _GatewayWizardSession,
    *,
    instance_options: list[dict[str, object]],
) -> None:
    if _normalized_mode_value(session.merged_value("mode")) != "remote":
        return
    session.patch["instance_mode"] = "existing"
    current_id = _string_or_none(session.merged_value("instance_id"))
    if current_id is None:
        if _string_or_none(session.merged_value("instance_name")) not in {
            None,
            _DEFAULT_SETUP_INSTANCE_NAME,
        }:
            session.patch["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME
        return
    instance_names = {
        option_value: _string_or_none(option.get("instanceName")) or _DEFAULT_SETUP_INSTANCE_NAME
        for option in instance_options
        if (option_value := _string_or_none(option.get("value"))) is not None
    }
    selected_name = instance_names.get(current_id)
    if selected_name is None:
        session.patch["instance_id"] = None
        session.patch["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME
        return
    if _string_or_none(session.merged_value("instance_name")) != selected_name:
        session.patch["instance_name"] = selected_name


def _status_payload(session: _GatewayWizardSession) -> dict[str, object]:
    payload: dict[str, object] = {"status": session.status}
    if session.error is not None:
        payload["error"] = session.error
    return payload
