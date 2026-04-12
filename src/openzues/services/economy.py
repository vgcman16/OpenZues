from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openzues.schemas import (
    DashboardEconomyScopeView,
    DashboardEconomyView,
    EconomyState,
    MissionView,
    ProjectView,
    RemoteRequestView,
    TaskBlueprintView,
)
from openzues.services.run_pressure import scope_checkpoint_pressure_threshold
from openzues.services.scope_enforcer import build_scope_assessment


@dataclass(frozen=True, slots=True)
class _Scope:
    key: str
    project_id: int | None
    label: str


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _scope_from_cwd(cwd: str) -> _Scope:
    name = Path(cwd).name or "Attached workspace"
    return _Scope(key=f"cwd:{cwd.lower()}", project_id=None, label=name)


def _scope_for_mission(
    mission: MissionView,
    projects_by_id: dict[int, ProjectView],
) -> _Scope | None:
    if mission.project_id is not None:
        project = projects_by_id.get(mission.project_id)
        if project is not None:
            return _Scope(
                key=f"project:{project.id}",
                project_id=project.id,
                label=project.label,
            )
    if mission.cwd:
        return _scope_from_cwd(mission.cwd)
    return None


def _scope_for_task(
    task: TaskBlueprintView,
    projects_by_id: dict[int, ProjectView],
) -> _Scope | None:
    if task.project_id is not None:
        project = projects_by_id.get(task.project_id)
        if project is not None:
            return _Scope(
                key=f"project:{project.id}",
                project_id=project.id,
                label=project.label,
            )
    if task.cwd:
        return _scope_from_cwd(task.cwd)
    return None


def _scope_for_request(
    request: RemoteRequestView,
    missions_by_id: dict[int, MissionView],
    tasks_by_id: dict[int, TaskBlueprintView],
    projects_by_id: dict[int, ProjectView],
) -> _Scope | None:
    if request.target_kind == "mission" and request.target_id is not None:
        mission = missions_by_id.get(request.target_id)
        if mission is not None:
            return _scope_for_mission(mission, projects_by_id)
    if request.target_kind == "task" and request.target_id is not None:
        task = tasks_by_id.get(request.target_id)
        if task is not None:
            return _scope_for_task(task, projects_by_id)
    return None


