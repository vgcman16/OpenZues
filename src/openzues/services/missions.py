from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import MissionCheckpointView, MissionCreate, MissionReflexRun, MissionView
from openzues.services.continuity import build_continuity_packet
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager

logger = logging.getLogger(__name__)

STALE_TURN_SECONDS = 8 * 60
HOT_MISSION_TOKEN_THRESHOLD = 60_000


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


def _thread_status_type(thread_state: dict[str, Any] | None) -> str | None:
    if not isinstance(thread_state, dict):
        return None
    status = thread_state.get("status")
    if isinstance(status, dict) and isinstance(status.get("type"), str):
        return str(status["type"])
    return None


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

    async def create(self, payload: MissionCreate) -> MissionView:
        await self.manager.get(payload.instance_id)
        project = (
            await self.database.get_project(payload.project_id)
            if payload.project_id is not None
            else None
        )
        if payload.project_id is not None and project is None:
            raise ValueError(f"Unknown project {payload.project_id}")
        if payload.task_blueprint_id is not None:
            task = await self.database.get_task_blueprint(payload.task_blueprint_id)
            if task is None:
                raise ValueError(f"Unknown task blueprint {payload.task_blueprint_id}")
        runtime = await self.manager.get(payload.instance_id)
        cwd = payload.cwd or (project["path"] if project is not None else runtime.cwd)
        status = "active" if payload.start_immediately else "paused"
        mission_id = await self.database.create_mission(
            name=payload.name,
            objective=payload.objective,
            status=status,
            instance_id=payload.instance_id,
            project_id=payload.project_id,
            task_blueprint_id=payload.task_blueprint_id,
            thread_id=payload.thread_id,
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
                updates["status"] = "failed"
                updates["phase"] = "failed"
                updates["failure_count"] = int(mission["failure_count"]) + 1
                updates["last_error"] = str(turn["error"])
                await self.database.append_mission_checkpoint(
                    mission_id=int(mission["id"]),
                    thread_id=thread_id,
                    turn_id=extract_turn_id(params),
                    kind="error",
                    summary=str(turn["error"]),
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
                    await self.database.append_mission_checkpoint(
                        mission_id=int(mission["id"]),
                        thread_id=thread_id,
                        turn_id=extract_turn_id(params),
                        kind="final_answer",
                        summary=summary,
                    )

        await self.database.update_mission(int(mission["id"]), **updates)
        await self._publish_snapshot(
            "mission/event",
            {"missionId": int(mission["id"]), "method": method, "threadId": thread_id},
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

    def _hot_token_threshold(self) -> int:
        return HOT_MISSION_TOKEN_THRESHOLD

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
        token_hot = int(mission.get("total_tokens") or 0) >= self._hot_token_threshold()
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
                f"Auto-yielded the lane after {int(mission.get('total_tokens') or 0):,} tokens "
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

    def _build_governor_reflex(self, mission: dict[str, Any]) -> MissionReflexRun | None:
        if not self._reflex_ready(mission):
            return None

        last_checkpoint = bool(mission.get("last_checkpoint"))
        last_activity_seconds = _seconds_since(mission.get("last_activity_at"))
        status = str(mission.get("status") or "")

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

        if int(mission.get("total_tokens") or 0) >= 40000 and not last_checkpoint:
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

    def _build_failover_prompt(
        self,
        mission: dict[str, Any],
        *,
        source_name: str,
        target_name: str,
        offline_error: str,
        checkpoints: list[dict[str, Any]],
    ) -> str:
        continuity = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=checkpoints,
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
        if bool(mission.get("use_builtin_agents")):
            instructions.append(
                "- Use built-in agents for bounded parallel subtasks once "
                "you have re-established context."
            )
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
        if checkpoints:
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
    ) -> str:
        continuity = build_continuity_packet(
            mission,
            instance_connected=True,
            checkpoints=checkpoints,
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
        if bool(mission.get("use_builtin_agents")):
            instructions.append(
                "- Use built-in agents only after you have rebuilt enough local context to "
                "delegate safely."
            )
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
        if checkpoints:
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
            if allow_stale_thread_recovery and _is_thread_not_found_error(exc):
                recovered = await self._attempt_stale_thread_recovery(
                    mission_id,
                    mission,
                    stale_thread_id=thread_id,
                    stale_error=str(exc),
                )
                if recovered:
                    return
            await self.database.update_mission(
                mission_id,
                status="failed",
                phase="failed",
                failure_count=int(mission["failure_count"]) + 1,
                last_error=str(exc),
                in_progress=0,
                last_activity_at=utcnow(),
            )
            await self.database.append_mission_checkpoint(
                mission_id=mission_id,
                thread_id=thread_id,
                turn_id=None,
                kind="error",
                summary=str(exc),
            )
            await self._publish_snapshot(
                "mission/failed",
                {"missionId": mission_id, "threadId": thread_id, "error": str(exc)},
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
                and str(candidate["status"]) in {"active", "blocked"}
                and bool(candidate["in_progress"])
            ]
            if missions_for_instance:
                queued_reason = f"Queued behind mission: {missions_for_instance[0]['name']}"
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    phase="queued",
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

            prompt = self._build_turn_prompt(mission)
            await self._start_turn_with_prompt(
                mission_id,
                mission,
                thread_id=thread_id,
                prompt=prompt,
                event_type="mission/cycle-started",
            )

    async def _build_view(self, mission: dict[str, Any]) -> MissionView:
        project_label = None
        if mission["project_id"] is not None:
            project = await self.database.get_project(int(mission["project_id"]))
            if project is not None:
                project_label = str(project["label"])
        runtime = self.manager.instances.get(int(mission["instance_id"]))
        checkpoints = [
            MissionCheckpointView.model_validate(item)
            for item in await self.database.list_mission_checkpoints(int(mission["id"]), limit=5)
        ]
        payload = {
            **mission,
            "instance_name": runtime.name if runtime is not None else None,
            "project_label": project_label,
            "checkpoints": checkpoints,
            "suggested_action": self._suggested_action(mission),
        }
        return MissionView.model_validate(payload)

    def _build_turn_prompt(self, mission: dict[str, Any]) -> str:
        continuity = build_continuity_packet(mission, instance_connected=True)
        instructions = [
            "You are running inside an OpenZues autonomous mission.",
            f"Mission: {mission['name']}",
            "",
            "Primary objective:",
            str(mission["objective"]),
            "",
            "Execution rules:",
            "- Continue from the current thread state. Do not restart finished work.",
            "- Pick the highest-leverage next step and carry it through to a verified result.",
            "- Inspect the workspace before making non-trivial changes.",
            "- Keep working until you either complete meaningful progress or hit a real blocker.",
        ]
        if bool(mission["use_builtin_agents"]):
            instructions.append(
                "- Use built-in agents or delegation when parallel subtasks have clear ownership."
            )
        if bool(mission["run_verification"]):
            instructions.append(
                "- Run relevant tests, builds, or browser checks after meaningful changes."
            )
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
        instructions.extend(
            [
                "",
                f"Autonomous cycle: {int(mission['turns_started']) + 1}",
                f"Continuity relay: {continuity.state} ({continuity.score}/100)",
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

    def _suggested_action(self, mission: dict[str, Any]) -> str:
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
        if bool(mission.get("in_progress")):
            if mission.get("phase") == "executing":
                return "Let the current command finish unless it is clearly stuck."
            return "Let Codex finish the active turn and watch for the next checkpoint."
        if not mission.get("thread_id"):
            return "Run the mission to create a fresh thread and start the first cycle."
        return "Mission is ready for another autonomous cycle."
