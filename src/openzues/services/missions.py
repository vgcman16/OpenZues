from __future__ import annotations

import asyncio
import inspect
import logging
import re
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    MissionCheckpointView,
    MissionCreate,
    MissionDelegationBriefView,
    MissionDelegationRoleView,
    MissionLiveTelemetryView,
    MissionReflexRun,
    MissionView,
    SkillPinView,
)
from openzues.services.continuity import build_continuity_packet
from openzues.services.ecc_catalog import build_ecc_workspace_lines
from openzues.services.followups import mission_row_matches_payload
from openzues.services.hermes_runtime_profile import (
    build_executor_launch_assessment,
    build_executor_profile_lines,
    build_memory_provider_lines,
    build_runtime_profile_summary,
    executor_label,
    load_saved_runtime_preferences,
    memory_provider_label,
)
from openzues.services.hermes_toolsets import (
    build_hermes_tool_policy,
    build_hermes_tool_policy_lines,
    infer_hermes_toolsets,
)
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import build_mempalace_protocol_lines
from openzues.services.run_pressure import (
    continuity_snapshot_threshold,
    has_checkpoint_pressure,
    has_verification_spike_pressure,
)
from openzues.services.scope_enforcer import ScopeAssessment, build_scope_assessment
from openzues.services.skillbook import build_prompt_skill_lines, resolve_skill_profile

logger = logging.getLogger(__name__)

STALE_TURN_SECONDS = 8 * 60
CONTINUITY_SNAPSHOT_MIN_SECONDS = 5 * 60
CONTINUITY_SNAPSHOT_KIND = "continuity_auto"
RESTART_SAFE_SNAPSHOT_MIN_SECONDS = 90
RESTART_SAFE_SNAPSHOT_KIND = "restart_safe"
RECOVERY_TRACE_EVENT_LIMIT = 80
RECOVERY_TRACE_LINE_LIMIT = 8
VERIFICATION_PASS_PATTERNS = (
    re.compile(r"\b\d+\s+passed\b", re.IGNORECASE),
    re.compile(r"\bno issues found\b", re.IGNORECASE),
    re.compile(r"\ball checks passed\b", re.IGNORECASE),
    re.compile(r"\bbuild succeeded\b", re.IGNORECASE),
)
VERIFICATION_FAIL_PATTERNS = (
    re.compile(r"\b\d+\s+failed\b", re.IGNORECASE),
    re.compile(r"=+\s*failures\s*=+", re.IGNORECASE),
    re.compile(r"\bassertionerror\b", re.IGNORECASE),
    re.compile(r"\btraceback \(most recent call last\)\b", re.IGNORECASE),
)
STALE_BLOCKER_PATTERNS = (
    re.compile(r"\bnot fully green\b", re.IGNORECASE),
    re.compile(r"\bregression\b", re.IGNORECASE),
    re.compile(r"\bstill live\b", re.IGNORECASE),
    re.compile(r"\bstill failing\b", re.IGNORECASE),
    re.compile(r"\bblock(?:ed|er)?\b", re.IGNORECASE),
    re.compile(r"\bfailing\b", re.IGNORECASE),
    re.compile(r"\bbroken\b", re.IGNORECASE),
)
CONTRACT_SEAM_MARKERS = (
    "schema",
    "pydantic",
    "dashboard",
    "payload",
    "contract",
    "gateway",
    "doctor",
    "endpoint",
    "api",
    "cli",
    "fixture",
    "constructor",
    "serializer",
    "view",
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(UTC) - parsed).total_seconds()))


def _is_thread_not_found_error(value: str | Exception | None) -> bool:
    if value is None:
        return False
    return "thread not found" in str(value).lower()


