from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from openzues.schemas import (
    ContinuityState,
    DashboardContinuityPacketView,
    DashboardContinuityView,
    DashboardDoctrineView,
    InstanceView,
    MissionCheckpointView,
    MissionView,
    ProjectView,
)
from openzues.services.cortex import doctrine_index

MissionRecord = MissionView | Mapping[str, Any]
CheckpointRecord = MissionCheckpointView | Mapping[str, Any]


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


def _mission_value(mission: MissionRecord, key: str, default: Any = None) -> Any:
    if isinstance(mission, Mapping):
        return mission.get(key, default)
    return getattr(mission, key, default)


def _checkpoint_value(checkpoint: CheckpointRecord, key: str, default: Any = None) -> Any:
    if isinstance(checkpoint, Mapping):
        return checkpoint.get(key, default)
    return getattr(checkpoint, key, default)


def _truncate(value: str | None, limit: int) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _is_orbiting(mission: MissionRecord) -> bool:
    turns_completed = int(_mission_value(mission, "turns_completed", 0) or 0)
    command_count = int(_mission_value(mission, "command_count", 0) or 0)
    last_checkpoint = str(_mission_value(mission, "last_checkpoint", "") or "")
    orbit_threshold = max(6, turns_completed * 4 + 4)
    return command_count >= orbit_threshold and not last_checkpoint


def _doctrine_hint(doctrine: DashboardDoctrineView | None) -> str | None:
    if doctrine is None:
        return None
    parts: list[str] = [
        f"Project doctrine currently prefers {doctrine.recommended_model}",
    ]
    if doctrine.recommended_max_turns is not None:
        parts.append(f"{doctrine.recommended_max_turns}-turn windows")
    parts.append("verification on" if doctrine.run_verification else "lighter loops")
    if doctrine.use_builtin_agents:
        parts.append("delegation when ownership is clear")
    return " ".join(parts) + "."


def _checkpoint_summaries(
    checkpoints: Sequence[CheckpointRecord] | None,
    *,
    fallback: str | None = None,
) -> list[str]:
    summaries = [
        _truncate(_checkpoint_value(checkpoint, "summary"), 320)
        for checkpoint in checkpoints or []
        if str(_checkpoint_value(checkpoint, "summary") or "").strip()
    ]
    if not summaries and fallback:
        summaries.append(_truncate(fallback, 320))
    return summaries


def _build_drift_signatures(
    mission: MissionRecord,
    *,
    instance_connected: bool,
    freshness_minutes: int | None,
    has_checkpoint: bool,
) -> list[str]:
    status = str(_mission_value(mission, "status", "") or "")
    phase = str(_mission_value(mission, "phase", "") or "")
    total_tokens = int(_mission_value(mission, "total_tokens", 0) or 0)
    failure_count = int(_mission_value(mission, "failure_count", 0) or 0)
    in_progress = bool(_mission_value(mission, "in_progress", False))
    signatures: list[str] = []

    if not instance_connected or phase == "offline":
        signatures.append("offline lane")
    if status == "failed":
        signatures.append("failure residue")
    if status == "blocked" and phase == "approval":
        signatures.append("approval gate")
    if status == "blocked" and phase == "queued":
        signatures.append("queue drag")
    if _is_orbiting(mission):
        signatures.append("orbiting scope")
    if total_tokens >= 40000 and not has_checkpoint:
        signatures.append("token heat")
    if (
        freshness_minutes is not None
        and freshness_minutes >= 8
        and status == "active"
        and not in_progress
    ):
        signatures.append("quiet lane")
    if not has_checkpoint:
        signatures.append("thin checkpoint memory")
    if not _mission_value(mission, "thread_id"):
        signatures.append("no thread anchor")
    if failure_count >= 2:
        signatures.append("repeat failures")
    return signatures


