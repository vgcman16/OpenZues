from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openzues.database import Database, utcnow
from openzues.schemas import (
    DashboardOpsMeshView,
    DashboardSkillbookView,
    DashboardTaskInboxView,
    DashboardTaskView,
    InstanceView,
    IntegrationCreate,
    IntegrationView,
    LaneSnapshotView,
    MissionCreate,
    MissionDraftView,
    MissionView,
    NotificationRouteCreate,
    NotificationRouteView,
    ProjectView,
    SkillPinCreate,
    SkillPinView,
    TaskBlueprintCreate,
    TaskBlueprintView,
    TaskStatus,
)
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService

logger = logging.getLogger(__name__)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _mask_secret(value: str | None) -> tuple[bool, str | None]:
    if not value:
        return False, None
    if len(value) <= 4:
        return True, "••••"
    return True, f"••••{value[-4:]}"


def _format_cadence(cadence_minutes: int | None) -> str:
    if cadence_minutes is None:
        return "Manual only"
    if cadence_minutes % 60 == 0:
        hours = cadence_minutes // 60
        return f"Every {hours}h"
    return f"Every {cadence_minutes}m"


def _next_run_at(task: TaskBlueprintView) -> str | None:
    if task.cadence_minutes is None or not task.enabled:
        return None
    last = _parse_timestamp(task.last_launched_at)
    if last is None:
        return utcnow()
    return (last + timedelta(minutes=task.cadence_minutes)).isoformat()


def _matches_event(pattern: str, event_type: str) -> bool:
    if pattern.endswith("*"):
        return event_type.startswith(pattern[:-1])
    return event_type == pattern


def _serialize_task(row: dict[str, Any]) -> TaskBlueprintView:
    return TaskBlueprintView.model_validate(row)


def _serialize_route(row: dict[str, Any]) -> NotificationRouteView:
    has_secret, secret_preview = _mask_secret(str(row.get("secret_token") or ""))
    return NotificationRouteView.model_validate(
        {
            **row,
            "has_secret": has_secret,
            "secret_preview": secret_preview,
        }
    )


def _serialize_integration(row: dict[str, Any]) -> IntegrationView:
    has_secret, secret_preview = _mask_secret(str(row.get("secret_value") or ""))
    return IntegrationView.model_validate(
        {
            **row,
            "has_secret": has_secret,
            "secret_preview": secret_preview,
        }
    )


def _serialize_skill_pin(row: dict[str, Any]) -> SkillPinView:
    return SkillPinView.model_validate(row)


def _build_lane_snapshot_view(
    row: dict[str, Any],
    instance_names: dict[int, str],
) -> LaneSnapshotView:
    summary = row.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    return LaneSnapshotView.model_validate(
        {
            "id": row["id"],
            "instance_id": row["instance_id"],
            "instance_name": instance_names.get(int(row["instance_id"])),
            "snapshot_kind": row["snapshot_kind"],
            "connected": bool(summary.get("connected")),
            "transport": summary.get("transport"),
            "model_count": int(summary.get("model_count") or 0),
            "skill_count": int(summary.get("skill_count") or 0),
            "thread_count": int(summary.get("thread_count") or 0),
            "note": summary.get("note"),
            "created_at": row["created_at"],
        }
    )


def _task_status(
    task: TaskBlueprintView,
    latest_mission: MissionView | None,
) -> TaskStatus:
    if not task.enabled:
        return "disabled"
    if latest_mission is not None:
        if latest_mission.status == "active":
            return "running"
        if latest_mission.status in {"blocked", "failed"}:
            return "attention"
        if latest_mission.status == "completed":
            return "completed"
    if task.cadence_minutes is not None:
        next_run = _parse_timestamp(_next_run_at(task))
        if next_run is not None and next_run <= datetime.now(UTC):
            return "due"
    return "idle"


def _task_result_summary(task: TaskBlueprintView, latest_mission: MissionView | None) -> str | None:
    if latest_mission is not None:
        if latest_mission.last_checkpoint:
            return latest_mission.last_checkpoint[:240]
        if latest_mission.last_error:
            return latest_mission.last_error[:240]
    return task.last_result_summary


def _summarize_objective(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:160] + ("..." if len(cleaned) > 160 else "")