def _truncate_text(value: str | None, limit: int = 320) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _error_summary(value: Any, *, fallback: str) -> str:
    if isinstance(value, BaseException):
        detail = str(value).strip()
        if detail:
            return detail
        return f"{value.__class__.__name__}: {fallback}"
    if isinstance(value, dict):
        for key in ("message", "detail", "summary", "error", "reason", "code"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        rendered = str(value).strip()
        if rendered and rendered not in {"{}", "None"}:
            return rendered
        return fallback
    detail = str(value).strip()
    if detail and detail not in {"{}", "None"}:
        return detail
    return fallback


def _thread_status_type(thread_state: dict[str, Any] | None) -> str | None:
    if not isinstance(thread_state, dict):
        return None
    status = thread_state.get("status")
    if isinstance(status, dict) and isinstance(status.get("type"), str):
        return str(status["type"])
    return None


def _thread_live_summary(
    *,
    streaming: bool,
    in_progress: bool,
    last_event_age_seconds: int | None,
    recent_event_count_30s: int,
    recent_output_delta_count_30s: int,
) -> str:
    if streaming:
        return (
            f"Streaming now with {recent_event_count_30s} thread event"
            f"{'' if recent_event_count_30s == 1 else 's'} in the last 30s."
        )
    if in_progress and last_event_age_seconds is not None and last_event_age_seconds <= 90:
        return (
            "Turn is still in progress and the thread was active recently, but it is not "
            "currently streaming command output."
        )
    if in_progress:
        return (
            "Mission is marked in progress, but no fresh thread activity has landed recently. "
            "Inspect the live thread if this persists."
        )
    if last_event_age_seconds is not None:
        return (
            f"Last thread event arrived {last_event_age_seconds}s ago. "
            f"{recent_output_delta_count_30s} output deltas landed in the last 30s."
        )
    return "No live thread telemetry has landed yet."


def _mission_text_blob(mission: dict[str, Any]) -> str:
    parts = [
        mission.get("name"),
        mission.get("objective"),
        mission.get("last_commentary"),
        mission.get("last_checkpoint"),
        mission.get("current_command"),
        mission.get("last_error"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _looks_like_contract_seam(mission: dict[str, Any]) -> bool:
    return _contains_any(_mission_text_blob(mission), CONTRACT_SEAM_MARKERS)


def _contract_seam_instruction_lines(mission: dict[str, Any]) -> list[str]:
    if not _looks_like_contract_seam(mission):
        return []
    lines = [
        "Contract seam guard:",
        (
            "- Treat schema/API/dashboard/CLI/view work as one contract seam. If you add or "
            "rename a required field, update constructors, payload builders, serializers, and "
            "shared test fixtures in the same turn."
        ),
        (
            "- Before calling this seam done, rerun the focused contract pack and at least one "
            "broader surface pack so partial wiring cannot hide behind narrow green checks."
        ),
    ]
    if bool(mission.get("run_verification")):
        lines.append(
            "- After dashboard or schema contract changes, rerun `tests/test_app.py` before "
            "checkpointing."
        )
    return lines


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _build_delegation_brief(
    mission: dict[str, Any],
    *,
    scope: ScopeAssessment | None = None,
    live_telemetry: MissionLiveTelemetryView | None = None,
    recovery_mode: bool = False,
) -> MissionDelegationBriefView:
    if not bool(mission.get("use_builtin_agents")):
        return MissionDelegationBriefView()

    text = _mission_text_blob(mission)
    command_count = int(mission.get("command_count") or 0)
    turns_started = int(mission.get("turns_started") or 0)
    has_workspace = bool(mission.get("project_id") is not None or mission.get("cwd"))
    in_progress = bool(mission.get("in_progress"))
    drifted = scope is not None and scope.drift_level in {"drifting", "critical"}
    activation = (
        "after_rebuild"
        if recovery_mode or turns_started <= 1 or drifted
        else "ready_now"
    )
    confidence = "high" if has_workspace and bool(mission.get("run_verification")) else "medium"
    if command_count == 0 and turns_started <= 1:
        confidence = "low"

    needs_brainstorm = _contains_any(
        text,
        (
            "brainstorm",
            "idea",
            "concept",
            "ux",
            "ui",
            "cleaner",
            "better",
            "fresh",
            "product direction",
            "what should",
            "design language",
        ),
    )
    needs_architect = has_workspace and (
        recovery_mode
        or command_count <= 6
        or _contains_any(
            text,
            (
                "parity",
                "harden",
                "reconstruct",
                "resume",
                "checkpoint",
                "routing",
                "gateway",
                "bootstrap",
                "schema",
                "api",
                "thread",
                "session",
                "control plane",
                "ops mesh",
                "wizard",
                "inventory",
            ),
        )
    )
    needs_planner = has_workspace and (
        recovery_mode
        or command_count <= 8
        or bool(scope is not None and scope.drift_level in {"watch", "drifting", "critical"})
        or not bool(mission.get("last_checkpoint"))
    )
    needs_coder = _contains_any(
        text,
        (
            "build",
            "ship",
            "implement",
            "land",
            "wire",
            "integrate",
            "fix",
            "refactor",
            "close the gap",
            "close biggest gaps",
            "continue",
            "harden",
            "parity",
        ),
    )
    needs_auditor = bool(mission.get("run_verification")) or _contains_any(
        text,
        (
            "verify",
            "validation",
            "tests",
            "regression",
            "doctor",
            "health",
            "smoke",
        ),
    )

    roles: list[MissionDelegationRoleView] = []
    if needs_brainstorm:
        roles.append(
            MissionDelegationRoleView(
                name="Brainstormer",
                objective=(
                    "Generate focused options, UX/product ideas, or alternate approaches without "
                    "taking over implementation decisions."
                ),
                ownership="Option generation only; no code changes and no authority over scope.",
                trigger=(
                    "Launch only when the task is still fuzzy or the lead lane needs option space."
                    if activation == "after_rebuild"
                    else "Launch when the lead lane wants fast idea generation before coding."
                ),
            )
        )
    if needs_architect:
        roles.append(
            MissionDelegationRoleView(
                name="Architect",
                objective=(
                    "Map the active seam, identify the right interfaces and file boundaries, and "
                    "name the smallest sound system shape before edits fan out."
                ),
                ownership="Read-heavy architecture mapping, contracts, and file-boundary guidance.",
                trigger=(
                    "Launch after the lead lane re-establishes context or when the change spans "
                    "multiple files or subsystems."
                ),
            )
        )
    if needs_planner:
        roles.append(
            MissionDelegationRoleView(
                name="Planner",
                objective=(
                    "Turn the chosen direction into bounded slices with ownership, sequencing, "
                    "and a concrete verification bar."
                ),
                ownership="Execution planning only; no code edits and no branch-wide redesign.",
                trigger=(
                    "Launch once the lead lane knows the seam but wants a tighter sequence before "
                    "implementation."
                ),
            )
        )
    if needs_coder:
        roles.append(
            MissionDelegationRoleView(
                name="Coder",
                objective=(
                    "Own one bounded implementation slice with explicit file ownership and avoid "
                    "broad refactors outside that seam."
                ),
                ownership="A single code-change slice chosen by the lead lane.",
                trigger=(
                    "Launch only after the lead lane locks the target seam and acceptance bar."
                ),
            )
        )
    if needs_auditor:
        roles.append(
            MissionDelegationRoleView(
                name="Auditor",
                objective=(
                    "Challenge the claimed milestone, run the tightest meaningful checks, and "
                    "report concrete pass/fail evidence before the checkpoint lands."
                ),
                ownership="Verification only: tests, lint, browser checks, or focused audits.",
                trigger=(
                    "Launch once an implementation candidate exists or when the lead lane needs "
                    "proof before checkpointing."
                ),
            )
        )

    if not roles:
        return MissionDelegationBriefView(
            enabled=True,
            mode="single_lane",
            activation=activation,
            confidence=confidence,
            summary=(
                "Keep the lead lane in charge and stay single-lane unless the task opens into a "
                "clear multi-role split."
            ),
            rationale=(
                "Built-in agents are available, but this mission does not yet show a strong "
                "parallel split."
            ),
        )

    if needs_brainstorm:
        mode = "conductor_brainstorm_architect_planner_coder_auditor"
        summary = (
            "Zues wants the main lane to conduct while a brainstormer opens option space, an "
            "architect maps the seam, a planner sequences the work, a coder lands the slice, and "
            "an auditor proves it before checkpoint."
        )
    elif needs_architect or needs_planner:
        mode = "conductor_architect_planner_coder_auditor"
        summary = (
            "Zues wants the main lane to conduct while architecture, planning, coding, and "
            "auditing stay explicitly split."
        )
    else:
        mode = "conductor_coder_auditor"
        summary = (
            "Zues wants the main lane to conduct while a coder lands the slice and an auditor "
            "proves it before the handoff lands."
        )

    rationale_bits: list[str] = []
    if recovery_mode:
        rationale_bits.append("recovery context must be rebuilt before delegation")
    elif activation == "after_rebuild":
        rationale_bits.append("delegation should wait until the lead lane re-anchors context")
    if has_workspace:
        rationale_bits.append("the mission is workspace-bound")
    if bool(mission.get("run_verification")):
        rationale_bits.append("verification is enabled")
    if live_telemetry is not None and live_telemetry.streaming and in_progress:
        rationale_bits.append("the live thread is already moving")
    if scope is not None and scope.drift_level in {"drifting", "critical"}:
        rationale_bits.append("scope drift risk is elevated")

    return MissionDelegationBriefView(
        enabled=True,
        mode=mode,
        activation=activation,
        confidence=confidence,
        summary=summary,
        rationale=", ".join(rationale_bits).capitalize() + "." if rationale_bits else None,
        roles=roles,
    )


def _delegation_instruction_lines(brief: MissionDelegationBriefView) -> list[str]:
    if not brief.enabled or not brief.roles:
        return []
    lines = [
        "Built-in agent stack:",
        f"- Mode: {brief.mode.replace('_', ' ')}.",
        (
            "- Timing: rebuild context in the main lane first, then fan out to helper agents."
            if brief.activation == "after_rebuild"
            else "- Timing: the main lane may delegate now if the seam is already clear."
        ),
        f"- Summary: {brief.summary}",
    ]
    if brief.rationale:
        lines.append(f"- Why: {brief.rationale}")
    lines.append(
        "- The main lane is the conductor: it keeps authority over scope, merge decisions, and "
        "the final checkpoint."
    )
    for role in brief.roles:
        role_line = f"- {role.name}: {role.objective} Ownership: {role.ownership}"
        if role.trigger:
            role_line += f" Trigger: {role.trigger}"
        lines.append(role_line)
    return lines


def _trace_fragment(value: Any, *, limit: int = 220) -> str | None:
    text = str(value or "").replace("\r", "").replace("\n", " ").strip()
    if not text:
        return None
    return _truncate_text(text, limit=limit)


def _thread_event_trace_line(event: dict[str, Any]) -> str | None:
    method = str(event.get("method") or "")
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None

    if method == "item/started":
        item = payload.get("item")
        if isinstance(item, dict) and str(item.get("type") or "") == "commandExecution":
            command = _trace_fragment(item.get("command"), limit=260)
            if command:
                return f"Command started: {command}"
        return None

    if method == "item/completed":
        item = payload.get("item")
        if not isinstance(item, dict):
            return None
        item_type = str(item.get("type") or "")
        if item_type == "agentMessage":
            phase = str(item.get("phase") or "")
            prefix = "Final answer" if phase == "final_answer" else "Commentary"
            text = _trace_fragment(item.get("text"), limit=260)
            if text:
                return f"{prefix}: {text}"
        if item_type == "commandExecution":
            return "Command completed."
        return None

    if method.endswith("commandExecution/outputDelta"):
        delta = _trace_fragment(payload.get("delta"))
        if delta:
            return f"Output: {delta}"
        return None

    if method.endswith("agentMessageDelta"):
        delta = _trace_fragment(payload.get("delta"))
        if delta:
            return f"Commentary delta: {delta}"
        return None

    if method == "turn/started":
        return "Turn started."
    if method == "turn/completed":
        return "Turn completed."
    return None


def _strip_trace_label(line: str) -> str:
    for prefix in (
        "Output: ",
        "Commentary: ",
        "Commentary delta: ",
        "Final answer: ",
        "Command started: ",
    ):
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return line.strip()


def _latest_trace_match(
    trace_lines: list[str],
    patterns: tuple[re.Pattern[str], ...],
) -> tuple[int, str] | None:
    for index in range(len(trace_lines) - 1, -1, -1):
        line = _strip_trace_label(trace_lines[index])
        if any(pattern.search(line) for pattern in patterns):
            return index, line
    return None


def _commentary_reads_as_blocker(commentary: str | None) -> bool:
    if not commentary:
        return False
    return any(pattern.search(commentary) for pattern in STALE_BLOCKER_PATTERNS)


def _derive_commentary_summary(
    mission: dict[str, Any],
    *,
    trace_lines: list[str],
) -> str | None:
    commentary = _truncate_text(str(mission.get("last_commentary") or "") or None, 420) or None
    latest_pass = _latest_trace_match(trace_lines, VERIFICATION_PASS_PATTERNS)
    latest_fail = _latest_trace_match(trace_lines, VERIFICATION_FAIL_PATTERNS)

    if latest_pass is not None and (latest_fail is None or latest_pass[0] > latest_fail[0]):
        proof = _truncate_text(latest_pass[1], 220)
        if _commentary_reads_as_blocker(commentary):
            return _truncate_text(
                "Recent verification looks green: "
                f"{proof} Earlier blocker language may already be stale, so land the "
                "checkpoint or continue from the cleared seam.",
                420,
            )
        return _truncate_text(f"Recent verification looks green: {proof}", 420)

    if latest_fail is not None:
        failure = _truncate_text(latest_fail[1], 220)
        if commentary:
            return _truncate_text(
                f"Recent verification still shows a failure: {failure} "
                "Fix the newest failing assertion before broadening scope.",
                420,
            )
        return _truncate_text(
            f"Recent verification still shows a failure: {failure}",
            420,
        )

    if _commentary_reads_as_blocker(commentary):
        return _truncate_text(
            "The last reported blocker has not been reconfirmed in the recent live trace. "
            "Re-run the smallest proof step before repeating it as current truth.",
            420,
        )

    return commentary


def extract_thread_id(payload: dict[str, Any]) -> str | None:
    thread_id = payload.get("threadId")
    if isinstance(thread_id, str):
        return thread_id
    thread = payload.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"]
    return None


def extract_turn_id(payload: dict[str, Any]) -> str | None:
    turn_id = payload.get("turnId")
    if isinstance(turn_id, str):
        return turn_id
    turn = payload.get("turn")
    if isinstance(turn, dict) and isinstance(turn.get("id"), str):
        return turn["id"]
    return None


class MissionService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        hub: BroadcastHub,
        *,
        poll_interval_seconds: float = 6.0,
    ) -> None:
        self.database = database
        self.manager = manager
        self.hub = hub
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._event_listeners: list[
            Callable[[str, dict[str, Any]], Awaitable[None] | None]
        ] = []

    def add_event_listener(
        self,
        listener: Callable[[str, dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        self._event_listeners.append(listener)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._runner_loop(), name="openzues-mission-runner")

    async def close(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def list_views(self) -> list[MissionView]:
        rows = await self.database.list_missions()
        return [await self._build_view(row) for row in rows]

    def _spawn_run_now(self, mission_id: int) -> None:
        task = asyncio.create_task(
            self.run_now(mission_id),
            name=f"openzues-mission-run-now-{mission_id}",
        )
        task.add_done_callback(
            lambda finished_task: self._handle_run_now_result(mission_id, finished_task)
        )

    def _handle_run_now_result(self, mission_id: int, task: asyncio.Task[MissionView]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except ValueError as exc:
            if str(exc) == f"Unknown mission {mission_id}":
                logger.info("Mission %s was deleted before the async cycle finished.", mission_id)
                return
            logger.warning(
                "Mission %s async cycle failed with a recoverable error.",
                mission_id,
                exc_info=True,
            )
        except Exception:
            logger.exception("Mission %s async cycle crashed.", mission_id)

    async def get_view(self, mission_id: int) -> MissionView:
        mission = await self.require_mission(mission_id)
        return await self._build_view(mission)

    def _resolve_toolsets(
        self,
        mission: dict[str, Any],
        *,
        project: dict[str, Any] | None = None,
        task: dict[str, Any] | None = None,
    ) -> list[str]:
        explicit_toolsets = mission.get("toolsets") or (task.get("toolsets") if task else [])
        cadence_minutes = None
        if task is not None and task.get("cadence_minutes") is not None:
            cadence_minutes = int(task["cadence_minutes"])
        return infer_hermes_toolsets(
            str(mission.get("objective") or ""),
            explicit_toolsets=explicit_toolsets,
            project_label=str(project["label"]) if project is not None else None,
            project_path=(
                str(project["path"])
                if project is not None
                else (str(mission.get("cwd") or "") or None)
            ),
            setup_mode="local",
            use_builtin_agents=bool(mission.get("use_builtin_agents", True)),
            run_verification=bool(mission.get("run_verification", True)),
            cadence_minutes=cadence_minutes,
        )

    async def _find_duplicate_inflight_mission(
        self,
        payload: MissionCreate,
        *,
        cwd: str | None,
    ) -> dict[str, Any] | None:
        inflight_missions = [
            mission
            for mission in await self.database.list_missions()
            if mission["status"] in {"active", "blocked", "paused"}
        ]
        if payload.task_blueprint_id is not None:
            candidates = [
                mission
                for mission in inflight_missions
                if mission.get("task_blueprint_id") == payload.task_blueprint_id
            ]
            if candidates:
                status_rank = {"active": 0, "blocked": 1, "paused": 2}
                return sorted(
                    candidates,
                    key=lambda mission: (
                        status_rank.get(str(mission.get("status") or ""), 99),
                        str(mission.get("updated_at") or ""),
                        int(mission.get("id") or 0),
                    ),
                    reverse=False,
                )[0]
        if not payload.thread_id:
            return None
        candidates = [
            mission
            for mission in inflight_missions
            if mission_row_matches_payload(mission, payload, cwd=cwd)
        ]
        if not candidates:
            return None
        status_rank = {"active": 0, "blocked": 1, "paused": 2}
        return sorted(
            candidates,
            key=lambda mission: (
                status_rank.get(str(mission.get("status") or ""), 99),
                str(mission.get("updated_at") or ""),
                int(mission.get("id") or 0),
            ),
            reverse=False,
        )[0]

    async def create(self, payload: MissionCreate) -> MissionView:
        await self.manager.get(payload.instance_id)
        project = (
            await self.database.get_project(payload.project_id)
            if payload.project_id is not None
            else None
        )
        if payload.project_id is not None and project is None:
            raise ValueError(f"Unknown project {payload.project_id}")
        task: dict[str, Any] | None = None
        if payload.task_blueprint_id is not None:
            task = await self.database.get_task_blueprint(payload.task_blueprint_id)
            if task is None:
                raise ValueError(f"Unknown task blueprint {payload.task_blueprint_id}")
        runtime = await self.manager.get(payload.instance_id)
        cwd = payload.cwd or (project["path"] if project is not None else runtime.cwd)
        resolved_toolsets = infer_hermes_toolsets(
            payload.objective,
            explicit_toolsets=payload.toolsets or (task.get("toolsets") if task else []),
            project_label=str(project["label"]) if project is not None else None,
            project_path=str(cwd) if cwd is not None else None,
            setup_mode="local",
            use_builtin_agents=payload.use_builtin_agents,
            run_verification=payload.run_verification,
            cadence_minutes=(
                int(task["cadence_minutes"])
                if task is not None and task.get("cadence_minutes") is not None
                else None
            ),
        )
        payload = payload.model_copy(update={"toolsets": resolved_toolsets})
        duplicate = await self._find_duplicate_inflight_mission(payload, cwd=cwd)
        if duplicate is not None:
            return await self._build_view(duplicate)
        status = "active" if payload.start_immediately else "paused"
        mission_id = await self.database.create_mission(
            name=payload.name,
            objective=payload.objective,
            status=status,
            instance_id=payload.instance_id,
            project_id=payload.project_id,
            task_blueprint_id=payload.task_blueprint_id,
            thread_id=payload.thread_id,
            session_key=payload.session_key,
            cwd=cwd,
            model=payload.model,
            reasoning_effort=payload.reasoning_effort,
            collaboration_mode=payload.collaboration_mode,
            max_turns=payload.max_turns,
            use_builtin_agents=payload.use_builtin_agents,
            run_verification=payload.run_verification,
            auto_commit=payload.auto_commit,
            pause_on_approval=payload.pause_on_approval,
            allow_auto_reflexes=payload.allow_auto_reflexes,
            auto_recover=payload.auto_recover,
            auto_recover_limit=payload.auto_recover_limit,
            reflex_cooldown_seconds=payload.reflex_cooldown_seconds,
            allow_failover=payload.allow_failover,
            toolsets=payload.toolsets,
        )
        await self.database.update_mission(
            mission_id,
            phase="ready" if payload.start_immediately else "paused",
        )
        await self._publish_snapshot("mission/created", {"missionId": mission_id})
        if payload.start_immediately:
            self._spawn_run_now(mission_id)
        return await self.get_view(mission_id)

    async def pause(self, mission_id: int) -> MissionView:
        await self.database.update_mission(
            mission_id,
            status="paused",
            phase="paused",
            in_progress=0,
        )
        await self._publish_snapshot("mission/paused", {"missionId": mission_id})
        return await self.get_view(mission_id)

    async def yield_for_queue(self, mission_id: int) -> MissionView:
        lock = self._locks[mission_id]
        async with lock:
            mission = await self.require_mission(mission_id)
            await self._yield_for_queue_locked(mission_id, mission)
        return await self.get_view(mission_id)

    async def resume(self, mission_id: int) -> MissionView:
        await self.database.update_mission(
            mission_id,
            status="active",
            phase="ready",
            last_error=None,
        )
        await self._publish_snapshot("mission/resumed", {"missionId": mission_id})
        await self.run_now(mission_id)
        return await self.get_view(mission_id)

    async def complete(self, mission_id: int) -> MissionView:
        await self.database.update_mission(
            mission_id,
            status="completed",
            phase="completed",
            in_progress=0,
        )
        await self._publish_snapshot("mission/completed", {"missionId": mission_id})
        return await self.get_view(mission_id)

    async def delete(self, mission_id: int) -> None:
        await self.database.delete_mission(mission_id)
        await self._publish_snapshot("mission/deleted", {"missionId": mission_id})

    async def fire_reflex(self, mission_id: int, payload: MissionReflexRun) -> MissionView:
        mission = await self.require_mission(mission_id)
        thread_id = mission.get("thread_id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("Mission needs an attached thread before you can fire a reflex.")

        if mission["status"] == "blocked" and str(mission.get("last_error") or "").startswith(
            "Waiting for approval:"
        ):
            raise ValueError(
                "Resolve the approval request before firing a reflex into this mission."
            )

        runtime = await self.manager.get(int(mission["instance_id"]))
        if not runtime.connected:
            try:
                runtime = await self.manager.connect_instance(int(mission["instance_id"]))
            except Exception as exc:
                raise RuntimeError(f"Instance is offline: {exc}") from exc
        if not runtime.connected:
            raise RuntimeError("Instance is offline.")

        await self._start_turn_with_prompt(
            mission_id,
            mission,
            thread_id=thread_id,
            prompt=payload.prompt,
            event_type="mission/reflex-fired",
            reflex=payload,
        )
        return await self.get_view(mission_id)

    async def run_now(self, mission_id: int) -> MissionView:
        mission = await self.require_mission(mission_id)
        if mission["status"] == "completed":
            return await self.get_view(mission_id)
        if mission["status"] in {"paused", "failed"}:
            await self.database.update_mission(
                mission_id,
                status="active",
                phase="ready",
                last_error=None,
            )
        await self._reconcile_mission(mission_id, force=True)
        return await self.get_view(mission_id)

    async def handle_event(self, instance_id: int, event: dict[str, Any]) -> None:
        thread_id = event.get("threadId")
        if not isinstance(thread_id, str):
            return
        mission = await self.database.get_mission_by_thread(instance_id, thread_id)
        if mission is None:
            return

        mission_id = int(mission["id"])
        updates: dict[str, Any] = {"last_activity_at": utcnow()}
        method = event["method"]
        params = event["params"]
        live_thread_signal = self._event_proves_thread_is_live(method, params)

        if live_thread_signal and (
            _is_thread_not_found_error(mission.get("last_error"))
            or str(mission.get("last_error") or "").startswith("Waiting for approval:")
        ):
            updates["status"] = "active"
            updates["last_error"] = None
            if method in {"turn/started", "item/started", "item/completed"}:
                updates["in_progress"] = 1

        if method == "turn/started":
            updates["in_progress"] = 1
            updates["last_turn_id"] = extract_turn_id(params)
            updates["phase"] = "thinking"
            if mission["status"] == "active":
                updates["last_error"] = None
        elif method == "turn/completed":
            turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
            updates["in_progress"] = 0
            updates["last_turn_id"] = extract_turn_id(params) or mission.get("last_turn_id")
            if turn.get("error"):
                error_summary = _error_summary(
                    turn["error"],
                    fallback="Codex reported turn failure without detailed error output.",
                )
                updates["status"] = "failed"
                updates["phase"] = "failed"
                updates["failure_count"] = int(mission["failure_count"]) + 1
                updates["last_error"] = error_summary
                await self.database.append_mission_checkpoint(
                    mission_id=int(mission["id"]),
                    thread_id=thread_id,
                    turn_id=extract_turn_id(params),
                    kind="error",
                    summary=error_summary,
                )
            else:
                next_completed = int(mission["turns_completed"]) + 1
                updates["turns_completed"] = next_completed
                updates["phase"] = "completed" if mission["status"] == "completed" else "ready"
                updates["current_command"] = None
                if mission["status"] == "active":
                    updates["last_error"] = None
                    max_turns = mission.get("max_turns")
                    if max_turns is None or next_completed < int(max_turns):
                        self._spawn_run_now(int(mission["id"]))
        elif method == "thread/status/changed":
            status = params.get("status") if isinstance(params.get("status"), dict) else {}
            if status.get("type") == "idle":
                updates["in_progress"] = 0
                updates["phase"] = "ready"
            if status.get("type") == "active":
                updates["in_progress"] = 1
                updates["phase"] = "thinking"
        elif method == "thread/tokenUsage/updated":
            raw_token_usage = params.get("tokenUsage")
            token_usage: dict[str, Any] = (
                raw_token_usage if isinstance(raw_token_usage, dict) else {}
            )
            raw_total = token_usage.get("total")
            total: dict[str, Any] = raw_total if isinstance(raw_total, dict) else {}
            updates["total_tokens"] = int(total.get("totalTokens") or 0)
            updates["output_tokens"] = int(total.get("outputTokens") or 0)
            updates["reasoning_tokens"] = int(total.get("reasoningOutputTokens") or 0)
        elif method == "item/started":
            item = params.get("item") if isinstance(params.get("item"), dict) else {}
            item_type = str(item.get("type") or "")
            if item_type == "reasoning":
                updates["phase"] = "reasoning"
            if item_type == "commandExecution":
                updates["phase"] = "executing"
                updates["current_command"] = str(item.get("command") or "")
            if item_type == "agentMessage":
                updates["phase"] = "reporting"
        elif method == "item/completed":
            item = params.get("item") if isinstance(params.get("item"), dict) else {}
            item_type = str(item.get("type") or "")
            if item_type == "commandExecution":
                updates["phase"] = "thinking"
                updates["current_command"] = None
                updates["command_count"] = int(mission["command_count"]) + 1
            if item_type == "agentMessage" and item.get("phase") == "commentary":
                text = str(item.get("text") or "").strip()
                if text:
                    updates["last_commentary"] = text[:1200]
            if item.get("type") == "agentMessage" and item.get("phase") == "final_answer":
                text = str(item.get("text") or "").strip()
                if text:
                    summary = text[:3000]
                    updates["last_checkpoint"] = summary
                    updates["status"] = "completed"
                    updates["phase"] = "completed"
                    updates["in_progress"] = 0
                    updates["current_command"] = None
                    await self.database.append_mission_checkpoint(
                        mission_id=mission_id,
                        thread_id=thread_id,
                        turn_id=extract_turn_id(params),
                        kind="final_answer",
                        summary=summary,
                    )

        merged_mission = {**mission, **updates}
        await self.database.update_mission(mission_id, **updates)
        turn_payload = params.get("turn") if isinstance(params.get("turn"), dict) else {}
        if (
            method == "turn/completed"
            and not turn_payload.get("error")
            and not bool(merged_mission.get("last_checkpoint"))
        ):
            await self._maybe_append_restart_safe_snapshot(
                mission_id,
                merged_mission,
                force=True,
                reason="turn_boundary",
            )
            await self._maybe_append_continuity_snapshot(
                mission_id,
                merged_mission,
                force=True,
                reason="turn_boundary",
            )
        await self._publish_snapshot(
            "mission/event",
            {"missionId": mission_id, "method": method, "threadId": thread_id},
        )

    def _event_proves_thread_is_live(self, method: str, params: dict[str, Any]) -> bool:
        if method in {"turn/started", "item/started", "item/completed"}:
            return True
        if method == "thread/tokenUsage/updated":
            return True
        if method != "thread/status/changed":
            return False
        raw_status = params.get("status")
        status = raw_status if isinstance(raw_status, dict) else {}
        return str(status.get("type") or "") in {"active", "idle"}

    async def handle_server_request(self, instance_id: int, request: dict[str, Any]) -> None:
        thread_id = request.get("threadId")
        if not isinstance(thread_id, str):
            return
        request_id = request.get("requestId")
        if isinstance(request_id, str):
            runtime = await self.manager.get(instance_id)
            if not any(
                item.get("request_id") == request_id for item in runtime.unresolved_requests
            ):
                return
        mission = await self.database.get_mission_by_thread(instance_id, thread_id)
        if mission is None or not bool(mission["pause_on_approval"]):
            return
        summary = f"Waiting for approval: {request['method']}"
        if mission.get("last_error") != summary:
            await self.database.append_mission_checkpoint(
                mission_id=int(mission["id"]),
                thread_id=thread_id,
                turn_id=None,
                kind="approval",
                summary=summary,
            )
        await self.database.update_mission(
            int(mission["id"]),
            status="blocked",
            phase="approval",
            last_error=summary,
            last_activity_at=utcnow(),
        )
        await self._publish_snapshot(
            "mission/blocked",
            {"missionId": int(mission["id"]), "threadId": thread_id, "reason": summary},
        )

    async def require_mission(self, mission_id: int) -> dict[str, Any]:
        mission = await self.database.get_mission(mission_id)
        if mission is None:
            raise ValueError(f"Unknown mission {mission_id}")
        return mission

    def _orbit_threshold(self, mission: dict[str, Any]) -> int:
        return max(6, int(mission["turns_completed"]) * 4 + 4)

    def _stale_turn_threshold_seconds(self) -> int:
        return STALE_TURN_SECONDS

    def _reflex_ready(self, mission: dict[str, Any]) -> bool:
        if not bool(mission.get("allow_auto_reflexes")):
            return False
        elapsed = _seconds_since(mission.get("last_reflex_at"))
        if elapsed is None:
            return True
        return elapsed >= int(mission.get("reflex_cooldown_seconds") or 900)

    def _should_auto_yield_for_queue(
        self,
        mission: dict[str, Any],
        *,
        queue_depth: int,
        last_activity_seconds: int | None,
    ) -> bool:
        if queue_depth <= 0:
            return False
        if str(mission.get("status") or "") != "active":
            return False
        if bool(mission.get("in_progress")):
            return False
        if bool(mission.get("last_checkpoint")):
            return False
        if (
            last_activity_seconds is None
            or last_activity_seconds < self._stale_turn_threshold_seconds()
        ):
            return False
        token_hot = has_checkpoint_pressure(
            total_tokens=int(mission.get("total_tokens") or 0),
            model=str(mission.get("model") or "") or None,
            has_checkpoint=bool(mission.get("last_checkpoint")),
        )
        orbiting = int(mission.get("command_count") or 0) >= self._orbit_threshold(mission)
        return token_hot or orbiting

    async def _build_queue_yield_checkpoint(
        self,
        mission_id: int,
        mission: dict[str, Any],
    ) -> str:
        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=3)
        packet = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=checkpoints,
        )
        queue_depth = sum(
            1
            for candidate in await self.database.list_missions()
            if int(candidate["instance_id"]) == int(mission["instance_id"])
            and int(candidate["id"]) != mission_id
            and str(candidate.get("status") or "") == "blocked"
            and str(candidate.get("phase") or "") == "queued"
        )
        lines = [
            (
                "Auto-yielded the lane after a long run of "
                f"{int(mission.get('total_tokens') or 0):,} tokens "
                f"and {int(mission.get('command_count') or 0)} commands "
                "without a durable checkpoint."
            ),
            f"Queue pressure: {queue_depth} queued mission(s) were waiting on this lane.",
            f"Anchor: {packet.anchor}",
            f"Drift: {packet.drift}",
            f"Next handoff: {packet.next_handoff}",
        ]
        return "\n".join(lines)

    async def _yield_for_queue_locked(
        self,
        mission_id: int,
        mission: dict[str, Any],
    ) -> None:
        existing_checkpoint = str(mission.get("last_checkpoint") or "")
        if (
            str(mission.get("status") or "") == "paused"
            and existing_checkpoint.startswith("Auto-yielded the lane after")
        ):
            return
        if str(mission.get("status") or "") != "active":
            return
        summary = await self._build_queue_yield_checkpoint(mission_id, mission)
        await self.database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id=str(mission.get("thread_id") or "") or None,
            turn_id=str(mission.get("last_turn_id") or "") or None,
            kind="queue_yield",
            summary=summary,
        )
        await self.database.update_mission(
            mission_id,
            status="paused",
            phase="paused",
            in_progress=0,
            current_command=None,
            last_error=None,
            last_checkpoint=summary,
            last_activity_at=utcnow(),
        )
        await self._publish_snapshot(
            "mission/auto-yielded",
            {"missionId": mission_id, "reason": "queue_pressure"},
        )

    async def _latest_checkpoint_of_kind(
        self,
        mission_id: int,
        *,
        kind: str,
        limit: int = 8,
    ) -> dict[str, Any] | None:
        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=limit)
        for checkpoint in checkpoints:
            if str(checkpoint.get("kind") or "") == kind:
                return checkpoint
        return None

    async def _recent_thread_trace_lines(
        self,
        *,
        instance_id: int,
        thread_id: str,
        limit: int = RECOVERY_TRACE_EVENT_LIMIT,
    ) -> list[str]:
        lines: list[str] = []
        for event in await self.database.list_thread_events(
            instance_id=instance_id,
            thread_id=thread_id,
            limit=limit,
        ):
            line = _thread_event_trace_line(event)
            if not line:
                continue
            if lines and lines[-1] == line:
                continue
            lines.append(line)
        return lines[-RECOVERY_TRACE_LINE_LIMIT:]

    def _should_capture_restart_safe_snapshot(
        self,
        mission: dict[str, Any],
        latest_snapshot: dict[str, Any] | None,
        *,
        force: bool,
    ) -> bool:
        if str(mission.get("status") or "") not in {"active", "blocked"}:
            return False
        if force:
            return True
        if not bool(mission.get("in_progress")):
            return False
        if not any(
            (
                str(mission.get("current_command") or "").strip(),
                str(mission.get("last_commentary") or "").strip(),
                int(mission.get("total_tokens") or 0) > 0,
                int(mission.get("command_count") or 0) > 0,
            )
        ):
            return False
        if latest_snapshot is None:
            return True
        age_seconds = _seconds_since(latest_snapshot.get("created_at"))
        if age_seconds is None:
            return True
        return age_seconds >= RESTART_SAFE_SNAPSHOT_MIN_SECONDS

    async def _maybe_append_restart_safe_snapshot(
        self,
        mission_id: int,
        mission: dict[str, Any],
        *,
        force: bool = False,
        reason: str = "background",
    ) -> bool:
        thread_id = str(mission.get("thread_id") or "") or None
        if thread_id is None:
            return False

        latest_snapshot = await self._latest_checkpoint_of_kind(
            mission_id,
            kind=RESTART_SAFE_SNAPSHOT_KIND,
        )
        if not self._should_capture_restart_safe_snapshot(
            mission,
            latest_snapshot,
            force=force,
        ):
            return False

        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=6)
        continuity_inputs = [
            checkpoint
            for checkpoint in checkpoints
            if str(checkpoint.get("kind") or "") != RESTART_SAFE_SNAPSHOT_KIND
        ]
        packet = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=continuity_inputs,
        )
        trace_lines = await self._recent_thread_trace_lines(
            instance_id=int(mission["instance_id"]),
            thread_id=thread_id,
        )
        commentary = _derive_commentary_summary(mission, trace_lines=trace_lines)

        command_count = int(mission.get("command_count") or 0)
        total_tokens = int(mission.get("total_tokens") or 0)
        current_command = _truncate_text(str(mission.get("current_command") or "") or None, 260)

        lines = [
            (
                f"Restart-safe recovery packet ({reason}) after {command_count} commands "
                f"and {total_tokens:,} tokens."
            ),
            f"State: {packet.state} ({packet.score}/100).",
            f"Anchor: {packet.anchor}",
            f"Drift: {packet.drift}",
            f"Next handoff: {packet.next_handoff}",
        ]
        if current_command:
            lines.insert(2, f"Current command: {current_command}")
        elif commentary:
            lines.insert(2, f"Current focus: {commentary}")
        if trace_lines:
            lines.extend(["", "Recent live trace:"])
            lines.extend(f"- {line}" for line in trace_lines)
        summary = "\n".join(lines)

        if latest_snapshot is not None and str(latest_snapshot.get("summary") or "") == summary:
            return False

        await self.database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id=thread_id,
            turn_id=str(mission.get("last_turn_id") or "") or None,
            kind=RESTART_SAFE_SNAPSHOT_KIND,
            summary=summary,
        )
        await self._publish_snapshot(
            "mission/restart-safe-snapshotted",
            {"missionId": mission_id, "reason": reason},
        )
        return True

    def _should_capture_continuity_snapshot(
        self,
        mission: dict[str, Any],
        latest_snapshot: dict[str, Any] | None,
        *,
        force: bool,
    ) -> bool:
        if str(mission.get("status") or "") != "active":
            return False
        if force:
            return True
        if bool(mission.get("last_checkpoint")):
            return False
        if not bool(mission.get("in_progress")):
            return False
        hot = int(mission.get("total_tokens") or 0) >= continuity_snapshot_threshold(
            str(mission.get("model") or "") or None
        )
        orbiting = int(mission.get("command_count") or 0) >= self._orbit_threshold(mission)
        if not hot and not orbiting:
            return False
        if latest_snapshot is None:
            return True
        age_seconds = _seconds_since(latest_snapshot.get("created_at"))
        if age_seconds is None:
            return True
        return age_seconds >= CONTINUITY_SNAPSHOT_MIN_SECONDS

    async def _maybe_append_continuity_snapshot(
        self,
        mission_id: int,
        mission: dict[str, Any],
        *,
        force: bool = False,
        reason: str = "background",
    ) -> bool:
        thread_id = str(mission.get("thread_id") or "") or None
        if thread_id is None:
            return False

        latest_snapshot = await self._latest_checkpoint_of_kind(
            mission_id,
            kind=CONTINUITY_SNAPSHOT_KIND,
        )
        if not self._should_capture_continuity_snapshot(
            mission,
            latest_snapshot,
            force=force,
        ):
            return False

        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=5)
        continuity_inputs = [
            checkpoint
            for checkpoint in checkpoints
            if str(checkpoint.get("kind") or "") != CONTINUITY_SNAPSHOT_KIND
        ]
        packet = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=continuity_inputs,
        )
        trace_lines = await self._recent_thread_trace_lines(
            instance_id=int(mission["instance_id"]),
            thread_id=thread_id,
        )

        command_count = int(mission.get("command_count") or 0)
        total_tokens = int(mission.get("total_tokens") or 0)
        phase = str(mission.get("phase") or "active")
        current_command = _truncate_text(str(mission.get("current_command") or "") or None, 260)
        commentary = _derive_commentary_summary(mission, trace_lines=trace_lines)

        lines = [
            (
                f"Auto continuity snapshot ({reason}) after {command_count} commands and "
                f"{total_tokens:,} tokens."
            ),
            f"State: {packet.state} ({packet.score}/100).",
            f"Anchor: {packet.anchor}",
            f"Drift: {packet.drift}",
            f"Next handoff: {packet.next_handoff}",
        ]
        if current_command:
            lines.insert(2, f"Current command: {current_command}")
        elif commentary:
            lines.insert(2, f"Current focus: {commentary}")
        else:
            lines.insert(2, f"Current phase: {phase}.")
        summary = "\n".join(lines)

        if latest_snapshot is not None and str(latest_snapshot.get("summary") or "") == summary:
            return False

        await self.database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id=thread_id,
            turn_id=str(mission.get("last_turn_id") or "") or None,
            kind=CONTINUITY_SNAPSHOT_KIND,
            summary=summary,
        )
        await self._publish_snapshot(
            "mission/continuity-snapshotted",
            {"missionId": mission_id, "reason": reason},
        )
        return True

    def _build_governor_reflex(self, mission: dict[str, Any]) -> MissionReflexRun | None:
        if not self._reflex_ready(mission):
            return None

        last_checkpoint = bool(mission.get("last_checkpoint"))
        last_activity_seconds = _seconds_since(mission.get("last_activity_at"))
        status = str(mission.get("status") or "")
        scope = build_scope_assessment(mission)

        if (
            status == "failed"
            and bool(mission.get("auto_recover"))
            and last_checkpoint
            and int(mission.get("failure_count") or 0)
            <= int(mission.get("auto_recover_limit") or 0)
        ):
            return MissionReflexRun(
                kind="recovery_triangle",
                title=f"Auto-recover {mission['name']}",
                prompt="\n".join(
                    [
                        f"You are resuming the OpenZues mission '{mission['name']}'.",
                        (
                            "A self-healing governor has re-armed this thread because "
                            "recovery is still within budget."
                        ),
                        "Read the most recent checkpoint and the latest failure context first.",
                        (
                            "Choose the safest recovery path, execute only the "
                            "highest-leverage repair, verify it, and end with a "
                            "concise recovery checkpoint."
                        ),
                        "Do not restart the project from scratch.",
                    ]
                ),
            )

        if status == "active" and scope.drift_level in {"drifting", "critical"}:
            return MissionReflexRun(
                kind="scope_realign",
                title=f"Realign {mission['name']} to its charter",
                prompt=scope.reflex_prompt,
            )

        if status != "active" or mission.get("in_progress"):
            return None

        if (
            int(mission.get("command_count") or 0) >= self._orbit_threshold(mission)
            and not last_checkpoint
        ):
            return MissionReflexRun(
                kind="checkpoint_now",
                title=f"Force landing for {mission['name']}",
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission['name']}'.",
                        "The self-healing governor detected scope expansion without a checkpoint.",
                        "Stop broadening the task.",
                        (
                            "Use this turn to verify the most important completed work, "
                            "finish only one small missing piece if necessary, and end "
                            "with a checkpoint: completed, verified, next smallest "
                            "step, blockers."
                        ),
                    ]
                ),
            )

        if has_verification_spike_pressure(
            total_tokens=int(mission.get("total_tokens") or 0),
            model=str(mission.get("model") or "") or None,
            has_checkpoint=last_checkpoint,
        ):
            return MissionReflexRun(
                kind="verification_spike",
                title=f"Verification spike for {mission['name']}",
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission['name']}'.",
                        "The self-healing governor wants proof before more exploration.",
                        (
                            "Pause new feature expansion for this turn, run the "
                            "highest-value verification you can, summarize what is "
                            "confirmed, what remains uncertain, and what the smallest "
                            "safe next move should be."
                        ),
                    ]
                ),
            )

        if last_activity_seconds is not None and last_activity_seconds >= 8 * 60:
            return MissionReflexRun(
                kind="heartbeat_nudge",
                title=f"Heartbeat nudge for {mission['name']}",
                prompt="\n".join(
                    [
                        f"You are still inside the OpenZues mission '{mission['name']}'.",
                        "The self-healing governor detected a quiet lane.",
                        (
                            "Re-orient from the current thread state, choose the "
                            "smallest high-leverage next step, complete it if feasible, "
                            "and leave a tight checkpoint."
                        ),
                    ]
                ),
            )

        return None

    def _runtime_supports_model(self, runtime: Any, model: str) -> bool:
        catalog = getattr(runtime, "models", None)
        if not isinstance(catalog, list) or not catalog:
            return True
        expected = model.strip().lower()
        for item in catalog:
            if not isinstance(item, dict):
                continue
            for key in ("id", "model", "displayName"):
                value = item.get(key)
                if isinstance(value, str) and expected in value.strip().lower():
                    return True
        return False

    async def _pick_failover_target(
        self,
        mission_id: int,
        mission: dict[str, Any],
    ) -> Any | None:
        live_counts: dict[int, int] = {}
        for candidate in await self.database.list_missions():
            instance_id = int(candidate["instance_id"])
            if int(candidate["id"]) == mission_id:
                continue
            if str(candidate.get("status") or "") in {"active", "blocked"}:
                live_counts[instance_id] = live_counts.get(instance_id, 0) + 1

        scored: list[tuple[int, int, int, int, Any]] = []
        for runtime in self.manager.instances.values():
            if runtime.instance_id == int(mission["instance_id"]) or not runtime.connected:
                continue
            if live_counts.get(runtime.instance_id, 0):
                continue
            model_penalty = 0 if self._runtime_supports_model(runtime, str(mission["model"])) else 1
            request_penalty = len(getattr(runtime, "unresolved_requests", []))
            freshness = _seconds_since(getattr(runtime, "last_event_at", None))
            freshness_penalty = 999999 if freshness is None else freshness
            scored.append(
                (
                    model_penalty,
                    request_penalty,
                    freshness_penalty,
                    runtime.instance_id,
                    runtime,
                )
            )

        if not scored:
            return None

        scored.sort(key=lambda item: item[:4])
        return scored[0][4]

    def _crash_safe_packet_summaries(
        self,
        checkpoints: list[dict[str, Any]],
    ) -> list[str]:
        summaries: list[str] = []
        for checkpoint in reversed(checkpoints):
            if str(checkpoint.get("kind") or "") not in {
                RESTART_SAFE_SNAPSHOT_KIND,
                CONTINUITY_SNAPSHOT_KIND,
                "queue_yield",
            }:
                continue
            summary = str(checkpoint.get("summary") or "").strip().replace("\n", " ")
            summaries.append(f"- [{checkpoint['kind']}] {summary[:700]}")
        return summaries

    def _build_failover_prompt(
        self,
        mission: dict[str, Any],
        *,
        source_name: str,
        target_name: str,
        offline_error: str,
        checkpoints: list[dict[str, Any]],
        trace_lines: list[str],
    ) -> str:
        continuity = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=checkpoints,
        )
        delegation_brief = _build_delegation_brief(
            mission,
            recovery_mode=True,
        )
        instructions = [
            "You are taking over an OpenZues autonomous mission after lane failover.",
            f"Mission: {mission['name']}",
            f"Source lane: {source_name}",
            f"Recovery lane: {target_name}",
            "",
            "Primary objective:",
            str(mission["objective"]),
            "",
            "Failover doctrine:",
            "- Reconstruct state from the checkpoint trail before making new changes.",
            "- Do not redo already-landed work unless verification proves it is broken.",
            "- Verify your footing quickly, then resume the highest-leverage next step.",
            (
                "- End this turn with a re-entry checkpoint: recovered state, "
                "verified facts, next move, blockers."
            ),
        ]
        instructions.extend(["", *_delegation_instruction_lines(delegation_brief)])
        if bool(mission.get("run_verification")):
            instructions.append(
                "- Run the fastest meaningful verification before broadening scope again."
            )
        if mission.get("cwd"):
            instructions.append(
                f"- Treat `{mission['cwd']}` as the primary workspace for this recovery lane."
            )
        instructions.extend(
            [
                "",
                "Failover trigger:",
                offline_error,
            ]
        )
        instructions.extend(
            [
                "",
                "Continuity relay packet:",
                f"- State: {continuity.state} ({continuity.score}/100)",
                f"- Anchor: {continuity.anchor}",
                f"- Drift: {continuity.drift}",
                f"- Safest handoff: {continuity.next_handoff}",
            ]
        )
        if trace_lines:
            instructions.extend(["", "Recent persisted live trace:"])
            instructions.extend(f"- {line}" for line in trace_lines)
        if checkpoints:
            crash_safe_packets = self._crash_safe_packet_summaries(checkpoints)
            if crash_safe_packets:
                instructions.extend(["", "Crash-safe relay packets:"])
                instructions.extend(crash_safe_packets)
            instructions.extend(
                [
                    "",
                    "Recent checkpoint trail:",
                ]
            )
            for checkpoint in reversed(checkpoints):
                summary = str(checkpoint.get("summary") or "").strip().replace("\n", " ")
                summary = summary[:700]
                instructions.append(f"- [{checkpoint['kind']}] {summary}")
        elif mission.get("last_checkpoint"):
            instructions.extend(
                [
                    "",
                    "Last known checkpoint:",
                    str(mission["last_checkpoint"]),
                ]
            )
        if mission.get("last_error") and str(mission["last_error"]) != offline_error:
            instructions.extend(
                [
                    "",
                    "Recent mission issue:",
                    str(mission["last_error"]),
                ]
        )
        return "\n".join(instructions)

    def _build_stale_thread_recovery_prompt(
        self,
        mission: dict[str, Any],
        *,
        stale_thread_id: str,
        new_thread_id: str,
        stale_error: str,
        checkpoints: list[dict[str, Any]],
        trace_lines: list[str],
    ) -> str:
        continuity = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=checkpoints,
        )
        delegation_brief = _build_delegation_brief(
            mission,
            recovery_mode=True,
        )
        instructions = [
            "You are resuming an OpenZues autonomous mission after stale-thread recovery.",
            f"Mission: {mission['name']}",
            f"Stale thread: {stale_thread_id}",
            f"Recovery thread: {new_thread_id}",
            "",
            "Primary objective:",
            str(mission["objective"]),
            "",
            "Recovery doctrine:",
            "- The prior thread can no longer be resumed, so treat this as a fresh re-entry lane.",
            "- Reconstruct context from the checkpoint trail before taking new action.",
            "- Do not redo verified work unless the checkpoint or repo state proves it is broken.",
            "- Verify your footing quickly, then continue with the smallest high-leverage step.",
            (
                "- End this turn with a re-entry checkpoint: recovered context, verified state, "
                "next step, blockers."
            ),
        ]
        instructions.extend(["", *_delegation_instruction_lines(delegation_brief)])
        if bool(mission.get("run_verification")):
            instructions.append(
                "- Run the fastest meaningful verification before broadening scope again."
            )
        if mission.get("cwd"):
            instructions.append(
                f"- Treat `{mission['cwd']}` as the primary workspace for this re-entry."
            )
        instructions.extend(
            [
                "",
                "Recovery trigger:",
                stale_error,
                "",
                "Continuity relay packet:",
                f"- State: {continuity.state} ({continuity.score}/100)",
                f"- Anchor: {continuity.anchor}",
                f"- Drift: {continuity.drift}",
                f"- Safest handoff: {continuity.next_handoff}",
            ]
        )
        if trace_lines:
            instructions.extend(["", "Recent persisted live trace:"])
            instructions.extend(f"- {line}" for line in trace_lines)
        if checkpoints:
            crash_safe_packets = self._crash_safe_packet_summaries(checkpoints)
            if crash_safe_packets:
                instructions.extend(["", "Crash-safe relay packets:"])
                instructions.extend(crash_safe_packets)
            instructions.extend(
                [
                    "",
                    "Recent checkpoint trail:",
                ]
            )
            for checkpoint in reversed(checkpoints):
                summary = str(checkpoint.get("summary") or "").strip().replace("\n", " ")
                instructions.append(f"- [{checkpoint['kind']}] {summary[:700]}")
        elif mission.get("last_checkpoint"):
            instructions.extend(
                [
                    "",
                    "Last known checkpoint:",
                    str(mission["last_checkpoint"]),
                ]
            )
        elif mission.get("last_commentary"):
            instructions.extend(
                [
                    "",
                    "Last known live commentary:",
                    str(mission["last_commentary"]),
                ]
            )
        return "\n".join(instructions)

    async def _attempt_stale_thread_recovery(
        self,
        mission_id: int,
        mission: dict[str, Any],
        *,
        stale_thread_id: str,
        stale_error: str,
    ) -> bool:
        runtime = await self.manager.get(int(mission["instance_id"]))
        if not runtime.connected:
            return False

        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=4)
        trace_lines = await self._recent_thread_trace_lines(
            instance_id=int(mission["instance_id"]),
            thread_id=stale_thread_id,
        )
        try:
            thread_result = await self.manager.start_thread(
                int(mission["instance_id"]),
                model=str(mission["model"]),
                cwd=mission["cwd"],
                reasoning_effort=mission["reasoning_effort"],
                collaboration_mode=mission["collaboration_mode"],
            )
        except Exception as exc:
            await self.database.update_mission(
                mission_id,
                status="failed",
                phase="failed",
                failure_count=int(mission["failure_count"]) + 1,
                last_error=f"{stale_error} Fresh-thread recovery failed: {exc}",
                in_progress=0,
                last_activity_at=utcnow(),
            )
            await self._publish_snapshot(
                "mission/thread-recovery-failed",
                {
                    "missionId": mission_id,
                    "staleThreadId": stale_thread_id,
                    "error": str(exc),
                },
            )
            return False

        new_thread_id = extract_thread_id(thread_result) or extract_thread_id(
            {"thread": thread_result.get("thread")}
        )
        if new_thread_id is None:
            await self.database.update_mission(
                mission_id,
                status="failed",
                phase="failed",
                failure_count=int(mission["failure_count"]) + 1,
                last_error=(
                    f"{stale_error} Fresh-thread recovery did not return a thread ID."
                ),
                in_progress=0,
                last_activity_at=utcnow(),
            )
            return False

        await self.database.update_mission(
            mission_id,
            thread_id=new_thread_id,
            status="active",
            phase="rehydrating",
            in_progress=0,
            last_turn_id=None,
            current_command=None,
            last_error=None,
            last_activity_at=utcnow(),
        )
        await self.database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id=new_thread_id,
            turn_id=None,
            kind="thread_rebind",
            summary=(
                f"Mission rebound from stale thread {stale_thread_id} to fresh thread "
                f"{new_thread_id}."
            ),
        )
        await self._publish_snapshot(
            "mission/thread-rebound",
            {
                "missionId": mission_id,
                "staleThreadId": stale_thread_id,
                "threadId": new_thread_id,
                "instanceId": int(mission["instance_id"]),
            },
        )
        refreshed = await self.require_mission(mission_id)
        await self._start_turn_with_prompt(
            mission_id,
            refreshed,
            thread_id=new_thread_id,
            prompt=self._build_stale_thread_recovery_prompt(
                refreshed,
                stale_thread_id=stale_thread_id,
                new_thread_id=new_thread_id,
                stale_error=stale_error,
                checkpoints=checkpoints,
                trace_lines=trace_lines,
            ),
            event_type="mission/thread-recovery-started",
            allow_stale_thread_recovery=False,
        )
        return True

    async def _attempt_failover(
        self,
        mission_id: int,
        mission: dict[str, Any],
        *,
        offline_error: str,
    ) -> bool:
        if not bool(mission.get("allow_failover")):
            await self.database.update_mission(
                mission_id,
                status="blocked",
                phase="offline",
                last_error=offline_error,
            )
            return False

        target = await self._pick_failover_target(mission_id, mission)
        if target is None:
            await self.database.update_mission(
                mission_id,
                status="blocked",
                phase="offline",
                last_error=(
                    f"{offline_error} No connected idle failover lane is available for "
                    "mission transplantation."
                ),
            )
            return False

        source_runtime = self.manager.instances.get(int(mission["instance_id"]))
        source_name = (
            source_runtime.name
            if source_runtime is not None
            else f"Instance {mission['instance_id']}"
        )
        checkpoints = await self.database.list_mission_checkpoints(mission_id, limit=4)
        trace_lines = (
            await self._recent_thread_trace_lines(
                instance_id=int(mission["instance_id"]),
                thread_id=str(mission.get("thread_id") or ""),
            )
            if str(mission.get("thread_id") or "")
            else []
        )
        try:
            thread_result = await self.manager.start_thread(
                target.instance_id,
                model=str(mission["model"]),
                cwd=mission["cwd"],
                reasoning_effort=mission["reasoning_effort"],
                collaboration_mode=mission["collaboration_mode"],
            )
        except Exception as exc:
            await self.database.update_mission(
                mission_id,
                status="blocked",
                phase="offline",
                last_error=(f"{offline_error} Failover to {target.name} could not start: {exc}"),
            )
            return False

        thread_id = extract_thread_id(thread_result) or extract_thread_id(
            {"thread": thread_result.get("thread")}
        )
        if thread_id is None:
            await self.database.update_mission(
                mission_id,
                status="blocked",
                phase="offline",
                last_error=(
                    f"{offline_error} Failover to {target.name} did not return a thread ID."
                ),
            )
            return False

        await self.database.update_mission(
            mission_id,
            instance_id=target.instance_id,
            thread_id=thread_id,
            status="active",
            phase="rehydrating",
            in_progress=0,
            last_error=None,
            last_activity_at=utcnow(),
        )
        await self.database.append_mission_checkpoint(
            mission_id=mission_id,
            thread_id=thread_id,
            turn_id=None,
            kind="failover",
            summary=f"Mission transplanted from {source_name} to {target.name}.",
        )
        await self._publish_snapshot(
            "mission/failover-routed",
            {
                "missionId": mission_id,
                "threadId": thread_id,
                "sourceInstanceId": int(mission["instance_id"]),
                "sourceInstanceName": source_name,
                "targetInstanceId": target.instance_id,
                "targetInstanceName": target.name,
            },
        )
        refreshed = await self.require_mission(mission_id)
        await self._start_turn_with_prompt(
            mission_id,
            refreshed,
            thread_id=thread_id,
            prompt=self._build_failover_prompt(
                refreshed,
                source_name=source_name,
                target_name=target.name,
                offline_error=offline_error,
                checkpoints=checkpoints,
                trace_lines=trace_lines,
            ),
            event_type="mission/failover-started",
        )
        return True

    async def _start_turn_with_prompt(
        self,
        mission_id: int,
        mission: dict[str, Any],
        *,
        thread_id: str,
        prompt: str,
        event_type: str,
        reflex: MissionReflexRun | None = None,
        checkpoint_kind: str = "reflex",
        allow_stale_thread_recovery: bool = True,
    ) -> None:
        if reflex is not None:
            await self.database.append_mission_checkpoint(
                mission_id=mission_id,
                thread_id=thread_id,
                turn_id=None,
                kind=checkpoint_kind,
                summary=reflex.title,
            )
        try:
            turn_result = await self.manager.start_turn(
                int(mission["instance_id"]),
                thread_id=thread_id,
                text=prompt,
                cwd=mission["cwd"],
                model=None,
                reasoning_effort=mission["reasoning_effort"],
                collaboration_mode=mission["collaboration_mode"],
            )
        except Exception as exc:
            error_summary = _error_summary(
                exc,
                fallback="Codex runtime failed to start the turn without a detailed error.",
            )
            if allow_stale_thread_recovery and _is_thread_not_found_error(exc):
                recovered = await self._attempt_stale_thread_recovery(
                    mission_id,
                    mission,
                    stale_thread_id=thread_id,
                    stale_error=error_summary,
                )
                if recovered:
                    return
            await self.database.update_mission(
                mission_id,
                status="failed",
                phase="failed",
                failure_count=int(mission["failure_count"]) + 1,
                last_error=error_summary,
                in_progress=0,
                last_activity_at=utcnow(),
            )
            await self.database.append_mission_checkpoint(
                mission_id=mission_id,
                thread_id=thread_id,
                turn_id=None,
                kind="error",
                summary=error_summary,
            )
            await self._publish_snapshot(
                "mission/failed",
                {"missionId": mission_id, "threadId": thread_id, "error": error_summary},
            )
            return

        updates: dict[str, Any] = {
            "status": "active",
            "in_progress": 1,
            "phase": "thinking",
            "turns_started": int(mission["turns_started"]) + 1,
            "last_turn_id": extract_turn_id(turn_result),
            "last_error": None,
            "last_activity_at": utcnow(),
        }
        if reflex is not None:
            updates["last_reflex_kind"] = reflex.kind
            updates["last_reflex_at"] = utcnow()
        await self.database.update_mission(mission_id, **updates)

        payload: dict[str, Any] = {"missionId": mission_id, "threadId": thread_id}
        if reflex is not None:
            payload["kind"] = reflex.kind
            payload["title"] = reflex.title
        await self._publish_snapshot(event_type, payload)

    async def _runner_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                missions = await self.database.list_missions()
                for mission in missions:
                    if mission["status"] in {"active", "blocked", "failed"}:
                        await self._reconcile_mission(int(mission["id"]))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Mission runner loop crashed")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _reconcile_mission(self, mission_id: int, *, force: bool = False) -> None:
        lock = self._locks[mission_id]
        async with lock:
            mission = await self.require_mission(mission_id)
            _preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
                self.database
            )
            allow_failed_recovery = (
                mission["status"] == "failed"
                and bool(mission.get("auto_recover"))
                and bool(mission.get("thread_id"))
            )
            if (
                mission["status"] not in {"active", "blocked"}
                and not allow_failed_recovery
                and not force
            ):
                return

            if str(preferred_executor or "").strip().lower() == "workspace_shell":
                target_cwd = str(mission.get("cwd") or "").strip() or None
                if target_cwd:
                    current_runtime = await self.manager.get(int(mission["instance_id"]))
                    current_cwd = str(current_runtime.cwd or "").strip().lower()
                    if current_runtime.transport != "stdio" or current_cwd != target_cwd.lower():
                        shell_runtime = await self.manager.ensure_workspace_shell_instance(
                            cwd=target_cwd,
                            auto_connect=False,
                        )
                        if shell_runtime.instance_id != int(mission["instance_id"]):
                            await self.database.update_mission(
                                mission_id,
                                instance_id=shell_runtime.instance_id,
                                last_activity_at=utcnow(),
                            )
                            await self._publish_snapshot(
                                "mission/executor-promoted",
                                {
                                    "missionId": mission_id,
                                    "executor": preferred_executor,
                                    "fromInstanceId": int(current_runtime.instance_id),
                                    "toInstanceId": int(shell_runtime.instance_id),
                                },
                            )
                            mission["instance_id"] = shell_runtime.instance_id

            runtime = await self.manager.get(int(mission["instance_id"]))
            if not runtime.connected:
                try:
                    runtime = await self.manager.connect_instance(int(mission["instance_id"]))
                except Exception as exc:
                    if await self._attempt_failover(
                        mission_id,
                        mission,
                        offline_error=f"Instance is offline: {exc}",
                    ):
                        return
                    return
            if not runtime.connected:
                if await self._attempt_failover(
                    mission_id,
                    mission,
                    offline_error="Instance is offline.",
                ):
                    return
                return
            executor_assessment = build_executor_launch_assessment(
                preferred_executor,
                instance=runtime,
                instances=self.manager.instances.values(),
                target_cwd=str(mission.get("cwd") or "").strip() or None,
            )
            if executor_assessment.status == "repair":
                blocker = (
                    f"Executor launch blocked ({executor_label(preferred_executor)}): "
                    f"{executor_assessment.summary}"
                )
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    phase="executor",
                    in_progress=0,
                    current_command=None,
                    last_error=blocker,
                    last_activity_at=utcnow(),
                )
                await self._publish_snapshot(
                    "mission/blocked",
                    {"missionId": mission_id, "reason": blocker},
                )
                return

            last_activity_seconds = _seconds_since(mission.get("last_activity_at"))
            if mission["thread_id"]:
                thread_state = next(
                    (
                        thread
                        for thread in runtime.threads
                        if thread.get("id") == mission["thread_id"]
                    ),
                    None,
                )
                if thread_state is not None:
                    status = thread_state.get("status")
                    thread_status = _thread_status_type(thread_state)
                    if (
                        bool(mission.get("in_progress"))
                        and thread_status != "active"
                        and last_activity_seconds is not None
                        and last_activity_seconds >= self._stale_turn_threshold_seconds()
                    ):
                        await self.database.update_mission(
                            mission_id,
                            in_progress=0,
                            phase=(
                                "ready"
                                if str(mission.get("status") or "") == "active"
                                else mission.get("phase")
                            ),
                            current_command=None,
                        )
                        mission["in_progress"] = 0
                        mission["current_command"] = None
                        if str(mission.get("status") or "") == "active":
                            mission["phase"] = "ready"
                    if (
                        isinstance(status, dict)
                        and status.get("type") == "idle"
                        and mission["in_progress"]
                    ):
                        await self.database.update_mission(mission_id, in_progress=0)
                        mission["in_progress"] = 0
                    if (
                        isinstance(status, dict)
                        and status.get("type") == "active"
                        and not mission["in_progress"]
                    ):
                        await self.database.update_mission(mission_id, in_progress=1)
                        mission["in_progress"] = 1
                    if _is_thread_not_found_error(mission.get("last_error")):
                        heal_updates: dict[str, Any] = {
                            "status": "active",
                            "last_error": None,
                        }
                        if thread_status == "active":
                            heal_updates["phase"] = "thinking"
                            heal_updates["in_progress"] = 1
                        elif thread_status == "idle":
                            heal_updates["phase"] = "ready"
                            heal_updates["in_progress"] = 0
                        await self.database.update_mission(mission_id, **heal_updates)
                        mission.update(heal_updates)
                elif _is_thread_not_found_error(mission.get("last_error")):
                    if await self._attempt_stale_thread_recovery(
                        mission_id,
                        mission,
                        stale_thread_id=str(mission["thread_id"]),
                        stale_error=str(mission.get("last_error") or ""),
                    ):
                        return

            missions_for_instance = [
                candidate
                for candidate in await self.database.list_missions()
                if int(candidate["instance_id"]) == int(mission["instance_id"])
                and int(candidate["id"]) != mission_id
                and (
                    str(candidate["status"]) == "active"
                    or (
                        str(candidate["status"]) == "blocked"
                        and str(candidate.get("phase") or "") != "queued"
                    )
                )
                and bool(candidate["in_progress"])
            ]
            if missions_for_instance:
                queued_reason = f"Queued behind mission: {missions_for_instance[0]['name']}"
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    phase="queued",
                    in_progress=0,
                    current_command=None,
                    last_error=queued_reason,
                )
                return

            pending_requests = [
                request
                for request in runtime.unresolved_requests
                if request.get("thread_id") == mission.get("thread_id")
            ]
            if pending_requests and bool(mission["pause_on_approval"]):
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    phase="approval",
                    last_error=f"Waiting for approval: {pending_requests[0]['method']}",
                )
                return
            blocked_reason = str(mission.get("last_error") or "")
            if mission["status"] == "blocked" and (
                blocked_reason.startswith("Waiting for approval:")
                or blocked_reason.startswith("Queued behind mission:")
            ):
                await self.database.update_mission(
                    mission_id,
                    status="active",
                    phase="ready",
                    last_error=None,
                )
                mission["status"] = "active"
            elif mission["status"] == "blocked":
                await self.database.update_mission(mission_id, status="active", phase="ready")
                mission["status"] = "active"

            if mission["max_turns"] and int(mission["turns_completed"]) >= int(
                mission["max_turns"]
            ):
                await self.database.update_mission(
                    mission_id,
                    status="completed",
                    phase="completed",
                    in_progress=0,
                )
                await self._publish_snapshot("mission/completed", {"missionId": mission_id})
                return

            queued_followers = [
                candidate
                for candidate in await self.database.list_missions()
                if int(candidate["instance_id"]) == int(mission["instance_id"])
                and int(candidate["id"]) != mission_id
                and str(candidate.get("status") or "") == "blocked"
                and str(candidate.get("phase") or "") == "queued"
            ]
            if (
                not force
                and self._should_auto_yield_for_queue(
                    mission,
                    queue_depth=len(queued_followers),
                    last_activity_seconds=last_activity_seconds,
                )
            ):
                await self._yield_for_queue_locked(mission_id, mission)
                return

            if mission["in_progress"] and not force:
                await self._maybe_append_restart_safe_snapshot(
                    mission_id,
                    mission,
                    reason="live_heartbeat",
                )
                await self._maybe_append_continuity_snapshot(
                    mission_id,
                    mission,
                    reason="live_orbit",
                )
                return

            thread_id = mission["thread_id"]
            if thread_id is None:
                thread_result = await self.manager.start_thread(
                    int(mission["instance_id"]),
                    model=str(mission["model"]),
                    cwd=mission["cwd"],
                    reasoning_effort=mission["reasoning_effort"],
                    collaboration_mode=mission["collaboration_mode"],
                )
                thread_id = extract_thread_id(thread_result) or extract_thread_id(
                    {"thread": thread_result.get("thread")}
                )
                if thread_id is None:
                    raise RuntimeError("Unable to resolve thread ID for mission.")
                await self.database.update_mission(
                    mission_id,
                    thread_id=thread_id,
                    phase="ready",
                    last_activity_at=utcnow(),
                )
                mission["thread_id"] = thread_id

            reflex = None if force else self._build_governor_reflex(mission)
            if reflex is not None:
                checkpoint_kind = (
                    "recovery" if reflex.kind == "recovery_triangle" else "reflex_auto"
                )
                event_type = (
                    "mission/auto-recovered"
                    if reflex.kind == "recovery_triangle"
                    else "mission/auto-reflex-fired"
                )
                await self._start_turn_with_prompt(
                    mission_id,
                    mission,
                    thread_id=thread_id,
                    prompt=reflex.prompt,
                    event_type=event_type,
                    reflex=reflex,
                    checkpoint_kind=checkpoint_kind,
                )
                return

            prompt = await self._build_turn_prompt(mission)
            await self._start_turn_with_prompt(
                mission_id,
                mission,
                thread_id=thread_id,
                prompt=prompt,
                event_type="mission/cycle-started",
            )

    async def _build_view(self, mission: dict[str, Any]) -> MissionView:
        project_label = None
        project: dict[str, Any] | None = None
        if mission["project_id"] is not None:
            project = await self.database.get_project(int(mission["project_id"]))
            if project is not None:
                project_label = str(project["label"])
        task: dict[str, Any] | None = None
        if mission.get("task_blueprint_id") is not None:
            task = await self.database.get_task_blueprint(int(mission["task_blueprint_id"]))
        runtime = self.manager.instances.get(int(mission["instance_id"]))
        checkpoints = [
            MissionCheckpointView.model_validate(item)
            for item in await self.database.list_mission_checkpoints(int(mission["id"]), limit=5)
        ]
        scope = build_scope_assessment(mission, checkpoints=checkpoints)
        live_telemetry = await self._build_live_telemetry(mission, runtime=runtime)
        trace_lines: list[str] = []
        thread_id = str(mission.get("thread_id") or "").strip()
        if thread_id and (
            mission.get("last_commentary")
            or mission.get("current_command")
            or str(mission.get("status") or "") == "active"
        ):
            trace_lines = await self._recent_thread_trace_lines(
                instance_id=int(mission["instance_id"]),
                thread_id=thread_id,
                limit=24,
            )
        commentary_summary = _derive_commentary_summary(mission, trace_lines=trace_lines)
        delegation_brief = _build_delegation_brief(
            mission,
            scope=scope,
            live_telemetry=live_telemetry,
        )
        toolsets = self._resolve_toolsets(mission, project=project, task=task)
        tool_policy = build_hermes_tool_policy(toolsets, setup_mode="local")
        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        payload = {
            **mission,
            "instance_name": runtime.name if runtime is not None else None,
            "project_label": project_label,
            "commentary_summary": commentary_summary,
            "checkpoints": checkpoints,
            "suggested_action": self._suggested_action(mission, scope),
            "charter_summary": scope.charter_summary,
            "charter_focus_terms": list(scope.focus_terms),
            "objective_gravity": scope.objective_gravity,
            "scope_drift_level": scope.drift_level,
            "scope_drift_summary": scope.drift_summary,
            "live_telemetry": live_telemetry,
            "delegation_brief": delegation_brief,
            "toolsets": toolsets,
            "tool_policy": tool_policy,
            "preferred_memory_provider": preferred_memory_provider,
            "preferred_memory_provider_label": memory_provider_label(
                preferred_memory_provider
            ),
            "preferred_executor": preferred_executor,
            "preferred_executor_label": executor_label(preferred_executor),
            "runtime_profile_summary": build_runtime_profile_summary(
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
        }
        return MissionView.model_validate(payload)

    async def _build_live_telemetry(
        self,
        mission: dict[str, Any],
        *,
        runtime: Any | None,
    ) -> MissionLiveTelemetryView:
        thread_id = str(mission.get("thread_id") or "").strip()
        if not thread_id:
            return MissionLiveTelemetryView(summary="Thread not created yet.")

        thread_status: str | None = None
        if runtime is not None:
            for thread in getattr(runtime, "threads", []):
                if str(thread.get("id") or "") == thread_id:
                    thread_status = _thread_status_type(thread)
                    break

        metrics = await self.database.get_thread_event_metrics(
            instance_id=int(mission["instance_id"]),
            thread_id=thread_id,
        )
        last_event_at = str(metrics.get("last_event_at") or "").strip() or None
        last_event_age_seconds = _seconds_since(last_event_at)
        recent_event_count_30s = int(metrics.get("recent_event_count_30s") or 0)
        recent_event_count_5m = int(metrics.get("recent_event_count_5m") or 0)
        recent_output_delta_count_30s = int(metrics.get("recent_output_delta_count_30s") or 0)
        recent_turn_activity_count_30s = int(
            metrics.get("recent_turn_activity_count_30s") or 0
        )
        in_progress = bool(mission.get("in_progress"))
        streaming = bool(
            recent_output_delta_count_30s > 0
            or (
                in_progress
                and thread_status == "active"
                and recent_turn_activity_count_30s > 0
                and (last_event_age_seconds is None or last_event_age_seconds <= 30)
            )
        )
        token_rollup_pending = bool(streaming and in_progress)
        summary = _thread_live_summary(
            streaming=streaming,
            in_progress=in_progress,
            last_event_age_seconds=last_event_age_seconds,
            recent_event_count_30s=recent_event_count_30s,
            recent_output_delta_count_30s=recent_output_delta_count_30s,
        )
        return MissionLiveTelemetryView(
            streaming=streaming,
            thread_status=thread_status,
            last_thread_event_at=last_event_at,
            last_thread_event_age_seconds=last_event_age_seconds,
            recent_event_count_30s=recent_event_count_30s,
            recent_event_count_5m=recent_event_count_5m,
            recent_output_delta_count_30s=recent_output_delta_count_30s,
            recent_turn_activity_count_30s=recent_turn_activity_count_30s,
            token_rollup_pending=token_rollup_pending,
            summary=summary,
        )

    async def _build_turn_prompt(self, mission: dict[str, Any]) -> str:
        continuity = build_continuity_packet(mission, instance_connected=True)
        scope = build_scope_assessment(mission)
        project_label: str | None = None
        project_path: str | None = None
        explicit_pins: list[SkillPinView] = []
        task: dict[str, Any] | None = None
        if mission.get("task_blueprint_id") is not None:
            task = await self.database.get_task_blueprint(int(mission["task_blueprint_id"]))
        scoped_integrations = [
            integration
            for integration in await self.database.list_integrations()
            if bool(integration.get("enabled", True))
            and integration.get("project_id") in {None, mission.get("project_id")}
        ]
        project: dict[str, Any] | None = None
        if mission["project_id"] is not None:
            project = await self.database.get_project(int(mission["project_id"]))
            if project is not None:
                project_label = str(project["label"])
                project_path = str(project["path"])
            explicit_pins = [
                SkillPinView.model_validate(item)
                for item in await self.database.list_skill_pins()
                if int(item["project_id"]) == int(mission["project_id"])
            ]
        toolsets = self._resolve_toolsets(mission, project=project, task=task)
        tool_policy = build_hermes_tool_policy(toolsets, setup_mode="local")
        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        skill_profile = resolve_skill_profile(
            str(mission.get("objective") or ""),
            explicit_pins=explicit_pins,
            project_label=project_label,
            project_path=project_path,
            toolsets=toolsets,
        )
        delegation_brief = _build_delegation_brief(
            mission,
            scope=scope,
        )
        instructions = [
            "You are running inside an OpenZues autonomous mission.",
            f"Mission: {mission['name']}",
            "",
            "Primary objective:",
            str(mission["objective"]),
            "",
            "Mission charter:",
            scope.charter_summary,
            (
                "Objective gravity guardrail: if the current branch stops clearly serving this "
                "charter, stop broadening scope and re-anchor before proceeding."
            ),
            "",
            "Execution rules:",
            "- Continue from the current thread state. Do not restart finished work.",
            "- Pick the highest-leverage next step and carry it through to a verified result.",
            "- Inspect the workspace before making non-trivial changes.",
            "- Keep working until you either complete meaningful progress or hit a real blocker.",
        ]
        instructions.extend(["", *_delegation_instruction_lines(delegation_brief)])
        if bool(mission["run_verification"]):
            instructions.append(
                "- Run relevant tests, builds, or browser checks after meaningful changes."
            )
        contract_lines = _contract_seam_instruction_lines(mission)
        if contract_lines:
            instructions.extend(["", *contract_lines])
        if bool(mission["auto_commit"]):
            instructions.append(
                "- Create focused git commits for verified milestones when appropriate."
            )
        if bool(mission["pause_on_approval"]):
            instructions.append(
                "- If you hit an approval, missing credential, or irreversible action,"
                " say exactly what is needed and stop there."
            )
        if mission["cwd"]:
            instructions.append(
                f"- Treat `{mission['cwd']}` as the primary workspace unless the thread"
                " already established a better target."
            )
        skill_lines = build_prompt_skill_lines(skill_profile.skills)
        if skill_lines:
            instructions.extend(["", *skill_lines])
        tool_policy_lines = build_hermes_tool_policy_lines(tool_policy)
        if tool_policy_lines:
            instructions.extend(["", *tool_policy_lines])
        resolved_instance_name = str(mission.get("instance_name") or "").strip() or None
        runtime_profile_row = await self.database.get_hermes_runtime_profile()
        runtime_profile = (
            runtime_profile_row.get("profile")
            if isinstance(runtime_profile_row, dict)
            and isinstance(runtime_profile_row.get("profile"), dict)
            else None
        )
        executor_lines = build_executor_profile_lines(
            preferred_executor,
            instance_name=resolved_instance_name,
            cwd=project_path or mission.get("cwd"),
            runtime_profile=runtime_profile,
        )
        memory_provider_lines = build_memory_provider_lines(
            preferred_memory_provider,
            integrations=scoped_integrations,
            toolsets=toolsets,
        )
        instructions.extend(
            [
                "",
                build_runtime_profile_summary(
                    preferred_memory_provider=preferred_memory_provider,
                    preferred_executor=preferred_executor,
                ),
                *executor_lines,
                *memory_provider_lines,
            ]
        )
        memory_protocol_lines = build_mempalace_protocol_lines(scoped_integrations)
        if memory_protocol_lines:
            instructions.extend(["", *memory_protocol_lines])
        ecc_workspace_lines = build_ecc_workspace_lines(project_path or mission.get("cwd"))
        if ecc_workspace_lines:
            instructions.extend(["", *ecc_workspace_lines])
        instructions.extend(
            [
                "",
                f"Autonomous cycle: {int(mission['turns_started']) + 1}",
                f"Continuity relay: {continuity.state} ({continuity.score}/100)",
                f"Objective gravity: {scope.objective_gravity}/100 ({scope.drift_level})",
                f"Anchor: {continuity.anchor}",
                f"Watch drift: {continuity.drift}",
                f"Safest next handoff: {continuity.next_handoff}",
                "End this turn with a concise operator handoff:"
                " completed, verified, next step, blockers.",
            ]
        )
        if mission.get("last_error"):
            instructions.extend(
                [
                    "",
                    "Recent mission issue to address first if still relevant:"
                    f" {mission['last_error']}",
                ]
            )
        return "\n".join(instructions)

    async def _publish_snapshot(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"type": event_type, **payload, "createdAt": utcnow()}
        await self.hub.publish(event)
        for listener in self._event_listeners:
            try:
                result = listener(event_type, event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Mission event listener failed for %s", event_type)

    def _suggested_action(self, mission: dict[str, Any], scope: ScopeAssessment) -> str:
        last_error = str(mission.get("last_error") or "")
        if str(mission.get("status")) == "blocked":
            if last_error.startswith("Waiting for approval:"):
                return (
                    "Zues will auto-approve safe read-only requests. Review only if this gate "
                    "looks risky, write-capable, or irreversible."
                )
            if last_error.startswith("Queued behind mission:"):
                return "Finish or pause the earlier mission, then tap run now to continue this one."
            if last_error.startswith("Instance is offline"):
                if bool(mission.get("allow_failover")):
                    return (
                        "Reconnect the original lane or keep another connected idle lane available "
                        "so OpenZues can transplant this mission."
                    )
                return "Reconnect the instance, then run the mission again."
            return "Inspect the blocker, then resume the mission when the path is clear."
        if str(mission.get("status")) == "failed":
            if _is_thread_not_found_error(last_error):
                return (
                    "The previous thread went stale. OpenZues can reopen this mission on a fresh "
                    "thread and rebuild context from the last checkpoint."
                )
            return "Inspect the failure checkpoint, adjust the mission, and run it again."
        if str(mission.get("status")) == "paused":
            return "Resume the mission when you want Codex to continue."
        if scope.drift_level in {"drifting", "critical"}:
            if bool(mission.get("in_progress")):
                return (
                    "Let the current turn finish, then force a charter realignment checkpoint "
                    "before more work fans out."
                )
            return scope.recommended_action
        if bool(mission.get("in_progress")):
            if mission.get("phase") == "executing":
                return "Let the current command finish unless it is clearly stuck."
            return "Let Codex finish the active turn and watch for the next checkpoint."
        if not mission.get("thread_id"):
            return "Run the mission to create a fresh thread and start the first cycle."
        return "Mission is ready for another autonomous cycle."
