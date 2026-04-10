from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import MissionCheckpointView, MissionCreate, MissionView
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager

logger = logging.getLogger(__name__)


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
        runtime = await self.manager.get(payload.instance_id)
        cwd = payload.cwd or (project["path"] if project is not None else runtime.cwd)
        status = "active" if payload.start_immediately else "paused"
        mission_id = await self.database.create_mission(
            name=payload.name,
            objective=payload.objective,
            status=status,
            instance_id=payload.instance_id,
            project_id=payload.project_id,
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
        )
        await self._publish_snapshot("mission/created", {"missionId": mission_id})
        if payload.start_immediately:
            asyncio.create_task(self.run_now(mission_id))
        return await self.get_view(mission_id)

    async def pause(self, mission_id: int) -> MissionView:
        await self.database.update_mission(mission_id, status="paused")
        await self._publish_snapshot("mission/paused", {"missionId": mission_id})
        return await self.get_view(mission_id)

    async def resume(self, mission_id: int) -> MissionView:
        await self.database.update_mission(mission_id, status="active", last_error=None)
        await self._publish_snapshot("mission/resumed", {"missionId": mission_id})
        await self.run_now(mission_id)
        return await self.get_view(mission_id)

    async def complete(self, mission_id: int) -> MissionView:
        await self.database.update_mission(mission_id, status="completed", in_progress=0)
        await self._publish_snapshot("mission/completed", {"missionId": mission_id})
        return await self.get_view(mission_id)

    async def delete(self, mission_id: int) -> None:
        await self.database.delete_mission(mission_id)
        await self._publish_snapshot("mission/deleted", {"missionId": mission_id})

    async def run_now(self, mission_id: int) -> MissionView:
        mission = await self.require_mission(mission_id)
        if mission["status"] == "completed":
            return await self.get_view(mission_id)
        if mission["status"] in {"paused", "failed"}:
            await self.database.update_mission(mission_id, status="active", last_error=None)
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

        if method == "turn/started":
            updates["in_progress"] = 1
            updates["last_turn_id"] = extract_turn_id(params)
            if mission["status"] == "active":
                updates["last_error"] = None
        elif method == "turn/completed":
            turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
            updates["in_progress"] = 0
            updates["last_turn_id"] = extract_turn_id(params) or mission.get("last_turn_id")
            if turn.get("error"):
                updates["status"] = "failed"
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
                if mission["status"] == "active":
                    updates["last_error"] = None
                    max_turns = mission.get("max_turns")
                    if max_turns is None or next_completed < int(max_turns):
                        asyncio.create_task(self.run_now(int(mission["id"])))
        elif method == "thread/status/changed":
            status = params.get("status") if isinstance(params.get("status"), dict) else {}
            if status.get("type") == "idle":
                updates["in_progress"] = 0
            if status.get("type") == "active":
                updates["in_progress"] = 1
        elif method == "item/completed":
            item = params.get("item") if isinstance(params.get("item"), dict) else {}
            if item.get("type") == "agentMessage" and item.get("phase") == "final_answer":
                text = str(item.get("text") or "").strip()
                if text:
                    summary = text[:3000]
                    updates["last_checkpoint"] = summary
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

    async def handle_server_request(self, instance_id: int, request: dict[str, Any]) -> None:
        thread_id = request.get("threadId")
        if not isinstance(thread_id, str):
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

    async def _runner_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                missions = await self.database.list_missions()
                for mission in missions:
                    if mission["status"] in {"active", "blocked"}:
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
            if mission["status"] not in {"active", "blocked"} and not force:
                return

            runtime = await self.manager.get(int(mission["instance_id"]))
            if not runtime.connected:
                try:
                    runtime = await self.manager.connect_instance(int(mission["instance_id"]))
                except Exception as exc:
                    await self.database.update_mission(
                        mission_id,
                        status="blocked",
                        last_error=f"Instance is offline: {exc}",
                    )
                    return
            if not runtime.connected:
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    last_error="Instance is offline.",
                )
                return

            missions_for_instance = [
                candidate
                for candidate in await self.database.list_missions()
                if int(candidate["instance_id"]) == int(mission["instance_id"])
                and int(candidate["id"]) != mission_id
                and bool(candidate["in_progress"])
            ]
            if missions_for_instance:
                queued_reason = f"Queued behind mission: {missions_for_instance[0]['name']}"
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    last_error=queued_reason,
                )
                return

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

            pending_requests = [
                request
                for request in runtime.unresolved_requests
                if request.get("thread_id") == mission.get("thread_id")
            ]
            if pending_requests and bool(mission["pause_on_approval"]):
                await self.database.update_mission(
                    mission_id,
                    status="blocked",
                    last_error=f"Waiting for approval: {pending_requests[0]['method']}",
                )
                return
            blocked_reason = str(mission.get("last_error") or "")
            if mission["status"] == "blocked" and (
                blocked_reason.startswith("Waiting for approval:")
                or blocked_reason.startswith("Queued behind mission:")
            ):
                await self.database.update_mission(mission_id, status="active", last_error=None)
                mission["status"] = "active"
            elif mission["status"] == "blocked":
                await self.database.update_mission(mission_id, status="active")
                mission["status"] = "active"

            if (
                mission["max_turns"]
                and int(mission["turns_completed"]) >= int(mission["max_turns"])
            ):
                await self.database.update_mission(mission_id, status="completed", in_progress=0)
                await self._publish_snapshot("mission/completed", {"missionId": mission_id})
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
                    last_activity_at=utcnow(),
                )
                mission["thread_id"] = thread_id

            prompt = self._build_turn_prompt(mission)
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
                await self.database.update_mission(
                    mission_id,
                    status="failed",
                    failure_count=int(mission["failure_count"]) + 1,
                    last_error=str(exc),
                    in_progress=0,
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

            await self.database.update_mission(
                mission_id,
                status="active",
                in_progress=1,
                turns_started=int(mission["turns_started"]) + 1,
                last_turn_id=extract_turn_id(turn_result),
                last_error=None,
                last_activity_at=utcnow(),
            )
            await self._publish_snapshot(
                "mission/cycle-started",
                {"missionId": mission_id, "threadId": thread_id},
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
        }
        return MissionView.model_validate(payload)

    def _build_turn_prompt(self, mission: dict[str, Any]) -> str:
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
        await self.hub.publish({"type": event_type, **payload, "createdAt": utcnow()})