def _build_anchor(mission: MissionRecord, checkpoint_summaries: Sequence[str]) -> str:
    if checkpoint_summaries:
        return checkpoint_summaries[0]
    last_commentary = str(_mission_value(mission, "last_commentary", "") or "").strip()
    if last_commentary:
        return f"Latest commentary: {_truncate(last_commentary, 260)}"
    if _mission_value(mission, "thread_id"):
        return "A live thread exists, but no durable checkpoint has landed yet."
    return "No durable mission memory has been established yet."


def _build_drift(
    mission: MissionRecord,
    *,
    instance_connected: bool,
    freshness_minutes: int | None,
    has_checkpoint: bool,
    drift_signatures: Sequence[str],
) -> str:
    status = str(_mission_value(mission, "status", "") or "")
    phase = str(_mission_value(mission, "phase", "") or "")
    last_error = str(_mission_value(mission, "last_error", "") or "").strip()

    if not instance_connected or phase == "offline":
        return (
            "The attached Codex lane is offline, so live context will keep cooling "
            "until a failover or reconnect happens."
        )
    if status == "failed":
        if last_error:
            return f"The most recent turn failed with: {_truncate(last_error, 220)}"
        return (
            "The mission failed its last cycle and needs a careful re-entry "
            "instead of blind repetition."
        )
    if status == "blocked" and phase == "approval":
        return (
            "A human approval is gating the next move, so context can drift if "
            "the resume step is not tightly framed."
        )
    if _is_orbiting(mission):
        return (
            "Command volume is outrunning checkpoint quality, so the mission risks "
            "losing its clearest thread of truth."
        )
    if (
        freshness_minutes is not None
        and freshness_minutes >= 8
        and status == "active"
        and not bool(_mission_value(mission, "in_progress", False))
    ):
        return (
            "The lane has gone quiet long enough that the next turn should begin "
            "with re-orientation and a compact relay packet."
        )
    if not has_checkpoint:
        return (
            "Thread memory exists, but it has not yet been compressed into a "
            "durable checkpoint that another lane can trust."
        )
    if drift_signatures:
        return f"Minor drift signatures remain: {', '.join(drift_signatures[:3])}."
    return (
        "Context currently looks stable; the main risk is letting the next turn "
        "broaden the scope without refreshing the handoff."
    )


def _build_next_handoff(
    mission: MissionRecord,
    *,
    instance_connected: bool,
    freshness_minutes: int | None,
    has_checkpoint: bool,
) -> str:
    status = str(_mission_value(mission, "status", "") or "")
    phase = str(_mission_value(mission, "phase", "") or "")

    if not instance_connected or phase == "offline":
        return (
            "Reconnect or fail over first, then ask Codex to restate what is "
            "already true before making any new edits."
        )
    if status == "failed" and has_checkpoint:
        return (
            "Resume from the latest checkpoint, verify the failed edge first, "
            "and repair only the smallest root cause."
        )
    if status == "failed":
        return (
            "Recover context before coding: inspect the failure, rebuild a "
            "trustworthy anchor, then take one tiny repair step."
        )
    if status == "blocked" and phase == "approval":
        return (
            "Resolve the approval and use the next turn to emit a fresh relay "
            "packet before broader work resumes."
        )
    if status == "paused" and has_checkpoint:
        return (
            "Resume from the handoff and take the next smallest verified slice "
            "instead of remapping the whole project."
        )
    if status == "completed" and has_checkpoint:
        return (
            "Treat the current checkpoint as a clean baton-pass and branch only "
            "into the next visible milestone."
        )
    if _is_orbiting(mission):
        return (
            "Force a landing turn that verifies one concrete claim and ends with "
            "a tight checkpoint packet."
        )
    if (
        freshness_minutes is not None
        and freshness_minutes >= 8
        and status == "active"
        and not bool(_mission_value(mission, "in_progress", False))
    ):
        return (
            "Wake the mission with a heartbeat turn and ask for a compact "
            "truths-drift-next-step relay."
        )
    if not has_checkpoint:
        return (
            "Spend the next turn producing a durable checkpoint before the "
            "mission fans out any further."
        )
    return (
        "Continue from the current anchor, verify one concrete claim, and "
        "refresh the relay packet at turn end."
    )


