from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    AttentionQueueActionStatus,
    AttentionQueueActionView,
    ControlChatActionKind,
    ControlChatMessageView,
    ControlChatResponse,
    DashboardAttentionQueueView,
    DashboardControlChatView,
    DashboardOpportunityView,
    DashboardSignalView,
    DashboardView,
    MissionCreate,
    MissionView,
)
from openzues.services.followups import (
    mission_followup_kind,
    mission_matches_payload,
    operator_blocked_missions,
    operator_ready_handoff_missions,
)
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.run_pressure import has_checkpoint_pressure
from openzues.services.skillbook import resolve_skill_profile

logger = logging.getLogger(__name__)

CONTINUE_PHRASES = (
    "continue",
    "keep going",
    "keep building",
    "keep cooking",
    "cook",
    "resume",
    "do the next thing",
    "do the next step",
    "keep pushing",
    "finish it",
    "push it forward",
    "ship the next thing",
    "keep working",
)
STATUS_PHRASES = (
    "status",
    "what is running",
    "what's running",
    "what is going on",
    "what's going on",
    "how is it doing",
    "how's it doing",
    "what are you doing",
    "what is zues doing",
)
HARDEN_PHRASES = ("harden", "harder", "checkpoint", "tighten", "verify it")
RECOVERY_PHRASES = ("recover", "recovery", "fix the failed", "retry the failed", "rescue")

