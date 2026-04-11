from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from openzues.schemas import MissionCreate, MissionDraftView, MissionView

FollowupKind = Literal["checkpoint_hardener", "recovery_run"]


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


def _followup_identity(
    *,
    name: str,
    objective: str,
    instance_id: int,
    project_id: int | None,
    thread_id: str | None,
    cwd: str | None,
) -> tuple[FollowupKind, int, int | None, str, str | None, str] | None:
    kind = classify_followup_kind(name, objective)
    if kind is None or not thread_id:
        return None
    return (kind, instance_id, project_id, thread_id, cwd, name)


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
        cwd=mission.cwd,
    )
    payload_identity = _followup_identity(
        name=payload.name,
        objective=payload.objective,
        instance_id=payload.instance_id,
        project_id=payload.project_id,
        thread_id=payload.thread_id,
        cwd=payload_cwd,
    )
    if mission_identity is not None and payload_identity is not None:
        return mission_identity == payload_identity
    return (
        mission.instance_id == payload.instance_id
        and mission.project_id == payload.project_id
        and mission.thread_id == payload.thread_id
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
        cwd=mission.get("cwd"),
    )
    payload_identity = _followup_identity(
        name=payload.name,
        objective=payload.objective,
        instance_id=payload.instance_id,
        project_id=payload.project_id,
        thread_id=payload.thread_id,
        cwd=cwd,
    )
    if mission_identity is not None and payload_identity is not None:
        return mission_identity == payload_identity
    return (
        int(mission.get("instance_id") or 0) == payload.instance_id
        and mission.get("project_id") == payload.project_id
        and mission.get("thread_id") == payload.thread_id
        and mission.get("cwd") == cwd
        and mission.get("name") == payload.name
        and mission.get("objective") == payload.objective
    )
