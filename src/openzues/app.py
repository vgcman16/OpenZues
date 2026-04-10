from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from openzues.database import Database
from openzues.logging_utils import configure_logging
from openzues.schemas import (
    CommandCreate,
    DashboardBriefView,
    DashboardDoctrineView,
    DashboardLaunchpadView,
    DashboardOpportunityView,
    DashboardRadarView,
    DashboardSignalView,
    DashboardView,
    DiagnosticsView,
    EventView,
    InstanceCreate,
    InstanceView,
    MissionCreate,
    MissionDraftView,
    MissionReflexRun,
    MissionView,
    PlaybookCreate,
    PlaybookRun,
    PlaybookRunResult,
    PlaybookView,
    ProjectCreate,
    ProjectView,
    RequestResolution,
    ReviewCreate,
    ThreadCreate,
    TurnCreate,
)
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.cortex import (
    build_cortex,
    build_doctrines,
    doctrine_index,
    tune_draft_with_doctrine,
)
from openzues.services.environment import EnvironmentService
from openzues.services.github import GitHubService
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager, compact_event_payload
from openzues.services.missions import MissionService
from openzues.services.playbooks import PlaybookService
from openzues.services.projects import ProjectService
from openzues.services.reflexes import build_reflex_deck
from openzues.settings import Settings, settings

configure_logging()


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


def _pick_launch_instance(
    instances: list[InstanceView],
    missions: list[MissionView],
    *,
    prefer_idle: bool = True,
) -> InstanceView | None:
    live_instance_ids = {
        mission.instance_id for mission in missions if mission.status in {"active", "blocked"}
    }
    if prefer_idle:
        for instance in instances:
            if instance.connected and instance.id not in live_instance_ids:
                return instance
    for instance in instances:
        if instance.connected:
            return instance
    return instances[0] if instances else None


def _is_project_dirty(project: ProjectView) -> bool:
    git_status = (project.git_status or "").strip()
    if not git_status:
        return False
    lowered = git_status.lower()
    return "working tree clean" not in lowered and "nothing to commit" not in lowered


def build_brief(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
) -> DashboardBriefView:
    connected = sum(1 for instance in instances if instance.connected)
    blocked = [mission for mission in missions if mission.status == "blocked"]
    active = [mission for mission in missions if mission.status == "active"]
    paused = [mission for mission in missions if mission.status == "paused"]
    focus = blocked[0] if blocked else active[0] if active else paused[0] if paused else None

    next_actions: list[str] = []
    if focus is not None and focus.suggested_action:
        next_actions.append(focus.suggested_action)
    if connected == 0 and instances:
        next_actions.append("Reconnect a Codex Desktop instance to resume autonomous work.")
    if not instances:
        next_actions.append("Create or quick-connect a Codex instance before launching missions.")
    if not projects:
        next_actions.append("Register a project so missions can target a real workspace.")
    if not missions:
        next_actions.append("Launch a mission from a preset to start a durable build loop.")

    status: Literal["idle", "active", "blocked", "mixed"]
    if blocked:
        status = "blocked"
        mission_word = "missions" if len(blocked) != 1 else "mission"
        headline = f"{len(blocked)} {mission_word} need operator attention"
        summary = "Approvals, queueing, or runtime blockers are pausing autonomous progress."
    elif active:
        status = "active"
        mission_word = "missions" if len(active) != 1 else "mission"
        headline = f"{len(active)} {mission_word} currently running"
        summary = "Autonomous cycles are live. Let them work or jump in at the recommended moment."
    elif connected:
        status = "idle"
        headline = "Control plane is connected and ready"
        summary = (
            "Launch a mission, start a thread manually, or prepare the workspace "
            "for the next run."
        )
    else:
        status = "mixed"
        headline = "OpenZues is ready to reconnect"
        summary = "The UI is live, but Codex is not currently attached to the control plane."

    return DashboardBriefView(
        status=status,
        headline=headline,
        summary=summary,
        focus_mission_id=focus.id if focus is not None else None,
        next_actions=next_actions[:3],
    )


