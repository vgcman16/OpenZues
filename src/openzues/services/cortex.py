from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Literal

from openzues.schemas import (
    DashboardCortexView,
    DashboardDoctrineView,
    DashboardInoculationView,
    InstanceView,
    MissionDraftView,
    MissionView,
    ProjectView,
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(UTC) - parsed).total_seconds() // 60))


def _is_project_dirty(project: ProjectView) -> bool:
    git_status = (project.git_status or "").strip()
    if not git_status:
        return False
    lowered = git_status.lower()
    return "working tree clean" not in lowered and "nothing to commit" not in lowered


def _is_orbiting(mission: MissionView) -> bool:
    orbit_threshold = max(6, mission.turns_completed * 4 + 4)
    return mission.command_count >= orbit_threshold and not mission.last_checkpoint


def _scope_for_mission(
    mission: MissionView,
    projects_by_id: dict[int, ProjectView],
) -> tuple[str, int | None, str] | None:
    if mission.project_id is not None:
        project = projects_by_id.get(mission.project_id)
        if project is not None:
            return (f"project:{project.id}", project.id, project.label)
    if mission.cwd:
        return (f"cwd:{mission.cwd.lower()}", None, Path(mission.cwd).name or "Attached workspace")
    return None


def _count_truthy(values: list[bool]) -> bool:
    if not values:
        return False
    return sum(1 for value in values if value) * 2 >= len(values)


def build_doctrines(
    missions: list[MissionView],
    projects: list[ProjectView],
) -> list[DashboardDoctrineView]:
    projects_by_id = {project.id: project for project in projects}
    grouped: dict[str, list[MissionView]] = defaultdict(list)
    scope_meta: dict[str, tuple[int | None, str]] = {}

    for mission in missions:
        scope = _scope_for_mission(mission, projects_by_id)
        if scope is None:
            continue
        scope_key, project_id, label = scope
        grouped[scope_key].append(mission)
        scope_meta[scope_key] = (project_id, label)

    doctrines: list[DashboardDoctrineView] = []
    confidence_rank = {"forming": 0, "solid": 1, "strong": 2}

    for scope_key, items in grouped.items():
        project_id, label = scope_meta[scope_key]
        checkpointed = [mission for mission in items if mission.last_checkpoint]
        stable = [
            mission
            for mission in checkpointed
            if mission.status in {"completed", "paused", "active"}
        ]
        unstable = [
            mission
            for mission in items
            if mission.status == "failed"
            or mission.phase == "offline"
            or _is_orbiting(mission)
        ]
        approval_bound = [
            mission
            for mission in items
            if mission.status == "blocked" and mission.phase == "approval"
        ]

        baseline = stable or checkpointed or items
        model_counter = Counter(mission.model for mission in baseline if mission.model)
        recommended_model = model_counter.most_common(1)[0][0] if model_counter else "gpt-5.4"

        max_turn_values = [mission.max_turns for mission in baseline if mission.max_turns]
        recommended_max_turns = (
            int(round(median(max_turn_values)))
            if max_turn_values
            else (4 if recommended_model == "gpt-5.4" else 3)
        )
        if any(_is_orbiting(mission) for mission in items):
            recommended_max_turns = min(recommended_max_turns, 3)
        if len(unstable) >= 2 and not checkpointed:
            recommended_max_turns = min(recommended_max_turns, 2)

        use_builtin_agents = _count_truthy(
            [mission.use_builtin_agents for mission in baseline]
        )
        run_verification = any(mission.failure_count for mission in items) or _count_truthy(
            [mission.run_verification for mission in baseline]
        )
        auto_commit = (
            False
            if len(unstable) > len(stable)
            else _count_truthy([mission.auto_commit for mission in baseline])
        )
        pause_on_approval = bool(approval_bound) or _count_truthy(
            [mission.pause_on_approval for mission in baseline]
        )

        confidence: Literal["forming", "solid", "strong"]
        if len(items) >= 4 or len(stable) >= 3:
            confidence = "strong"
        elif len(items) >= 2 or len(checkpointed) >= 2:
            confidence = "solid"
        else:
            confidence = "forming"

        loop_style = [
            "verified" if run_verification else "lightweight",
            f"{recommended_max_turns}-turn",
            "agent-assisted" if use_builtin_agents else "single-lane",
        ]
        commit_style = "milestone commits on" if auto_commit else "commits held until stable"
        summary = (
            f"{label} currently prefers {' '.join(loop_style)} loops on "
            f"{recommended_model} with {commit_style}."
        )

        rationale_parts = [
            f"{len(checkpointed)} checkpointed run{'s' if len(checkpointed) != 1 else ''}",
            f"{len(unstable)} unstable pattern{'s' if len(unstable) != 1 else ''}",
        ]
        if approval_bound:
            rationale_parts.append(
                f"{len(approval_bound)} approval pause{'s' if len(approval_bound) != 1 else ''}"
            )
        rationale = ", ".join(rationale_parts) + "."
        if any(_is_orbiting(mission) for mission in items):
            rationale += " Long uncheckpointed cycles were compressed into shorter loops."

        doctrines.append(
            DashboardDoctrineView(
                id=scope_key,
                project_id=project_id,
                project_label=label,
                confidence=confidence,
                summary=summary,
                rationale=rationale,
                mission_count=len(items),
                checkpoint_count=len(checkpointed),
                unstable_count=len(unstable),
                recommended_model=recommended_model,
                recommended_max_turns=recommended_max_turns,
                use_builtin_agents=use_builtin_agents,
                run_verification=run_verification,
                auto_commit=auto_commit,
                pause_on_approval=pause_on_approval,
            )
        )

    return sorted(
        doctrines,
        key=lambda doctrine: (
            confidence_rank[doctrine.confidence],
            doctrine.checkpoint_count,
            doctrine.mission_count,
            doctrine.project_label.lower(),
        ),
        reverse=True,
    )[:4]


