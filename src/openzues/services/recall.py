from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from openzues.database import Database
from openzues.schemas import DashboardRecallItemView, DashboardRecallView, MissionView
from openzues.services.continuity import build_continuity_packet
from openzues.services.hermes_runtime_profile import (
    load_saved_runtime_preferences,
    memory_provider_label,
)
from openzues.services.memory_protocol import (
    is_mempalace_automation_task,
    is_mempalace_direct_proof_mission,
)

if TYPE_CHECKING:
    from openzues.services.missions import MissionService


QUERY_TOKEN_RE = re.compile(r"[a-z0-9_./:-]{2,}", re.IGNORECASE)

SOURCE_WEIGHTS: dict[str, int] = {
    "checkpoint": 6,
    "summary": 5,
    "commentary": 4,
    "error": 4,
    "memory_proof": 6,
    "objective": 2,
}


def _clip_text(text: str, *, limit: int = 220) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def _tokenize_query(query: str) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for match in QUERY_TOKEN_RE.finditer(query.lower()):
        token = match.group(0).strip()
        if token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _freshness_minutes(updated_at: datetime | None) -> int | None:
    if updated_at is None:
        return None
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - updated_at.astimezone(UTC)
    return max(0, int(delta.total_seconds() // 60))


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    return phrase in text.lower()


def _score_text(
    text: str,
    *,
    query: str,
    tokens: list[str],
    source: str,
) -> int:
    if not text.strip():
        return 0
    haystack = text.lower()
    score = 0
    if _contains_phrase(haystack, query):
        score += 10
    for token in tokens:
        if token in haystack:
            score += 3 if len(token) >= 5 else 2
    if score == 0:
        return 0
    return score + SOURCE_WEIGHTS.get(source, 1)


def _recent_excerpt(mission: MissionView) -> tuple[str, str]:
    if is_mempalace_direct_proof_mission(mission):
        text = mission.last_checkpoint or mission.last_commentary or mission.objective
        return "memory_proof", _clip_text(text)
    if mission.last_checkpoint:
        return "checkpoint", _clip_text(mission.last_checkpoint)
    if mission.checkpoints:
        return "checkpoint", _clip_text(mission.checkpoints[0].summary)
    if mission.commentary_summary:
        return "commentary", _clip_text(mission.commentary_summary)
    if mission.last_error:
        return "error", _clip_text(mission.last_error)
    if mission.last_commentary:
        return "commentary", _clip_text(mission.last_commentary)
    return "objective", _clip_text(mission.objective)


def _search_candidates(mission: MissionView) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if mission.last_checkpoint:
        source = "memory_proof" if is_mempalace_direct_proof_mission(mission) else "summary"
        candidates.append((source, mission.last_checkpoint))
    if mission.commentary_summary:
        candidates.append(("commentary", mission.commentary_summary))
    if mission.last_commentary:
        candidates.append(("commentary", mission.last_commentary))
    if mission.last_error:
        candidates.append(("error", mission.last_error))
    candidates.append(("objective", mission.objective))
    for checkpoint in mission.checkpoints:
        source = (
            "memory_proof"
            if checkpoint.kind in {"recovery", "continuity_auto"}
            and (
                is_mempalace_direct_proof_mission(mission) or is_mempalace_automation_task(mission)
            )
            else "checkpoint"
        )
        candidates.append((source, checkpoint.summary))
    return candidates


class RecallService:
    def __init__(
        self,
        missions: MissionService,
        database: Database | None = None,
    ) -> None:
        self.missions = missions
        self.database = database

    async def search(
        self,
        query: str | None = None,
        *,
        project_id: int | None = None,
        limit: int = 5,
        missions: list[MissionView] | None = None,
    ) -> DashboardRecallView:
        bounded_limit = max(1, min(limit, 12))
        mission_views = missions if missions is not None else await self.missions.list_views()
        query_text = (query or "").strip()
        preferred_memory_provider, _preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        preferred_memory_label = memory_provider_label(preferred_memory_provider)
        scoped = [
            mission
            for mission in mission_views
            if project_id is None or mission.project_id == project_id
        ]
        if not scoped:
            return DashboardRecallView(
                mode="query" if query_text else "recent",
                query=query_text or None,
                headline="No durable recall is available yet",
                summary=(
                    "Once missions start leaving checkpoints, continuity packets, or proof "
                    f"handoffs, Zeus will surface them here. Preferred provider: "
                    f"{preferred_memory_label}."
                ),
                preferred_memory_provider=preferred_memory_provider,
                preferred_memory_provider_label=preferred_memory_label,
                total_matches=0,
                items=[],
            )

        normalized_query = str(query or "").strip().lower()
        if not normalized_query:
            items = self._build_recent_items(
                scoped,
                limit=bounded_limit,
                preferred_memory_provider=preferred_memory_provider,
            )
            return DashboardRecallView(
                mode="recent",
                query=None,
                headline="Recent recall is ready",
                summary=(
                    "Search prior missions, checkpoints, and memory proofs without reopening "
                    f"every thread. Preferred provider: {preferred_memory_label}."
                ),
                preferred_memory_provider=preferred_memory_provider,
                preferred_memory_provider_label=preferred_memory_label,
                total_matches=len(items),
                items=items,
            )

        items = self._build_query_items(
            scoped,
            query=normalized_query,
            limit=bounded_limit,
            preferred_memory_provider=preferred_memory_provider,
        )
        if not items:
            return DashboardRecallView(
                mode="query",
                query=query_text,
                headline=f'No saved recall matched "{query_text}"',
                summary=(
                    "Try broader keywords, a project filter, or open the recent recall deck to "
                    f"reload the latest durable handoffs. Preferred provider: "
                    f"{preferred_memory_label}."
                ),
                preferred_memory_provider=preferred_memory_provider,
                preferred_memory_provider_label=preferred_memory_label,
                total_matches=0,
                items=[],
            )
        return DashboardRecallView(
            mode="query",
            query=query_text,
            headline=f"Recall found {len(items)} match{'es' if len(items) != 1 else ''}",
            summary=(
                f'Saved mission memory matched "{query_text}". These results are built from '
                "persisted checkpoints, summaries, and proof handoffs. Preferred provider: "
                f"{preferred_memory_label}."
            ),
            preferred_memory_provider=preferred_memory_provider,
            preferred_memory_provider_label=preferred_memory_label,
            total_matches=len(items),
            items=items,
        )

    def _build_recent_items(
        self,
        missions: list[MissionView],
        *,
        limit: int,
        preferred_memory_provider: str,
    ) -> list[DashboardRecallItemView]:
        recent = sorted(
            missions,
            key=lambda mission: (
                self._provider_priority(
                    mission,
                    preferred_memory_provider=preferred_memory_provider,
                ),
                mission.updated_at,
            ),
            reverse=True,
        )[:limit]
        items: list[DashboardRecallItemView] = []
        for mission in recent:
            source, excerpt = _recent_excerpt(mission)
            items.append(
                self._build_item(
                    mission,
                    score=None,
                    source=source,
                    excerpt=excerpt,
                )
            )
        return items

    def _build_query_items(
        self,
        missions: list[MissionView],
        *,
        query: str,
        limit: int,
        preferred_memory_provider: str,
    ) -> list[DashboardRecallItemView]:
        tokens = _tokenize_query(query)
        ranked: list[tuple[int, datetime, MissionView, str, str]] = []
        for mission in missions:
            best_score = 0
            best_source = "objective"
            best_excerpt = ""
            for source, text in _search_candidates(mission):
                score = _score_text(text, query=query, tokens=tokens, source=source)
                if score <= 0:
                    continue
                score += self._provider_priority(
                    mission,
                    preferred_memory_provider=preferred_memory_provider,
                )
                if score > best_score:
                    best_score = score
                    best_source = source
                    best_excerpt = _clip_text(text)
            if best_score <= 0:
                continue
            ranked.append((best_score, mission.updated_at, mission, best_source, best_excerpt))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [
            self._build_item(mission, score=score, source=source, excerpt=excerpt)
            for score, _, mission, source, excerpt in ranked[:limit]
        ]

    def _provider_priority(
        self,
        mission: MissionView,
        *,
        preferred_memory_provider: str,
    ) -> int:
        provider_key = str(preferred_memory_provider or "").strip().lower()
        if provider_key != "mempalace":
            return 0
        if is_mempalace_direct_proof_mission(mission):
            return 4
        if is_mempalace_automation_task(mission):
            return 3
        toolsets = {str(toolset or "").strip().lower() for toolset in mission.toolsets}
        if {"memory", "session_search"} & toolsets:
            return 2
        if "memory" in toolsets:
            return 1
        return 0

    def _build_item(
        self,
        mission: MissionView,
        *,
        score: int | None,
        source: str,
        excerpt: str,
    ) -> DashboardRecallItemView:
        continuity = build_continuity_packet(
            mission,
            instance_connected=bool(mission.live_telemetry.streaming or mission.status == "active"),
            checkpoints=mission.checkpoints,
        )
        match_source = source if source in SOURCE_WEIGHTS else "recent"
        if source == "memory_proof":
            match_source = "memory_proof"
        return DashboardRecallItemView(
            mission_id=mission.id,
            mission_name=mission.name,
            project_id=mission.project_id,
            project_label=mission.project_label,
            status=mission.status,
            phase=mission.phase,
            updated_at=mission.updated_at,
            freshness_minutes=_freshness_minutes(mission.updated_at),
            score=score,
            match_source=match_source,  # type: ignore[arg-type]
            excerpt=excerpt,
            continuity_state=continuity.state,
            continuity_score=continuity.score,
            next_handoff=continuity.next_handoff,
            continuity_path=f"/api/missions/{mission.id}/continuity",
            toolsets=list(mission.toolsets),
        )
