from __future__ import annotations

import json
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    MissionCreate,
    MissionView,
    RemoteMissionCreate,
    RemoteRequestView,
    RemoteTaskTrigger,
    TeamView,
)
from openzues.services.access import AuthenticatedOperator
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.ops_mesh import OpsMeshService

PAYLOAD_PREVIEW_LIMIT = 220


def _preview(value: Any) -> str | None:
    try:
        rendered = json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        rendered = json.dumps(str(value), ensure_ascii=True)
    if not rendered:
        return None
    suffix = "..." if len(rendered) > PAYLOAD_PREVIEW_LIMIT else ""
    return rendered[:PAYLOAD_PREVIEW_LIMIT] + suffix


class RemoteOpsService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        missions: MissionService,
        ops_mesh: OpsMeshService,
        hub: BroadcastHub,
    ) -> None:
        self.database = database
        self.manager = manager
        self.missions = missions
        self.ops_mesh = ops_mesh
        self.hub = hub

    async def list_remote_request_views(self, *, limit: int = 25) -> list[RemoteRequestView]:
        teams = {
            int(team["id"]): TeamView.model_validate({**team, "member_count": 0})
            for team in await self.database.list_teams()
        }
        operators = {int(row["id"]): row for row in await self.database.list_operators()}
        return [
            self._serialize_remote_request(
                row,
                operator=operators.get(int(row["operator_id"])),
                team=teams.get(int(row["team_id"])),
            )
            for row in await self.database.list_remote_requests(limit=limit)
        ]

    async def record_denied_request(
        self,
        *,
        auth: AuthenticatedOperator,
        kind: str,
        payload: dict[str, Any],
        source_ip: str | None,
        user_agent: str | None,
        idempotency_key: str | None,
        error: str,
    ) -> RemoteRequestView:
        request_id = await self.database.create_remote_request(
            team_id=auth.team.id,
            operator_id=auth.operator.id,
            idempotency_key=idempotency_key,
            kind=kind,
            status="denied",
            source="api_key",
            source_ip=source_ip,
            user_agent=user_agent,
            target_kind=None,
            target_id=None,
            target_label=None,
            payload=payload,
            result={"summary": error},
            error=error,
            resolved_at=utcnow(),
        )
        request_view = await self._require_remote_request_view(request_id)
        await self._publish_remote_event("remote/denied", request_view)
        return request_view

    async def create_mission_request(
        self,
        payload: RemoteMissionCreate,
        *,
        auth: AuthenticatedOperator,
        source_ip: str | None,
        user_agent: str | None,
        idempotency_key: str | None,
    ) -> RemoteRequestView:
        payload_dict = payload.model_dump()
        existing = await self._maybe_get_existing_request(
            auth.operator.id,
            idempotency_key,
            kind="mission.create",
            target_kind="mission",
        )
        if existing is not None:
            return existing

        instance_id = payload.instance_id or await self._pick_instance_id()
        resolved_payload = {**payload_dict, "instance_id": instance_id}
        await self._validate_mission_payload(payload, instance_id=instance_id)
        if payload.dry_run:
            request_id = await self.database.create_remote_request(
                team_id=auth.team.id,
                operator_id=auth.operator.id,
                idempotency_key=idempotency_key,
                kind="mission.create",
                status="dry_run",
                source="api_key",
                source_ip=source_ip,
                user_agent=user_agent,
                target_kind="mission",
                target_id=None,
                target_label=payload.name,
                payload=resolved_payload,
                result={
                    "summary": (
                        f"Validated mission '{payload.name}' for instance {instance_id} "
                        "without starting it."
                    )
                },
                resolved_at=utcnow(),
            )
            request_view = await self._require_remote_request_view(request_id)
            await self._publish_remote_event("remote/dry-run", request_view)
            return request_view

        request_id = await self.database.create_remote_request(
            team_id=auth.team.id,
            operator_id=auth.operator.id,
            idempotency_key=idempotency_key,
            kind="mission.create",
            status="accepted",
            source="api_key",
            source_ip=source_ip,
            user_agent=user_agent,
            target_kind="mission",
            target_id=None,
            target_label=payload.name,
            payload=resolved_payload,
        )
        accepted_view = await self._require_remote_request_view(request_id)
        await self._publish_remote_event("remote/accepted", accepted_view)

        try:
            mission = await self.missions.create(
                MissionCreate(
                    **{key: value for key, value in resolved_payload.items() if key != "dry_run"}
                )
            )
        except Exception as exc:
            error = str(exc)
            await self.database.update_remote_request(
                request_id,
                status="failed",
                error=error[:240],
                result={"summary": error[:240]},
                resolved_at=utcnow(),
            )
            failed_view = await self._require_remote_request_view(request_id)
            await self._publish_remote_event("remote/failed", failed_view)
            return failed_view

        result = self._mission_result_payload(mission)
        await self.database.update_remote_request(
            request_id,
            status="completed",
            target_id=mission.id,
            target_label=mission.name,
            result=result,
            error=None,
            resolved_at=utcnow(),
        )
        completed_view = await self._require_remote_request_view(request_id)
        await self._publish_remote_event("remote/completed", completed_view)
        return completed_view

    async def trigger_task_request(
        self,
        task_id: int,
        payload: RemoteTaskTrigger,
        *,
        auth: AuthenticatedOperator,
        source_ip: str | None,
        user_agent: str | None,
        idempotency_key: str | None,
    ) -> RemoteRequestView:
        payload_dict = {"task_id": task_id, **payload.model_dump()}
        existing = await self._maybe_get_existing_request(
            auth.operator.id,
            idempotency_key,
            kind="task.trigger",
            target_kind="task",
            target_id=task_id,
        )
        if existing is not None:
            return existing

        task = await self.database.get_task_blueprint(task_id)
        if task is None:
            raise ValueError(f"Unknown task blueprint {task_id}")

        if payload.dry_run:
            request_id = await self.database.create_remote_request(
                team_id=auth.team.id,
                operator_id=auth.operator.id,
                idempotency_key=idempotency_key,
                kind="task.trigger",
                status="dry_run",
                source="api_key",
                source_ip=source_ip,
                user_agent=user_agent,
                target_kind="task",
                target_id=task_id,
                target_label=str(task["name"]),
                payload=payload_dict,
                result={"summary": f"Validated task '{task['name']}' without launching it."},
                resolved_at=utcnow(),
            )
            request_view = await self._require_remote_request_view(request_id)
            await self._publish_remote_event("remote/dry-run", request_view)
            return request_view

        request_id = await self.database.create_remote_request(
            team_id=auth.team.id,
            operator_id=auth.operator.id,
            idempotency_key=idempotency_key,
            kind="task.trigger",
            status="accepted",
            source="api_key",
            source_ip=source_ip,
            user_agent=user_agent,
            target_kind="task",
            target_id=task_id,
            target_label=str(task["name"]),
            payload=payload_dict,
        )
        accepted_view = await self._require_remote_request_view(request_id)
        await self._publish_remote_event("remote/accepted", accepted_view)

        try:
            mission = await self.ops_mesh.run_task_blueprint_now(task_id, trigger="remote")
        except Exception as exc:
            error = str(exc)
            await self.database.update_remote_request(
                request_id,
                status="failed",
                error=error[:240],
                result={"summary": error[:240]},
                resolved_at=utcnow(),
            )
            failed_view = await self._require_remote_request_view(request_id)
            await self._publish_remote_event("remote/failed", failed_view)
            return failed_view

        result = {
            **self._mission_result_payload(mission),
            "summary": f"Triggered task '{task['name']}' via mission '{mission.name}'.",
        }
        await self.database.update_remote_request(
            request_id,
            status="completed",
            result=result,
            error=None,
            resolved_at=utcnow(),
        )
        completed_view = await self._require_remote_request_view(request_id)
        await self._publish_remote_event("remote/completed", completed_view)
        return completed_view

    async def _pick_instance_id(self) -> int:
        instances = await self.manager.list_views()
        connected = next((instance.id for instance in instances if instance.connected), None)
        if connected is not None:
            return connected
        if instances:
            return instances[0].id
        raise ValueError("No instance is available for remote mission control.")

    async def _maybe_get_existing_request(
        self,
        operator_id: int,
        idempotency_key: str | None,
        *,
        kind: str,
        target_kind: str,
        target_id: int | None = None,
    ) -> RemoteRequestView | None:
        if not idempotency_key:
            return None
        existing = await self.database.get_remote_request_by_idempotency(
            operator_id=operator_id,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            return None
        existing_kind = str(existing.get("kind"))
        existing_target_kind = str(existing.get("target_kind") or "")
        if existing_kind != kind or existing_target_kind != target_kind:
            raise ValueError(
                f"Idempotency key '{idempotency_key}' is already bound to "
                f"{existing_kind} request {existing.get('id')}."
            )
        if target_id is not None and existing.get("target_id") != target_id:
            raise ValueError(
                f"Idempotency key '{idempotency_key}' is already bound to "
                f"{existing.get('target_kind')} {existing.get('target_id')}."
            )
        teams = {
            int(team["id"]): TeamView.model_validate({**team, "member_count": 0})
            for team in await self.database.list_teams()
        }
        operator = await self.database.get_operator(int(existing["operator_id"]))
        return self._serialize_remote_request(
            existing,
            operator=operator,
            team=teams.get(int(existing["team_id"])),
        )

    async def _require_remote_request_view(self, request_id: int) -> RemoteRequestView:
        row = await self.database.get_remote_request(request_id)
        assert row is not None
        operator = await self.database.get_operator(int(row["operator_id"]))
        team_row = await self.database.get_team(int(row["team_id"]))
        team = TeamView.model_validate({**team_row, "member_count": 0}) if team_row else None
        return self._serialize_remote_request(row, operator=operator, team=team)

    def _serialize_remote_request(
        self,
        row: dict[str, Any],
        *,
        operator: dict[str, Any] | None,
        team: TeamView | None,
    ) -> RemoteRequestView:
        result = row.get("result")
        result_summary = (
            result.get("summary")
            if isinstance(result, dict) and isinstance(result.get("summary"), str)
            else None
        )
        summary = result_summary or str(row.get("error") or "") or f"{row['kind']} {row['status']}"
        return RemoteRequestView.model_validate(
            {
                **row,
                "team_name": team.name if team is not None else None,
                "operator_name": operator.get("name") if operator is not None else None,
                "operator_role": operator.get("role") if operator is not None else "viewer",
                "summary": summary,
                "payload_preview": _preview(row.get("payload")),
                "result_preview": _preview(result),
            }
        )

    def _mission_result_payload(self, mission: MissionView) -> dict[str, Any]:
        return {
            "mission_id": mission.id,
            "mission_name": mission.name,
            "mission_status": mission.status,
            "thread_id": mission.thread_id,
            "summary": (
                f"Created mission '{mission.name}' with status '{mission.status}' "
                f"on instance {mission.instance_id}."
            ),
        }

    async def _validate_mission_payload(
        self,
        payload: RemoteMissionCreate,
        *,
        instance_id: int,
    ) -> None:
        await self.manager.get(instance_id)
        if (
            payload.project_id is not None
            and await self.database.get_project(payload.project_id) is None
        ):
            raise ValueError(f"Unknown project {payload.project_id}")
        if (
            payload.task_blueprint_id is not None
            and await self.database.get_task_blueprint(payload.task_blueprint_id) is None
        ):
            raise ValueError(f"Unknown task blueprint {payload.task_blueprint_id}")

    async def _publish_remote_event(
        self,
        event_type: str,
        request_view: RemoteRequestView,
    ) -> None:
        await self.hub.publish(
            {
                "type": event_type,
                "requestId": request_view.id,
                "kind": request_view.kind,
                "status": request_view.status,
                "teamId": request_view.team_id,
                "operatorId": request_view.operator_id,
                "targetKind": request_view.target_kind,
                "targetId": request_view.target_id,
                "createdAt": utcnow(),
            }
        )