def build_inoculations(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
) -> list[DashboardInoculationView]:
    inoculations: list[DashboardInoculationView] = []

    orbiting = [mission for mission in missions if _is_orbiting(mission)]
    if orbiting:
        hottest = max(orbiting, key=lambda mission: mission.command_count)
        inoculations.append(
            DashboardInoculationView(
                id="checkpoint-compression",
                level=(
                    "critical"
                    if any(mission.status == "active" for mission in orbiting)
                    else "warn"
                ),
                title="Checkpoint compression",
                summary=(
                    f"{len(orbiting)} mission(s) are stretching beyond their handoff window "
                    "without landing a durable checkpoint."
                ),
                prescription=(
                    "Cap the next cycle at three turns, keep verification on, and require every "
                    "loop to end with a concise checkpoint before more commands fan out."
                ),
                mission_id=hottest.id,
                project_id=hottest.project_id,
            )
        )

    approval_bound = [
        mission
        for mission in missions
        if mission.status == "blocked" and mission.phase == "approval"
    ]
    orphan_approvals = sum(len(instance.unresolved_requests) for instance in instances)
    if approval_bound or orphan_approvals:
        anchor = approval_bound[0] if approval_bound else None
        inoculations.append(
            DashboardInoculationView(
                id="approval-sentry",
                level="critical" if approval_bound else "warn",
                title="Approval sentry",
                summary=(
                    "Human decisions are part of the live control loop, so autonomy needs "
                    "clean pause boundaries."
                ),
                prescription=(
                    "Keep approval pauses enabled, cluster risky actions near cycle ends, and have "
                    "missions ask for the exact decision text they need before they stop."
                ),
                mission_id=anchor.id if anchor is not None else None,
                project_id=anchor.project_id if anchor is not None else None,
            )
        )

    dirty_projects = [project for project in projects if _is_project_dirty(project)]
    if dirty_projects:
        inoculations.append(
            DashboardInoculationView(
                id="drift-quarantine",
                level="warn",
                title="Drift quarantine",
                summary=(
                    f"{len(dirty_projects)} project(s) already contain unmodeled worktree drift."
                ),
                prescription=(
                    "Run a drift sweep before the next ship slice and suppress auto-commit until "
                    "Codex has mapped the branch and unfinished edits."
                ),
                project_id=dirty_projects[0].id,
            )
        )

    recoverable = [
        mission
        for mission in missions
        if mission.status == "failed" and mission.last_checkpoint and mission.thread_id
    ]
    if recoverable:
        anchor = recoverable[0]
        inoculations.append(
            DashboardInoculationView(
                id="recovery-echo",
                level="warn",
                title="Recovery echo",
                summary=(
                    "Some failures already have enough thread memory to recover without losing "
                    "context."
                ),
                prescription=(
                    "Resume the failed run from its existing thread, shorten the next window to "
                    "two or three turns, and use verification to re-anchor the mission."
                ),
                mission_id=anchor.id,
                project_id=anchor.project_id,
            )
        )

    quiet = [
        mission
        for mission in missions
        if mission.status == "active"
        and not mission.in_progress
        and (_minutes_since(mission.last_activity_at) or 0) >= 8
    ]
    if quiet:
        anchor = quiet[0]
        inoculations.append(
            DashboardInoculationView(
                id="silence-relay",
                level="warn",
                title="Silence relay",
                summary=(
                    "A live mission has gone quiet long enough that throughput may be slipping."
                ),
                prescription=(
                    "Treat prolonged silence as a degraded state: reconnect the lane or trigger "
                    "Run now before stacking more work onto that instance."
                ),
                mission_id=anchor.id,
                project_id=anchor.project_id,
            )
        )

    level_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    return sorted(
        inoculations,
        key=lambda inoculation: (level_rank[inoculation.level], inoculation.title.lower()),
    )[:4]


def build_cortex(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    *,
    doctrines: list[DashboardDoctrineView] | None = None,
) -> DashboardCortexView:
    learned_doctrines = doctrines if doctrines is not None else build_doctrines(missions, projects)
    inoculations = build_inoculations(instances, missions, projects)

    if learned_doctrines or inoculations:
        headline = "The autonomy cortex is learning"
        summary = (
            f"{len(learned_doctrines)} doctrine pattern(s) and "
            f"{len(inoculations)} preflight inoculation(s) are now shaping future runs."
        )
    else:
        headline = "The autonomy cortex is still forming"
        summary = (
            "Launch a few missions and OpenZues will start extracting doctrine, recovery habits, "
            "and hardening rules from the run history."
        )

    return DashboardCortexView(
        headline=headline,
        summary=summary,
        doctrines=learned_doctrines,
        inoculations=inoculations,
    )


def doctrine_index(
    doctrines: list[DashboardDoctrineView],
) -> dict[int, DashboardDoctrineView]:
    return {
        doctrine.project_id: doctrine
        for doctrine in doctrines
        if doctrine.project_id is not None
    }


def tune_draft_with_doctrine(
    draft: MissionDraftView,
    doctrine: DashboardDoctrineView,
) -> MissionDraftView:
    return draft.model_copy(
        update={
            "model": doctrine.recommended_model,
            "max_turns": doctrine.recommended_max_turns,
            "use_builtin_agents": draft.use_builtin_agents and doctrine.use_builtin_agents,
            "run_verification": draft.run_verification or doctrine.run_verification,
            "auto_commit": doctrine.auto_commit if draft.auto_commit else False,
            "pause_on_approval": draft.pause_on_approval and doctrine.pause_on_approval,
        }
    )
