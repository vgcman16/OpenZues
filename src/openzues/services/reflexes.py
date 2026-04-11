from __future__ import annotations

from datetime import UTC, datetime

from openzues.schemas import (
    DashboardDoctrineView,
    DashboardReflexDeckView,
    DashboardReflexView,
    InstanceView,
    MissionView,
    ProjectView,
    ReflexKind,
    SignalLevel,
)
from openzues.services.cortex import doctrine_index
from openzues.services.run_pressure import has_verification_spike_pressure
from openzues.services.scope_enforcer import build_scope_assessment


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


def _is_orbiting(mission: MissionView) -> bool:
    orbit_threshold = max(6, mission.turns_completed * 4 + 4)
    return mission.command_count >= orbit_threshold and not mission.last_checkpoint


def _doctrine_hint(doctrine: DashboardDoctrineView | None) -> str:
    if doctrine is None:
        return ""
    parts: list[str] = [
        f"Project doctrine currently prefers {doctrine.recommended_model}",
    ]
    if doctrine.recommended_max_turns is not None:
        parts.append(f"{doctrine.recommended_max_turns}-turn windows")
    parts.append("verification on" if doctrine.run_verification else "lighter loops")
    if doctrine.use_builtin_agents:
        parts.append("delegation when ownership is clear")
    return " ".join(parts) + "."


def build_reflex_deck(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    *,
    doctrines: list[DashboardDoctrineView] | None = None,
) -> DashboardReflexDeckView:
    del projects
    project_doctrine_index = doctrine_index(doctrines or [])
    connected_by_instance = {instance.id: instance.connected for instance in instances}
    reflexes: list[DashboardReflexView] = []
    seen_ids: set[str] = set()

    def add_reflex(
        mission: MissionView,
        *,
        reflex_id: str,
        kind: ReflexKind,
        level: SignalLevel,
        title: str,
        summary: str,
        prompt: str,
        action_label: str,
    ) -> None:
        if reflex_id in seen_ids:
            return
        seen_ids.add(reflex_id)
        reflexes.append(
            DashboardReflexView(
                id=reflex_id,
                kind=kind,
                level=level,
                mission_id=mission.id,
                mission_name=mission.name,
                project_label=mission.project_label,
                title=title,
                summary=summary,
                prompt=prompt,
                action_label=action_label,
            )
        )

    for mission in missions:
        if not mission.thread_id:
            continue
        if not connected_by_instance.get(mission.instance_id):
            continue
        doctrine = project_doctrine_index.get(mission.project_id or -1)
        doctrine_hint = _doctrine_hint(doctrine)
        scope = build_scope_assessment(mission, checkpoints=mission.checkpoints)

        if mission.status == "active" and scope.drift_level in {"drifting", "critical"}:
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:scope-realign",
                kind="scope_realign",
                level="critical" if scope.drift_level == "critical" else "warn",
                title=f"Realign {mission.name} to its charter",
                summary=scope.drift_summary,
                prompt=scope.reflex_prompt,
                action_label="Realign scope",
            )
            continue

        if mission.status == "active" and _is_orbiting(mission):
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:checkpoint-now",
                kind="checkpoint_now",
                level="critical",
                title=f"Force a landing for {mission.name}",
                summary=(
                    "This mission is expanding faster than it is checkpointing. Inject a landing "
                    "signal so the next turn compresses the work into one verified handoff."
                ),
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission.name}'.",
                        doctrine_hint,
                        "Stop expanding scope.",
                        "Use this turn to land the work:",
                        "1. Summarize what is already true right now.",
                        "2. Verify the most important claim with a concrete check.",
                        (
                            "3. If one small missing piece blocks the checkpoint, "
                            "finish only that piece."
                        ),
                        (
                            "4. End with a checkpoint: completed, verified, next smallest "
                            "step, blockers."
                        ),
                        "Do not branch into a new broad implementation path in this turn.",
                    ]
                ).strip(),
                action_label="Force landing",
            )

        if mission.status == "active" and has_verification_spike_pressure(
            total_tokens=mission.total_tokens,
            model=mission.model,
            has_checkpoint=bool(mission.last_checkpoint),
        ):
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:verification-spike",
                kind="verification_spike",
                level="warn",
                title=f"Trigger a verification spike for {mission.name}",
                summary=(
                    "Long-run continuity risk is climbing without a durable handoff. This reflex "
                    "redirects the next turn toward proof instead of further sprawl."
                ),
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission.name}'.",
                        doctrine_hint,
                        "Pause new feature expansion for this turn.",
                        "Audit the current state, run the highest-value verification available, "
                        "and report exactly what is confirmed, what is still uncertain, and what "
                        "the smallest safe next move should be.",
                        "End with a concise checkpoint packet.",
                    ]
                ).strip(),
                action_label="Run verify spike",
            )

        quiet_minutes = _minutes_since(mission.last_activity_at)
        if (
            mission.status == "active"
            and not mission.in_progress
            and quiet_minutes is not None
            and quiet_minutes >= 8
        ):
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:heartbeat",
                kind="heartbeat_nudge",
                level="warn",
                title=f"Wake {mission.name} with a heartbeat nudge",
                summary=(
                    "The mission has gone quiet. This reflex asks Codex to re-orient, choose the "
                    "smallest high-leverage next step, and keep momentum moving."
                ),
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission.name}'.",
                        doctrine_hint,
                        "Re-orient from the current thread state without repeating old work.",
                        "Pick the smallest high-leverage step that moves the objective forward, "
                        "complete it if feasible, and leave a concise checkpoint with verified "
                        "facts and the next move.",
                    ]
                ).strip(),
                action_label="Wake mission",
            )

        if mission.status == "failed" and mission.last_checkpoint:
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:recovery-triangle",
                kind="recovery_triangle",
                level="critical",
                title=f"Plan a recovery triangle for {mission.name}",
                summary=(
                    "This mission already has enough memory to recover intelligently. The reflex "
                    "asks for a tight recovery plan instead of a blind retry."
                ),
                prompt="\n".join(
                    [
                        f"You are resuming the OpenZues mission '{mission.name}'.",
                        doctrine_hint,
                        "Read the most recent checkpoint and the latest failure context first.",
                        "Produce three recovery paths ranked by safety and speed, choose the best "
                        "one, execute it if it is low-risk, and verify the path forward before you "
                        "finish the turn.",
                        "End with a recovery checkpoint.",
                    ]
                ).strip(),
                action_label="Plan recovery",
            )

        if mission.status == "paused" and mission.last_checkpoint:
            add_reflex(
                mission,
                reflex_id=f"{mission.id}:resume-handoff",
                kind="resume_handoff",
                level="ready",
                title=f"Resume {mission.name} from its handoff",
                summary=(
                    "This paused mission already has a checkpoint. The reflex nudges it to pick up "
                    "from the handoff with the smallest verified next slice."
                ),
                prompt="\n".join(
                    [
                        f"You are resuming the OpenZues mission '{mission.name}'.",
                        doctrine_hint,
                        "Start from the latest checkpoint in the thread.",
                        "Do not re-map the whole project.",
                        "Take the smallest verified next slice, complete it if feasible, and leave "
                        "an updated checkpoint that clearly states what changed and what remains.",
                    ]
                ).strip(),
                action_label="Resume from handoff",
            )

    level_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    reflexes = sorted(
        reflexes,
        key=lambda reflex: (level_rank[reflex.level], reflex.mission_name.lower(), reflex.title),
    )[:5]

    if reflexes:
        headline = "Autonomic reflexes are armed"
        summary = (
            "These are tiny corrective prompts synthesized from live mission telemetry. Fire one "
            "straight into a thread when a run needs steering without launching a whole new "
            "mission."
        )
    else:
        headline = "No reflexes armed yet"
        summary = (
            "Once a connected mission starts drifting, pausing, failing, or over-expanding, "
            "OpenZues will synthesize intervention prompts here."
        )

    return DashboardReflexDeckView(
        headline=headline,
        summary=summary,
        reflexes=reflexes,
    )