def _build_task_objective(
    task: TaskBlueprintView,
    *,
    skill_pins: list[SkillPinView],
    integrations: list[IntegrationView],
) -> str:
    sections = [task.objective_template]
    if skill_pins:
        sections.extend(
            [
                "",
                "Project skillbook:",
                *[
                    f"- {skill.name}: {skill.prompt_hint}"
                    + (f" Source: {skill.source}." if skill.source else "")
                    for skill in skill_pins
                    if skill.enabled
                ],
            ]
        )
    if integrations:
        sections.extend(
            [
                "",
                "Known integration inventory:",
                *[
                    f"- {integration.name} ({integration.kind})"
                    + (f" at {integration.base_url}" if integration.base_url else "")
                    + (
                        f". Notes: {integration.notes}"
                        if integration.notes
                        else ". Credentials are managed by the operator."
                    )
                    for integration in integrations
                    if integration.enabled
                ],
                "- If a credential is required, ask for the exact operator action instead "
                "of inventing access.",
            ]
        )
    return "\n".join(sections)


def build_ops_mesh(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    task_blueprints: list[TaskBlueprintView],
    skill_pins: list[SkillPinView],
    integrations: list[IntegrationView],
    notification_routes: list[NotificationRouteView],
    lane_snapshots: list[LaneSnapshotView],
) -> DashboardOpsMeshView:
    project_by_id = {project.id: project for project in projects}
    instance_by_id = {instance.id: instance for instance in instances}
    missions_by_task: dict[int, list[MissionView]] = {}
    for mission in missions:
        if mission.task_blueprint_id is not None:
            missions_by_task.setdefault(mission.task_blueprint_id, []).append(mission)

    skills_by_project: dict[int, list[SkillPinView]] = {}
    for skill in skill_pins:
        skills_by_project.setdefault(skill.project_id, []).append(skill)

    integrations_by_project: dict[int | None, list[IntegrationView]] = {}
    for integration in integrations:
        integrations_by_project.setdefault(integration.project_id, []).append(integration)

    tasks: list[DashboardTaskView] = []
    for task in task_blueprints:
        related_missions = sorted(
            missions_by_task.get(task.id, []),
            key=lambda mission: mission.updated_at,
            reverse=True,
        )
        latest_mission = related_missions[0] if related_missions else None
        project = project_by_id.get(task.project_id) if task.project_id is not None else None
        instance = instance_by_id.get(task.instance_id) if task.instance_id is not None else None
        scoped_skills = skills_by_project.get(task.project_id or -1, [])
        scoped_integrations = [
            *integrations_by_project.get(None, []),
            *integrations_by_project.get(task.project_id, []),
        ]
        instance_id = task.instance_id
        if instance_id is None:
            connected = next((item.id for item in instances if item.connected), None)
            instance_id = connected or (instances[0].id if instances else None)
        if instance_id is None:
            continue

        draft = MissionDraftView(
            name=task.name,
            objective=_build_task_objective(
                task,
                skill_pins=scoped_skills,
                integrations=scoped_integrations,
            ),
            instance_id=instance_id,
            project_id=task.project_id,
            task_blueprint_id=task.id,
            cwd=task.cwd or (project.path if project is not None else None),
            thread_id=None,
            model=task.model,
            reasoning_effort=task.reasoning_effort,
            collaboration_mode=task.collaboration_mode,
            max_turns=task.max_turns,
            use_builtin_agents=task.use_builtin_agents,
            run_verification=task.run_verification,
            auto_commit=task.auto_commit,
            pause_on_approval=task.pause_on_approval,
            allow_auto_reflexes=task.allow_auto_reflexes,
            auto_recover=task.auto_recover,
            auto_recover_limit=task.auto_recover_limit,
            reflex_cooldown_seconds=task.reflex_cooldown_seconds,
            allow_failover=task.allow_failover,
            start_immediately=True,
        )
        tasks.append(
            DashboardTaskView(
                id=task.id,
                name=task.name,
                summary=task.summary or _summarize_objective(task.objective_template),
                status=_task_status(task, latest_mission),
                cadence_label=_format_cadence(task.cadence_minutes),
                next_run_at=_next_run_at(task),
                project_label=project.label if project is not None else None,
                instance_name=instance.name if instance is not None else None,
                mission_id=latest_mission.id if latest_mission is not None else None,
                mission_name=latest_mission.name if latest_mission is not None else None,
                skill_count=len([skill for skill in scoped_skills if skill.enabled]),
                integration_count=len(
                    [integration for integration in scoped_integrations if integration.enabled]
                ),
                last_result_summary=_task_result_summary(task, latest_mission),
                mission_draft=draft,
            )
        )

    rank = {
        "attention": 0,
        "due": 1,
        "running": 2,
        "completed": 3,
        "idle": 4,
        "disabled": 5,
    }
    tasks = sorted(tasks, key=lambda task: (rank[task.status], task.name.lower()))

    attention = sum(task.status == "attention" for task in tasks)
    due = sum(task.status == "due" for task in tasks)
    running = sum(task.status == "running" for task in tasks)
    if attention:
        headline = "Ops mesh needs attention"
        summary = (
            f"{attention} scheduled workflow(s) are blocked or degraded. "
            "Clear those first so the always-on layer stays trustworthy."
        )
    elif due or running:
        headline = "Ops mesh is active"
        summary = (
            f"{running} workflow(s) are live and {due} more are ready to launch."
        )
    else:
        headline = "Ops mesh is ready"
        summary = (
            "Recurring workflows, notifications, skillbooks, and lane history are "
            "configured and waiting for the next run."
        )

    task_headline = "Task inbox is ready" if tasks else "No task blueprints yet"
    task_summary = (
        "Recurring task blueprints can launch autonomous missions on a schedule and "
        "report back through the control plane."
        if tasks
        else "Create a task blueprint to turn a repeated objective into a durable mission loop."
    )

    skillbooks = [
        DashboardSkillbookView(
            project_id=project.id,
            project_label=project.label,
            skills=sorted(
                skills_by_project.get(project.id, []),
                key=lambda skill: skill.name.lower(),
            ),
        )
        for project in projects
        if skills_by_project.get(project.id)
    ]

    return DashboardOpsMeshView(
        headline=headline,
        summary=summary,
        task_inbox=DashboardTaskInboxView(
            headline=task_headline,
            summary=task_summary,
            tasks=tasks,
        ),
        skillbooks=skillbooks,
        integrations=integrations,
        notification_routes=notification_routes,
        lane_snapshots=sorted(
            lane_snapshots,
            key=lambda snapshot: snapshot.created_at,
            reverse=True,
        )[:8],
    )


