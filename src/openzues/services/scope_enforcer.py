from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from openzues.schemas import MissionCheckpointView, MissionView, ScopeDriftLevel

MissionRecord = MissionView | Mapping[str, Any]
CheckpointRecord = MissionCheckpointView | Mapping[str, Any]

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "agent",
    "agents",
    "already",
    "also",
    "and",
    "another",
    "around",
    "before",
    "behind",
    "being",
    "best",
    "between",
    "blockers",
    "build",
    "building",
    "carry",
    "check",
    "checkpoint",
    "checkpoints",
    "clear",
    "close",
    "codex",
    "complete",
    "completed",
    "continue",
    "current",
    "cycle",
    "cycles",
    "directly",
    "document",
    "doing",
    "each",
    "either",
    "end",
    "ensure",
    "every",
    "existing",
    "feature",
    "first",
    "focus",
    "from",
    "fully",
    "highest",
    "human",
    "inside",
    "into",
    "iterating",
    "keep",
    "land",
    "latest",
    "leave",
    "meaningful",
    "mission",
    "next",
    "objective",
    "operator",
    "original",
    "outcome",
    "over",
    "path",
    "piece",
    "product",
    "project",
    "proof",
    "real",
    "relevant",
    "repo",
    "result",
    "safe",
    "same",
    "scope",
    "ship",
    "shipping",
    "should",
    "slice",
    "small",
    "smallest",
    "something",
    "state",
    "step",
    "still",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "through",
    "tight",
    "until",
    "using",
    "verified",
    "verify",
    "what",
    "when",
    "while",
    "with",
    "work",
    "workflow",
    "zues",
    "returning",
}
_BROAD_CHARTER_MARKERS = (
    "parity",
    "highest-leverage",
    "keep iterating",
    "inventory",
    "control plane",
    "platform",
    "operating system",
    "bootstrap",
    "workflow",
    "product",
    "autonomous",
)
_UI_RELATED_MARKERS = {
    "ui",
    "frontend",
    "front-end",
    "design",
    "dashboard",
    "landing",
    "chat",
    "canvas",
    "web",
}
_MICRO_POLISH_MARKERS = {
    "align",
    "animation",
    "border",
    "bubble",
    "color",
    "colors",
    "copy",
    "css",
    "font",
    "gradient",
    "hover",
    "layout",
    "padding",
    "palette",
    "polish",
    "shadow",
    "spacing",
    "style",
    "styles",
    "typography",
}
_UI_SURFACE_MARKERS = {
    "bubble",
    "chat",
    "css",
    "dashboard",
    "font",
    "gradient",
    "layout",
    "spacing",
    "style",
    "styles",
    "typography",
    "web",
}
_HOUSEKEEPING_MARKERS = {
    "comment",
    "comments",
    "doc",
    "docs",
    "docstring",
    "docstrings",
    "format",
    "formatted",
    "formatting",
    "readme",
    "rename",
    "renamed",
}
_RELEVANCE_MARKERS = {
    "anchor",
    "checkpoint",
    "handoff",
    "highest-leverage",
    "milestone",
    "parity",
    "proof",
    "ship",
    "slice",
    "verified",
    "verification",
}


@dataclass(frozen=True, slots=True)
class ScopeAssessment:
    charter_summary: str
    focus_terms: tuple[str, ...]
    evidence_summary: str
    objective_gravity: int
    drift_level: ScopeDriftLevel
    drift_summary: str
    recommended_action: str
    reflex_prompt: str


def _mission_value(mission: MissionRecord, key: str, default: Any = None) -> Any:
    if isinstance(mission, Mapping):
        return mission.get(key, default)
    return getattr(mission, key, default)


def _checkpoint_value(checkpoint: CheckpointRecord, key: str, default: Any = None) -> Any:
    if isinstance(checkpoint, Mapping):
        return checkpoint.get(key, default)
    return getattr(checkpoint, key, default)


def _truncate(value: str | None, limit: int = 220) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _tokenize(value: str | None) -> list[str]:
    text = str(value or "").lower().replace("\\", " ").replace("/", " ")
    return [token for token in _TOKEN_RE.findall(text) if token not in _STOPWORDS]


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _focus_terms(mission: MissionRecord) -> tuple[str, ...]:
    name_tokens = _tokenize(_mission_value(mission, "name", ""))
    objective_tokens = _tokenize(_mission_value(mission, "objective", ""))
    return _dedupe((name_tokens + objective_tokens)[:18])[:8]


def _evidence_parts(
    mission: MissionRecord,
    checkpoints: Sequence[CheckpointRecord] | None,
) -> list[str]:
    parts: list[str] = []
    for key in ("current_command", "last_commentary", "last_checkpoint", "last_error"):
        value = _truncate(_mission_value(mission, key, ""), 260)
        if value:
            parts.append(value)
    for checkpoint in checkpoints or []:
        summary = _truncate(_checkpoint_value(checkpoint, "summary", ""), 220)
        if summary:
            parts.append(summary)
        if len(parts) >= 6:
            break
    return parts


def _is_broad_charter(mission: MissionRecord) -> bool:
    text = " ".join(
        [
            str(_mission_value(mission, "name", "") or ""),
            str(_mission_value(mission, "objective", "") or ""),
        ]
    ).lower()
    return any(marker in text for marker in _BROAD_CHARTER_MARKERS)


def _objective_is_ui_heavy(mission: MissionRecord) -> bool:
    objective_tokens = set(
        _tokenize(
            " ".join(
                [
                    str(_mission_value(mission, "name", "") or ""),
                    str(_mission_value(mission, "objective", "") or ""),
                ]
            )
        )
    )
    return bool(objective_tokens & _UI_RELATED_MARKERS)


def _build_charter_summary(mission: MissionRecord, focus_terms: Sequence[str]) -> str:
    objective = _truncate(str(_mission_value(mission, "objective", "") or ""), 220)
    if focus_terms:
        return f"{objective} Focus gravity stays on: {', '.join(focus_terms[:4])}."
    return objective or "Keep the mission anchored to its original objective."


def build_scope_assessment(
    mission: MissionRecord,
    *,
    checkpoints: Sequence[CheckpointRecord] | None = None,
) -> ScopeAssessment:
    focus_terms = _focus_terms(mission)
    charter_summary = _build_charter_summary(mission, focus_terms)
    evidence_parts = _evidence_parts(mission, checkpoints)
    evidence_summary = evidence_parts[0] if evidence_parts else "No concrete work evidence yet."
    evidence_tokens = set(_tokenize(" ".join(evidence_parts)))
    focus_overlap = len(set(focus_terms) & evidence_tokens)
    broad_charter = _is_broad_charter(mission)
    ui_heavy_objective = _objective_is_ui_heavy(mission)
    polish_hits = 0 if ui_heavy_objective else len(evidence_tokens & _MICRO_POLISH_MARKERS)
    ui_surface_hits = len(evidence_tokens & _UI_SURFACE_MARKERS)
    housekeeping_hits = len(evidence_tokens & _HOUSEKEEPING_MARKERS)
    relevance_hits = len(evidence_tokens & _RELEVANCE_MARKERS)
    command_count = int(_mission_value(mission, "command_count", 0) or 0)
    turns_completed = int(_mission_value(mission, "turns_completed", 0) or 0)
    status = str(_mission_value(mission, "status", "") or "")
    has_checkpoint = bool(_mission_value(mission, "last_checkpoint"))

    score = 80 if broad_charter else 72
    if status in {"paused", "completed"} and has_checkpoint:
        score += 10
    if evidence_parts:
        score += min(18, focus_overlap * 6)
        if focus_overlap == 0:
            score -= 8 if broad_charter else 18
        elif focus_overlap == 1 and not broad_charter:
            score -= 4
    else:
        score -= 4
    score += min(10, relevance_hits * 2)
    if polish_hits >= 2:
        score -= 16
        if focus_overlap <= 1 and not broad_charter:
            score -= 10
    if ui_surface_hits >= 2 and not ui_heavy_objective and focus_overlap <= 1:
        score -= 6
    if housekeeping_hits >= 3 and focus_overlap == 0:
        score -= 10
    if (
        status == "active"
        and not has_checkpoint
        and command_count >= max(6, turns_completed * 4 + 4)
        and focus_overlap == 0
    ):
        score -= 10
    score = max(0, min(100, score))

    if score >= 70:
        drift_level: ScopeDriftLevel = "aligned"
    elif score >= 52:
        drift_level = "watch"
    elif score >= 35:
        drift_level = "drifting"
    else:
        drift_level = "critical"

    focus_label = ", ".join(focus_terms[:4]) if focus_terms else "the primary objective"
    if drift_level == "aligned":
        drift_summary = (
            f"Current evidence still tracks the mission charter around {focus_label}. "
            f"Objective gravity is {score}/100."
        )
        recommended_action = (
            "Keep the next slice explicit and name how it advances the charter in the checkpoint."
        )
    elif drift_level == "watch":
        drift_summary = (
            f"The current branch only weakly ties back to {focus_label}. "
            f"Objective gravity is softening at {score}/100."
        )
        recommended_action = (
            "Use the next checkpoint to prove how this branch advances the charter before "
            "opening another side quest."
        )
    elif drift_level == "drifting":
        drift_summary = (
            f"Current work looks loosely connected to {focus_label}. "
            f"Objective gravity has dropped to {score}/100."
        )
        recommended_action = (
            "Pause lateral work, restate the charter, and land one directly relevant verified "
            "slice before continuing."
        )
    else:
        drift_summary = (
            f"The mission is spending effort away from {focus_label}. "
            f"Objective gravity has collapsed to {score}/100."
        )
        recommended_action = (
            "Stop the current branch, re-anchor to the charter, and only continue once one "
            "in-bounds slice is selected."
        )

    mission_name = str(_mission_value(mission, "name", "Unnamed mission") or "Unnamed mission")
    reflex_prompt = "\n".join(
        [
            f"You are still inside the OpenZues mission '{mission_name}'.",
            f"Mission charter: {charter_summary}",
            f"Objective gravity: {score}/100 ({drift_level}).",
            f"Current evidence to audit first: {evidence_summary}",
            "Stop any branch that cannot be justified against the charter.",
            "Use this turn to:",
            "1. Restate the charter in one sentence.",
            "2. List which current work directly advances it.",
            "3. Drop or defer anything that does not clearly serve it.",
            "4. Finish one directly relevant verified slice if feasible.",
            (
                "End with a relevance checkpoint: charter, in-bounds work, removed drift, "
                "next step, blockers."
            ),
        ]
    )

    return ScopeAssessment(
        charter_summary=charter_summary,
        focus_terms=focus_terms,
        evidence_summary=evidence_summary,
        objective_gravity=score,
        drift_level=drift_level,
        drift_summary=drift_summary,
        recommended_action=recommended_action,
        reflex_prompt=reflex_prompt,
    )