IMPACT_RANK = {"high": 0, "medium": 1, "low": 2}
SAFE_APPROVAL_COMMAND_PATTERNS = (
    "rg ",
    "rg.exe",
    "get-content ",
    "select-string ",
    "get-childitem",
    "git status",
    "git diff",
    "git show",
    "git log",
    "pwd",
    "get-location",
    "pytest",
    "ruff check",
    "mypy ",
    "python -m pytest",
    "python -m ruff",
    "python -m mypy",
    "uv run pytest",
    "uv run ruff",
    "uv run mypy",
)
UNSAFE_APPROVAL_COMMAND_PATTERNS = (
    "remove-item",
    "rm ",
    "del ",
    "erase ",
    "move-item",
    "rename-item",
    "copy-item",
    "new-item",
    "set-content",
    "add-content",
    "out-file",
    "mkdir ",
    " md ",
    "git checkout",
    "git reset",
    "git clean",
    "git commit",
    "git push",
    "git merge",
    "git rebase",
    "git apply",
    "npm install",
    "pnpm install",
    "yarn install",
    "pip install",
    "uv add",
    "cargo add",
    "invoke-webrequest",
    "curl ",
    "wget ",
    "winget ",
    "choco ",
    "start-process",
    "stop-process",
    "shutdown",
    "restart-computer",
    "format-",
    "diskpart",
    "reg add",
    "set-itemproperty",
    " >",
    " >>",
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


def _sort_missions(missions: list[MissionView]) -> list[MissionView]:
    return sorted(
        missions,
        key=lambda mission: (
            _parse_timestamp(mission.last_activity_at) or datetime.min.replace(tzinfo=UTC),
            mission.updated_at,
        ),
        reverse=True,
    )


def _normalize_prompt(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _looks_like_status_request(text: str) -> bool:
    return _contains_any(text, STATUS_PHRASES)


def _looks_like_continue_request(text: str) -> bool:
    return _contains_any(text, CONTINUE_PHRASES)


def _looks_like_harden_request(text: str) -> bool:
    return _contains_any(text, HARDEN_PHRASES)


def _looks_like_recovery_request(text: str) -> bool:
    return _contains_any(text, RECOVERY_PHRASES)


def _gateway_needs_repair(dashboard: DashboardView) -> bool:
    gateway = dashboard.gateway_capability
    launch_route = gateway.launch_policy.launch_route
    return (
        gateway.level == "critical"
        or gateway.inventory.tracked_gap_count > 0
        or gateway.approval_posture.approval_count > 0
        or (launch_route is not None and launch_route.status == "repair")
        or (
            gateway.connected_lane_health.total_count > 0
            and gateway.connected_lane_health.ready_count == 0
        )
    )


def _gateway_repair_reason(dashboard: DashboardView) -> str:
    gateway = dashboard.gateway_capability
    if gateway.warnings:
        return gateway.warnings[0]
    return gateway.summary


def _mission_phase_label(mission: MissionView) -> str:
    if mission.phase == "executing":
        return "executing"
    if mission.phase == "reasoning":
        return "reasoning"
    if mission.phase == "approval":
        return "waiting on approval"
    return "running"


def _pick_launch_instance_id(dashboard: DashboardView) -> int | None:
    live_instance_ids = {
        mission.instance_id
        for mission in dashboard.missions
        if mission.status in {"active", "blocked"}
    }
    for instance in dashboard.instances:
        if instance.connected and instance.id not in live_instance_ids:
            return instance.id
    for instance in dashboard.instances:
        if instance.connected:
            return instance.id
    return dashboard.instances[0].id if dashboard.instances else None


def _pick_project_id(dashboard: DashboardView) -> int | None:
    if len(dashboard.projects) == 1:
        return dashboard.projects[0].id
    focus_mission_id = dashboard.brief.focus_mission_id
    if focus_mission_id is not None:
        focus = next(
            (mission for mission in dashboard.missions if mission.id == focus_mission_id),
            None,
        )
        if focus is not None and focus.project_id is not None:
            return focus.project_id
    for mission in _sort_missions(dashboard.missions):
        if mission.project_id is not None:
            return mission.project_id
    return None


def _derive_mission_name(prompt: str) -> str:
    words = [segment for segment in prompt.replace("\n", " ").split(" ") if segment]
    if not words:
        return "Chat Directed Mission"
    clipped = words[:6]
    title = " ".join(clipped).strip(" .,:;!-")
    return title.title() or "Chat Directed Mission"


def _create_prompt_mission(prompt: str, dashboard: DashboardView) -> MissionCreate | None:
    instance_id = _pick_launch_instance_id(dashboard)
    if instance_id is None:
        return None
    project_id = _pick_project_id(dashboard)
    project = next((item for item in dashboard.projects if item.id == project_id), None)
    instance = next((item for item in dashboard.instances if item.id == instance_id), None)
    objective = prompt.strip()
    if objective and objective[-1] not in ".!?":
        objective = f"{objective}."
    ops_mesh = getattr(dashboard, "ops_mesh", None)
    skillbooks = getattr(ops_mesh, "skillbooks", []) if ops_mesh is not None else []
    skillbook = next(
        (
            item
            for item in skillbooks
            if project_id is not None and item.project_id == project_id
        ),
        None,
    )
    skill_profile = resolve_skill_profile(
        objective,
        explicit_pins=skillbook.skills if skillbook is not None else [],
        project_label=project.label if project is not None else None,
        project_path=project.path if project is not None else None,
    )
    return MissionCreate(
        name=_derive_mission_name(prompt),
        objective=objective,
        instance_id=instance_id,
        project_id=project_id,
        cwd=(
            project.path
            if project is not None
            else (instance.cwd if instance is not None else None)
        ),
        model="gpt-5.4",
        reasoning_effort=skill_profile.reasoning_effort,
        collaboration_mode=None,
        max_turns=max(5, skill_profile.max_turns_floor or 0),
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
        start_immediately=True,
    )


def _sorted_opportunities(dashboard: DashboardView) -> list[DashboardOpportunityView]:
    return sorted(
        dashboard.launchpad.opportunities,
        key=lambda opportunity: (
            IMPACT_RANK.get(opportunity.impact, 99),
            opportunity.title.lower(),
        ),
    )


def _find_opportunity(
    dashboard: DashboardView,
    *,
    preferred_kinds: tuple[str, ...] = (),
) -> DashboardOpportunityView | None:
    opportunities = _sorted_opportunities(dashboard)
    for kind in preferred_kinds:
        match = next((item for item in opportunities if item.kind == kind), None)
        if match is not None:
            return match
    return opportunities[0] if opportunities else None


def _find_gateway_repair_opportunity(dashboard: DashboardView) -> DashboardOpportunityView | None:
    return _find_opportunity(dashboard, preferred_kinds=("gateway_repair",))


def _find_draft_instance(
    dashboard: DashboardView,
    opportunity: DashboardOpportunityView,
) -> Any | None:
    instance_id = opportunity.mission_draft.instance_id
    return next((instance for instance in dashboard.instances if instance.id == instance_id), None)


def _opportunity_can_autolaunch(
    dashboard: DashboardView,
    opportunity: DashboardOpportunityView,
) -> bool:
    instance = _find_draft_instance(dashboard, opportunity)
    return (
        opportunity.mission_draft.start_immediately
        and instance is not None
        and bool(instance.connected)
    )


def _opportunity_hold_reason(
    dashboard: DashboardView,
    opportunity: DashboardOpportunityView,
) -> str:
    instance = _find_draft_instance(dashboard, opportunity)
    if instance is None:
        return "its target lane is not registered in the control plane right now"
    if not opportunity.mission_draft.start_immediately:
        if instance.connected:
            return f"`{instance.name}` is available, but this draft is staged for a manual start"
        return f"`{instance.name}` is offline, so this draft is staged until that lane reconnects"
    if not instance.connected:
        return f"`{instance.name}` is offline right now"
    return "its target lane is not ready yet"


def _find_mission(dashboard: DashboardView, mission_id: int | None) -> MissionView | None:
    if mission_id is None:
        return None
    return next((mission for mission in dashboard.missions if mission.id == mission_id), None)


def _has_active_mission_for_target_label(
    dashboard: DashboardView,
    target_label: str | None,
) -> bool:
    normalized_label = str(target_label or "").strip().lower()
    if not normalized_label:
        return False
    return any(
        mission.status == "active" and mission.name.strip().lower() == normalized_label
        for mission in dashboard.missions
    )


def _latest_mission_for_target_label(
    dashboard: DashboardView,
    target_label: str | None,
) -> MissionView | None:
    normalized_label = str(target_label or "").strip().lower()
    if not normalized_label:
        return None
    matches = [
        mission
        for mission in dashboard.missions
        if mission.name.strip().lower() == normalized_label
    ]
    if not matches:
        return None
    return max(matches, key=lambda mission: mission.updated_at)


def _latest_target_supersedes_stale_failure_or_quiet(
    dashboard: DashboardView,
    target_label: str | None,
) -> bool:
    mission = _latest_mission_for_target_label(dashboard, target_label)
    if mission is None:
        return False
    if mission.status in {"active", "blocked"}:
        return True
    return mission.status in {"completed", "paused"} and bool(mission.last_checkpoint)


def _is_stale_failure_or_quiet_summary(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    return (
        "failed, but there is no safe recovery draft yet" in normalized
        or "went quiet without closing the loop" in normalized
    )


def _find_queued_followers(dashboard: DashboardView, mission: MissionView) -> list[MissionView]:
    return sorted(
        [
            candidate
            for candidate in dashboard.missions
            if candidate.instance_id == mission.instance_id
            and candidate.id != mission.id
            and candidate.status == "blocked"
            and candidate.phase == "queued"
        ],
        key=lambda candidate: candidate.id,
    )


def _should_pause_long_run_mission_for_queue(mission: MissionView) -> bool:
    if mission.status != "active" or mission.last_checkpoint:
        return False
    quiet_minutes = _minutes_since(mission.last_activity_at)
    if quiet_minutes is None or quiet_minutes < 8:
        return False
    orbit_threshold = max(6, mission.turns_completed * 4 + 4)
    return (
        has_checkpoint_pressure(
            total_tokens=mission.total_tokens,
            model=mission.model,
            has_checkpoint=bool(mission.last_checkpoint),
        )
        or mission.command_count >= orbit_threshold
    )


def _find_signal_mission_fingerprint(
    signal: DashboardSignalView,
    dashboard: DashboardView,
) -> str:
    mission = _find_mission(dashboard, signal.mission_id)
    if mission is not None:
        if signal.id.endswith("-failed"):
            return "|".join(
                [
                    signal.id,
                    mission.status,
                    str(mission.phase or ""),
                    str(mission.last_turn_id or ""),
                    str(mission.failure_count),
                    str(mission.last_error or ""),
                    str(mission.last_checkpoint or ""),
                ]
            )
        if signal.id.endswith("-queued"):
            return "|".join(
                [
                    signal.id,
                    mission.status,
                    str(mission.phase or ""),
                    str(mission.last_error or ""),
                ]
            )
        if signal.id.endswith("-handoff"):
            return "|".join(
                [
                    signal.id,
                    mission.status,
                    str(mission.phase or ""),
                    str(mission.last_turn_id or ""),
                    str(mission.last_checkpoint or ""),
                ]
            )
        return "|".join(
            [
                signal.id,
                mission.status,
                str(mission.phase or ""),
                str(mission.last_error or ""),
                str(mission.last_checkpoint or ""),
                mission.updated_at.isoformat(),
            ]
        )
    return "|".join(
        [
            signal.id,
            signal.level,
            str(signal.detail or ""),
            str(signal.action or ""),
        ]
    )


def _find_signal_opportunity(
    dashboard: DashboardView,
    signal: DashboardSignalView,
    *,
    kind: str,
) -> DashboardOpportunityView | None:
    if signal.mission_id is not None:
        exact_id = (
            f"recover-{signal.mission_id}"
            if kind == "recovery_run"
            else f"harden-{signal.mission_id}"
        )
        direct = next(
            (
                opportunity
                for opportunity in dashboard.launchpad.opportunities
                if opportunity.kind == kind and opportunity.id == exact_id
            ),
            None,
        )
        if direct is not None:
            return direct
    return next(
        (
            opportunity
            for opportunity in dashboard.launchpad.opportunities
            if opportunity.kind == kind
        ),
        None,
    )


def _find_gateway_signal(dashboard: DashboardView) -> DashboardSignalView | None:
    return next(
        (signal for signal in dashboard.radar.signals if signal.id == "gateway/capability"),
        None,
    )


def _available_attention_queue_signal_ids(dashboard: DashboardView) -> list[str]:
    return [signal.id for signal in dashboard.radar.signals if signal.id]


def _resolve_attention_queue_signal(
    dashboard: DashboardView,
    target_signal_id: str | None,
) -> DashboardSignalView | None:
    wanted = str(target_signal_id or "").strip()
    if not wanted:
        return None
    signal = next((item for item in dashboard.radar.signals if item.id == wanted), None)
    if signal is not None:
        return signal
    available_ids = _available_attention_queue_signal_ids(dashboard)
    available_note = (
        f" Available ids: {', '.join(available_ids)}."
        if available_ids
        else " The radar is clear right now."
    )
    raise ValueError(
        f"Attention-queue signal '{wanted}' is not available right now."
        f"{available_note} Run `openzues status --json` to inspect the current radar."
    )


def _matches_mission_payload(mission: MissionView, payload: MissionCreate) -> bool:
    return mission.status in {"active", "blocked", "paused"} and mission_matches_payload(
        mission,
        payload,
    )


def _find_existing_followup_mission(
    dashboard: DashboardView,
    payload: MissionCreate,
) -> MissionView | None:
    candidates = [
        mission for mission in dashboard.missions if _matches_mission_payload(mission, payload)
    ]
    if not candidates:
        return None
    status_rank = {"active": 0, "blocked": 1, "paused": 2}
    return sorted(
        candidates,
        key=lambda mission: (
            status_rank.get(mission.status, 99),
            mission.updated_at,
        ),
        reverse=False,
    )[0]


def _build_recovery_payload(mission: MissionView) -> MissionCreate:
    return MissionCreate(
        name=f"Recover {mission.name}",
        objective=(
            f"Continue the mission '{mission.name}' from its existing thread. Start by "
            "reading the last checkpoint and failure context, fix the blocker, verify the "
            "path forward, and leave a cleaner checkpoint when done."
        ),
        instance_id=mission.instance_id,
        project_id=mission.project_id,
        task_blueprint_id=None,
        cwd=mission.cwd,
        thread_id=mission.thread_id,
        session_key=mission.session_key,
        model=mission.model,
        reasoning_effort=mission.reasoning_effort,
        collaboration_mode=mission.collaboration_mode,
        max_turns=3,
        use_builtin_agents=mission.use_builtin_agents,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=mission.pause_on_approval,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=mission.toolsets,
        start_immediately=True,
    )


def _build_hardener_payload(mission: MissionView) -> MissionCreate:
    return MissionCreate(
        name=f"Harden {mission.project_label or mission.name}",
        objective=(
            f"Continue from the latest checkpoint in the mission '{mission.name}'. "
            "First read the existing handoff in the thread, verify what is already true, "
            "close the biggest gaps, and leave a stronger checkpoint with validation."
        ),
        instance_id=mission.instance_id,
        project_id=mission.project_id,
        task_blueprint_id=None,
        cwd=mission.cwd,
        thread_id=mission.thread_id,
        session_key=mission.session_key,
        model=mission.model,
        reasoning_effort=mission.reasoning_effort,
        collaboration_mode=mission.collaboration_mode,
        max_turns=3,
        use_builtin_agents=mission.use_builtin_agents,
        run_verification=True,
        auto_commit=True,
        pause_on_approval=mission.pause_on_approval,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=mission.toolsets,
        start_immediately=True,
    )


@dataclass(slots=True)
class AttentionQueuePlan:
    signal_id: str
    signal_fingerprint: str
    signal_level: str
    action_kind: ControlChatActionKind
    status: AttentionQueueActionStatus
    reply: str
    mission_id: int | None = None
    opportunity_id: str | None = None
    target_label: str | None = None
    mission_payload: MissionCreate | None = None


@dataclass(slots=True)
class ControlChatPlan:
    action_kind: ControlChatActionKind
    reply: str
    mission_id: int | None = None
    opportunity_id: str | None = None
    target_label: str | None = None
    mission_payload: MissionCreate | None = None


@dataclass(slots=True)
class ApprovalAutopilotDecision:
    instance_id: int
    request_id: str
    signal_id: str
    signal_fingerprint: str
    signal_level: str
    result: Any
    reply: str
    mission_id: int | None = None
    target_label: str | None = None


def plan_control_chat(prompt: str, dashboard: DashboardView) -> ControlChatPlan:
    normalized = _normalize_prompt(prompt)
    gateway_needs_repair = _gateway_needs_repair(dashboard)
    gateway_repair = _find_gateway_repair_opportunity(dashboard)
    gateway_reason = _gateway_repair_reason(dashboard)
    active_in_progress = [
        mission
        for mission in _sort_missions(dashboard.missions)
        if mission.status == "active" and mission.in_progress
    ]
    blocked = _sort_missions(operator_blocked_missions(dashboard.missions))
    paused = [
        mission for mission in _sort_missions(dashboard.missions) if mission.status == "paused"
    ]
    active_ready = [
        mission
        for mission in _sort_missions(dashboard.missions)
        if mission.status == "active" and not mission.in_progress
    ]

    if _looks_like_status_request(normalized):
        ready_handoffs = sum(
            1
            for mission in operator_ready_handoff_missions(dashboard.missions)
        )
        connected_lanes = sum(1 for instance in dashboard.instances if instance.connected)
        gateway_note = ""
        if gateway_needs_repair:
            gateway_note = f" Gateway Doctor says: {dashboard.gateway_capability.summary}"
            if gateway_repair is not None:
                gateway_note += f" `{gateway_repair.title}` is the bounded repair move."
        return ControlChatPlan(
            action_kind="observe",
            reply=(
                f"{len(active_in_progress)} mission(s) are actively running, "
                f"{len(blocked)} are blocked, {ready_handoffs} have checkpoint handoffs ready, "
                f"and {connected_lanes} Codex lane(s) are connected.{gateway_note}"
            ),
        )

    if _looks_like_continue_request(normalized):
        if active_in_progress:
            live = active_in_progress[0]
            next_hardener = _find_opportunity(dashboard, preferred_kinds=("checkpoint_hardener",))
            note = ""
            if next_hardener is not None:
                note = (
                    f" `{next_hardener.title}` is already staged as the next hardening move once "
                    "the "
                    "live lane settles."
                )
            return ControlChatPlan(
                action_kind="wait",
                mission_id=live.id,
                target_label=live.name,
                reply=(
                    f"I left `{live.name}` alone because it is already "
                    f"{_mission_phase_label(live)} on "
                    f"lane {live.instance_id}. I did not launch a duplicate loop.{note}"
                ),
            )

        approval_block = next(
            (
                mission
                for mission in blocked
                if str(mission.last_error or "").startswith("Waiting for approval:")
            ),
            None,
        )
        if approval_block is not None:
            return ControlChatPlan(
                action_kind="blocked",
                mission_id=approval_block.id,
                target_label=approval_block.name,
                reply=(
                    f"`{approval_block.name}` is blocked on an approval gate, so I did not force "
                    "it "
                    "forward. Resolve the approval and then tell me to continue again."
                ),
            )

        if gateway_needs_repair:
            if gateway_repair is not None:
                if not _opportunity_can_autolaunch(dashboard, gateway_repair):
                    hold_reason = _opportunity_hold_reason(dashboard, gateway_repair)
                    return ControlChatPlan(
                        action_kind="observe",
                        opportunity_id=gateway_repair.id,
                        target_label=gateway_repair.title,
                        reply=(
                            f"I staged `{gateway_repair.title}` because Gateway Doctor says "
                            f"{gateway_reason.rstrip('.')} but I held the launch because "
                            f"{hold_reason}. Reconnect the lane and then run the staged repair."
                        ),
                    )
                return ControlChatPlan(
                    action_kind="launch_opportunity",
                    opportunity_id=gateway_repair.id,
                    target_label=gateway_repair.title,
                    mission_payload=MissionCreate.model_validate(
                        gateway_repair.mission_draft.model_dump()
                    ),
                    reply=(
                        f"I launched `{gateway_repair.title}` because Gateway Doctor says "
                        f"{gateway_reason.rstrip('.')} and that needs repair before another "
                        "recovery, hardening pass, or fresh launch."
                    ),
                )
            return ControlChatPlan(
                action_kind="observe",
                reply=(
                    f"I held the next launch because Gateway Doctor says "
                    f"{gateway_reason.rstrip('.')}. Repair the gateway posture before asking "
                    "me to continue again."
                ),
            )

        if _looks_like_recovery_request(normalized):
            recovery = _find_opportunity(dashboard, preferred_kinds=("recovery_run",))
            if recovery is not None:
                return ControlChatPlan(
                    action_kind="launch_opportunity",
                    opportunity_id=recovery.id,
                    target_label=recovery.title,
                    mission_payload=MissionCreate.model_validate(
                        recovery.mission_draft.model_dump()
                    ),
                    reply=(
                        f"I launched `{recovery.title}` because the strongest next move is a "
                        "recovery "
                        "loop, not a blind retry."
                    ),
                )

        if _looks_like_harden_request(normalized):
            hardener = _find_opportunity(dashboard, preferred_kinds=("checkpoint_hardener",))
            if hardener is not None:
                return ControlChatPlan(
                    action_kind="launch_opportunity",
                    opportunity_id=hardener.id,
                    target_label=hardener.title,
                    mission_payload=MissionCreate.model_validate(
                        hardener.mission_draft.model_dump()
                    ),
                    reply=(
                        f"I launched `{hardener.title}` because a verified hardening pass is the "
                        "shortest path to durable progress from the finished checkpoint."
                    ),
                )

        recovery = _find_opportunity(dashboard, preferred_kinds=("recovery_run",))
        if recovery is not None:
            return ControlChatPlan(
                action_kind="launch_opportunity",
                opportunity_id=recovery.id,
                target_label=recovery.title,
                mission_payload=MissionCreate.model_validate(recovery.mission_draft.model_dump()),
                reply=(
                    f"I launched `{recovery.title}` because the failed checkpoint already gives us "
                    "a better continuation path than restarting from scratch."
                ),
            )

        hardener = _find_opportunity(dashboard, preferred_kinds=("checkpoint_hardener",))
        if hardener is not None:
            return ControlChatPlan(
                action_kind="launch_opportunity",
                opportunity_id=hardener.id,
                target_label=hardener.title,
                mission_payload=MissionCreate.model_validate(hardener.mission_draft.model_dump()),
                reply=(
                    f"I launched `{hardener.title}` because the finished run already produced a "
                    "checkpoint and that is the highest-leverage follow-through."
                ),
            )

        if paused:
            mission = paused[0]
            return ControlChatPlan(
                action_kind="resume_mission",
                mission_id=mission.id,
                target_label=mission.name,
                reply=(
                    f"I resumed `{mission.name}` because it already has context and was paused, "
                    "not complete."
                ),
            )

        if active_ready:
            mission = active_ready[0]
            return ControlChatPlan(
                action_kind="run_mission",
                mission_id=mission.id,
                target_label=mission.name,
                reply=(
                    f"I kicked `{mission.name}` into another autonomous cycle because it was idle "
                    "and ready to continue on its existing thread."
                ),
            )

        next_opportunity = _find_opportunity(dashboard)
        if next_opportunity is not None:
            if not _opportunity_can_autolaunch(dashboard, next_opportunity):
                hold_reason = _opportunity_hold_reason(dashboard, next_opportunity)
                return ControlChatPlan(
                    action_kind="observe",
                    opportunity_id=next_opportunity.id,
                    target_label=next_opportunity.title,
                    reply=(
                        f"I staged `{next_opportunity.title}` but I held the launch because "
                        f"{hold_reason}. Reconnect the lane or start the draft manually when "
                        "you are ready."
                    ),
                )
            return ControlChatPlan(
                action_kind="launch_opportunity",
                opportunity_id=next_opportunity.id,
                target_label=next_opportunity.title,
                mission_payload=MissionCreate.model_validate(
                    next_opportunity.mission_draft.model_dump()
                ),
                reply=(
                    f"I launched `{next_opportunity.title}` because it is the strongest ready move "
                    "available right now."
                ),
            )

        if not dashboard.instances:
            return ControlChatPlan(
                action_kind="unavailable",
                reply="I need a connected Codex lane before I can continue work from chat.",
            )

        return ControlChatPlan(
            action_kind="observe",
            reply=(
                "Nothing was queued because there is no stronger follow-through candidate right "
                "now. "
                "Give me a new objective and I will start a fresh mission."
            ),
        )

    mission_payload = _create_prompt_mission(prompt, dashboard)
    if mission_payload is None:
        return ControlChatPlan(
            action_kind="unavailable",
            reply="I do not have a Codex lane to launch that on yet. Connect a lane first.",
        )
    project_note = ""
    if mission_payload.project_id is not None:
        project = next(
            (item for item in dashboard.projects if item.id == mission_payload.project_id),
            None,
        )
        if project is not None:
            project_note = f" targeting `{project.label}`"
    return ControlChatPlan(
        action_kind="create_mission",
        target_label=mission_payload.name,
        mission_payload=mission_payload,
        reply=(
            f"I launched `{mission_payload.name}` from your chat request on lane "
            f"{mission_payload.instance_id}{project_note}."
        ),
    )


def plan_attention_queue(
    dashboard: DashboardView,
    *,
    target_signal_id: str | None = None,
) -> AttentionQueuePlan | None:
    gateway_needs_repair = _gateway_needs_repair(dashboard)
    active_in_progress = any(
        mission.status == "active" and mission.in_progress for mission in dashboard.missions
    )
    selected_signal = _resolve_attention_queue_signal(dashboard, target_signal_id)
    actionable_signals = [selected_signal] if selected_signal is not None else list(
        dashboard.radar.signals
    )

    approval_signal = next(
        (
            signal
            for signal in actionable_signals
            if signal.mission_id is not None and signal.id.endswith("-approval")
        ),
        None,
    )
    if approval_signal is not None:
        mission = _find_mission(dashboard, approval_signal.mission_id)
        target_label = mission.name if mission is not None else approval_signal.title
        return AttentionQueuePlan(
            signal_id=approval_signal.id,
            signal_fingerprint=_find_signal_mission_fingerprint(approval_signal, dashboard),
            signal_level=approval_signal.level,
            action_kind="blocked",
            status="escalated",
            mission_id=approval_signal.mission_id,
            target_label=target_label,
            reply=(
                f"I left `{target_label}` paused because it is waiting on an approval gate. "
                "The autonomous queue will not guess its way through irreversible actions."
            ),
        )

    orphan_approval_signal = next(
        (signal for signal in actionable_signals if signal.id.endswith("orphan-approval")),
        None,
    )
    if orphan_approval_signal is not None:
        return AttentionQueuePlan(
            signal_id=orphan_approval_signal.id,
            signal_fingerprint=_find_signal_mission_fingerprint(orphan_approval_signal, dashboard),
            signal_level=orphan_approval_signal.level,
            action_kind="observe",
            status="escalated",
            mission_id=orphan_approval_signal.mission_id,
            target_label=orphan_approval_signal.title,
            reply=(
                "I found an approval request outside the tracked mission set, so I surfaced it "
                "instead of auto-approving or inventing a thread attachment."
            ),
        )

    for signal in actionable_signals:
        if signal.mission_id is None or not signal.id.endswith(("-burn", "-orbit")):
            continue
        mission = _find_mission(dashboard, signal.mission_id)
        if mission is None or not _should_pause_long_run_mission_for_queue(mission):
            continue
        queued_followers = _find_queued_followers(dashboard, mission)
        if not queued_followers:
            continue
        next_target = queued_followers[0]
        return AttentionQueuePlan(
            signal_id=signal.id,
            signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
            signal_level=signal.level,
            action_kind="pause_mission",
            status="executed",
            mission_id=mission.id,
            target_label=mission.name,
            reply=(
                f"I cooled `{mission.name}` into a paused relay because it was blocking "
                f"`{next_target.name}` after a long run without a durable checkpoint. The lane is "
                "free for the next queued mission to advance automatically."
            ),
        )

    if active_in_progress:
        return None

    gateway_signal = _find_gateway_signal(dashboard)
    if selected_signal is not None and (
        gateway_signal is None or gateway_signal.id != selected_signal.id
    ):
        gateway_signal = None
    if gateway_needs_repair and gateway_signal is not None:
        gateway_repair = _find_gateway_repair_opportunity(dashboard)
        if gateway_repair is not None:
            if not _opportunity_can_autolaunch(dashboard, gateway_repair):
                hold_reason = _opportunity_hold_reason(dashboard, gateway_repair)
                return AttentionQueuePlan(
                    signal_id=gateway_signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(gateway_signal, dashboard),
                    signal_level=gateway_signal.level,
                    action_kind="observe",
                    status="escalated",
                    opportunity_id=gateway_repair.id,
                    target_label=gateway_repair.title,
                    reply=(
                        f"I staged `{gateway_repair.title}` from the attention queue because "
                        f"Gateway Doctor says {_gateway_repair_reason(dashboard).rstrip('.')} "
                        f"but I held the launch because {hold_reason}. Reconnect the lane and "
                        "then run the staged repair."
                    ),
                )
            return AttentionQueuePlan(
                signal_id=gateway_signal.id,
                signal_fingerprint=_find_signal_mission_fingerprint(gateway_signal, dashboard),
                signal_level=gateway_signal.level,
                action_kind="launch_opportunity",
                status="executed",
                opportunity_id=gateway_repair.id,
                target_label=gateway_repair.title,
                mission_payload=MissionCreate.model_validate(
                    gateway_repair.mission_draft.model_dump()
                ),
                reply=(
                    f"I launched `{gateway_repair.title}` from the attention queue because "
                    f"Gateway Doctor says {_gateway_repair_reason(dashboard).rstrip('.')} and "
                    "the queue should repair the gateway posture before auto-launching more "
                    "follow-through work."
                ),
            )
        return AttentionQueuePlan(
            signal_id=gateway_signal.id,
            signal_fingerprint=_find_signal_mission_fingerprint(gateway_signal, dashboard),
            signal_level=gateway_signal.level,
            action_kind="observe",
            status="escalated",
            target_label=gateway_signal.title,
            reply=(
                f"I held the attention queue because Gateway Doctor says "
                f"{_gateway_repair_reason(dashboard).rstrip('.')}. There is no bounded gateway "
                "repair draft attached yet."
            ),
        )

    for signal in actionable_signals:
        if signal.mission_id is not None and signal.id.endswith("-failed"):
            recovery = _find_signal_opportunity(dashboard, signal, kind="recovery_run")
            mission = _find_mission(dashboard, signal.mission_id)
            target_label = (
                recovery.title
                if recovery is not None
                else (mission.name if mission is not None else signal.title)
            )
            recovery_payload = (
                MissionCreate.model_validate(recovery.mission_draft.model_dump())
                if recovery is not None
                else (_build_recovery_payload(mission) if mission is not None else None)
            )
            existing_followup = (
                _find_existing_followup_mission(dashboard, recovery_payload)
                if recovery_payload is not None
                else None
            )
            if existing_followup is not None:
                if existing_followup.status == "active":
                    return AttentionQueuePlan(
                        signal_id=signal.id,
                        signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                        signal_level=signal.level,
                        action_kind="observe",
                        status="observed",
                        mission_id=existing_followup.id,
                        target_label=existing_followup.name,
                        reply=(
                            f"`{existing_followup.name}` is already in flight, so I did not "
                            "spawn another recovery loop for the same checkpoint."
                        ),
                    )
                return AttentionQueuePlan(
                    signal_id=signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                    signal_level=signal.level,
                    action_kind="run_mission",
                    status="executed",
                    mission_id=existing_followup.id,
                    target_label=existing_followup.name,
                    reply=(
                        f"I reused the existing recovery mission `{existing_followup.name}` "
                        "instead of launching a duplicate loop for the same failure."
                    ),
                )
            if recovery is not None:
                return AttentionQueuePlan(
                    signal_id=signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                    signal_level=signal.level,
                    action_kind="launch_opportunity",
                    status="executed",
                    mission_id=signal.mission_id,
                    opportunity_id=recovery.id,
                    target_label=target_label,
                    mission_payload=MissionCreate.model_validate(
                        recovery.mission_draft.model_dump()
                    ),
                    reply=(
                        f"I launched `{target_label}` from the attention queue because the failed "
                        "cycle already has enough context for a tighter recovery pass."
                    ),
                )
            return AttentionQueuePlan(
                signal_id=signal.id,
                signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                signal_level=signal.level,
                action_kind="observe",
                status="escalated",
                mission_id=signal.mission_id,
                target_label=target_label,
                reply=(
                    f"`{target_label}` failed, but there is no safe recovery draft yet. I held "
                    "the queue instead of retrying blindly."
                ),
            )

        if signal.mission_id is not None and signal.id.endswith("-handoff"):
            mission = _find_mission(dashboard, signal.mission_id)
            if mission is not None and mission_followup_kind(mission) is not None:
                return AttentionQueuePlan(
                    signal_id=signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                    signal_level=signal.level,
                    action_kind="observe",
                    status="observed",
                    mission_id=mission.id,
                    target_label=mission.name,
                    reply=(
                        f"`{mission.name}` already is a follow-up mission, so I held the queue "
                        "instead of hardening a hardener again."
                    ),
                )
            hardener = _find_signal_opportunity(dashboard, signal, kind="checkpoint_hardener")
            target_label = (
                hardener.title
                if hardener is not None
                else (mission.name if mission is not None else signal.title)
            )
            hardener_payload = (
                MissionCreate.model_validate(hardener.mission_draft.model_dump())
                if hardener is not None
                else (_build_hardener_payload(mission) if mission is not None else None)
            )
            existing_followup = (
                _find_existing_followup_mission(dashboard, hardener_payload)
                if hardener_payload is not None
                else None
            )
            if existing_followup is not None:
                if existing_followup.status == "active":
                    return AttentionQueuePlan(
                        signal_id=signal.id,
                        signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                        signal_level=signal.level,
                        action_kind="observe",
                        status="observed",
                        mission_id=existing_followup.id,
                        target_label=existing_followup.name,
                        reply=(
                            f"`{existing_followup.name}` is already hardening this checkpoint, "
                            "so I did not spawn another duplicate follow-up."
                        ),
                    )
                return AttentionQueuePlan(
                    signal_id=signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                    signal_level=signal.level,
                    action_kind="run_mission",
                    status="executed",
                    mission_id=existing_followup.id,
                    target_label=existing_followup.name,
                    reply=(
                        f"I reused the existing hardener `{existing_followup.name}` instead of "
                        "launching another follow-up for the same checkpoint."
                    ),
                )
            if hardener is not None:
                return AttentionQueuePlan(
                    signal_id=signal.id,
                    signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                    signal_level=signal.level,
                    action_kind="launch_opportunity",
                    status="executed",
                    mission_id=signal.mission_id,
                    opportunity_id=hardener.id,
                    target_label=target_label,
                    mission_payload=MissionCreate.model_validate(
                        hardener.mission_draft.model_dump()
                    ),
                    reply=(
                        f"I launched `{target_label}` from the attention queue so the finished "
                        "checkpoint gets hardened automatically instead of waiting for a manual "
                        "button click."
                    ),
                )
            return AttentionQueuePlan(
                signal_id=signal.id,
                signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                signal_level=signal.level,
                action_kind="observe",
                status="observed",
                mission_id=signal.mission_id,
                target_label=target_label,
                reply=(
                    f"`{target_label}` has a ready checkpoint, but there is no hardening draft "
                    "attached yet."
                ),
            )

        if signal.mission_id is not None and signal.id.endswith("-quiet"):
            mission = _find_mission(dashboard, signal.mission_id)
            target_label = mission.name if mission is not None else signal.title
            return AttentionQueuePlan(
                signal_id=signal.id,
                signal_fingerprint=_find_signal_mission_fingerprint(signal, dashboard),
                signal_level=signal.level,
                action_kind="run_mission",
                status="executed",
                mission_id=signal.mission_id,
                target_label=target_label,
                reply=(
                    f"I nudged `{target_label}` into another cycle because the lane went quiet "
                    "without closing the loop."
                ),
            )

    return None


def _collapse_repeated_control_chat_messages(
    messages: list[ControlChatMessageView],
) -> list[ControlChatMessageView]:
    collapsed: list[ControlChatMessageView] = []
    for message in messages:
        if collapsed and _same_control_chat_message(collapsed[-1], message):
            collapsed[-1] = message
            continue
        collapsed.append(message)
    return collapsed


def _same_control_chat_message(
    left: ControlChatMessageView,
    right: ControlChatMessageView,
) -> bool:
    return (
        left.role == right.role
        and left.action_kind == right.action_kind
        and left.mission_id == right.mission_id
        and left.opportunity_id == right.opportunity_id
        and left.target_label == right.target_label
        and left.content == right.content
    )


def _collapse_repeated_attention_queue_actions(
    actions: list[AttentionQueueActionView],
) -> list[AttentionQueueActionView]:
    collapsed: list[AttentionQueueActionView] = []
    for action in actions:
        if collapsed and _same_attention_queue_action(collapsed[-1], action):
            collapsed[-1] = action
            continue
        collapsed.append(action)
    return collapsed


def _same_attention_queue_action(
    left: AttentionQueueActionView,
    right: AttentionQueueActionView,
) -> bool:
    return (
        left.signal_id == right.signal_id
        and left.action_kind == right.action_kind
        and left.status == right.status
        and left.mission_id == right.mission_id
        and left.opportunity_id == right.opportunity_id
        and left.target_label == right.target_label
        and left.summary == right.summary
    )


class ControlChatService:
    def __init__(
        self,
        database: Database,
        missions: MissionService,
        manager: RuntimeManager,
        hub: BroadcastHub,
    ) -> None:
        self.database = database
        self.missions = missions
        self.manager = manager
        self.hub = hub
        self._attention_task: asyncio.Task[None] | None = None
        self._attention_stop_event = asyncio.Event()

    async def start_attention_queue(
        self,
        dashboard_loader: Callable[[], Awaitable[DashboardView]],
        *,
        enabled: bool = True,
        poll_interval_seconds: float = 30.0,
    ) -> None:
        if not enabled or self._attention_task is not None:
            return
        self._attention_stop_event.clear()
        self._attention_task = asyncio.create_task(
            self._attention_queue_loop(
                dashboard_loader,
                poll_interval_seconds=poll_interval_seconds,
            ),
            name="openzues-attention-queue",
        )

    async def close_attention_queue(self) -> None:
        self._attention_stop_event.set()
        if self._attention_task is not None:
            self._attention_task.cancel()
            try:
                await self._attention_task
            except asyncio.CancelledError:
                pass
            self._attention_task = None

    async def build_view(
        self,
        dashboard: DashboardView,
        *,
        limit: int = 18,
    ) -> DashboardControlChatView:
        messages = [
            ControlChatMessageView.model_validate(row)
            for row in await self.database.list_control_chat_messages(limit=limit)
        ]
        messages = [
            message
            for message in messages
            if not (
                _latest_target_supersedes_stale_failure_or_quiet(
                    dashboard,
                    message.target_label,
                )
                and message.action_kind in {"observe", "run_mission"}
                and _is_stale_failure_or_quiet_summary(message.content)
            )
        ]
        messages = _collapse_repeated_control_chat_messages(messages)
        attention_queue = getattr(dashboard, "attention_queue", None)
        gateway_needs_repair = _gateway_needs_repair(dashboard)
        active_running = sum(
            1
            for mission in dashboard.missions
            if mission.status == "active" and mission.in_progress
        )
        ready_moves = len(dashboard.launchpad.opportunities)
        if active_running:
            headline = "Chat can steer the live build without duplicate launches"
            summary = (
                "Type the outcome you want and Zues will wait, nudge, recover, or harden based on "
                "the current mission state."
            )
            if gateway_needs_repair:
                summary = (
                    f"{summary} Gateway Doctor still warns: {dashboard.gateway_capability.summary}"
                )
            placeholder = (
                "Try: keep going, status, recover the failed run, or harden the finished one"
            )
        elif gateway_needs_repair:
            headline = "Chat is steering from Gateway Doctor"
            summary = (
                f"{dashboard.gateway_capability.summary} Chat will prefer the bounded gateway "
                "repair move before broader launches."
            )
            placeholder = "Try: continue, status, or repair the gateway posture"
        elif attention_queue is not None and attention_queue.enabled:
            headline = "Chat steers while the attention queue keeps momentum alive"
            summary = (
                "Zues can auto-recover failed runs, harden finished checkpoints, and escalate "
                "risky approval gates while safe inspection requests auto-resolve in the "
                "background."
            )
            placeholder = (
                "Try: continue building, status, recover the failed run, or give me a new goal"
            )
        elif ready_moves:
            headline = "Describe the next outcome and Zues will pick the move"
            summary = (
                "Launchpad logic is now reachable through chat, so you do not need to manually "
                "load "
                "drafts just to keep momentum up."
            )
            placeholder = (
                "Try: continue building, harden the last checkpoint, or describe a new goal"
            )
        else:
            headline = "Tell Zues what to do next"
            summary = (
                "You can describe a fresh build objective here, and OpenZues will choose the lane, "
                "project, and continuation path automatically."
            )
            placeholder = "Describe the next thing you want built, fixed, or verified"
        return DashboardControlChatView(
            headline=headline,
            summary=summary,
            input_placeholder=placeholder,
            messages=messages,
        )

    async def build_attention_queue_view(
        self,
        dashboard: DashboardView,
        *,
        enabled: bool,
        limit: int = 8,
    ) -> DashboardAttentionQueueView:
        actions = [
            AttentionQueueActionView.model_validate(row)
            for row in await self.database.list_attention_queue_actions(limit=limit)
        ]
        actions = [
            action
            for action in actions
            if not (
                _latest_target_supersedes_stale_failure_or_quiet(
                    dashboard,
                    action.target_label,
                )
                and (
                    action.signal_id.endswith("-failed")
                    or action.signal_id.endswith("-quiet")
                    or _is_stale_failure_or_quiet_summary(action.summary)
                )
            )
        ]
        actions = _collapse_repeated_attention_queue_actions(actions)
        gateway_needs_repair = _gateway_needs_repair(dashboard)
        critical = sum(signal.level == "critical" for signal in dashboard.radar.signals)
        if not enabled:
            headline = "Attention queue is manual"
            summary = "Autonomous follow-through is disabled, so Zues will only suggest actions."
        elif gateway_needs_repair:
            headline = "Attention queue is holding for gateway repair"
            summary = (
                f"{dashboard.gateway_capability.summary} The queue will prefer the bounded "
                "gateway repair move before auto-launching more recoveries or hardeners."
            )
        elif critical:
            headline = "Attention queue is autonomous"
            summary = (
                f"Zues is actively auto-routing recoveries, hardening passes, and safe approval "
                f"responses while leaving {critical} critical human-risk signal"
                f"{'s' if critical != 1 else ''} explicit."
            )
        elif actions:
            headline = "Attention queue is keeping momentum"
            summary = (
                "Recent recoveries, hardeners, queue nudges, and approval autopilot decisions are "
                "being logged directly into the transcript."
            )
        else:
            headline = "Attention queue is standing by"
            summary = (
                "Recoveries and checkpoint hardeners will auto-launch from the transcript when the "
                "lane is safe to continue."
            )
        return DashboardAttentionQueueView(
            enabled=enabled,
            headline=headline,
            summary=summary,
            actions=actions,
        )

    async def submit(self, prompt: str, dashboard: DashboardView) -> ControlChatResponse:
        text = prompt.strip()
        if not text:
            raise ValueError("Enter a message before sending it to Zues.")

        user_message = await self._append_message(role="user", content=text)
        plan = plan_control_chat(text, dashboard)
        executed = False
        mission_id = plan.mission_id
        target_label = plan.target_label

        if plan.action_kind == "resume_mission" and plan.mission_id is not None:
            mission = await self.missions.resume(plan.mission_id)
            executed = True
            mission_id = mission.id
            target_label = mission.name
        elif plan.action_kind == "run_mission" and plan.mission_id is not None:
            mission = await self.missions.run_now(plan.mission_id)
            executed = True
            mission_id = mission.id
            target_label = mission.name
        elif (
            plan.action_kind in {"launch_opportunity", "create_mission"}
            and plan.mission_payload is not None
        ):
            mission = await self.missions.create(plan.mission_payload)
            executed = True
            mission_id = mission.id
            target_label = mission.name

        assistant_message = await self._append_message(
            role="assistant",
            content=plan.reply,
            action_kind=plan.action_kind,
            mission_id=mission_id,
            opportunity_id=plan.opportunity_id,
            target_label=target_label,
        )
        await self.hub.publish(
            {
                "type": "control-chat/replied",
                "createdAt": utcnow(),
                "actionKind": plan.action_kind,
                "missionId": mission_id,
                "targetLabel": target_label,
            }
        )
        return ControlChatResponse(
            user=user_message,
            assistant=assistant_message,
            action_kind=plan.action_kind,
            executed=executed,
        )

    async def handle_server_request(self, instance_id: int, request: dict[str, Any]) -> None:
        payload = self._normalize_request_payload(request)
        decision = await self._build_approval_autopilot_decision(instance_id, payload)
        if decision is None:
            return
        await self._execute_approval_autopilot(decision)

    async def tick_attention_queue(
        self,
        dashboard: DashboardView,
        *,
        target_signal_id: str | None = None,
    ) -> bool:
        if target_signal_id is None and await self._sweep_safe_approvals(dashboard):
            return True

        plan = plan_attention_queue(dashboard, target_signal_id=target_signal_id)
        if plan is None:
            return False

        latest = await self.database.get_latest_attention_queue_action(plan.signal_fingerprint)
        if latest is not None:
            return False

        executed = False
        mission_id = plan.mission_id
        target_label = plan.target_label

        if plan.action_kind == "run_mission" and plan.mission_id is not None:
            mission = await self.missions.run_now(plan.mission_id)
            executed = True
            mission_id = mission.id
            target_label = mission.name
        elif plan.action_kind == "pause_mission" and plan.mission_id is not None:
            mission = await self.missions.yield_for_queue(plan.mission_id)
            executed = True
            mission_id = mission.id
            target_label = mission.name
        elif plan.action_kind == "launch_opportunity" and plan.mission_payload is not None:
            mission = await self.missions.create(plan.mission_payload)
            executed = True
            mission_id = mission.id
            target_label = mission.name

        assistant_message = await self._append_message(
            role="assistant",
            content=plan.reply,
            action_kind=plan.action_kind,
            mission_id=mission_id,
            opportunity_id=plan.opportunity_id,
            target_label=target_label,
        )
        await self.database.append_attention_queue_action(
            signal_id=plan.signal_id,
            signal_fingerprint=plan.signal_fingerprint,
            signal_level=plan.signal_level,
            mission_id=plan.mission_id,
            opportunity_id=plan.opportunity_id,
            target_label=target_label,
            action_kind=plan.action_kind,
            status=plan.status,
            summary=assistant_message.content,
        )
        await self.hub.publish(
            {
                "type": "attention-queue/acted",
                "createdAt": utcnow(),
                "signalId": plan.signal_id,
                "actionKind": plan.action_kind,
                "status": plan.status,
                "missionId": mission_id,
                "executed": executed,
                "targetLabel": target_label,
            }
        )
        return True

    async def _sweep_safe_approvals(self, dashboard: DashboardView) -> bool:
        for instance in dashboard.instances:
            for request in instance.unresolved_requests:
                payload = self._normalize_request_payload(request)
                decision = await self._build_approval_autopilot_decision(instance.id, payload)
                if decision is None:
                    continue
                await self._execute_approval_autopilot(decision)
                return True
        return False

    def _normalize_request_payload(self, request: dict[str, Any]) -> dict[str, Any]:
        return {
            "request_id": self._request_id(request),
            "thread_id": self._request_thread_id(request),
            "method": self._request_method(request),
            "payload": self._request_payload(request),
        }

    def _request_id(self, request: dict[str, Any]) -> str | None:
        value = request.get("request_id")
        if isinstance(value, str):
            return value
        value = request.get("requestId")
        return value if isinstance(value, str) else None

    def _request_thread_id(self, request: dict[str, Any]) -> str | None:
        value = request.get("thread_id")
        if isinstance(value, str):
            return value
        value = request.get("threadId")
        return value if isinstance(value, str) else None

    def _request_method(self, request: dict[str, Any]) -> str | None:
        value = request.get("method")
        return value if isinstance(value, str) else None

    def _request_payload(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = request.get("payload")
        if isinstance(payload, dict):
            return payload
        params = request.get("params")
        return params if isinstance(params, dict) else {}

    async def _build_approval_autopilot_decision(
        self,
        instance_id: int,
        request: dict[str, Any],
    ) -> ApprovalAutopilotDecision | None:
        request_id = request.get("request_id")
        method = request.get("method")
        if not isinstance(request_id, str) or not isinstance(method, str):
            return None

        payload = request.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        result = self._pick_safe_approval_result(method, payload)
        if result is None:
            return None

        signal_fingerprint = self._approval_fingerprint(instance_id, request)
        latest = await self.database.get_latest_attention_queue_action(signal_fingerprint)
        if latest is not None:
            return None

        thread_id = request.get("thread_id")
        thread_id = thread_id if isinstance(thread_id, str) else None
        mission = (
            await self.database.get_mission_by_thread(instance_id, thread_id)
            if thread_id is not None
            else None
        )
        command = self._approval_command_preview(payload)
        target_label = (
            str(mission["name"])
            if mission is not None
            else f"Instance {instance_id} request {request_id}"
        )
        if mission is not None:
            reply = (
                f"I auto-approved a safe request for `{target_label}` because it was a low-risk "
                f"inspection or verification command: `{command}`."
            )
            signal_id = f"mission-{int(mission['id'])}-approval"
            mission_id = int(mission["id"])
        else:
            reply = (
                f"I auto-approved an unassigned safe request on lane {instance_id} because it was "
                f"only a low-risk inspection or verification command: `{command}`."
            )
            signal_id = f"instance-{instance_id}-orphan-approval"
            mission_id = None
        return ApprovalAutopilotDecision(
            instance_id=instance_id,
            request_id=request_id,
            signal_id=signal_id,
            signal_fingerprint=signal_fingerprint,
            signal_level="warn",
            result=result,
            reply=reply,
            mission_id=mission_id,
            target_label=target_label,
        )

    def _approval_fingerprint(self, instance_id: int, request: dict[str, Any]) -> str:
        payload = request.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        return "|".join(
            [
                str(instance_id),
                str(request.get("request_id") or ""),
                str(request.get("method") or ""),
                str(request.get("thread_id") or ""),
                self._approval_command_preview(payload),
            ]
        )

    def _approval_command_preview(self, payload: dict[str, Any]) -> str:
        commands = self._approval_command_texts(payload)
        preview = (
            commands[0] if commands else str(payload.get("reason") or payload.get("message") or "")
        )
        preview = " ".join(preview.split())
        return preview[:220] if preview else "approval request"

    def _approval_command_texts(self, payload: dict[str, Any]) -> list[str]:
        texts: list[str] = []
        command = payload.get("command")
        if isinstance(command, str) and command.strip():
            texts.append(command.strip())
        actions = payload.get("commandActions")
        if isinstance(actions, list):
            for action in actions:
                if not isinstance(action, dict):
                    continue
                action_command = action.get("command")
                if isinstance(action_command, str) and action_command.strip():
                    texts.append(action_command.strip())
        return texts

    def _pick_safe_approval_result(self, method: str, payload: dict[str, Any]) -> Any | None:
        if method not in {"item/commandExecution/requestApproval", "approval/request"}:
            return None

        commands = self._approval_command_texts(payload)
        if not commands:
            return None
        lowered = [text.lower() for text in commands]
        if any(pattern in text for text in lowered for pattern in UNSAFE_APPROVAL_COMMAND_PATTERNS):
            return None
        if not any(
            pattern in text for text in lowered for pattern in SAFE_APPROVAL_COMMAND_PATTERNS
        ):
            return None

        available = payload.get("availableDecisions")
        decisions = available if isinstance(available, list) else []
        if "accept" in decisions:
            return "accept"
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            amendment = decision.get("acceptWithExecpolicyAmendment")
            if isinstance(amendment, dict):
                return {"acceptWithExecpolicyAmendment": amendment}
        return None

    async def _execute_approval_autopilot(self, decision: ApprovalAutopilotDecision) -> None:
        await self.manager.resolve_request(
            decision.instance_id,
            decision.request_id,
            decision.result,
        )
        if decision.mission_id is not None:
            await self.database.update_mission(
                decision.mission_id,
                status="active",
                phase="thinking",
                in_progress=1,
                last_error=None,
                last_activity_at=utcnow(),
            )
        assistant_message = await self._append_message(
            role="assistant",
            content=decision.reply,
            action_kind="resolve_request",
            mission_id=decision.mission_id,
            target_label=decision.target_label,
        )
        await self.database.append_attention_queue_action(
            signal_id=decision.signal_id,
            signal_fingerprint=decision.signal_fingerprint,
            signal_level=decision.signal_level,
            mission_id=decision.mission_id,
            target_label=decision.target_label,
            action_kind="resolve_request",
            status="executed",
            summary=assistant_message.content,
        )
        await self.hub.publish(
            {
                "type": "attention-queue/acted",
                "createdAt": utcnow(),
                "signalId": decision.signal_id,
                "actionKind": "resolve_request",
                "status": "executed",
                "missionId": decision.mission_id,
                "executed": True,
                "targetLabel": decision.target_label,
            }
        )

    async def _attention_queue_loop(
        self,
        dashboard_loader: Callable[[], Awaitable[DashboardView]],
        *,
        poll_interval_seconds: float,
    ) -> None:
        while not self._attention_stop_event.is_set():
            try:
                dashboard = await dashboard_loader()
                await self.tick_attention_queue(dashboard)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Attention queue loop crashed")
            try:
                await asyncio.wait_for(
                    self._attention_stop_event.wait(),
                    timeout=poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _append_message(
        self,
        *,
        role: str,
        content: str,
        action_kind: str | None = None,
        mission_id: int | None = None,
        opportunity_id: str | None = None,
        target_label: str | None = None,
    ) -> ControlChatMessageView:
        message_id = await self.database.append_control_chat_message(
            role=role,
            content=content,
            action_kind=action_kind,
            mission_id=mission_id,
            opportunity_id=opportunity_id,
            target_label=target_label,
        )
        row = await self.database.get_control_chat_message(message_id)
        assert row is not None
        return ControlChatMessageView.model_validate(row)
