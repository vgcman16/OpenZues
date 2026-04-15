from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from openzues.schemas import MissionCreate, MissionDraftView, MissionView

FollowupKind = Literal["checkpoint_hardener", "recovery_run"]


def _normalize_session_identity(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def _conversation_target_key(
    target: Mapping[str, Any] | Any | None,
) -> tuple[str, str, str, str] | None:
    if target is None:
        return None
    if isinstance(target, Mapping):
        channel = str(target.get("channel") or "").strip().lower()
        account_id = str(target.get("account_id") or "").strip().lower()
        peer_kind = str(target.get("peer_kind") or "").strip().lower()
        peer_id = str(target.get("peer_id") or "").strip().lower()
    else:
        channel = str(getattr(target, "channel", "") or "").strip().lower()
        account_id = str(getattr(target, "account_id", "") or "").strip().lower()
        peer_kind = str(getattr(target, "peer_kind", "") or "").strip().lower()
        peer_id = str(getattr(target, "peer_id", "") or "").strip().lower()
    if not channel:
        return None
    return (channel, account_id, peer_kind, peer_id)


def classify_followup_kind(name: str, objective: str) -> FollowupKind | None:
    normalized_name = name.strip()
    normalized_objective = " ".join(objective.split())
    if normalized_name.startswith("Recover ") and normalized_objective.startswith(
        "Continue the mission '"
    ):
        return "recovery_run"
    if normalized_name.startswith("Harden ") and normalized_objective.startswith(
        "Continue from the latest checkpoint in the mission '"
    ):
        return "checkpoint_hardener"
    return None


def mission_followup_kind(
    mission: MissionCreate | MissionDraftView | MissionView,
) -> FollowupKind | None:
    return classify_followup_kind(mission.name, mission.objective)


def _normalize_workspace_identity(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    while "\\\\" in normalized:
        normalized = normalized.replace("\\\\", "\\")
    normalized = normalized.replace("/", "\\")
    return normalized.lower()


def _mission_lineage_key(mission: MissionView) -> tuple[str, ...]:
    task_blueprint_id = mission.task_blueprint_id
    if task_blueprint_id is not None:
        return (
            "task",
            str(task_blueprint_id),
            str(mission.instance_id),
            str(mission.project_id),
        )
    session_key = _normalize_session_identity(mission.session_key)
    if session_key is not None:
        return ("session", session_key)

    workspace_identity = _normalize_workspace_identity(mission.cwd) or ""
    return (
        "workspace",
        str(mission.instance_id),
        str(mission.project_id),
        workspace_identity,
        mission.name.strip().lower(),
    )


def mission_is_passive_queued_followup(
    mission: MissionView,
    missions: Sequence[MissionView],
) -> bool:
    if mission.status != "blocked" or mission.phase != "queued":
        return False
    if mission_followup_kind(mission) != "recovery_run":
        return False
    if not str(mission.last_error or "").startswith("Queued behind mission:"):
        return False

    base_name = mission.name.removeprefix("Recover ").strip()
    for candidate in missions:
        if candidate.id == mission.id:
            continue
        if candidate.instance_id != mission.instance_id:
            continue
        if candidate.status != "active" or not candidate.in_progress:
            continue
        same_thread = bool(mission.thread_id) and mission.thread_id == candidate.thread_id
        same_name = candidate.name.strip() == base_name
        same_project = mission.project_id is not None and mission.project_id == candidate.project_id
        same_cwd = bool(mission.cwd) and mission.cwd == candidate.cwd
        if same_thread or (same_name and (same_project or same_cwd)):
            return True
    return False


def operator_blocked_missions(missions: Sequence[MissionView]) -> list[MissionView]:
    return [
        mission
        for mission in missions
        if mission.status == "blocked" and not mission_is_passive_queued_followup(mission, missions)
    ]


def operator_ready_handoff_missions(
    missions: Sequence[MissionView],
    *,
    statuses: set[str] | None = None,
) -> list[MissionView]:
    allowed_statuses = statuses or {"paused", "completed", "failed"}
    live_lineages = {
        _mission_lineage_key(mission)
        for mission in missions
        if mission.status in {"active", "blocked"}
    }
    latest_by_lineage: dict[tuple[str, ...], MissionView] = {}
    for mission in missions:
        if mission.status not in allowed_statuses:
            continue
        if not mission.last_checkpoint:
            continue
        if mission_followup_kind(mission) is not None:
            continue
        lineage_key = _mission_lineage_key(mission)
        if lineage_key in live_lineages:
            continue
        existing = latest_by_lineage.get(lineage_key)
        if existing is None or mission.updated_at > existing.updated_at:
            latest_by_lineage[lineage_key] = mission
    return sorted(
        latest_by_lineage.values(),
        key=lambda mission: mission.updated_at,
        reverse=True,
    )


def _followup_identity(
    *,
    name: str,
    objective: str,
    instance_id: int,
    project_id: int | None,
    thread_id: str | None,
    session_key: str | None,
    conversation_target: Mapping[str, Any] | Any | None,
    cwd: str | None,
) -> tuple[FollowupKind, int, int | None, tuple[str, str], str | None, str] | None:
    kind = classify_followup_kind(name, objective)
    conversation_identity = _conversation_target_key(conversation_target)
    if conversation_identity is not None:
        key = ("conversation", "|".join(conversation_identity))
    else:
        session_identity = _normalize_session_identity(session_key)
        if session_identity:
            key = ("session", session_identity)
        elif thread_id:
            key = ("thread", thread_id)
        elif kind is not None and project_id is not None:
            key = ("project", str(project_id))
        elif kind is not None and (workspace_identity := _normalize_workspace_identity(cwd)):
            key = ("workspace", workspace_identity)
        else:
            key = None
    if kind is None or key is None:
        return None
    return (kind, instance_id, project_id, key, cwd, name)


def mission_matches_payload(
    mission: MissionView,
    payload: MissionCreate | MissionDraftView,
    *,
    cwd: str | None = None,
) -> bool:
    payload_cwd = cwd if cwd is not None else payload.cwd
    mission_identity = _followup_identity(
        name=mission.name,
        objective=mission.objective,
        instance_id=mission.instance_id,
        project_id=mission.project_id,
        thread_id=mission.thread_id,
        session_key=mission.session_key,
        conversation_target=mission.conversation_target,
        cwd=mission.cwd,
    )
    payload_identity = _followup_identity(
        name=payload.name,
        objective=payload.objective,
        instance_id=payload.instance_id,
        project_id=payload.project_id,
        thread_id=payload.thread_id,
        session_key=payload.session_key,
        conversation_target=payload.conversation_target,
        cwd=payload_cwd,
    )
    if mission_identity is not None and payload_identity is not None:
        return mission_identity == payload_identity
    same_session_key = bool(payload.session_key) and (
        _normalize_session_identity(mission.session_key)
        == _normalize_session_identity(payload.session_key)
    )
    return (
        mission.instance_id == payload.instance_id
        and mission.project_id == payload.project_id
        and (mission.thread_id == payload.thread_id or same_session_key)
        and mission.cwd == payload_cwd
        and mission.name == payload.name
        and mission.objective == payload.objective
    )


def mission_row_matches_payload(
    mission: Mapping[str, Any],
    payload: MissionCreate,
    *,
    cwd: str | None,
) -> bool:
    mission_identity = _followup_identity(
        name=str(mission.get("name") or ""),
        objective=str(mission.get("objective") or ""),
        instance_id=int(mission.get("instance_id") or 0),
        project_id=mission.get("project_id"),
        thread_id=mission.get("thread_id"),
        session_key=mission.get("session_key"),
        conversation_target=mission.get("conversation_target"),
        cwd=mission.get("cwd"),
    )
    payload_identity = _followup_identity(
        name=payload.name,
        objective=payload.objective,
        instance_id=payload.instance_id,
        project_id=payload.project_id,
        thread_id=payload.thread_id,
        session_key=payload.session_key,
        conversation_target=payload.conversation_target,
        cwd=cwd,
    )
    if mission_identity is not None and payload_identity is not None:
        return mission_identity == payload_identity
    same_session_key = bool(payload.session_key) and (
        _normalize_session_identity(mission.get("session_key"))
        == _normalize_session_identity(payload.session_key)
    )
    return (
        int(mission.get("instance_id") or 0) == payload.instance_id
        and mission.get("project_id") == payload.project_id
        and (mission.get("thread_id") == payload.thread_id or same_session_key)
        and mission.get("cwd") == cwd
        and mission.get("name") == payload.name
        and mission.get("objective") == payload.objective
    )