def _build_summary(state: str, mission: MissionRecord) -> str:
    status = str(_mission_value(mission, "status", "") or "")
    if state == "anchored":
        if status in {"paused", "completed"}:
            return (
                "This mission is packed cleanly enough for a low-friction "
                "handoff or later resume."
            )
        return (
            "This mission retains a strong working memory and can survive "
            "another long cycle without much context loss."
        )
    if state == "warming":
        return (
            "This mission is still legible, but another tighter checkpoint "
            "would make recovery and relay much safer."
        )
    return (
        "This mission is losing coherence and should emit a relay packet "
        "before autonomy stretches any further."
    )


def _build_relay_prompt(
    mission: MissionRecord,
    *,
    state: str,
    score: int,
    anchor: str,
    drift: str,
    next_handoff: str,
    checkpoint_summaries: Sequence[str],
    doctrine: DashboardDoctrineView | None,
) -> str:
    mission_name = str(_mission_value(mission, "name", "Unnamed mission") or "Unnamed mission")
    objective = str(_mission_value(mission, "objective", "") or "").strip()
    instructions = [
        "You are resuming or taking over an OpenZues mission.",
        f"Mission: {mission_name}",
        "",
        "Objective:",
        objective,
        "",
        f"Continuity state: {state} ({score}/100)",
        "Current anchor:",
        f"- {anchor}",
        "Current drift to inspect first:",
        f"- {drift}",
        "Safest next handoff:",
        f"- {next_handoff}",
    ]
    doctrine_hint = _doctrine_hint(doctrine)
    if doctrine_hint:
        instructions.extend(["", doctrine_hint])
    if checkpoint_summaries:
        instructions.extend(["", "Recent relay trail:"])
        for summary in checkpoint_summaries[:3]:
            instructions.append(f"- {summary}")
    instructions.extend(
        [
            "",
            "Relay doctrine:",
            (
                "- Do not restart or remap the whole project unless verification "
                "proves the context is wrong."
            ),
            "- Preserve already-landed work and choose the smallest verified next step.",
            "- End this turn with a relay packet: truths, drift, next step, blockers.",
        ]
    )
    return "\n".join(instructions)