@dataclass(slots=True)
class OpsMeshService:
    database: Database
    manager: RuntimeManager
    missions: MissionService
    hub: BroadcastHub
    poll_interval_seconds: float = 20.0
    snapshot_interval_seconds: float = 1800.0
    _task: asyncio.Task[None] | None = field(init=False, default=None)
    _stop_event: asyncio.Event = field(init=False, default_factory=asyncio.Event)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._runner_loop(), name="openzues-ops-mesh")

    async def close(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def list_task_blueprint_views(self) -> list[TaskBlueprintView]:
        return [_serialize_task(row) for row in await self.database.list_task_blueprints()]

    async def list_notification_route_views(self) -> list[NotificationRouteView]:
        return [
            _serialize_route(row) for row in await self.database.list_notification_routes()
        ]

    async def list_integration_views(self) -> list[IntegrationView]:
        return [_serialize_integration(row) for row in await self.database.list_integrations()]

    async def list_skill_pin_views(self) -> list[SkillPinView]:
        return [_serialize_skill_pin(row) for row in await self.database.list_skill_pins()]

    async def list_lane_snapshot_views(self) -> list[LaneSnapshotView]:
        instance_names = {
            instance.id: instance.name for instance in await self.manager.list_views()
        }
        return [
            _build_lane_snapshot_view(row, instance_names)
            for row in await self.database.list_lane_snapshots()
        ]

    async def create_task_blueprint(self, payload: TaskBlueprintCreate) -> TaskBlueprintView:
        task_id = await self.database.create_task_blueprint(
            name=payload.name,
            summary=payload.summary,
            project_id=payload.project_id,
            instance_id=payload.instance_id,
            cadence_minutes=payload.cadence_minutes,
            enabled=payload.enabled,
            payload=payload.model_dump(
                exclude={
                    "name",
                    "summary",
                    "project_id",
                    "instance_id",
                    "cadence_minutes",
                    "enabled",
                }
            ),
        )
        row = await self.database.get_task_blueprint(task_id)
        assert row is not None
        return _serialize_task(row)

    async def delete_task_blueprint(self, task_id: int) -> None:
        await self.database.delete_task_blueprint(task_id)

    async def create_notification_route(
        self,
        payload: NotificationRouteCreate,
    ) -> NotificationRouteView:
        route_id = await self.database.create_notification_route(
            name=payload.name,
            kind=payload.kind,
            target=payload.target,
            events=payload.events,
            enabled=payload.enabled,
            secret_header_name=payload.secret_header_name,
            secret_token=payload.secret_token,
        )
        row = next(
            route
            for route in await self.database.list_notification_routes()
            if int(route["id"]) == route_id
        )
        return _serialize_route(row)

    async def delete_notification_route(self, route_id: int) -> None:
        await self.database.delete_notification_route(route_id)

    async def create_integration(self, payload: IntegrationCreate) -> IntegrationView:
        integration_id = await self.database.create_integration(
            name=payload.name,
            kind=payload.kind,
            project_id=payload.project_id,
            base_url=payload.base_url,
            auth_scheme=payload.auth_scheme,
            secret_label=payload.secret_label,
            secret_value=payload.secret_value,
            notes=payload.notes,
            enabled=payload.enabled,
        )
        row = next(
            integration
            for integration in await self.database.list_integrations()
            if int(integration["id"]) == integration_id
        )
        return _serialize_integration(row)

    async def delete_integration(self, integration_id: int) -> None:
        await self.database.delete_integration(integration_id)

    async def create_skill_pin(self, payload: SkillPinCreate) -> SkillPinView:
        skill_id = await self.database.create_skill_pin(
            project_id=payload.project_id,
            name=payload.name,
            prompt_hint=payload.prompt_hint,
            source=payload.source,
            enabled=payload.enabled,
        )
        row = next(
            skill
            for skill in await self.database.list_skill_pins()
            if int(skill["id"]) == skill_id
        )
        return _serialize_skill_pin(row)

    async def delete_skill_pin(self, skill_pin_id: int) -> None:
        await self.database.delete_skill_pin(skill_pin_id)

    async def capture_lane_snapshot(
        self,
        instance_id: int,
        *,
        snapshot_kind: str = "manual",
    ) -> LaneSnapshotView:
        runtime = await self.manager.get(instance_id)
        view = runtime.view()
        note = view.error or view.transport_note
        snapshot_id = await self.database.append_lane_snapshot(
            instance_id=instance_id,
            snapshot_kind=snapshot_kind,
            summary={
                "connected": view.connected,
                "transport": view.transport,
                "model_count": len(view.models),
                "skill_count": len(view.skills),
                "thread_count": len(view.threads),
                "note": note,
            },
        )
        row = next(
            snapshot
            for snapshot in await self.database.list_lane_snapshots()
            if int(snapshot["id"]) == snapshot_id
        )
        return _build_lane_snapshot_view(row, {view.id: view.name})

    async def run_task_blueprint_now(
        self,
        task_id: int,
        *,
        trigger: str = "manual",
    ) -> MissionView:
        task = await self.database.get_task_blueprint(task_id)
        if task is None:
            raise ValueError(f"Unknown task blueprint {task_id}")
        draft = await self._build_draft_for_task(_serialize_task(task))
        mission = await self.missions.create(MissionCreate(**draft.model_dump()))
        await self.database.update_task_blueprint(
            task_id,
            last_launched_at=utcnow(),
            last_status="active",
            last_result_summary=f"Launched mission {mission.name} via {trigger}.",
        )
        await self._publish_ops_event(
            "task/launched",
            {
                "taskId": task_id,
                "taskName": task["name"],
                "missionId": mission.id,
                "trigger": trigger,
            },
        )
        return mission

    async def handle_mission_event(self, event_type: str, event: dict[str, Any]) -> None:
        mission_id = event.get("missionId")
        if isinstance(mission_id, int):
            mission = await self.database.get_mission(mission_id)
            if mission is not None and mission.get("task_blueprint_id") is not None:
                task_id = int(mission["task_blueprint_id"])
                status = mission["status"]
                summary = (
                    str(mission.get("last_checkpoint") or mission.get("last_error") or "")
                    or f"Mission {mission['name']} changed state."
                )
                await self.database.update_task_blueprint(
                    task_id,
                    last_status=str(status),
                    last_result_summary=summary[:240],
                )
        await self._deliver_notifications(event_type, event)

    async def tick_once(self) -> None:
        tasks = await self.list_task_blueprint_views()
        missions = await self.missions.list_views()
        instances = await self.manager.list_views()

        for task in tasks:
            if not task.enabled or task.cadence_minutes is None:
                continue
            next_run = _parse_timestamp(_next_run_at(task))
            if next_run is None or next_run > datetime.now(UTC):
                continue
            active = any(
                mission.task_blueprint_id == task.id
                and mission.status in {"active", "blocked"}
                for mission in missions
            )
            if active:
                continue
            try:
                await self.run_task_blueprint_now(task.id, trigger="schedule")
            except Exception:
                logger.exception("Scheduled task launch failed for %s", task.name)

        snapshots = await self.database.list_lane_snapshots(limit=200)
        last_snapshot_by_instance: dict[int, datetime] = {}
        for snapshot in snapshots:
            created = _parse_timestamp(str(snapshot["created_at"]))
            if created is None:
                continue
            instance_id = int(snapshot["instance_id"])
            current = last_snapshot_by_instance.get(instance_id)
            if current is None or created > current:
                last_snapshot_by_instance[instance_id] = created

        for instance in instances:
            last_snapshot = last_snapshot_by_instance.get(instance.id)
            if (
                last_snapshot is None
                or (datetime.now(UTC) - last_snapshot).total_seconds()
                >= self.snapshot_interval_seconds
            ):
                try:
                    await self.capture_lane_snapshot(instance.id, snapshot_kind="auto")
                except Exception:
                    logger.exception("Auto snapshot failed for instance %s", instance.name)

    async def _build_draft_for_task(self, task: TaskBlueprintView) -> MissionDraftView:
        projects = {
            int(project["id"]): project for project in await self.database.list_projects()
        }
        project = projects.get(task.project_id) if task.project_id is not None else None
        skill_pins = [
            skill
            for skill in await self.list_skill_pin_views()
            if skill.project_id == task.project_id and skill.enabled
        ]
        integrations = [
            integration
            for integration in await self.list_integration_views()
            if integration.enabled
            and integration.project_id in {None, task.project_id}
        ]
        instances = await self.manager.list_views()
        instance_id = task.instance_id
        if instance_id is None:
            connected = next((item.id for item in instances if item.connected), None)
            instance_id = connected or (instances[0].id if instances else None)
        if instance_id is None:
            raise ValueError("No instance is available for this task blueprint.")

        return MissionDraftView(
            name=task.name,
            objective=_build_task_objective(
                task,
                skill_pins=skill_pins,
                integrations=integrations,
            ),
            instance_id=instance_id,
            project_id=task.project_id,
            task_blueprint_id=task.id,
            cwd=task.cwd or (str(project["path"]) if project is not None else None),
            thread_id=None,
            model=task.model,
            reasoning_effort=task.reasoning_effort,
            collaboration_mode=task.collaboration_mode,
            max_turns=task.max_turns,
            use_builtin_agents=task.use_builtin_agents,
            run_verification=task.run_verification,
            auto_commit=task.auto_commit,
            pause_on_approval=task.pause_on_approval,
            allow_auto_reflexes=task.allow_auto_reflexes,
            auto_recover=task.auto_recover,
            auto_recover_limit=task.auto_recover_limit,
            reflex_cooldown_seconds=task.reflex_cooldown_seconds,
            allow_failover=task.allow_failover,
            start_immediately=True,
        )

    async def _deliver_notifications(self, event_type: str, event: dict[str, Any]) -> None:
        routes = await self.database.list_notification_routes()
        for route in routes:
            if not bool(route.get("enabled")):
                continue
            events = route.get("events", [])
            if not isinstance(events, list) or not any(
                _matches_event(str(pattern), event_type) for pattern in events
            ):
                continue
            try:
                await asyncio.to_thread(self._post_webhook, route, event_type, event)
                await self.database.update_notification_route(
                    int(route["id"]),
                    last_delivery_at=utcnow(),
                    last_result=f"Delivered {event_type}",
                    last_error=None,
                )
            except Exception as exc:
                await self.database.update_notification_route(
                    int(route["id"]),
                    last_delivery_at=utcnow(),
                    last_result=f"Failed {event_type}",
                    last_error=str(exc)[:240],
                )

    def _post_webhook(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
    ) -> None:
        body = json.dumps({"eventType": event_type, "payload": event}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        secret_header_name = route.get("secret_header_name")
        secret_token = route.get("secret_token")
        if secret_header_name and secret_token:
            headers[str(secret_header_name)] = str(secret_token)
        request = Request(
            str(route["target"]),
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Webhook returned {response.status}")
        except HTTPError as exc:
            raise RuntimeError(f"Webhook returned {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Webhook failed: {exc.reason}") from exc

    async def _publish_ops_event(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"type": event_type, **payload, "createdAt": utcnow()}
        await self.hub.publish(event)
        await self._deliver_notifications(event_type, event)

    async def _runner_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.tick_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ops mesh loop crashed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue
