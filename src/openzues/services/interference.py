from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from openzues.schemas import (
    DashboardInterferenceVectorView,
    DashboardInterferenceView,
    GatewayCapabilityView,
    MissionView,
    ProjectView,
    RemoteRequestView,
    SignalLevel,
    TaskBlueprintView,
)


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


def _lane_braid_prompt(scope_label: str, mission_ids: list[int]) -> str:
    joined = ", ".join(str(mission_id) for mission_id in mission_ids)
    return (
        f"You are entering a braided scope for {scope_label}. Before any new edits, read the "
        f"latest checkpoints from missions {joined}, choose one authority thread, state ownership "
        "boundaries, and avoid overlapping file changes until the braid is resolved."
    )


def _checkpoint_eclipse_prompt(scope_label: str, anchor_id: int, live_id: int) -> str:
    return (
        f"You are about to eclipse a fresh checkpoint in {scope_label}. Read mission {anchor_id}'s "
        f"latest handoff before continuing mission {live_id}, restate what is already true, and "
        "explicitly list what must remain unchanged while new work proceeds."
    )


def _task_overlap_prompt(scope_label: str, task_ids: list[int]) -> str:
    joined = ", ".join(str(task_id) for task_id in task_ids)
    return (
        f"Task blueprints {joined} all target {scope_label}. Before scheduling or triggering more "
        "runs, assign each loop a distinct objective boundary and serialize anything that would "
        "touch the same files or reuse the same operator attention."
    )


def _remote_echo_prompt(scope_label: str, operator_ids: list[int]) -> str:
    joined = ", ".join(str(operator_id) for operator_id in operator_ids)
    return (
        f"Remote operators {joined} have all touched {scope_label} recently. Require each incoming "
        "request to cite the current authority mission, summarize the latest checkpoint, and say "
        "whether it is extending, validating, or interrupting the active lane."
    )


def build_interference(
    missions: list[MissionView],
    projects: list[ProjectView],
    task_blueprints: list[TaskBlueprintView],
    remote_requests: list[RemoteRequestView],
    *,
    gateway_capability: GatewayCapabilityView | None = None,
) -> DashboardInterferenceView:
    projects_by_id = {project.id: project for project in projects}
    missions_by_id = {mission.id: mission for mission in missions}
    tasks_by_id = {task.id: task for task in task_blueprints}
    vectors: list[DashboardInterferenceVectorView] = []

    scoped_missions: dict[str, list[MissionView]] = defaultdict(list)
    scoped_meta: dict[str, _Scope] = {}
    for mission in missions:
        scope = _scope_for_mission(mission, projects_by_id)
        if scope is None:
            continue
        scoped_missions[scope.key].append(mission)
        scoped_meta[scope.key] = scope

    scoped_tasks: dict[str, list[TaskBlueprintView]] = defaultdict(list)
    for task in task_blueprints:
        scope = _scope_for_task(task, projects_by_id)
        if scope is None or not task.enabled:
            continue
        scoped_tasks[scope.key].append(task)
        scoped_meta[scope.key] = scope

    recent_cutoff = datetime.now(UTC) - timedelta(hours=6)
    scoped_requests: dict[str, list[RemoteRequestView]] = defaultdict(list)
    for request in remote_requests:
        if request.status not in {"accepted", "completed", "dry_run"}:
            continue
        if request.requested_at < recent_cutoff:
            continue
        scope = _scope_for_request(request, missions_by_id, tasks_by_id, projects_by_id)
        if scope is None:
            continue
        scoped_requests[scope.key].append(request)
        scoped_meta[scope.key] = scope

    for scope_key, items in scoped_missions.items():
        scope = scoped_meta[scope_key]
        live = [mission for mission in items if mission.status in {"active", "blocked"}]
        if len(live) >= 2:
            distinct_instances = len({mission.instance_id for mission in live})
            lane_level: SignalLevel = "critical" if len(live) >= 3 else "warn"
            vectors.append(
                DashboardInterferenceVectorView(
                    id=f"lane-braid:{scope.key}",
                    kind="lane_braid",
                    level=lane_level,
                    scope_label=scope.label,
                    project_id=scope.project_id,
                    summary=(
                        f"{len(live)} live missions are touching {scope.label} across "
                        f"{distinct_instances} lane(s)."
                    ),
                    pressure=(
                        "Parallel autonomous loops are now likely to fork context, duplicate "
                        "fixes, or step on the same workspace state."
                    ),
                    treaty_prompt=_lane_braid_prompt(scope.label, [mission.id for mission in live]),
                    mission_ids=[mission.id for mission in live],
                )
            )

        anchored = sorted(
            [
                mission
                for mission in items
                if mission.last_checkpoint and mission.status in {"paused", "completed", "failed"}
            ],
            key=lambda mission: mission.updated_at,
            reverse=True,
        )
        if anchored and live:
            anchor = anchored[0]
            eclipsers = [
                mission
                for mission in live
                if mission.thread_id != anchor.thread_id and not mission.last_checkpoint
            ]
            if eclipsers:
                vectors.append(
                    DashboardInterferenceVectorView(
                        id=f"checkpoint-eclipse:{scope.key}",
                        kind="checkpoint_eclipse",
                        level="warn",
                        scope_label=scope.label,
                        project_id=scope.project_id,
                        summary=(
                            f"A fresh checkpoint in {scope.label} is being shadowed by a newer "
                            "live thread without its own anchor."
                        ),
                        pressure=(
                            "The next loop can erase a known-good handoff by marching forward "
                            "without first adopting the latest verified state."
                        ),
                        treaty_prompt=_checkpoint_eclipse_prompt(
                            scope.label,
                            anchor.id,
                            eclipsers[0].id,
                        ),
                        mission_ids=[anchor.id, *[mission.id for mission in eclipsers]],
                    )
                )

    for scope_key, tasks in scoped_tasks.items():
        scope = scoped_meta[scope_key]
        scheduled = [task for task in tasks if task.cadence_minutes is not None]
        if len(tasks) >= 2 and scheduled:
            overlap_level: SignalLevel = "warn" if len(scheduled) >= 2 else "info"
            vectors.append(
                DashboardInterferenceVectorView(
                    id=f"task-overlap:{scope.key}",
                    kind="task_overlap",
                    level=overlap_level,
                    scope_label=scope.label,
                    project_id=scope.project_id,
                    summary=(
                        f"{len(tasks)} enabled task loop(s) target {scope.label}, with "
                        f"{len(scheduled)} scheduled run(s)."
                    ),
                    pressure=(
                        "Automation can start competing for the same repo state before earlier "
                        "handoffs are absorbed."
                    ),
                    treaty_prompt=_task_overlap_prompt(
                        scope.label,
                        [task.id for task in tasks],
                    ),
                    task_ids=[task.id for task in tasks],
                )
            )

    for scope_key, requests in scoped_requests.items():
        scope = scoped_meta[scope_key]
        operator_ids = sorted({request.operator_id for request in requests})
        if len(requests) >= 2 and (len(operator_ids) >= 2 or len(requests) >= 3):
            echo_level: SignalLevel = "warn" if len(operator_ids) >= 2 else "info"
            vectors.append(
                DashboardInterferenceVectorView(
                    id=f"remote-echo:{scope.key}",
                    kind="remote_echo",
                    level=echo_level,
                    scope_label=scope.label,
                    project_id=scope.project_id,
                    summary=(
                        f"{len(requests)} recent remote request(s) echoed into {scope.label} from "
                        f"{len(operator_ids)} operator lane(s)."
                    ),
                    pressure=(
                        "External launches are arriving faster than a single authority thread can "
                        "absorb them."
                    ),
                    treaty_prompt=_remote_echo_prompt(scope.label, operator_ids),
                    mission_ids=[
                        request.target_id
                        for request in requests
                        if request.target_kind == "mission" and request.target_id is not None
                    ],
                    task_ids=[
                        request.target_id
                        for request in requests
                        if request.target_kind == "task" and request.target_id is not None
                    ],
                    operator_ids=operator_ids,
                    request_ids=[request.id for request in requests],
                )
            )

    if gateway_capability is not None and (
        gateway_capability.level == "critical"
        or gateway_capability.inventory.tracked_gap_count
        or gateway_capability.approval_posture.approval_count
        or (
            gateway_capability.launch_policy.launch_route is not None
            and gateway_capability.launch_policy.launch_route.status == "repair"
        )
        or (
            gateway_capability.connected_lane_health.total_count > 0
            and gateway_capability.connected_lane_health.ready_count == 0
        )
    ):
        launch_route = gateway_capability.launch_policy.launch_route
        scope_label = (
            launch_route.preferred_instance.label
            if launch_route is not None and launch_route.preferred_instance is not None
            else (
                launch_route.resolved_instance.label
                if launch_route is not None and launch_route.resolved_instance is not None
                else "Gateway launch policy"
            )
        )
        route_warning = (
            launch_route.warnings[0]
            if launch_route is not None and launch_route.warnings
            else gateway_capability.warnings[0]
            if gateway_capability.warnings
            else gateway_capability.summary
        )
        vectors.append(
            DashboardInterferenceVectorView(
                id="gateway-posture",
                kind="gateway_posture",
                level="critical" if gateway_capability.level == "critical" else "warn",
                scope_label=scope_label,
                project_id=None,
                summary=(
                    f"{gateway_capability.headline}. {gateway_capability.connected_lane_health.summary}"
                ),
                pressure=(
                    "Operators can fork work around the saved launch posture when approvals, "
                    "tracked gaps, or lane readiness are already degraded."
                ),
                treaty_prompt=(
                    "Read the shared gateway doctor summary first. Repair the saved launch "
                    "posture, lane readiness, approvals, or tracked inventory gaps before "
                    f"starting another autonomous cycle. Current lead warning: {route_warning}"
                ),
            )
        )

    level_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    vectors = sorted(
        vectors,
        key=lambda vector: (
            level_rank[vector.level],
            vector.scope_label.lower(),
            vector.kind,
        ),
    )[:6]

    if not vectors:
        return DashboardInterferenceView(
            headline="Interference forecast is calm",
            summary=(
                "No overlapping mission, task, or remote-launch pressure is currently forecast "
                "across the registered scopes."
            ),
            vectors=[],
        )

    critical = sum(vector.level == "critical" for vector in vectors)
    warn = sum(vector.level == "warn" for vector in vectors)
    if critical:
        headline = "Interference forecast is hot"
        summary = (
            f"{critical} critical braid(s) and {warn} warning signal(s) suggest autonomous work "
            "is starting to collide with itself."
        )
    elif warn:
        headline = "Interference forecast is watchful"
        summary = (
            f"{warn} warning signal(s) suggest upcoming overlap between missions, tasks, or "
            "remote operators."
        )
    else:
        headline = "Interference forecast is active"
        summary = (
            "Low-grade overlap is forming, but the current treaty prompts should be enough to "
            "keep scopes separated."
        )

    return DashboardInterferenceView(
        headline=headline,
        summary=summary,
        vectors=vectors,
    )
