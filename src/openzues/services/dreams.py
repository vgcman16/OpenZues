from __future__ import annotations

import re
from datetime import UTC, datetime

from openzues.schemas import (
    DashboardDoctrineView,
    DashboardDreamDeckView,
    DashboardDreamView,
    DreamStatus,
    InstanceView,
    MissionDraftView,
    MissionView,
    ProjectView,
)
from openzues.services.hermes_runtime_profile import (
    DEFAULT_HERMES_EXECUTOR,
    DEFAULT_HERMES_MEMORY_PROVIDER,
    build_runtime_profile_fields,
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _hours_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(UTC) - parsed).total_seconds() // 3600))


def _is_project_dirty(project: ProjectView) -> bool:
    git_status = (project.git_status or "").strip()
    if not git_status:
        return False
    lowered = git_status.lower()
    return "working tree clean" not in lowered and "nothing to commit" not in lowered


def _is_orbiting(mission: MissionView) -> bool:
    orbit_threshold = max(6, mission.turns_completed * 4 + 4)
    return mission.command_count >= orbit_threshold and not mission.last_checkpoint


def _clean_text(value: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = cleaned.replace("#", " ")
    cleaned = cleaned.replace("*", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_sentences(value: str, *, limit: int = 3) -> list[str]:
    sentences: list[str] = []
    for raw_line in value.splitlines():
        line = _clean_text(raw_line)
        if len(line) < 24:
            continue
        lowered = line.lower()
        if lowered in {"completed", "verified", "next step", "blockers"}:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            sentence = _clean_text(part)
            if len(sentence) < 24:
                continue
            if sentence[-1] not in ".!?":
                sentence = f"{sentence}."
            sentences.append(sentence)
            if len(sentences) >= limit:
                return sentences
    return sentences


def _mission_anchor(mission: MissionView) -> str:
    source = mission.last_checkpoint or mission.last_commentary or mission.objective
    snippets = _extract_sentences(source, limit=1)
    if snippets:
        return f"{mission.name}: {snippets[0]}"
    return mission.name


def _pick_project_instance(
    instances: list[InstanceView],
    missions: list[MissionView],
    project_id: int,
) -> InstanceView | None:
    by_id = {instance.id: instance for instance in instances}
    ranked_missions = sorted(
        [mission for mission in missions if mission.project_id == project_id],
        key=lambda mission: mission.updated_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    for mission in ranked_missions:
        preferred = by_id.get(mission.instance_id)
        if preferred is not None and preferred.connected:
            return preferred
    for mission in ranked_missions:
        preferred = by_id.get(mission.instance_id)
        if preferred is not None:
            return preferred
    for instance in instances:
        if instance.connected:
            return instance
    return instances[0] if instances else None


def _dream_status(checkpoint_count: int, freshness_hours: int | None) -> DreamStatus:
    if checkpoint_count >= 3 and freshness_hours is not None and freshness_hours <= 24:
        return "fresh"
    if checkpoint_count >= 2:
        return "ready"
    return "forming"


def _build_prune_notes(project: ProjectView, missions: list[MissionView]) -> list[str]:
    notes: list[str] = []
    if _is_project_dirty(project):
        notes.append(
            "The worktree is carrying live drift. Prune stale assumptions before future "
            "missions treat the current branch as settled truth."
        )
    if any(mission.status == "failed" for mission in missions):
        notes.append(
            "Recent failed runs likely contain disproved paths. Remove those dead ends "
            "from any durable operator memory."
        )
    if any(_is_orbiting(mission) for mission in missions):
        notes.append(
            "Long exploratory loops need compression. Preserve only truths, drift "
            "signatures, and the next safe move."
        )
    if any(
        mission.status == "blocked" and mission.phase == "approval"
        for mission in missions
    ):
        notes.append(
            "Approval pauses are situational. Keep the decision and its consequence, "
            "but prune the temporary waiting state."
        )
    if not notes:
        notes.append(
            "No obvious stale memory signature is dominant yet. Focus on consolidating "
            "the strongest new truths into durable project guidance."
        )
    return notes[:3]


def _build_prompt(
    project: ProjectView,
    missions: list[MissionView],
    anchors: list[str],
    prune_notes: list[str],
    doctrine: DashboardDoctrineView | None,
) -> str:
    mission_names = [f"- {mission.name}" for mission in missions[:4]]
    doctrine_line = (
        f"Project doctrine currently prefers {doctrine.recommended_model}"
        f" with {doctrine.recommended_max_turns or 2}-turn verified loops."
        if doctrine is not None
        else "No strong doctrine is locked yet, so preserve reusable truths conservatively."
    )
    return "\n".join(
        [
            "# Dream: OpenZues Project Consolidation",
            "",
            f"Project: {project.label}",
            f"Workspace: {project.path}",
            "",
            "You are performing an OpenZues dream pass over recent autonomous mission history.",
            "Consolidate what is now true into durable project memory so later runs "
            "orient faster and repeat fewer mistakes.",
            "",
            doctrine_line,
            "",
            "## Phase 1 - Orient",
            "- Review the strongest recent checkpoints before touching any durable memory.",
            "- Distinguish stable truths from temporary execution noise.",
            "- Prefer improving an existing memory artifact over creating scattered duplicates.",
            "",
            "## Phase 2 - Gather recent signal",
            *(anchors or ["- No major checkpoint anchors yet."]),
            "",
            "Recent missions in scope:",
            *(mission_names or ["- No mission trail is available yet."]),
            "",
            "## Phase 3 - Consolidate",
            "- Update or create durable operator memory inside this workspace.",
            "- Convert relative timing into absolute dates when useful.",
            "- Merge repeated lessons into one crisp source of truth.",
            "- Preserve what future missions need: truths, winning patterns, drift "
            "signatures, and handoff rules.",
            "",
            "## Phase 4 - Prune",
            *[f"- {note}" for note in prune_notes],
            "",
            "Return a concise handoff with:",
            "- files changed",
            "- truths preserved",
            "- things pruned or corrected",
            "- next watchpoints for future autonomous runs",
        ]
    )


def build_dream_deck(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    *,
    doctrines: list[DashboardDoctrineView] | None = None,
    preferred_memory_provider: str = DEFAULT_HERMES_MEMORY_PROVIDER,
    preferred_executor: str = DEFAULT_HERMES_EXECUTOR,
) -> DashboardDreamDeckView:
    doctrine_by_project = {
        doctrine.project_id: doctrine
        for doctrine in doctrines or []
        if doctrine.project_id is not None
    }
    runtime_profile_fields = build_runtime_profile_fields(
        preferred_memory_provider=preferred_memory_provider,
        preferred_executor=preferred_executor,
    )
    dreams: list[DashboardDreamView] = []
    status_rank = {"fresh": 0, "ready": 1, "forming": 2}

    for project in projects:
        scoped = [
            mission
            for mission in missions
            if mission.project_id == project.id
            and mission.status in {"completed", "active", "paused", "blocked", "failed"}
        ]
        if not scoped:
            continue

        checkpointed = [mission for mission in scoped if mission.last_checkpoint]
        if not checkpointed and len(scoped) < 2:
            continue

        freshness_hours = min(
            (
                hours
                for hours in (
                    _hours_since(mission.updated_at.isoformat()) for mission in scoped
                )
                if hours is not None
            ),
            default=None,
        )
        anchors = [_mission_anchor(mission) for mission in checkpointed[:3]]
        prune_notes = _build_prune_notes(project, scoped)
        status = _dream_status(len(checkpointed), freshness_hours)
        doctrine = doctrine_by_project.get(project.id)
        prompt = _build_prompt(project, scoped, anchors, prune_notes, doctrine)
        instance = _pick_project_instance(instances, scoped, project.id)
        if instance is None:
            continue

        if status == "fresh":
            headline = f"{project.label} has fresh signal worth dreaming on"
            summary = (
                f"{len(checkpointed)} checkpointed mission(s) landed recently. "
                "Consolidate them now before the winning pattern gets diluted."
            )
        elif status == "ready":
            headline = f"{project.label} is ready for a dream pass"
            summary = (
                f"{len(checkpointed)} checkpointed mission(s) and {len(scoped)} total "
                "run(s) now contain enough durable signal to condense into project memory."
            )
        else:
            headline = f"{project.label} is forming a dream trail"
            summary = (
                f"{len(scoped)} recent mission(s) are creating signal, but one more "
                "solid landing would make the consolidation pass stronger."
            )

        recommended_max_turns = (
            min(doctrine.recommended_max_turns or 2, 2) if doctrine is not None else 2
        )
        mission_draft = MissionDraftView(
            name=f"Dream {project.label}",
            objective=prompt,
            instance_id=instance.id,
            project_id=project.id,
            cwd=project.path,
            model=doctrine.recommended_model if doctrine is not None else "gpt-5.4",
            max_turns=recommended_max_turns,
            use_builtin_agents=False,
            run_verification=False,
            auto_commit=False,
            pause_on_approval=True,
            allow_auto_reflexes=False,
            auto_recover=False,
            auto_recover_limit=0,
            reflex_cooldown_seconds=900,
            allow_failover=False,
            start_immediately=False,
            **runtime_profile_fields,
        )
        dreams.append(
            DashboardDreamView(
                id=f"project:{project.id}",
                project_id=project.id,
                project_label=project.label,
                status=status,
                freshness_hours=freshness_hours,
                mission_count=len(scoped),
                checkpoint_count=len(checkpointed),
                headline=headline,
                summary=summary,
                anchors=anchors,
                prune_notes=prune_notes,
                memory_prompt=prompt,
                action_label="Load dream",
                mission_draft=mission_draft,
            )
        )

    dreams = sorted(
        dreams,
        key=lambda dream: (
            status_rank[dream.status],
            -dream.checkpoint_count,
            -dream.mission_count,
            dream.project_label.lower(),
        ),
    )[:4]

    if dreams:
        ready = sum(1 for dream in dreams if dream.status in {"fresh", "ready"})
        headline = "Dream passes are ready" if ready else "Dream signal is forming"
        summary = (
            f"{ready} workspace(s) have enough mission memory to justify a "
            "consolidation pass."
            if ready
            else "Recent missions are starting to accumulate durable signal, but most "
            "workspaces still want another landing first."
        )
    else:
        headline = "No dream candidates yet"
        summary = (
            "Once projects accumulate checkpointed mission history, OpenZues will "
            "synthesize dream passes that consolidate the strongest truths into "
            "durable workspace memory."
        )

    return DashboardDreamDeckView(
        headline=headline,
        summary=summary,
        dreams=dreams,
    )