def _freshness_minutes(missions: list[MissionView]) -> int | None:
    timestamps = [
        parsed
        for parsed in (_parse_timestamp(mission.last_activity_at) for mission in missions)
        if parsed is not None
    ]
    if not timestamps:
        return None
    freshest = max(timestamps)
    return max(0, int((datetime.now(UTC) - freshest).total_seconds() // 60))


def _checkpoint_efficiency(
    *,
    checkpoint_count: int,
    token_burn: int,
    command_burn: int,
    failure_count: int,
    approval_count: int,
    remote_pressure_count: int,
) -> float:
    capital_units = (
        max(token_burn / 10000, 0.0)
        + max(command_burn / 10, 0.0)
        + failure_count * 2.0
        + approval_count * 1.5
        + remote_pressure_count * 0.5
    )
    if capital_units <= 0:
        return float(checkpoint_count)
    return round(checkpoint_count / capital_units, 2)


def _score_scope(
    *,
    checkpoint_count: int,
    failure_count: int,
    approval_count: int,
    active_count: int,
    task_pressure_count: int,
    remote_pressure_count: int,
    token_burn: int,
    command_burn: int,
    checkpoint_pressure_tokens: int,
    objective_gravity: int,
    drift_mission_count: int,
) -> int:
    score = 45
    score += min(checkpoint_count, 4) * 10
    if checkpoint_count >= 2 and failure_count == 0:
        score += 8
    if checkpoint_count and task_pressure_count:
        score += min(task_pressure_count, 2) * 3
    score -= min(failure_count, 3) * 12
    score -= min(approval_count, 3) * 7
    if token_burn >= checkpoint_pressure_tokens and checkpoint_count == 0:
        score -= 12
    if objective_gravity < 70:
        score -= min(18, (70 - objective_gravity) // 2)
    if command_burn >= 12 and checkpoint_count == 0:
        score -= 8
    if active_count >= 2:
        score -= 6
    if remote_pressure_count >= 3:
        score -= 5
    if drift_mission_count:
        score -= min(18, drift_mission_count * 6)
    if task_pressure_count >= 2 and checkpoint_count == 0:
        score -= 5
    return max(0, min(100, score))


def _state_for_scope(
    *,
    score: int,
    checkpoint_count: int,
    failure_count: int,
    active_count: int,
    token_burn: int,
    command_burn: int,
    freshness_minutes: int | None,
    remote_pressure_count: int,
    checkpoint_pressure_tokens: int,
    objective_gravity: int,
    drift_mission_count: int,
) -> EconomyState:
    if checkpoint_count >= 2 and score >= 72 and failure_count == 0:
        return "compounding"
    if checkpoint_count == 0 and (
        failure_count > 0
        or (token_burn >= checkpoint_pressure_tokens and command_burn >= 12)
        or remote_pressure_count >= 3
        or (drift_mission_count > 0 and objective_gravity < 55)
    ):
        return "leaking"
    if active_count > 0 and checkpoint_count == 0:
        return "speculative"
    if (
        checkpoint_count > 0
        and active_count == 0
        and freshness_minutes is not None
        and freshness_minutes >= 360
    ):
        return "hibernating"
    return "balanced"


def _state_text(
    state: EconomyState,
    *,
    label: str,
    checkpoint_count: int,
    failure_count: int,
    active_count: int,
    task_pressure_count: int,
    remote_pressure_count: int,
    checkpoint_efficiency: float,
    objective_gravity: int,
    drift_mission_count: int,
) -> tuple[str, str, str]:
    drift_clause = (
        f" {drift_mission_count} drifting mission(s) are pulling it off-mandate."
        if drift_mission_count
        else ""
    )
    if state == "compounding":
        return (
            f"{label} is converting prior checkpoints into durable progress efficiently.",
            "Allocate the next idle lane here before funding colder scopes.",
            (
                f"Continue from the freshest checkpoint in {label}, preserve the current winning "
                "loop shape, and turn that momentum into the next durable milestone."
            ),
        )
    if state == "leaking":
        return (
            (
                f"{label} is spending autonomy capital faster than it is earning durable anchors "
                f"back. Objective gravity is {objective_gravity}/100.{drift_clause}"
            ),
            "Stop broad exploration and compress this scope until it can land a checkpoint.",
            (
                f"Compress {label} to a 2-turn loop, disable speculative fan-out, realign the "
                "scope to the original charter, and require a verified checkpoint before any "
                "further expansion."
            ),
        )
    if state == "speculative":
        return (
            (
                f"{label} is still speculative: live work is underway but no durable anchor "
                "exists yet."
            ),
            "Keep only one lane active and demand an anchor checkpoint soon.",
            (
                f"Keep a single active lane on {label}, narrow the objective, and force the next "
                "cycle to end with a concise checkpoint or explicit abort reason."
            ),
        )
    if state == "hibernating":
        return (
            f"{label} has usable memory but no fresh motion.",
            "Wake this scope from its last checkpoint instead of cold-starting it later.",
            (
                f"Resume {label} from the latest checkpoint, verify what still holds, and either "
                "turn it back into a compounding loop or archive the path cleanly."
            ),
        )
    return (
        (
            f"{label} is balanced with {checkpoint_count} checkpoint(s), "
            f"{failure_count} failure(s), "
            f"{active_count} live lane(s), {task_pressure_count} task loop(s), and "
            f"{remote_pressure_count} remote nudge(s)."
        ),
        (
            f"Keep the current cadence unless another scope clearly outperforms its "
            f"{checkpoint_efficiency:.2f} checkpoint-efficiency."
        ),
        (
            f"Maintain the current operating shape for {label}, but compare its yield against the "
            "other scopes before assigning more capacity."
        ),
    )


def build_economy(
    missions: list[MissionView],
    projects: list[ProjectView],
    task_blueprints: list[TaskBlueprintView],
    remote_requests: list[RemoteRequestView],
) -> DashboardEconomyView:
    projects_by_id = {project.id: project for project in projects}
    missions_by_id = {mission.id: mission for mission in missions}
    tasks_by_id = {task.id: task for task in task_blueprints}

    grouped_missions: dict[str, list[MissionView]] = defaultdict(list)
    grouped_tasks: dict[str, list[TaskBlueprintView]] = defaultdict(list)
    grouped_requests: dict[str, list[RemoteRequestView]] = defaultdict(list)
    scope_meta: dict[str, _Scope] = {}

    for mission in missions:
        scope = _scope_for_mission(mission, projects_by_id)
        if scope is None:
            continue
        grouped_missions[scope.key].append(mission)
        scope_meta[scope.key] = scope

    for task in task_blueprints:
        if not task.enabled:
            continue
        scope = _scope_for_task(task, projects_by_id)
        if scope is None:
            continue
        grouped_tasks[scope.key].append(task)
        scope_meta[scope.key] = scope

    request_cutoff = datetime.now(UTC) - timedelta(hours=24)
    for request in remote_requests:
        if request.status not in {"accepted", "completed", "dry_run"}:
            continue
        if request.requested_at < request_cutoff:
            continue
        scope = _scope_for_request(request, missions_by_id, tasks_by_id, projects_by_id)
        if scope is None:
            continue
        grouped_requests[scope.key].append(request)
        scope_meta[scope.key] = scope

    scopes: list[DashboardEconomyScopeView] = []
    for scope_key, scope in scope_meta.items():
        scoped_missions = grouped_missions.get(scope_key, [])
        scoped_tasks = grouped_tasks.get(scope_key, [])
        scoped_requests = grouped_requests.get(scope_key, [])
        scope_assessments = [
            build_scope_assessment(mission, checkpoints=mission.checkpoints)
            for mission in scoped_missions
        ]

        checkpoint_count = sum(1 for mission in scoped_missions if mission.last_checkpoint)
        active_count = sum(mission.status in {"active", "blocked"} for mission in scoped_missions)
        failure_count = sum(mission.status == "failed" for mission in scoped_missions)
        approval_count = sum(
            mission.status == "blocked" and mission.phase == "approval"
            for mission in scoped_missions
        )
        token_burn = sum(mission.total_tokens for mission in scoped_missions)
        command_burn = sum(mission.command_count for mission in scoped_missions)
        objective_gravity = (
            round(
                sum(assessment.objective_gravity for assessment in scope_assessments)
                / len(scope_assessments)
            )
            if scope_assessments
            else 100
        )
        drift_mission_count = sum(
            assessment.drift_level in {"drifting", "critical"} for assessment in scope_assessments
        )
        checkpoint_pressure_tokens = scope_checkpoint_pressure_threshold(
            mission.model for mission in scoped_missions
        )
        task_pressure_count = len(scoped_tasks)
        remote_pressure_count = len(scoped_requests)
        freshness_minutes = _freshness_minutes(scoped_missions)
        checkpoint_efficiency = _checkpoint_efficiency(
            checkpoint_count=checkpoint_count,
            token_burn=token_burn,
            command_burn=command_burn,
            failure_count=failure_count,
            approval_count=approval_count,
            remote_pressure_count=remote_pressure_count,
        )
        score = _score_scope(
            checkpoint_count=checkpoint_count,
            failure_count=failure_count,
            approval_count=approval_count,
            active_count=active_count,
            task_pressure_count=task_pressure_count,
            remote_pressure_count=remote_pressure_count,
            token_burn=token_burn,
            command_burn=command_burn,
            checkpoint_pressure_tokens=checkpoint_pressure_tokens,
            objective_gravity=objective_gravity,
            drift_mission_count=drift_mission_count,
        )
        state = _state_for_scope(
            score=score,
            checkpoint_count=checkpoint_count,
            failure_count=failure_count,
            active_count=active_count,
            token_burn=token_burn,
            command_burn=command_burn,
            freshness_minutes=freshness_minutes,
            remote_pressure_count=remote_pressure_count,
            checkpoint_pressure_tokens=checkpoint_pressure_tokens,
            objective_gravity=objective_gravity,
            drift_mission_count=drift_mission_count,
        )
        summary, arbitrage_edge, capital_prompt = _state_text(
            state,
            label=scope.label,
            checkpoint_count=checkpoint_count,
            failure_count=failure_count,
            active_count=active_count,
            task_pressure_count=task_pressure_count,
            remote_pressure_count=remote_pressure_count,
            checkpoint_efficiency=checkpoint_efficiency,
            objective_gravity=objective_gravity,
            drift_mission_count=drift_mission_count,
        )
        scopes.append(
            DashboardEconomyScopeView(
                id=scope.key,
                project_id=scope.project_id,
                scope_label=scope.label,
                state=state,
                score=score,
                summary=summary,
                arbitrage_edge=arbitrage_edge,
                capital_prompt=capital_prompt,
                mission_count=len(scoped_missions),
                active_count=active_count,
                checkpoint_count=checkpoint_count,
                failure_count=failure_count,
                approval_count=approval_count,
                task_pressure_count=task_pressure_count,
                remote_pressure_count=remote_pressure_count,
                drift_mission_count=drift_mission_count,
                objective_gravity=objective_gravity,
                token_burn=token_burn,
                command_burn=command_burn,
                checkpoint_efficiency=checkpoint_efficiency,
            )
        )

    state_rank = {
        "leaking": 0,
        "speculative": 1,
        "compounding": 2,
        "balanced": 3,
        "hibernating": 4,
    }
    scopes = sorted(
        scopes,
        key=lambda scope: (
            state_rank[scope.state],
            -scope.score if scope.state == "compounding" else scope.score,
            scope.scope_label.lower(),
        ),
    )[:6]

    if not scopes:
        return DashboardEconomyView(
            headline="Autonomy economy is idle",
            summary=(
                "No scoped mission history exists yet, so Zues has not learned where capital "
                "compounds or leaks."
            ),
            scopes=[],
        )

    compounding = sum(scope.state == "compounding" for scope in scopes)
    leaking = sum(scope.state == "leaking" for scope in scopes)
    speculative = sum(scope.state == "speculative" for scope in scopes)

    if leaking:
        headline = "Autonomy economy is leaking"
        summary = (
            f"{leaking} scope(s) are spending capital faster than they are earning durable "
            "checkpoints."
        )
    elif compounding:
        headline = "Autonomy economy is compounding"
        summary = (
            f"{compounding} scope(s) are producing durable checkpoints efficiently enough to fund "
            "more autonomy."
        )
    elif speculative:
        headline = "Autonomy economy is speculative"
        summary = f"{speculative} live scope(s) are still searching for their first durable anchor."
    else:
        headline = "Autonomy economy is balanced"
        summary = "Current scopes are neither obviously compounding nor obviously leaking."

    return DashboardEconomyView(headline=headline, summary=summary, scopes=scopes)
