from __future__ import annotations

import json
import os
import re
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from openzues.database import Database
from openzues.logging_utils import configure_logging
from openzues.schemas import (
    CommandCreate,
    ControlChatCreate,
    ControlChatResponse,
    DashboardAttentionQueueView,
    DashboardBriefView,
    DashboardContinuityPacketView,
    DashboardControlChatView,
    DashboardCortexView,
    DashboardDoctrineView,
    DashboardDreamView,
    DashboardEconomyView,
    DashboardInterferenceView,
    DashboardLaunchpadView,
    DashboardOpportunityView,
    DashboardRadarView,
    DashboardRecallView,
    DashboardSignalView,
    DashboardView,
    DiagnosticsView,
    DockerExecutorArmRequest,
    DockerExecutorPreflightRequest,
    EventView,
    GatewayBootstrapUpdate,
    GatewayBootstrapView,
    GatewayCapabilityView,
    GatewayMemoryProofRun,
    HermesDoctorView,
    HermesExecutorArmResultView,
    HermesExecutorPreflightView,
    HermesRuntimeProfileUpdate,
    HermesRuntimeProfileView,
    HermesUpdateView,
    InstanceCreate,
    InstanceView,
    IntegrationCreate,
    IntegrationView,
    LaneSnapshotView,
    MissionCreate,
    MissionDraftView,
    MissionReflexRun,
    MissionView,
    NotificationRouteCreate,
    NotificationRouteTestResultView,
    NotificationRouteView,
    OnboardingBootstrapCreate,
    OnboardingBootstrapResultView,
    OperatorCreate,
    OperatorCredentialView,
    PlaybookCreate,
    PlaybookRun,
    PlaybookRunResult,
    PlaybookView,
    ProjectAgentHarnessView,
    ProjectCreate,
    ProjectHarnessOperationCreate,
    ProjectHarnessOperationView,
    ProjectView,
    RemoteMissionCreate,
    RemoteRequestView,
    RemoteTaskTrigger,
    RequestResolution,
    ReviewCreate,
    SetupLaunchHandoffView,
    SetupResetRequest,
    SetupResetResultView,
    SetupStatusView,
    SetupWizardSessionUpdate,
    SetupWizardSessionView,
    SkillPinCreate,
    SkillPinView,
    TaskBlueprintCreate,
    TaskBlueprintView,
    TeamCreate,
    TeamView,
    ThreadCreate,
    TurnCreate,
    VaultSecretCreate,
    VaultSecretView,
    WorkspaceShellArmRequest,
)
from openzues.services.access import AccessService, AuthenticatedOperator, build_access_posture
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.continuity import build_continuity, build_continuity_packet
from openzues.services.control_chat import ControlChatService
from openzues.services.control_plane import ControlPlaneLease
from openzues.services.cortex import (
    build_cortex,
    build_doctrines,
    doctrine_index,
    tune_draft_with_doctrine,
)
from openzues.services.dreams import build_dream_deck
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.economy import build_economy
from openzues.services.environment import EnvironmentService
from openzues.services.followups import mission_followup_kind, mission_matches_payload
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.gateway_capability import GatewayCapabilityService
from openzues.services.github import GitHubService
from openzues.services.hermes_platform import HermesPlatformService
from openzues.services.hermes_runtime_profile import (
    DEFAULT_HERMES_EXECUTOR,
    DEFAULT_HERMES_MEMORY_PROVIDER,
    build_runtime_profile_fields,
    load_saved_runtime_preferences,
)
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.hub import BroadcastHub
from openzues.services.interference import build_interference
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager, compact_event_payload
from openzues.services.missions import MissionService
from openzues.services.onboarding import OnboardingService
from openzues.services.ops_mesh import OpsMeshService, build_ops_mesh
from openzues.services.playbooks import PlaybookService, summarize_playbook_result
from openzues.services.projects import ProjectService
from openzues.services.recall import RecallService
from openzues.services.reflexes import build_reflex_deck
from openzues.services.remote_ops import RemoteOpsService
from openzues.services.run_pressure import has_checkpoint_pressure
from openzues.services.runtime_updates import RuntimeUpdateService
from openzues.services.scope_enforcer import build_scope_assessment
from openzues.services.setup import SetupService
from openzues.services.vault import VaultService
from openzues.settings import Settings, settings

configure_logging()

CHECKPOINT_HARDENER_COOLDOWN = timedelta(minutes=30)