def build_continuity_packet(
    mission: MissionRecord,
    *,
    instance_connected: bool,
    checkpoints: Sequence[CheckpointRecord] | None = None,
    project_label: str | None = None,
    doctrine: DashboardDoctrineView | None = None,
) -> DashboardContinuityPacketView:
    mission_id = int(_mission_value(mission, "id", 0) or 0)
    mission_name = str(_mission_value(mission, "name", "Unnamed mission") or "Unnamed mission")
    freshness_minutes = _minutes_since(_mission_value(mission, "last_activity_at"))
    checkpoint_summaries = _checkpoint_summaries(
        checkpoints,
        fallback=str(_mission_value(mission, "last_checkpoint", "") or "") or None,
    )
    has_checkpoint = bool(checkpoint_summaries)
    status = str(_mission_value(mission, "status", "") or "")
    phase = str(_mission_value(mission, "phase", "") or "")
    thread_id = str(_mission_value(mission, "thread_id", "") or "")
    in_progress = bool(_mission_value(mission, "in_progress", False))
    failure_count = int(_mission_value(mission, "failure_count", 0) or 0)
    total_tokens = int(_mission_value(mission, "total_tokens", 0) or 0)

    score = 38
    if thread_id:
        score += 12
    if has_checkpoint:
        score += 18
    if len(checkpoint_summaries) >= 2:
        score += 5
    if instance_connected:
        score += 8
    if status in {"paused", "completed"} and has_checkpoint:
        score += 9
    if in_progress:
        score += 4
    elif freshness_minutes is not None and freshness_minutes <= 10:
        score += 3

    if not instance_connected or phase == "offline":
        score -= 22
    if status == "failed":
        score -= 18
    if status == "blocked" and phase == "approval":
        score -= 12
    if status == "blocked" and phase == "queued":
        score -= 9
    if _is_orbiting(mission):
        score -= 14
    if total_tokens >= 40000 and not has_checkpoint:
        score -= 10
    if (
        freshness_minutes is not None
        and freshness_minutes >= 8
        and status == "active"
        and not in_progress
    ):
        score -= 10
    score -= min(18, failure_count * 6)
    score = max(0, min(100, score))

    state: ContinuityState
    if (status == "failed" and not has_checkpoint) or (not thread_id and not has_checkpoint):
        state = "fragile"
    elif score >= 72:
        state = "anchored"
    elif score >= 48:
        state = "warming"
    else:
        state = "fragile"

    drift_signatures = _build_drift_signatures(
        mission,
        instance_connected=instance_connected,
        freshness_minutes=freshness_minutes,
        has_checkpoint=has_checkpoint,
    )
    anchor = _build_anchor(mission, checkpoint_summaries)
    drift = _build_drift(
        mission,
        instance_connected=instance_connected,
        freshness_minutes=freshness_minutes,
        has_checkpoint=has_checkpoint,
        drift_signatures=drift_signatures,
    )
    next_handoff = _build_next_handoff(
        mission,
        instance_connected=instance_connected,
        freshness_minutes=freshness_minutes,
        has_checkpoint=has_checkpoint,
    )

    return DashboardContinuityPacketView(
        id=f"mission:{mission_id}",
        mission_id=mission_id,
        mission_name=mission_name,
        project_label=project_label or _mission_value(mission, "project_label"),
        state=state,
        score=score,
        freshness_minutes=freshness_minutes,
        drift_signatures=drift_signatures,
        summary=_build_summary(state, mission),
        anchor=anchor,
        drift=drift,
        next_handoff=next_handoff,
        relay_prompt=_build_relay_prompt(
            mission,
            state=state,
            score=score,
            anchor=anchor,
            drift=drift,
            next_handoff=next_handoff,
            checkpoint_summaries=checkpoint_summaries,
            doctrine=doctrine,
        ),
    )


def build_continuity(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    *,
    doctrines: list[DashboardDoctrineView] | None = None,
) -> DashboardContinuityView:
    del projects
    connected_by_instance = {instance.id: instance.connected for instance in instances}
    project_doctrine_index = doctrine_index(doctrines or [])
    packets = [
        build_continuity_packet(
            mission,
            instance_connected=connected_by_instance.get(mission.instance_id, False),
            checkpoints=mission.checkpoints,
            doctrine=project_doctrine_index.get(mission.project_id or -1),
        )
        for mission in missions
        if mission.thread_id
        or mission.last_checkpoint
        or mission.status in {"active", "blocked", "failed", "completed"}
    ]

    state_rank = {"fragile": 0, "warming": 1, "anchored": 2}
    packets = sorted(
        packets,
        key=lambda packet: (
            state_rank[packet.state],
            packet.score,
            packet.freshness_minutes if packet.freshness_minutes is not None else 99999,
            packet.mission_name.lower(),
        ),
    )[:5]

    fragile = sum(packet.state == "fragile" for packet in packets)
    warming = sum(packet.state == "warming" for packet in packets)
    anchored = sum(packet.state == "anchored" for packet in packets)

    if packets:
        headline = "Relay packets are ready"
        if fragile:
            summary = (
                f"{fragile} mission(s) have fragile continuity. Use the relay packets before "
                "long autonomy stretches or lane failovers."
            )
        elif warming:
            summary = (
                f"{warming} mission(s) are still warm but would benefit from another compact "
                "checkpoint before the next long run."
            )
        else:
            summary = (
                f"{anchored} mission(s) are well-packed for resume, relay, or failover with low "
                "context loss."
            )
    else:
        headline = "No relay packets yet"
        summary = (
            "Once missions start building thread memory and checkpoints, OpenZues will compress "
            "their current truth into continuity packets here."
        )

    return DashboardContinuityView(
        headline=headline,
        summary=summary,
        packets=packets,
    )