def build_radar(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
) -> DashboardRadarView:
    signals: list[DashboardSignalView] = []
    missions_by_instance: dict[int, list[MissionView]] = {}
    for mission in missions:
        missions_by_instance.setdefault(mission.instance_id, []).append(mission)

    def add_signal(
        signal_id: str,
        *,
        lane: Literal["attention", "throughput", "reliability", "capacity"],
        level: Literal["critical", "warn", "ready", "info"],
        title: str,
        detail: str,
        action: str | None = None,
        mission_id: int | None = None,
        instance_id: int | None = None,
        freshness_minutes: int | None = None,
    ) -> None:
        signals.append(
            DashboardSignalView(
                id=signal_id,
                lane=lane,
                level=level,
                title=title,
                detail=detail,
                action=action,
                mission_id=mission_id,
                instance_id=instance_id,
                freshness_minutes=freshness_minutes,
            )
        )

    if not instances:
        add_signal(
            "capacity/no-instance",
            lane="capacity",
            level="warn",
            title="No Codex lane attached",
            detail=(
                "Create or quick-connect a desktop bridge so the site can run "
                "durable autonomous work."
            ),
            action="Use Quick Connect to attach Codex Desktop.",
        )
    if not projects:
        add_signal(
            "capacity/no-project",
            lane="capacity",
            level="info",
            title="No workspace registered",
            detail=(
                "Missions can run without a project, but attaching a repo gives "
                "Codex a stable build target."
            ),
            action="Add a local project path in the workspace section.",
        )

    for mission in missions:
        age_minutes = _minutes_since(mission.last_activity_at)
        last_error = str(mission.last_error or "")

        if mission.status == "blocked" and mission.phase == "approval":
            add_signal(
                f"mission-{mission.id}-approval",
                lane="attention",
                level="critical",
                title=f"Approval gate open for {mission.name}",
                detail=last_error or "Codex is waiting for a decision before it continues.",
                action=mission.suggested_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.phase == "offline" or last_error.startswith("Instance is offline"):
            add_signal(
                f"mission-{mission.id}-offline",
                lane="reliability",
                level="critical",
                title=f"{mission.name} lost its Codex connection",
                detail=last_error or "The mission cannot progress until its instance reconnects.",
                action="Reconnect the instance, then run the mission again.",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.status == "failed":
            add_signal(
                f"mission-{mission.id}-failed",
                lane="reliability",
                level="critical",
                title=f"{mission.name} failed its last cycle",
                detail=last_error or "The last mission cycle exited with an unrecovered error.",
                action=mission.suggested_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.status == "blocked" and mission.phase == "queued":
            add_signal(
                f"mission-{mission.id}-queued",
                lane="throughput",
                level="warn",
                title=f"{mission.name} is queued behind another run",
                detail=last_error
                or (
                    "This mission is waiting for another in-progress mission on "
                    "the same instance."
                ),
                action=mission.suggested_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if (
            mission.status == "active"
            and not mission.in_progress
            and age_minutes is not None
            and age_minutes >= 8
        ):
            add_signal(
                f"mission-{mission.id}-quiet",
                lane="reliability",
                level="warn",
                title=f"{mission.name} went quiet",
                detail=f"No mission activity has landed for {age_minutes} minutes.",
                action="Inspect the last checkpoint or nudge the mission with Run now.",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if (
            mission.status == "active"
            and mission.total_tokens >= 60000
            and not mission.last_checkpoint
        ):
            add_signal(
                f"mission-{mission.id}-burn",
                lane="throughput",
                level="warn",
                title=f"{mission.name} is burning hot without a handoff",
                detail=(
                    f"The mission has consumed {mission.total_tokens:,} tokens "
                    "without producing a durable checkpoint yet."
                ),
                action=(
                    "Review the live commentary and checkpoint strategy before it "
                    "keeps looping."
                ),
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        orbit_threshold = max(6, mission.turns_completed * 4 + 4)
        if (
            mission.status == "active"
            and mission.command_count >= orbit_threshold
            and not mission.last_checkpoint
        ):
            add_signal(
                f"mission-{mission.id}-orbit",
                lane="throughput",
                level="warn",
                title=f"{mission.name} is orbiting without landing",
                detail=(
                    f"{mission.command_count} commands have run without a checkpointed handoff."
                ),
                action="Check whether the objective is too broad and tighten the next cycle.",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.status in {"paused", "completed"} and mission.last_checkpoint:
            add_signal(
                f"mission-{mission.id}-handoff",
                lane="attention",
                level="ready",
                title=f"Handoff ready from {mission.name}",
                detail="A fresh checkpoint is available for review or continuation.",
                action=mission.suggested_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )

    idle_connected = [
        instance
        for instance in instances
        if instance.connected
        and not any(
            mission.status in {"active", "blocked"}
            for mission in missions_by_instance.get(instance.id, [])
        )
    ]
    if idle_connected:
        idle_names = ", ".join(instance.name for instance in idle_connected[:2])
        remainder = len(idle_connected) - 2
        suffix = f" and {remainder} more" if remainder > 0 else ""
        add_signal(
            "capacity/idle-connected",
            lane="capacity",
            level="ready",
            title="Connected capacity is available",
            detail=f"{idle_names}{suffix} can start a new mission immediately.",
            action="Load a preset or launch the next build objective.",
        )

    for instance in instances:
        mission_threads = {
            mission.thread_id
            for mission in missions_by_instance.get(instance.id, [])
            if mission.thread_id
        }
        orphan_requests = [
            request
            for request in instance.unresolved_requests
            if request.get("thread_id") not in mission_threads
        ]
        if orphan_requests:
            add_signal(
                f"instance-{instance.id}-orphan-approval",
                lane="attention",
                level="warn",
                title=f"{instance.name} has unassigned approvals",
                detail=(
                    f"{len(orphan_requests)} approval request(s) are waiting "
                    "outside the tracked mission set."
                ),
                action="Resolve the request or attach the related thread to a mission.",
                instance_id=instance.id,
            )

    level_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    lane_rank = {"attention": 0, "reliability": 1, "throughput": 2, "capacity": 3}
    sorted_signals = sorted(
        signals,
        key=lambda signal: (
            level_rank[signal.level],
            lane_rank[signal.lane],
            signal.freshness_minutes if signal.freshness_minutes is not None else 9999,
            signal.title.lower(),
        ),
    )[:8]

    critical_count = sum(signal.level == "critical" for signal in sorted_signals)
    warn_count = sum(signal.level == "warn" for signal in sorted_signals)

    posture: Literal["steady", "watch", "hot"]
    if critical_count:
        posture = "hot"
        summary = (
            f"{critical_count} live risk signal{'s' if critical_count != 1 else ''} "
            "need operator action now."
        )
    elif warn_count:
        posture = "watch"
        summary = (
            f"{warn_count} autonomy signal{'s' if warn_count != 1 else ''} "
            "should be watched before throughput slips."
        )
    else:
        posture = "steady"
        summary = "Autonomy lanes are clear. Use the ready signals to keep momentum up."

    if not sorted_signals:
        sorted_signals = [
            DashboardSignalView(
                id="steady/all-clear",
                lane="capacity",
                level="ready",
                title="Autonomy corridor is clear",
                detail="Connections, missions, and handoffs are in a healthy state.",
                action="Launch the next mission when you are ready.",
            )
        ]

    return DashboardRadarView(posture=posture, summary=summary, signals=sorted_signals)


def build_launchpad(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    *,
    doctrines: list[DashboardDoctrineView] | None = None,
) -> DashboardLaunchpadView:
    opportunities: list[DashboardOpportunityView] = []
    project_doctrine_index = doctrine_index(doctrines or build_doctrines(missions, projects))
    live_project_ids = {
        mission.project_id
        for mission in missions
        if mission.project_id is not None and mission.status in {"active", "blocked"}
    }
    seen_ids: set[str] = set()

    def add_opportunity(
        opportunity_id: str,
        *,
        kind: Literal[
            "workspace_scout",
            "ship_slice",
            "drift_sweep",
            "checkpoint_hardener",
            "recovery_run",
            "shadow_scout",
        ],
        impact: Literal["high", "medium", "low"],
        title: str,
        summary: str,
        why_now: str,
        draft: MissionDraftView,
        action_label: str = "Load draft",
    ) -> None:
        if opportunity_id in seen_ids:
            return
        seen_ids.add(opportunity_id)
        opportunities.append(
            DashboardOpportunityView(
                id=opportunity_id,
                kind=kind,
                impact=impact,
                title=title,
                summary=summary,
                why_now=why_now,
                action_label=action_label,
                mission_draft=draft,
            )
        )

    def tune_project_draft(
        project_id: int | None,
        draft: MissionDraftView,
    ) -> MissionDraftView:
        if project_id is None:
            return draft
        doctrine = project_doctrine_index.get(project_id)
        if doctrine is None:
            return draft
        return tune_draft_with_doctrine(draft, doctrine)

    idle_instance = _pick_launch_instance(instances, missions, prefer_idle=True)
    connected_instance = _pick_launch_instance(instances, missions, prefer_idle=False)

    if connected_instance is not None and not projects:
        add_opportunity(
            "workspace-scout",
            kind="workspace_scout",
            impact="medium",
            title="Scout the current workspace",
            summary="Map the attached directory and let Codex propose the best durable build loop.",
            why_now=(
                "You have connected capacity but no registered repo, so the fastest gain is a "
                "short orientation run."
            ),
            draft=MissionDraftView(
                name="Scout Current Workspace",
                objective=(
                    "Map the current workspace, identify the highest-leverage product or tooling "
                    "opportunity, and leave a concise operator handoff with recommended next "
                    "missions and risks."
                ),
                instance_id=connected_instance.id,
                project_id=None,
                cwd=connected_instance.cwd,
                thread_id=None,
                model="gpt-5.4-mini",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=2,
                use_builtin_agents=True,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                start_immediately=True,
            ),
            action_label="Load scout",
        )

    checkpoint_missions = sorted(
        [
            mission
            for mission in missions
            if mission.last_checkpoint and mission.status in {"paused", "completed", "failed"}
        ],
        key=lambda mission: mission.updated_at,
        reverse=True,
    )
    for mission in checkpoint_missions[:3]:
        target_instance = next(
            (
                instance
                for instance in instances
                if instance.id == mission.instance_id and instance.connected
            ),
            idle_instance or connected_instance,
        )
        if target_instance is None:
            continue
        if mission.project_id is not None and mission.project_id in live_project_ids:
            continue

        if mission.status == "failed":
            add_opportunity(
                f"recover-{mission.id}",
                kind="recovery_run",
                impact="high",
                title=f"Recover {mission.name}",
                summary=(
                    "Re-open the path from the last failure without throwing away "
                    "mission context."
                ),
                why_now=(
                    "The mission already has thread memory and a failure checkpoint, which makes "
                    "a tight recovery loop faster than starting over."
                ),
                draft=tune_project_draft(
                    mission.project_id,
                    MissionDraftView(
                        name=f"Recover {mission.name}",
                        objective=(
                            f"Continue the mission '{mission.name}' from its existing thread. "
                            "Start by reading the last checkpoint and failure context, fix the "
                            "blocker, verify the path forward, and leave a cleaner checkpoint "
                            "when done."
                        ),
                        instance_id=target_instance.id,
                        project_id=mission.project_id,
                        cwd=mission.cwd,
                        thread_id=mission.thread_id,
                        model=mission.model,
                        reasoning_effort=mission.reasoning_effort,
                        collaboration_mode=mission.collaboration_mode,
                        max_turns=3,
                        use_builtin_agents=mission.use_builtin_agents,
                        run_verification=True,
                        auto_commit=False,
                        pause_on_approval=mission.pause_on_approval,
                        start_immediately=True,
                    ),
                ),
                action_label="Recover run",
            )
            continue

        add_opportunity(
            f"harden-{mission.id}",
            kind="checkpoint_hardener",
            impact="high",
            title=f"Harden {mission.project_label or mission.name}",
            summary=(
                "Turn the latest checkpoint into a cleaner, verified milestone "
                "instead of vague progress."
            ),
            why_now=(
                "A handoff already exists, so the shortest path to durable progress is to verify, "
                "tighten, and lock in that checkpoint."
            ),
            draft=tune_project_draft(
                mission.project_id,
                MissionDraftView(
                    name=f"Harden {mission.project_label or mission.name}",
                    objective=(
                        f"Continue from the latest checkpoint in the mission '{mission.name}'. "
                        "First read the existing handoff in the thread, verify what is already "
                        "true, close the biggest gaps, and leave a stronger checkpoint with "
                        "validation."
                    ),
                    instance_id=target_instance.id,
                    project_id=mission.project_id,
                    cwd=mission.cwd,
                    thread_id=mission.thread_id,
                    model=mission.model,
                    reasoning_effort=mission.reasoning_effort,
                    collaboration_mode=mission.collaboration_mode,
                    max_turns=3,
                    use_builtin_agents=mission.use_builtin_agents,
                    run_verification=True,
                    auto_commit=True,
                    pause_on_approval=mission.pause_on_approval,
                    start_immediately=True,
                ),
            ),
            action_label="Load hardener",
        )

    if idle_instance is not None:
        for project in projects:
            if project.id in live_project_ids:
                continue
            if _is_project_dirty(project):
                add_opportunity(
                    f"drift-{project.id}",
                    kind="drift_sweep",
                    impact="medium",
                    title=f"Sweep drift in {project.label}",
                    summary=(
                        "Map unfinished edits, branch state, and repo risk before "
                        "starting fresh feature work."
                    ),
                    why_now=(
                        "The worktree already has drift, so a short scout run can prevent autonomy "
                        "from compounding hidden state."
                    ),
                    draft=tune_project_draft(
                        project.id,
                        MissionDraftView(
                            name=f"Drift Sweep: {project.label}",
                            objective=(
                                f"Inspect the repository at {project.path}, explain the current "
                                "branch and worktree state, identify unfinished or risky changes, "
                                "and propose the safest next autonomous mission."
                            ),
                            instance_id=idle_instance.id,
                            project_id=project.id,
                            cwd=project.path,
                            thread_id=None,
                            model="gpt-5.4-mini",
                            reasoning_effort=None,
                            collaboration_mode=None,
                            max_turns=2,
                            use_builtin_agents=True,
                            run_verification=True,
                            auto_commit=False,
                            pause_on_approval=True,
                            start_immediately=True,
                        ),
                    ),
                    action_label="Load sweep",
                )
            else:
                add_opportunity(
                    f"ship-{project.id}",
                    kind="ship_slice",
                    impact="high",
                    title=f"Ship the next slice in {project.label}",
                    summary=(
                        "Use idle capacity to land the highest-leverage visible "
                        "milestone in this repo."
                    ),
                    why_now=(
                        "A connected lane is free and this repo is not currently under autonomous "
                        "load."
                    ),
                    draft=tune_project_draft(
                        project.id,
                        MissionDraftView(
                            name=f"Ship Next Slice: {project.label}",
                            objective=(
                                f"Identify the highest-leverage product or engineering improvement "
                                f"in {project.path}, implement a meaningful milestone, verify it, "
                                "and keep iterating until you leave a durable checkpoint."
                            ),
                            instance_id=idle_instance.id,
                            project_id=project.id,
                            cwd=project.path,
                            thread_id=None,
                            model="gpt-5.4",
                            reasoning_effort=None,
                            collaboration_mode=None,
                            max_turns=5,
                            use_builtin_agents=True,
                            run_verification=True,
                            auto_commit=True,
                            pause_on_approval=True,
                            start_immediately=True,
                        ),
                    ),
                    action_label="Load ship run",
                )

    active_project_missions = [
        mission
        for mission in missions
        if mission.status == "active" and mission.project_id is not None
    ]
    if idle_instance is not None and len(instances) > 1 and active_project_missions:
        anchor = active_project_missions[0]
        add_opportunity(
            f"shadow-{anchor.id}",
            kind="shadow_scout",
            impact="medium",
            title=f"Run a shadow scout for {anchor.project_label or anchor.name}",
            summary=(
                "Use spare capacity to explore risks or alternative approaches "
                "while the main mission keeps shipping."
            ),
            why_now=(
                "Parallel capacity exists, so a smaller scout can find blind spots without slowing "
                "the main build loop."
            ),
            draft=tune_project_draft(
                anchor.project_id,
                MissionDraftView(
                    name=f"Shadow Scout: {anchor.project_label or anchor.name}",
                    objective=(
                        f"While the main mission continues, scout the project behind "
                        f"'{anchor.name}' "
                        "for hidden risks, alternative implementation paths, or missing "
                        "validation. Leave a short, high-signal handoff only."
                    ),
                    instance_id=idle_instance.id,
                    project_id=anchor.project_id,
                    cwd=anchor.cwd,
                    thread_id=None,
                    model="gpt-5.4-mini",
                    reasoning_effort=None,
                    collaboration_mode=None,
                    max_turns=2,
                    use_builtin_agents=True,
                    run_verification=False,
                    auto_commit=False,
                    pause_on_approval=True,
                    start_immediately=True,
                ),
            ),
            action_label="Load shadow scout",
        )

    ranked = {"high": 0, "medium": 1, "low": 2}
    opportunities = sorted(
        opportunities,
        key=lambda opportunity: (ranked[opportunity.impact], opportunity.title.lower()),
    )[:4]

    if opportunities:
        headline = "Ghost launches are ready"
        summary = (
            "These mission drafts are synthesized from live capacity, repo state, and recent "
            "checkpoints."
        )
    else:
        headline = "No ghost launches yet"
        summary = (
            "Connect a Codex lane or register a project and OpenZues will start proposing mission "
            "drafts here."
        )

    return DashboardLaunchpadView(
        headline=headline,
        summary=summary,
        opportunities=opportunities,
    )


def create_app(
    app_settings: Settings | None = None,
    *,
    database: Database | None = None,
    hub: BroadcastHub | None = None,
    manager: RuntimeManager | None = None,
    project_service: ProjectService | None = None,
    playbook_service: PlaybookService | None = None,
    environment_service: EnvironmentService | None = None,
    desktop_service: CodexDesktopService | None = None,
    mission_service: MissionService | None = None,
) -> FastAPI:
    active_settings = app_settings or settings
    active_database = database or Database(active_settings.effective_db_path)
    active_hub = hub or BroadcastHub()
    active_desktop_service = desktop_service or CodexDesktopService()
    active_manager = manager or RuntimeManager(
        active_database,
        active_hub,
        desktop_service=active_desktop_service,
    )
    active_project_service = project_service or ProjectService(GitHubService())
    active_playbook_service = playbook_service or PlaybookService()
    active_environment_service = environment_service or EnvironmentService(
        desktop_service=active_desktop_service
    )
    active_mission_service = mission_service or MissionService(
        active_database,
        active_manager,
        active_hub,
    )
    active_manager.add_event_listener(active_mission_service.handle_event)
    active_manager.add_server_request_listener(active_mission_service.handle_server_request)
    templates = Jinja2Templates(directory=str(active_settings.templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active_settings.data_dir.mkdir(parents=True, exist_ok=True)
        await active_database.initialize()
        await active_manager.load()
        await active_mission_service.start()
        yield
        await active_mission_service.close()
        for runtime in active_manager.instances.values():
            if runtime.client is not None:
                await runtime.client.close()

    fastapi_app = FastAPI(title="OpenZues", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    fastapi_app.mount(
        "/static",
        StaticFiles(directory=str(active_settings.static_dir)),
        name="static",
    )

    async def build_dashboard() -> DashboardView:
        project_rows = await active_database.list_projects()
        playbook_rows = await active_database.list_playbooks()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row))
            for row in project_rows
        ]
        playbooks = [PlaybookView.model_validate(row) for row in playbook_rows]
        events = [
            EventView.model_validate(
                {
                    **row,
                    "payload": compact_event_payload(row["method"], row["payload"]),
                }
            )
            for row in await active_database.list_events(250)
        ]
        instances = await active_manager.list_views()
        missions = await active_mission_service.list_views()
        doctrines = build_doctrines(missions, projects)
        return DashboardView(
            brief=build_brief(instances, missions, projects),
            launchpad=build_launchpad(instances, missions, projects, doctrines=doctrines),
            radar=build_radar(instances, missions, projects),
            cortex=build_cortex(instances, missions, projects, doctrines=doctrines),
            reflex_deck=build_reflex_deck(instances, missions, projects, doctrines=doctrines),
            instances=instances,
            missions=missions,
            projects=projects,
            playbooks=playbooks,
            events=events,
        )

    @fastapi_app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"settings": active_settings},
        )

    @fastapi_app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @fastapi_app.get("/api/dashboard")
    async def dashboard() -> DashboardView:
        return await build_dashboard()

    @fastapi_app.get("/api/diagnostics")
    async def diagnostics() -> DiagnosticsView:
        return active_environment_service.collect()

    @fastapi_app.post("/api/instances")
    async def create_instance(payload: InstanceCreate) -> dict:
        command = None if payload.transport == "desktop" else (
            payload.command or active_settings.default_codex_command
        )
        args = None if payload.transport == "desktop" else (
            payload.args or active_settings.default_codex_args
        )
        websocket_url = payload.websocket_url if payload.transport == "websocket" else None
        runtime = await active_manager.create_instance(
            name=payload.name,
            transport=payload.transport,
            command=command,
            args=args,
            websocket_url=websocket_url,
            cwd=payload.cwd,
            auto_connect=payload.auto_connect,
        )
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/quick-connect/desktop")
    async def quick_connect_desktop() -> dict:
        runtime = await active_manager.quick_connect_desktop(cwd=str(Path.cwd()))
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/connect")
    async def connect_instance(instance_id: int) -> dict:
        runtime = await active_manager.connect_instance(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/disconnect")
    async def disconnect_instance(instance_id: int) -> dict:
        await active_manager.disconnect_instance(instance_id)
        runtime = await active_manager.get(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/refresh")
    async def refresh_instance(instance_id: int) -> dict:
        runtime = await active_manager.refresh_instance(instance_id)
        return runtime.view().model_dump()

    @fastapi_app.post("/api/instances/{instance_id}/threads")
    async def start_thread(instance_id: int, payload: ThreadCreate) -> dict:
        return await active_manager.start_thread(
            instance_id,
            model=payload.model,
            cwd=payload.cwd,
            reasoning_effort=payload.reasoning_effort,
            collaboration_mode=payload.collaboration_mode,
        )

    @fastapi_app.post("/api/instances/{instance_id}/turns")
    async def start_turn(instance_id: int, payload: TurnCreate) -> dict:
        return await active_manager.start_turn(
            instance_id,
            thread_id=payload.thread_id,
            text=payload.text,
            cwd=payload.cwd,
            model=payload.model,
            reasoning_effort=payload.reasoning_effort,
            collaboration_mode=payload.collaboration_mode,
        )

    @fastapi_app.post("/api/instances/{instance_id}/turns/{thread_id}/interrupt")
    async def interrupt_turn(instance_id: int, thread_id: str) -> dict:
        return await active_manager.interrupt_turn(instance_id, thread_id)

    @fastapi_app.post("/api/instances/{instance_id}/reviews")
    async def start_review(instance_id: int, payload: ReviewCreate) -> dict:
        return await active_manager.start_review(instance_id, payload.thread_id)

    @fastapi_app.post("/api/instances/{instance_id}/commands")
    async def exec_command(instance_id: int, payload: CommandCreate) -> dict:
        return await active_manager.exec_command(
            instance_id,
            command=payload.command,
            cwd=payload.cwd,
            timeout_ms=payload.timeout_ms,
            tty=payload.tty,
        )

    @fastapi_app.post("/api/instances/{instance_id}/requests/{request_id}/resolve")
    async def resolve_request(
        instance_id: int,
        request_id: str,
        payload: RequestResolution,
    ) -> dict[str, bool]:
        await active_manager.resolve_request(instance_id, request_id, payload.result)
        return {"ok": True}

    @fastapi_app.post("/api/projects")
    async def create_project(payload: ProjectCreate) -> ProjectView:
        path = str(Path(payload.path).expanduser())
        label = payload.label or Path(path).name
        await active_database.create_project(path=path, label=label)
        rows = await active_database.list_projects()
        row = next((item for item in rows if Path(item["path"]).expanduser() == Path(path)), None)
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create project.")
        return ProjectView.model_validate(active_project_service.inspect(row))

    @fastapi_app.post("/api/missions")
    async def create_mission(payload: MissionCreate) -> dict:
        try:
            return (await active_mission_service.create(payload)).model_dump()
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/start")
    async def start_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.resume(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/pause")
    async def pause_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.pause(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/run-now")
    async def run_mission_now(mission_id: int) -> dict:
        try:
            return (await active_mission_service.run_now(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/reflex")
    async def fire_mission_reflex(mission_id: int, payload: MissionReflexRun) -> dict:
        try:
            return (await active_mission_service.fire_reflex(mission_id, payload)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @fastapi_app.post("/api/missions/{mission_id}/complete")
    async def complete_mission(mission_id: int) -> dict:
        try:
            return (await active_mission_service.complete(mission_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.delete("/api/missions/{mission_id}")
    async def delete_mission(mission_id: int) -> dict[str, bool]:
        await active_mission_service.delete(mission_id)
        return {"ok": True}

    @fastapi_app.get("/api/playbooks")
    async def list_playbooks() -> list[PlaybookView]:
        rows = await active_database.list_playbooks()
        return [PlaybookView.model_validate(row) for row in rows]

    @fastapi_app.post("/api/playbooks")
    async def create_playbook(payload: PlaybookCreate) -> PlaybookView:
        playbook_id = await active_database.create_playbook(
            name=payload.name,
            description=payload.description,
            kind=payload.kind,
            instance_id=payload.instance_id,
            payload=payload.model_dump(exclude={"name", "description", "kind", "instance_id"}),
        )
        row = await active_database.get_playbook(playbook_id)
        if row is None:
            raise HTTPException(status_code=500, detail="Failed to create playbook.")
        return PlaybookView.model_validate(row)

    @fastapi_app.delete("/api/playbooks/{playbook_id}")
    async def delete_playbook(playbook_id: int) -> dict[str, bool]:
        await active_database.delete_playbook(playbook_id)
        return {"ok": True}

    @fastapi_app.post("/api/playbooks/{playbook_id}/run")
    async def run_playbook(playbook_id: int, payload: PlaybookRun) -> PlaybookRunResult:
        playbook = await active_database.get_playbook(playbook_id)
        if playbook is None:
            raise HTTPException(status_code=404, detail="Playbook not found.")
        try:
            return await active_playbook_service.execute(playbook, payload, active_manager)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.websocket("/ws")
    async def websocket_events(websocket: WebSocket) -> None:
        await websocket.accept()
        async with active_hub.subscribe() as queue:
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_text(json.dumps(event))
            except WebSocketDisconnect:
                return

    return fastapi_app


app = create_app()