PLUGIN_DUPLICATE_SERVER_RE = re.compile(
    r"skipping duplicate plugin MCP server name.*?plugin\s*=\s*\"(?P<plugin>[^\"]+)\""
    r".*?previous_plugin\s*=\s*\"(?P<previous>[^\"]+)\".*?server\s*=\s*\"(?P<server>[^\"]+)\"",
    re.IGNORECASE,
)
PLUGIN_DEFAULT_PROMPT_RE = re.compile(
    r"ignoring interface\.defaultPrompt: prompt must be at most 128 characters"
    r"(?:\s+path\s*=\s*(?P<path>.+))?",
    re.IGNORECASE,
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


def _mission_is_streaming(mission: MissionView) -> bool:
    return bool(mission.live_telemetry.streaming)


def _mission_thread_quiet(mission: MissionView, *, threshold_seconds: int = 180) -> bool:
    if _mission_is_streaming(mission):
        return False
    age_seconds = mission.live_telemetry.last_thread_event_age_seconds
    return age_seconds is None or age_seconds >= threshold_seconds


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.split("%", 1)[0].strip().lower()
    if normalized in {"localhost", "testclient"}:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _pick_launch_instance(
    instances: list[InstanceView],
    missions: list[MissionView],
    *,
    prefer_idle: bool = True,
    allowed_instance_ids: set[int] | None = None,
) -> InstanceView | None:
    live_instance_ids = {
        mission.instance_id for mission in missions if mission.status in {"active", "blocked"}
    }
    if prefer_idle:
        for instance in instances:
            if (
                instance.connected
                and instance.id not in live_instance_ids
                and (allowed_instance_ids is None or instance.id in allowed_instance_ids)
            ):
                return instance
    for instance in instances:
        if instance.connected and (
            allowed_instance_ids is None or instance.id in allowed_instance_ids
        ):
            return instance
    if allowed_instance_ids is not None:
        return None
    return instances[0] if instances else None


def _gateway_planning_action(gateway_capability: GatewayCapabilityView) -> str:
    if gateway_capability.approval_posture.approval_count:
        return "Resolve pending approvals before launching more autonomous work."
    if gateway_capability.inventory.tracked_gap_count:
        return "Repair the tracked integration gaps before trusting the next launch."
    route = gateway_capability.launch_policy.launch_route
    if route is not None and route.status == "repair":
        return "Repair the saved launch route before trusting the next remote-first handoff."
    if (
        gateway_capability.connected_lane_health.total_count
        and not gateway_capability.connected_lane_health.ready_count
    ):
        return "Reconnect or clear a lane so at least one gateway lane is launch-ready."
    if gateway_capability.warnings:
        return gateway_capability.warnings[0]
    return "Inspect Gateway Doctor before launching the next mission."


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
            "Launch a mission, start a thread manually, or prepare the workspace for the next run."
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
    *,
    gateway_capability: GatewayCapabilityView | None = None,
) -> DashboardRadarView:
    signals: list[DashboardSignalView] = []
    ready_handoffs: list[MissionView] = []
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
        add_signal(
            "gateway/capability",
            lane="reliability",
            level="critical" if gateway_capability.level == "critical" else "warn",
            title=gateway_capability.headline,
            detail=gateway_capability.summary,
            action=_gateway_planning_action(gateway_capability),
        )

    for mission in missions:
        age_minutes = _minutes_since(mission.last_activity_at)
        last_error = str(mission.last_error or "")
        scope = build_scope_assessment(mission, checkpoints=mission.checkpoints)
        streaming = _mission_is_streaming(mission)

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
                action=mission.suggested_action,
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
                    "This mission is waiting for another in-progress mission on the same instance."
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
            and not streaming
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

        if mission.status == "active" and scope.drift_level in {"drifting", "critical"}:
            add_signal(
                f"mission-{mission.id}-scope",
                lane="attention",
                level="critical" if scope.drift_level == "critical" else "warn",
                title=f"{mission.name} is drifting away from its charter",
                detail=scope.drift_summary,
                action=scope.recommended_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.status == "active" and has_checkpoint_pressure(
            total_tokens=mission.total_tokens,
            model=mission.model,
            has_checkpoint=bool(mission.last_checkpoint),
        ):
            add_signal(
                f"mission-{mission.id}-burn",
                lane="throughput",
                level="warn",
                title=f"{mission.name} is on a long run without a handoff",
                detail=(
                    f"The mission has consumed {mission.total_tokens:,} tokens "
                    "without producing a durable checkpoint yet."
                ),
                action=(
                    "Review the live commentary and checkpoint strategy before continuity "
                    "gets fuzzy."
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

        if mission.status == "active" and mission.in_progress and _mission_thread_quiet(mission):
            add_signal(
                f"mission-{mission.id}-thread-quiet",
                lane="reliability",
                level="warn",
                title=f"{mission.name} is in progress but the live thread went quiet",
                detail=mission.live_telemetry.summary,
                action=(
                    "Inspect the active thread before assuming the run is healthy, then steer it "
                    "toward one verified next step."
                ),
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=age_minutes,
            )
            continue

        if mission.status in {"paused", "completed"} and mission.last_checkpoint:
            ready_handoffs.append(mission)

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

    ready_handoffs = sorted(
        ready_handoffs,
        key=lambda mission: (
            _minutes_since(mission.last_activity_at)
            if _minutes_since(mission.last_activity_at) is not None
            else 9999,
            mission.name.lower(),
        ),
    )
    if len(ready_handoffs) > 2:
        focus_names = ", ".join(mission.name for mission in ready_handoffs[:2])
        remainder = len(ready_handoffs) - 2
        suffix = f", and {remainder} more" if remainder > 0 else ""
        add_signal(
            "attention/handoff-backlog",
            lane="attention",
            level="ready",
            title=f"{len(ready_handoffs)} checkpoint handoffs are parked in reserve",
            detail=(
                f"{focus_names}{suffix} already have durable checkpoints ready for continuation."
            ),
            action="Open the mission list or transcript and pick the next relay to resume.",
            freshness_minutes=_minutes_since(ready_handoffs[0].last_activity_at),
        )
    else:
        for mission in ready_handoffs:
            add_signal(
                f"mission-{mission.id}-handoff",
                lane="attention",
                level="ready",
                title=f"Handoff ready from {mission.name}",
                detail="A fresh checkpoint is available for review or continuation.",
                action=mission.suggested_action,
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=_minutes_since(mission.last_activity_at),
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
        ready_count = len(ready_handoffs)
        if ready_count > 2:
            summary = (
                "Autonomy lanes are clear. "
                f"{ready_count} ready handoff{'s are' if ready_count != 1 else ' is'} "
                "parked in reserve."
            )
        else:
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
    gateway_capability: GatewayCapabilityView | None = None,
    preferred_memory_provider: str = DEFAULT_HERMES_MEMORY_PROVIDER,
    preferred_executor: str = DEFAULT_HERMES_EXECUTOR,
) -> DashboardLaunchpadView:
    opportunities: list[DashboardOpportunityView] = []
    project_doctrine_index = doctrine_index(doctrines or build_doctrines(missions, projects))
    runtime_profile_fields = build_runtime_profile_fields(
        preferred_memory_provider=preferred_memory_provider,
        preferred_executor=preferred_executor,
    )
    live_project_ids = {
        mission.project_id
        for mission in missions
        if mission.project_id is not None and mission.status in {"active", "blocked"}
    }
    seen_ids: set[str] = set()

    def has_equivalent_live_draft(draft: MissionDraftView) -> bool:
        return any(
            mission.status in {"active", "blocked", "paused"}
            and mission_matches_payload(mission, draft)
            for mission in missions
        )

    def latest_completed_equivalent_followup(
        draft: MissionDraftView,
        *,
        kind: Literal["checkpoint_hardener", "recovery_run"],
    ) -> MissionView | None:
        completed = [
            mission
            for mission in missions
            if mission.status == "completed"
            and mission_followup_kind(mission) == kind
            and mission_matches_payload(mission, draft)
        ]
        if not completed:
            return None
        return max(completed, key=lambda mission: mission.updated_at)

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
            "gateway_repair",
        ],
        impact: Literal["high", "medium", "low"],
        title: str,
        summary: str,
        why_now: str,
        draft: MissionDraftView,
        action_label: str = "Load draft",
    ) -> None:
        if kind in {"checkpoint_hardener", "recovery_run"} and has_equivalent_live_draft(draft):
            return
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

    ready_launch_instance_ids = (
        {
            lane.instance_id
            for lane in gateway_capability.connected_lane_health.lanes
            if lane.connected and lane.level == "ready"
        }
        if gateway_capability is not None
        else None
    )
    connected_launch_instance_ids = (
        {
            lane.instance_id
            for lane in gateway_capability.connected_lane_health.lanes
            if lane.connected
        }
        if gateway_capability is not None
        else None
    )
    idle_instance = _pick_launch_instance(
        instances,
        missions,
        prefer_idle=True,
        allowed_instance_ids=ready_launch_instance_ids,
    )
    connected_instance = _pick_launch_instance(
        instances,
        missions,
        prefer_idle=False,
        allowed_instance_ids=ready_launch_instance_ids,
    )
    repair_instance = _pick_launch_instance(
        instances,
        missions,
        prefer_idle=True,
        allowed_instance_ids=connected_launch_instance_ids,
    )

    if (
        gateway_capability is not None
        and repair_instance is not None
        and (
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
        )
    ):
        add_opportunity(
            "gateway-repair",
            kind="gateway_repair",
            impact="high" if gateway_capability.level == "critical" else "medium",
            title="Stabilize gateway posture",
            summary=(
                "Use the shared gateway doctor surface to repair launch blockers before "
                "starting another autonomous slice."
            ),
            why_now=gateway_capability.summary,
            draft=MissionDraftView(
                name="Stabilize Gateway Posture",
                objective=(
                    "Continue from the current gateway capability / doctor summary. Reuse the "
                    "existing runtime, diagnostics, Ops Mesh inventory, and saved gateway "
                    "bootstrap state to repair the highest-risk gateway blocker without "
                    "broadening scope. Verify the fix and leave a durable checkpoint."
                ),
                instance_id=repair_instance.id,
                project_id=None,
                cwd=repair_instance.cwd,
                thread_id=None,
                model="gpt-5.4-mini",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                start_immediately=True,
                **runtime_profile_fields,
            ),
            action_label="Load gateway repair",
        )

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
                **runtime_profile_fields,
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
        if mission_followup_kind(mission) is not None:
            continue
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
                    "Re-open the path from the last failure without throwing away mission context."
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
                        **runtime_profile_fields,
                    ),
                ),
                action_label="Recover run",
            )
            continue

        hardener_draft = tune_project_draft(
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
                **runtime_profile_fields,
            ),
        )
        prior_hardener = latest_completed_equivalent_followup(
            hardener_draft,
            kind="checkpoint_hardener",
        )
        if (
            prior_hardener is not None
            and datetime.now(UTC) - prior_hardener.updated_at <= CHECKPOINT_HARDENER_COOLDOWN
        ):
            continue

        add_opportunity(
            f"harden-{mission.id}",
            kind="checkpoint_hardener",
            impact="high",
            title=f"Harden {mission.project_label or mission.name}",
            summary=(
                "Run another optional tightening pass from the latest checkpoint."
                if prior_hardener is not None
                else (
                    "Turn the latest checkpoint into a cleaner, verified milestone "
                    "instead of vague progress."
                )
            ),
            why_now=(
                "A prior hardening pass already landed. Reopen this only if you want another "
                "verification-focused tightening pass."
                if prior_hardener is not None
                else (
                    "A handoff already exists, so the shortest path to durable progress is to "
                    "verify, tighten, and lock in that checkpoint."
                )
            ),
            draft=hardener_draft,
            action_label="Load another hardener" if prior_hardener is not None else "Load hardener",
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
                            **runtime_profile_fields,
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
                            **runtime_profile_fields,
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
                    **runtime_profile_fields,
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
        if (
            gateway_capability is not None
            and gateway_capability.level in {"critical", "warn"}
            and gateway_capability.connected_lane_health.ready_count == 0
        ):
            headline = "Gateway posture needs repair before broad launches"
            summary = gateway_capability.summary
        else:
            headline = "Ghost launches are ready"
            summary = (
                "These mission drafts are synthesized from live capacity, repo state, and recent "
                "checkpoints."
            )
    else:
        if (
            gateway_capability is not None
            and gateway_capability.connected_lane_health.total_count > 0
            and gateway_capability.connected_lane_health.ready_count == 0
        ):
            headline = "Gateway posture needs repair before new launches"
            summary = gateway_capability.summary
        else:
            headline = "No ghost launches yet"
            summary = (
                "Connect a Codex lane or register a project and OpenZues will start "
                "proposing mission drafts here."
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
    ops_mesh_service: OpsMeshService | None = None,
    vault_service: VaultService | None = None,
    access_service: AccessService | None = None,
    gateway_capability_service: GatewayCapabilityService | None = None,
    gateway_bootstrap_service: GatewayBootstrapService | None = None,
    remote_ops_service: RemoteOpsService | None = None,
    control_chat_service: ControlChatService | None = None,
    control_plane_lease: ControlPlaneLease | None = None,
) -> FastAPI:
    active_settings = app_settings or settings
    configure_hermes_skill_catalog(active_settings.hermes_source_path)
    configure_ecc_catalog(active_settings.ecc_source_path)
    active_database = database or Database(active_settings.effective_db_path)
    active_hub = hub or BroadcastHub()
    active_desktop_service = desktop_service or CodexDesktopService(
        approval_policy=active_settings.desktop_approval_policy,
        sandbox_mode=active_settings.desktop_sandbox_mode,
    )
    active_manager = manager or RuntimeManager(
        active_database,
        active_hub,
        desktop_service=active_desktop_service,
        default_stdio_command=active_settings.default_codex_command,
        default_stdio_args=active_settings.default_codex_args,
    )
    active_project_service = project_service or ProjectService(GitHubService())
    active_playbook_service = playbook_service or PlaybookService()
    active_environment_service = environment_service or EnvironmentService(
        desktop_service=active_desktop_service
    )
    active_vault_service = vault_service or VaultService(active_database, active_settings)
    active_access_service = access_service or AccessService(active_database)
    active_launch_routing_service = LaunchRoutingService(
        active_database,
        active_manager,
    )
    active_gateway_bootstrap_service = gateway_bootstrap_service or GatewayBootstrapService(
        active_database,
        active_manager,
        active_access_service,
        active_launch_routing_service,
    )
    active_mission_service = mission_service or MissionService(
        active_database,
        active_manager,
        active_hub,
    )
    active_ops_mesh_service = ops_mesh_service or OpsMeshService(
        active_database,
        active_manager,
        active_mission_service,
        active_hub,
        active_vault_service,
        playbooks=active_playbook_service,
        launch_routing=active_launch_routing_service,
    )
    active_setup_service = SetupService(
        active_database,
        active_manager,
        active_access_service,
        active_gateway_bootstrap_service,
        active_ops_mesh_service,
    )
    runtime_restart_requested = False

    async def request_runtime_restart() -> None:
        nonlocal runtime_restart_requested
        if runtime_restart_requested:
            return
        runtime_restart_requested = True
        try:
            await active_control_chat_service.close_attention_queue()
            await active_ops_mesh_service.close()
            await active_mission_service.close()
            for runtime in active_manager.instances.values():
                if runtime.client is not None:
                    await runtime.client.close()
        finally:
            active_control_plane_lease.release()
        reexec_args = list(getattr(sys, "orig_argv", []))
        if reexec_args:
            os.execv(sys.executable, [sys.executable, *reexec_args[1:]])
        os.execv(
            sys.executable,
            [
                sys.executable,
                "-m",
                "openzues.cli",
                "serve",
                "--port",
                str(active_settings.port),
            ],
        )

    active_runtime_update_service = RuntimeUpdateService(
        active_database,
        enabled=active_settings.auto_self_update_enabled,
        poll_interval_seconds=active_settings.auto_self_update_poll_interval_seconds,
        restart_callback=request_runtime_restart,
    )
    active_onboarding_service = OnboardingService(
        active_database,
        active_manager,
        active_access_service,
        active_ops_mesh_service,
        active_gateway_bootstrap_service,
        active_setup_service,
    )
    active_remote_ops_service = remote_ops_service or RemoteOpsService(
        active_database,
        active_manager,
        active_mission_service,
        active_ops_mesh_service,
        active_hub,
    )
    active_gateway_capability_service = gateway_capability_service or GatewayCapabilityService(
        active_database,
        active_manager,
        active_mission_service,
        active_access_service,
        active_remote_ops_service,
        active_ops_mesh_service,
        active_gateway_bootstrap_service,
        active_environment_service,
    )
    active_recall_service = RecallService(active_mission_service, active_database)
    active_hermes_platform_service = HermesPlatformService(
        active_database,
        active_manager,
        active_mission_service,
        active_project_service,
        active_gateway_bootstrap_service,
        active_settings,
        runtime_updates=active_runtime_update_service,
        hub=active_hub,
        poll_interval_seconds=active_settings.hermes_learning_poll_interval_seconds,
    )
    active_control_chat_service = control_chat_service or ControlChatService(
        active_database,
        active_mission_service,
        active_manager,
        active_hub,
    )
    active_control_plane_lease = control_plane_lease or ControlPlaneLease(
        active_settings.data_dir / "control-plane.lock"
    )
    active_manager.add_event_listener(active_mission_service.handle_event)
    active_manager.add_server_request_listener(active_control_chat_service.handle_server_request)
    active_manager.add_server_request_listener(active_mission_service.handle_server_request)
    active_mission_service.add_event_listener(active_ops_mesh_service.handle_mission_event)
    templates = Jinja2Templates(directory=str(active_settings.templates_dir))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        active_settings.data_dir.mkdir(parents=True, exist_ok=True)
        active_vault_service.initialize()
        await active_database.initialize()
        await active_access_service.initialize()
        is_control_plane_owner = active_control_plane_lease.acquire(
            metadata={
                "port": active_settings.port,
                "host": active_settings.host,
                "cwd": str(Path.cwd()),
            }
        )
        app.state.control_plane_role = active_control_plane_lease.role
        app.state.control_plane_owner_pid = active_control_plane_lease.owner_pid
        app.state.control_plane_lock_path = str(active_control_plane_lease.path)
        await active_manager.load(auto_connect=is_control_plane_owner)
        if is_control_plane_owner:
            await active_mission_service.start()
            await active_ops_mesh_service.start()
            await active_control_chat_service.start_attention_queue(
                build_dashboard,
                enabled=active_settings.attention_queue_enabled,
                poll_interval_seconds=active_settings.attention_queue_poll_interval_seconds,
            )
            await active_hermes_platform_service.start()
            await active_runtime_update_service.start()
        yield
        if is_control_plane_owner:
            await active_runtime_update_service.close()
            await active_hermes_platform_service.close()
            await active_control_chat_service.close_attention_queue()
            await active_ops_mesh_service.close()
            await active_mission_service.close()
        await active_manager.close()
        active_control_plane_lease.release()

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
    fastapi_app.state.database = active_database
    fastapi_app.state.manager = active_manager
    fastapi_app.state.mission_service = active_mission_service
    fastapi_app.state.control_chat_service = active_control_chat_service
    fastapi_app.state.onboarding_service = active_onboarding_service
    fastapi_app.state.gateway_capability_service = active_gateway_capability_service
    fastapi_app.state.recall_service = active_recall_service
    fastapi_app.state.hermes_platform_service = active_hermes_platform_service
    fastapi_app.state.gateway_bootstrap_service = active_gateway_bootstrap_service
    fastapi_app.state.setup_service = active_setup_service
    fastapi_app.state.control_plane_role = "leader"
    fastapi_app.state.control_plane_owner_pid = None
    fastapi_app.state.control_plane_lock_path = str(active_control_plane_lease.path)
    fastapi_app.state.runtime_update_service = active_runtime_update_service

    def empty_control_chat_view() -> DashboardControlChatView:
        if fastapi_app.state.control_plane_role != "leader":
            owner_pid = fastapi_app.state.control_plane_owner_pid
            summary = (
                "Observer mode is active because another OpenZues server already owns the "
                "autonomous control plane for this data dir."
            )
            if owner_pid is not None:
                summary = f"{summary} Leader PID: {owner_pid}."
            return DashboardControlChatView(
                headline="Observer mode is active",
                summary=summary,
                input_placeholder="Use the leader window to launch or steer missions",
                messages=[],
            )
        return DashboardControlChatView(
            headline="Tell Zues what to do next",
            summary=(
                "Chat can decide when to wait, resume, recover, harden, or launch without "
                "flooding the main transcript with manual controls."
            ),
            input_placeholder="Describe the next thing you want built, fixed, or verified",
            messages=[],
        )

    def empty_attention_queue_view() -> DashboardAttentionQueueView:
        if fastapi_app.state.control_plane_role != "leader":
            owner_pid = fastapi_app.state.control_plane_owner_pid
            summary = (
                "Autonomous queue workers are paused in this window because another "
                "OpenZues server already owns the control-plane lease."
            )
            if owner_pid is not None:
                summary = f"{summary} Leader PID: {owner_pid}."
            return DashboardAttentionQueueView(
                enabled=False,
                headline="Observer mode is active",
                summary=summary,
                actions=[],
            )
        return DashboardAttentionQueueView(
            enabled=active_settings.attention_queue_enabled,
            headline="Attention queue is standing by",
            summary=(
                "Recoveries and checkpoint hardeners will auto-launch when the lane is safe to "
                "continue."
            ),
            actions=[],
        )

    def _event_merge_key(
        row: dict[str, Any],
        payload: dict[str, Any],
    ) -> tuple[Any, ...] | None:
        if row.get("method") != "server/stderr":
            return None
        line = str(payload.get("line") or "")
        duplicate_match = PLUGIN_DUPLICATE_SERVER_RE.search(line)
        if duplicate_match:
            return (
                "plugin-duplicate-server",
                row.get("instance_id"),
                row.get("thread_id"),
                duplicate_match.group("plugin"),
                duplicate_match.group("previous"),
                duplicate_match.group("server"),
            )
        if PLUGIN_DEFAULT_PROMPT_RE.search(line):
            return (
                "plugin-default-prompt",
                row.get("instance_id"),
                row.get("thread_id"),
            )
        return None

    def _merge_event_payload(
        existing_payload: dict[str, Any],
        incoming_payload: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(existing_payload)
        merged["repeatCount"] = int(existing_payload.get("repeatCount") or 1) + 1
        merged["line"] = str(incoming_payload.get("line") or merged.get("line") or "")

        default_prompt_match = PLUGIN_DEFAULT_PROMPT_RE.search(merged["line"])
        if default_prompt_match:
            existing_paths = [
                str(path)
                for path in merged.get("paths", [])
                if isinstance(path, str) and path.strip()
            ]
            incoming_path = default_prompt_match.group("path")
            if incoming_path:
                unique_paths = list(dict.fromkeys([*existing_paths, incoming_path.strip()]))
                merged["paths"] = unique_paths[:6]
                merged["pathCount"] = len(unique_paths)
        return merged

    async def build_dashboard_events() -> list[EventView]:
        merged_events: dict[tuple[Any, ...], EventView] = {}
        passthrough_events: list[EventView] = []
        for row in await active_database.list_events(250):
            compact_payload = compact_event_payload(row["method"], row["payload"])
            event = EventView.model_validate({**row, "payload": compact_payload})
            merge_key = _event_merge_key(row, compact_payload)
            if merge_key is None:
                passthrough_events.append(event)
                continue
            existing = merged_events.get(merge_key)
            if existing is None:
                payload = dict(compact_payload)
                payload["repeatCount"] = 1
                default_prompt_match = PLUGIN_DEFAULT_PROMPT_RE.search(
                    str(payload.get("line") or "")
                )
                if default_prompt_match:
                    path = default_prompt_match.group("path")
                    if path:
                        payload["paths"] = [path.strip()]
                        payload["pathCount"] = 1
                merged_events[merge_key] = event.model_copy(update={"payload": payload})
                continue
            merged_payload = _merge_event_payload(existing.payload, compact_payload)
            merged_events[merge_key] = existing.model_copy(
                update={"payload": merged_payload, "created_at": event.created_at}
            )
        events = [*passthrough_events, *merged_events.values()]
        return sorted(events, key=lambda item: item.created_at)

    async def build_dashboard() -> DashboardView:
        project_rows = await active_database.list_projects()
        playbook_rows = await active_database.list_playbooks()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row)) for row in project_rows
        ]
        playbooks = [PlaybookView.model_validate(row) for row in playbook_rows]
        task_blueprints = await active_ops_mesh_service.list_task_blueprint_views()
        vault_secrets = await active_ops_mesh_service.list_vault_secret_views()
        integrations = await active_ops_mesh_service.list_integration_views()
        notification_routes = await active_ops_mesh_service.list_notification_route_views()
        skill_pins = await active_ops_mesh_service.list_skill_pin_views()
        lane_snapshots = await active_ops_mesh_service.list_lane_snapshot_views()
        teams = await active_access_service.list_team_views()
        operators = await active_access_service.list_operator_views()
        remote_requests = await active_remote_ops_service.list_remote_request_views()
        access_posture = build_access_posture(teams, operators, remote_requests)
        events = await build_dashboard_events()
        instances = await active_manager.list_views()
        missions = await active_mission_service.list_views()
        doctrines = build_doctrines(missions, projects)
        gateway_capability = await active_gateway_capability_service.get_view()
        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            active_database
        )
        economy = build_economy(missions, projects, task_blueprints, remote_requests)
        interference = build_interference(
            missions,
            projects,
            task_blueprints,
            remote_requests,
            gateway_capability=gateway_capability,
        )
        dashboard_view = DashboardView(
            brief=build_brief(instances, missions, projects),
            control_chat=empty_control_chat_view(),
            attention_queue=empty_attention_queue_view(),
            launchpad=build_launchpad(
                instances,
                missions,
                projects,
                doctrines=doctrines,
                gateway_capability=gateway_capability,
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
            radar=build_radar(
                instances,
                missions,
                projects,
                gateway_capability=gateway_capability,
            ),
            gateway_capability=gateway_capability,
            gateway_bootstrap=await active_gateway_bootstrap_service.get_view(),
            ops_mesh=build_ops_mesh(
                instances,
                missions,
                projects,
                playbooks,
                task_blueprints,
                skill_pins,
                vault_secrets,
                integrations,
                notification_routes,
                lane_snapshots,
                access_posture=access_posture,
                teams=teams,
                operators=operators,
                remote_requests=remote_requests,
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
            economy=economy,
            interference=interference,
            continuity=build_continuity(
                instances,
                missions,
                projects,
                doctrines=doctrines,
            ),
            recall=await active_recall_service.search(limit=6),
            dream_deck=build_dream_deck(
                instances,
                missions,
                projects,
                doctrines=doctrines,
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
            cortex=build_cortex(instances, missions, projects, doctrines=doctrines),
            reflex_deck=build_reflex_deck(instances, missions, projects, doctrines=doctrines),
            instances=instances,
            missions=missions,
            projects=projects,
            playbooks=playbooks,
            task_blueprints=task_blueprints,
            integrations=integrations,
            notification_routes=notification_routes,
            skill_pins=skill_pins,
            lane_snapshots=lane_snapshots,
            events=events,
        )
        if fastapi_app.state.control_plane_role != "leader":
            return dashboard_view
        return dashboard_view.model_copy(
            update={
                "attention_queue": await active_control_chat_service.build_attention_queue_view(
                    dashboard_view,
                    enabled=active_settings.attention_queue_enabled,
                ),
                "control_chat": await active_control_chat_service.build_view(dashboard_view),
            }
        )

    @fastapi_app.middleware("http")
    async def guard_observer_mutations(request: Request, call_next):
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path.startswith("/api/")
            and fastapi_app.state.control_plane_role != "leader"
        ):
            owner_pid = fastapi_app.state.control_plane_owner_pid
            detail = (
                "Observer mode is active because another OpenZues server owns the control plane."
            )
            if owner_pid is not None:
                detail = f"{detail} Leader PID: {owner_pid}."
            return JSONResponse(
                status_code=409,
                content={
                    "detail": detail,
                    "control_plane": fastapi_app.state.control_plane_role,
                },
            )
        return await call_next(request)

    async def require_remote_operator(
        request: Request,
        permission: str,
    ) -> AuthenticatedOperator:
        api_key = active_access_service.extract_api_key(dict(request.headers))
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Remote control requires an API key via Authorization: Bearer <key> "
                    "or X-OpenZues-Key."
                ),
            )
        try:
            return await active_access_service.authenticate_api_key(api_key, permission=permission)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    async def require_management_access(request: Request, permission: str) -> None:
        host = request.client.host if request.client is not None else None
        if _is_loopback_host(host):
            return
        await require_remote_operator(request, permission)

    @fastapi_app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        asset_version = max(
            (
                path.stat().st_mtime_ns
                for path in active_settings.static_dir.rglob("*")
                if path.is_file()
            ),
            default=0,
        )
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"settings": active_settings, "asset_version": asset_version},
        )

    @fastapi_app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "control_plane": fastapi_app.state.control_plane_role,
            "owner_pid": fastapi_app.state.control_plane_owner_pid,
            "lock_path": fastapi_app.state.control_plane_lock_path,
            "runtime_update": active_runtime_update_service.snapshot(),
        }

    @fastapi_app.get("/api/dashboard")
    async def dashboard() -> DashboardView:
        return await build_dashboard()

    @fastapi_app.post("/api/control-chat")
    async def control_chat(payload: ControlChatCreate) -> ControlChatResponse:
        text = payload.text.strip()
        if not text:
            raise HTTPException(
                status_code=400,
                detail="Enter a message before sending it to Zues.",
            )
        dashboard_view = await build_dashboard()
        try:
            return await active_control_chat_service.submit(text, dashboard_view)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.get("/api/economy")
    async def economy() -> DashboardEconomyView:
        dashboard_view = await build_dashboard()
        return dashboard_view.economy

    @fastapi_app.get("/api/projects/{project_id}/economy")
    async def project_economy(project_id: int) -> DashboardEconomyView:
        dashboard_view = await build_dashboard()
        scopes = [
            scope for scope in dashboard_view.economy.scopes if scope.project_id == project_id
        ]
        if not scopes:
            project_rows = await active_database.list_projects()
            project = next((row for row in project_rows if int(row["id"]) == project_id), None)
            if project is None:
                raise HTTPException(status_code=404, detail="Project not found.")
            label = str(project["label"])
            return DashboardEconomyView(
                headline=f"Autonomy economy is idle for {label}",
                summary=(
                    "No scoped mission history exists yet for this project, so there is no capital "
                    "profile to learn from."
                ),
                scopes=[],
            )
        return DashboardEconomyView(
            headline=dashboard_view.economy.headline,
            summary=dashboard_view.economy.summary,
            scopes=scopes,
        )

    @fastapi_app.get("/api/interference")
    async def interference() -> DashboardInterferenceView:
        dashboard_view = await build_dashboard()
        return dashboard_view.interference

    @fastapi_app.get("/api/projects/{project_id}/interference")
    async def project_interference(project_id: int) -> DashboardInterferenceView:
        dashboard_view = await build_dashboard()
        vectors = [
            vector
            for vector in dashboard_view.interference.vectors
            if vector.project_id == project_id
        ]
        if not vectors:
            project_rows = await active_database.list_projects()
            project = next((row for row in project_rows if int(row["id"]) == project_id), None)
            if project is None:
                raise HTTPException(status_code=404, detail="Project not found.")
            label = str(project["label"])
            return DashboardInterferenceView(
                headline=f"Interference is calm for {label}",
                summary=(
                    "No overlap between live missions, automation loops, or remote launches is "
                    "currently forecast for this project."
                ),
                vectors=[],
            )
        return DashboardInterferenceView(
            headline=dashboard_view.interference.headline,
            summary=dashboard_view.interference.summary,
            vectors=vectors,
        )

    @fastapi_app.get("/api/missions/{mission_id}/continuity")
    async def mission_continuity(mission_id: int) -> DashboardContinuityPacketView:
        try:
            mission = await active_mission_service.get_view(mission_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        project_rows = await active_database.list_projects()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row)) for row in project_rows
        ]
        doctrines = build_doctrines(await active_mission_service.list_views(), projects)
        doctrine = doctrine_index(doctrines).get(mission.project_id or -1)
        instances = await active_manager.list_views()
        connected = next(
            (instance.connected for instance in instances if instance.id == mission.instance_id),
            False,
        )
        return build_continuity_packet(
            mission,
            instance_connected=connected,
            checkpoints=mission.checkpoints,
            doctrine=doctrine,
        )

    @fastapi_app.get("/api/projects/{project_id}/dream")
    async def project_dream(project_id: int) -> DashboardDreamView:
        project_rows = await active_database.list_projects()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row)) for row in project_rows
        ]
        project = next((item for item in projects if item.id == project_id), None)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")

        instances = await active_manager.list_views()
        missions = await active_mission_service.list_views()
        doctrines = build_doctrines(missions, projects)
        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            active_database
        )
        deck = build_dream_deck(
            instances,
            missions,
            projects,
            doctrines=doctrines,
            preferred_memory_provider=preferred_memory_provider,
            preferred_executor=preferred_executor,
        )
        dream = next((item for item in deck.dreams if item.project_id == project_id), None)
        if dream is None:
            raise HTTPException(status_code=404, detail="Dream candidate not available yet.")
        return dream

    @fastapi_app.get(
        "/api/projects/{project_id}/harness",
        response_model=ProjectAgentHarnessView,
    )
    async def project_harness(project_id: int) -> ProjectAgentHarnessView:
        row = await active_database.get_project(project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        harness = active_project_service.inspect_harness(row)
        if harness is None:
            raise HTTPException(status_code=404, detail="Project harness not available.")
        return ProjectAgentHarnessView.model_validate(harness)

    @fastapi_app.post(
        "/api/projects/{project_id}/harness/actions",
        response_model=ProjectHarnessOperationView,
    )
    async def project_harness_action(
        project_id: int,
        payload: ProjectHarnessOperationCreate,
    ) -> ProjectHarnessOperationView:
        row = await active_database.get_project(project_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        try:
            result = active_project_service.run_harness_operation(
                row,
                payload.mode,
                profile=payload.profile,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ProjectHarnessOperationView.model_validate(result)

    @fastapi_app.get("/api/diagnostics")
    async def diagnostics() -> DiagnosticsView:
        return active_environment_service.collect()

    @fastapi_app.get("/api/recall")
    async def recall(
        query: str | None = None,
        project_id: int | None = None,
        limit: int = 6,
    ) -> DashboardRecallView:
        return await active_recall_service.search(
            query=query,
            project_id=project_id,
            limit=limit,
        )

    @fastapi_app.get("/api/cortex")
    async def cortex() -> DashboardCortexView:
        project_rows = await active_database.list_projects()
        projects = [
            ProjectView.model_validate(active_project_service.inspect(row)) for row in project_rows
        ]
        instances = await active_manager.list_views()
        missions = await active_mission_service.list_views()
        doctrines = build_doctrines(missions, projects)
        return build_cortex(instances, missions, projects, doctrines=doctrines)

    @fastapi_app.get("/api/hermes/profile")
    async def hermes_profile() -> HermesRuntimeProfileView:
        return await active_hermes_platform_service.get_runtime_profile()

    @fastapi_app.put("/api/hermes/profile")
    async def update_hermes_profile(
        payload: HermesRuntimeProfileUpdate,
    ) -> HermesRuntimeProfileView:
        try:
            return await active_hermes_platform_service.update_runtime_profile(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.get("/api/hermes/doctor")
    async def hermes_doctor() -> HermesDoctorView:
        return await active_hermes_platform_service.get_doctor_view()

    @fastapi_app.post("/api/hermes/executors/workspace-shell/arm")
    async def arm_workspace_shell(
        request: Request,
        payload: WorkspaceShellArmRequest,
    ) -> HermesExecutorArmResultView:
        await require_management_access(request, "team.manage")
        try:
            return await active_hermes_platform_service.arm_workspace_shell(
                cwd=payload.cwd,
                auto_connect=payload.auto_connect,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/hermes/executors/docker/arm")
    async def arm_docker_backend(
        request: Request,
        payload: DockerExecutorArmRequest,
    ) -> HermesExecutorArmResultView:
        await require_management_access(request, "team.manage")
        try:
            return await active_hermes_platform_service.arm_docker_backend(
                cwd=payload.cwd,
                image=payload.image,
                auto_connect=payload.auto_connect,
                mount_workspace=payload.mount_workspace,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/hermes/executors/docker/preflight")
    async def preflight_docker_backend(
        request: Request,
        payload: DockerExecutorPreflightRequest,
    ) -> HermesExecutorPreflightView:
        await require_management_access(request, "team.manage")
        return await active_hermes_platform_service.preflight_docker_backend(
            cwd=payload.cwd,
            image=payload.image,
        )

    @fastapi_app.get("/api/runtime/update")
    async def runtime_update() -> HermesUpdateView:
        return await active_hermes_platform_service.get_update_view()

    @fastapi_app.post("/api/instances")
    async def create_instance(payload: InstanceCreate) -> dict:
        command = (
            None
            if payload.transport == "desktop"
            else (payload.command or active_settings.default_codex_command)
        )
        args = (
            None
            if payload.transport == "desktop"
            else (payload.args or active_settings.default_codex_args)
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

    @fastapi_app.post("/api/onboarding/bootstrap")
    async def bootstrap_onboarding(
        request: Request,
        payload: OnboardingBootstrapCreate,
    ) -> OnboardingBootstrapResultView:
        await require_management_access(request, "team.manage")
        try:
            return await active_onboarding_service.bootstrap(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.get("/api/setup")
    async def get_setup() -> SetupStatusView:
        return await active_setup_service.inspect()

    @fastapi_app.get("/api/setup/launch")
    async def get_setup_launch() -> SetupLaunchHandoffView:
        return await active_setup_service.get_launch_handoff()

    @fastapi_app.get("/api/setup/wizard")
    async def get_setup_wizard() -> SetupWizardSessionView:
        return await active_setup_service.get_wizard_session()

    @fastapi_app.put("/api/setup/wizard")
    async def update_setup_wizard(
        request: Request,
        payload: SetupWizardSessionUpdate,
    ) -> SetupWizardSessionView:
        await require_management_access(request, "team.manage")
        return await active_setup_service.save_wizard_session(payload)

    @fastapi_app.post("/api/setup/reset")
    async def reset_setup(
        request: Request,
        payload: SetupResetRequest,
    ) -> SetupResetResultView:
        await require_management_access(request, "team.manage")
        try:
            return await active_setup_service.reset(payload.scope)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.get("/api/gateway/bootstrap")
    async def get_gateway_bootstrap() -> GatewayBootstrapView:
        return await active_gateway_bootstrap_service.get_view()

    @fastapi_app.get("/api/gateway/capability", response_model=GatewayCapabilityView)
    async def get_gateway_capability() -> GatewayCapabilityView:
        return await active_gateway_capability_service.get_view()

    @fastapi_app.post("/api/gateway/memory/prove", response_model=MissionView)
    async def run_gateway_memory_proof(
        request: Request,
        payload: GatewayMemoryProofRun,
    ) -> MissionView:
        await require_management_access(request, "team.manage")
        try:
            return await active_gateway_capability_service.launch_memory_proof(
                instance_id=payload.instance_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.put("/api/gateway/bootstrap")
    async def update_gateway_bootstrap(
        request: Request,
        payload: GatewayBootstrapUpdate,
    ) -> GatewayBootstrapView:
        await require_management_access(request, "team.manage")
        try:
            return await active_gateway_bootstrap_service.save(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/teams")
    async def create_team(request: Request, payload: TeamCreate) -> TeamView:
        await require_management_access(request, "team.manage")
        try:
            return await active_access_service.create_team(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/operators")
    async def create_operator(request: Request, payload: OperatorCreate) -> OperatorCredentialView:
        await require_management_access(request, "operator.manage")
        try:
            return await active_access_service.create_operator(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/operators/{operator_id}/api-key")
    async def issue_operator_api_key(
        operator_id: int,
        request: Request,
    ) -> OperatorCredentialView:
        await require_management_access(request, "api_key.issue")
        try:
            return await active_access_service.issue_api_key(operator_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/remote/missions")
    async def remote_create_mission(
        request: Request,
        payload: RemoteMissionCreate,
    ) -> RemoteRequestView:
        auth = await require_remote_operator(request, "remote.mission.create")
        try:
            return await active_remote_ops_service.create_mission_request(
                payload,
                auth=auth,
                source_ip=request.client.host if request.client is not None else None,
                user_agent=request.headers.get("user-agent"),
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.post("/api/remote/tasks/{task_id}/run")
    async def remote_run_task(
        task_id: int,
        request: Request,
        payload: RemoteTaskTrigger,
    ) -> RemoteRequestView:
        auth = await require_remote_operator(request, "remote.task.trigger")
        try:
            return await active_remote_ops_service.trigger_task_request(
                task_id,
                payload,
                auth=auth,
                source_ip=request.client.host if request.client is not None else None,
                user_agent=request.headers.get("user-agent"),
                idempotency_key=request.headers.get("Idempotency-Key"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.get("/api/tasks")
    async def list_tasks() -> list[TaskBlueprintView]:
        return await active_ops_mesh_service.list_task_blueprint_views()

    @fastapi_app.post("/api/tasks")
    async def create_task(payload: TaskBlueprintCreate) -> TaskBlueprintView:
        return await active_ops_mesh_service.create_task_blueprint(payload)

    @fastapi_app.post("/api/tasks/{task_id}/run")
    async def run_task(task_id: int) -> dict[str, Any]:
        try:
            return (await active_ops_mesh_service.run_task_blueprint_now(task_id)).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: int) -> dict[str, bool]:
        await active_ops_mesh_service.delete_task_blueprint(task_id)
        return {"ok": True}

    @fastapi_app.post("/api/vault-secrets")
    async def create_vault_secret(payload: VaultSecretCreate) -> VaultSecretView:
        return await active_ops_mesh_service.create_vault_secret(payload)

    @fastapi_app.delete("/api/vault-secrets/{secret_id}")
    async def delete_vault_secret(secret_id: int) -> dict[str, bool]:
        try:
            await active_ops_mesh_service.delete_vault_secret(secret_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True}

    @fastapi_app.post("/api/notification-routes")
    async def create_notification_route(payload: NotificationRouteCreate) -> NotificationRouteView:
        try:
            return await active_ops_mesh_service.create_notification_route(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.delete("/api/notification-routes/{route_id}")
    async def delete_notification_route(route_id: int) -> dict[str, bool]:
        await active_ops_mesh_service.delete_notification_route(route_id)
        return {"ok": True}

    @fastapi_app.post("/api/notification-routes/{route_id}/test")
    async def test_notification_route(route_id: int) -> NotificationRouteTestResultView:
        try:
            return await active_ops_mesh_service.test_notification_route(route_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @fastapi_app.post("/api/integrations")
    async def create_integration(payload: IntegrationCreate) -> IntegrationView:
        try:
            return await active_ops_mesh_service.create_integration(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @fastapi_app.delete("/api/integrations/{integration_id}")
    async def delete_integration(integration_id: int) -> dict[str, bool]:
        await active_ops_mesh_service.delete_integration(integration_id)
        return {"ok": True}

    @fastapi_app.post("/api/skill-pins")
    async def create_skill_pin(payload: SkillPinCreate) -> SkillPinView:
        return await active_ops_mesh_service.create_skill_pin(payload)

    @fastapi_app.delete("/api/skill-pins/{skill_pin_id}")
    async def delete_skill_pin(skill_pin_id: int) -> dict[str, bool]:
        await active_ops_mesh_service.delete_skill_pin(skill_pin_id)
        return {"ok": True}

    @fastapi_app.post("/api/instances/{instance_id}/snapshots")
    async def capture_lane_snapshot(instance_id: int) -> LaneSnapshotView:
        try:
            return await active_ops_mesh_service.capture_lane_snapshot(instance_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

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
            cadence_minutes=payload.cadence_minutes,
            enabled=payload.enabled,
            payload=payload.model_dump(
                exclude={
                    "name",
                    "description",
                    "kind",
                    "instance_id",
                    "cadence_minutes",
                    "enabled",
                }
            ),
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
            result = await active_playbook_service.execute(playbook, payload, active_manager)
            await active_database.update_playbook(
                playbook_id,
                last_run_at=datetime.now(UTC).isoformat(),
                last_status="completed",
                last_result_summary=summarize_playbook_result(playbook, result)[:240],
            )
            return result
        except ValueError as exc:
            await active_database.update_playbook(
                playbook_id,
                last_run_at=datetime.now(UTC).isoformat(),
                last_status="failed",
                last_result_summary=str(exc)[:240],
            )
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
