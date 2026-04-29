from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any, Literal, NamedTuple, cast
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openzues.database import Database
from openzues.schemas import ConversationTargetView, TaskBlueprintCreate
from openzues.services.session_keys import (
    build_agent_main_session_key,
    resolve_agent_id_from_session_key,
    to_agent_request_session_key,
    to_agent_store_session_key,
)

CronEnabledFilter = Literal["all", "enabled", "disabled"]
CronSortBy = Literal["nextRunAtMs", "updatedAtMs", "name"]
CronSortDir = Literal["asc", "desc"]
CronRunMode = Literal["due", "force"]
CronRunsScope = Literal["job", "all"]
CronRunStatus = Literal["ok", "error", "skipped"]
CronRunStatusFilter = Literal["all", "ok", "error", "skipped"]
CronDeliveryStatus = Literal["delivered", "not-delivered", "unknown", "not-requested"]
CronFailoverReason = Literal[
    "auth",
    "format",
    "rate_limit",
    "billing",
    "timeout",
    "model_not_found",
    "unknown",
]
_GATEWAY_CRON_AGENT_ID = "openzues"
_CRON_CUSTOM_SESSION_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
_CRON_DELIVERY_CHANNEL_ID_RE = re.compile(r"^[a-z][a-z_-]{0,63}$")
_CRON_LOOKAHEAD_MINUTES = 366 * 24 * 60
_CRON_STATE_INT_FIELDS = {
    "consecutiveErrors",
    "lastDurationMs",
    "lastFailureAlertAtMs",
    "lastRunAtMs",
    "nextRunAtMs",
    "runningAtMs",
}
_CRON_STATE_TEXT_FIELDS = {"lastDeliveryError", "lastError"}
_CRON_STATE_RUN_STATUS_FIELDS = {"lastRunStatus", "lastStatus"}
_CRON_RUN_STATUS_VALUES = {"ok", "error", "skipped"}
_CRON_DELIVERY_STATUS_VALUES = {"delivered", "not-delivered", "not-requested", "unknown"}
_CRON_FAILOVER_REASON_VALUES = {
    "auth",
    "billing",
    "format",
    "model_not_found",
    "rate_limit",
    "timeout",
    "unknown",
}
_CRON_STATE_ALLOWED_KEYS = (
    _CRON_STATE_INT_FIELDS
    | _CRON_STATE_TEXT_FIELDS
    | _CRON_STATE_RUN_STATUS_FIELDS
    | {
        "lastDelivered",
        "lastDeliveryStatus",
        "lastErrorReason",
    }
)


class _ParsedCronSchedule(NamedTuple):
    seconds: set[int]
    minutes: set[int]
    hours: set[int]
    days_of_month: set[int]
    months: set[int]
    days_of_week: set[int]
    day_of_month_any: bool
    day_of_week_any: bool


class GatewayCronService:
    def __init__(
        self,
        database: Database,
        *,
        create_task_blueprint: Callable[[TaskBlueprintCreate], Awaitable[object]] | None = None,
        run_task_blueprint_now: Callable[..., Awaitable[object]] | None = None,
        dispatch_system_event_task: Callable[..., Awaitable[str]] | None = None,
        delete_task_blueprint: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self._database = database
        self._create_task_blueprint = create_task_blueprint
        self._run_task_blueprint_now = run_task_blueprint_now
        self._dispatch_system_event_task = dispatch_system_event_task
        self._delete_task_blueprint = delete_task_blueprint

    @property
    def can_add_jobs(self) -> bool:
        return self._create_task_blueprint is not None

    @property
    def can_run_jobs(self) -> bool:
        return (
            self._run_task_blueprint_now is not None
            or self._dispatch_system_event_task is not None
        )

    @property
    def can_remove_jobs(self) -> bool:
        return self._delete_task_blueprint is not None

    async def status(self) -> dict[str, Any]:
        jobs = [
            self._job_payload(task)
            for task in await self._database.list_task_blueprint_records()
            if _is_gateway_cron_task(task)
        ]
        next_wake_candidates: list[int] = []
        for job in jobs:
            state = cast(dict[str, Any], job.get("state") or {})
            next_run_at_ms = state.get("nextRunAtMs")
            if bool(job.get("enabled")) and isinstance(next_run_at_ms, int):
                next_wake_candidates.append(next_run_at_ms)
        next_wake_at_ms = min(next_wake_candidates, default=None)
        return {
            "enabled": True,
            "storePath": str(self._database.path),
            "jobs": len(jobs),
            "nextWakeAtMs": next_wake_at_ms,
        }

    async def list_page(
        self,
        *,
        enabled: CronEnabledFilter = "enabled",
        query: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: CronSortBy = "nextRunAtMs",
        sort_dir: CronSortDir = "asc",
    ) -> dict[str, Any]:
        jobs = [
            self._job_payload(task)
            for task in await self._database.list_task_blueprint_records()
            if _is_gateway_cron_task(task)
        ]

        normalized_query = str(query or "").strip().lower()
        filtered_jobs = [
            job
            for job in jobs
            if self._matches_enabled(job, enabled)
            and self._matches_query(job, normalized_query)
        ]
        sorted_jobs = sorted(
            filtered_jobs,
            key=lambda job: self._sort_key(job, sort_by),
            reverse=sort_dir == "desc",
        )

        total = len(sorted_jobs)
        resolved_offset = min(max(offset or 0, 0), total)
        default_limit = 50 if total == 0 else total
        resolved_limit = min(max(limit or default_limit, 1), 200)
        page = sorted_jobs[resolved_offset : resolved_offset + resolved_limit]
        next_offset = resolved_offset + len(page)
        has_more = next_offset < total
        return {
            "jobs": page,
            "total": total,
            "offset": resolved_offset,
            "limit": resolved_limit,
            "hasMore": has_more,
            "nextOffset": next_offset if has_more else None,
        }

    async def add(self, job_create: dict[str, Any]) -> dict[str, Any]:
        if self._create_task_blueprint is None:
            raise RuntimeError("cron.add is unavailable until scheduled task creation is wired")
        created_task = build_gateway_cron_task_blueprint(job_create)
        await self._validate_explicit_announce_channel_on_add(job_create, created_task)
        created = await self._create_task_blueprint(created_task)
        task_blueprint_id = _task_blueprint_id_from_result(created)
        if task_blueprint_id is None:
            raise ValueError("scheduled task creation did not return a task id")
        task = next(
            (
                entry
                for entry in await self._database.list_task_blueprint_records()
                if _int_or_none(entry.get("id")) == task_blueprint_id
            ),
            None,
        )
        if task is None:
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')
        return self._job_payload(task)

    async def run(
        self,
        *,
        job_id: str,
        mode: CronRunMode = "force",
    ) -> dict[str, Any]:
        if not self.can_run_jobs:
            raise RuntimeError("cron.run is unavailable until scheduled task launch is wired")
        task_blueprint_id = self._task_blueprint_id_from_job_id(job_id)
        task = await self._database.get_task_blueprint(task_blueprint_id)
        if task is None or not _is_gateway_cron_task(task):
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')
        if await self._task_has_active_mission(task_blueprint_id):
            return {"ok": True, "ran": False, "reason": "already-running"}
        if mode == "due" and not _task_is_due(task):
            return {"ok": True, "ran": False, "reason": "not-due"}
        if _task_routes_through_system_event_wake(task):
            if self._dispatch_system_event_task is None:
                raise RuntimeError(
                    "cron.run is unavailable until system-event wake dispatch is wired"
                )
            run_id = await self._dispatch_system_event_task(
                task_blueprint_id,
                trigger=f"gateway-cron:{mode}",
            )
            return {"ok": True, "enqueued": True, "runId": run_id}
        if self._run_task_blueprint_now is None:
            raise RuntimeError("cron.run is unavailable until scheduled task launch is wired")
        try:
            mission = await self._run_task_blueprint_now(
                task_blueprint_id,
                trigger=f"gateway-cron:{mode}",
            )
        except ValueError:
            return {"ok": True, "ran": False, "reason": "invalid-spec"}
        mission_id = _mission_id_from_result(mission)
        if mission_id is None:
            raise ValueError("scheduled task launch did not return a mission id")
        return {"ok": True, "enqueued": True, "runId": f"mission:{mission_id}"}

    async def remove(self, job_id: str) -> dict[str, Any]:
        if self._delete_task_blueprint is None:
            raise RuntimeError("cron.remove is unavailable until scheduled task deletion is wired")
        task_blueprint_id = _maybe_task_blueprint_id_from_job_id(job_id)
        if task_blueprint_id is None:
            return {"ok": True, "removed": False}
        task = await self._database.get_task_blueprint(task_blueprint_id)
        if task is None or not _is_gateway_cron_task(task):
            return {"ok": True, "removed": False}
        await self._delete_task_blueprint(task_blueprint_id)
        return {"ok": True, "removed": True}

    async def update(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        task_blueprint_id = self._task_blueprint_id_from_job_id(job_id)
        task = await self._database.get_task_blueprint(task_blueprint_id)
        if task is None or not _is_gateway_cron_task(task):
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')

        row_updates, payload_updates = build_gateway_cron_job_patch(task, patch)
        await self._validate_explicit_announce_channel_on_update(task, patch, payload_updates)
        if row_updates:
            await self._database.update_task_blueprint(task_blueprint_id, **row_updates)
        if payload_updates:
            await self._database.update_task_blueprint_payload(task_blueprint_id, **payload_updates)

        updated = next(
            (
                entry
                for entry in await self._database.list_task_blueprint_records()
                if _int_or_none(entry.get("id")) == task_blueprint_id
            ),
            None,
        )
        if updated is None:
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')
        return self._job_payload(updated)

    async def _enabled_notification_route_channels(self) -> tuple[str, ...]:
        channels: set[str] = set()
        for route in await self._database.list_notification_routes():
            if not bool(route.get("enabled")):
                continue
            conversation_target = route.get("conversation_target")
            if not isinstance(conversation_target, dict):
                continue
            channel = str(conversation_target.get("channel") or "").strip().lower()
            if channel:
                channels.add(channel)
        return tuple(sorted(channels))

    async def _validate_explicit_announce_channel_on_add(
        self,
        job_create: dict[str, Any],
        created_task: TaskBlueprintCreate,
    ) -> None:
        delivery = job_create.get("delivery")
        if not isinstance(delivery, dict):
            return
        raw_mode = str(delivery.get("mode") or "").strip().lower()
        if raw_mode == "deliver":
            raw_mode = "announce"
        if raw_mode != "announce" or created_task.cron_delivery_channel is not None:
            return
        enabled_channels = await self._enabled_notification_route_channels()
        if len(enabled_channels) > 1:
            raise ValueError(
                "invalid cron.add params: delivery.channel is required when multiple delivery "
                "channels are enabled"
            )

    async def _validate_explicit_announce_channel_on_update(
        self,
        task: dict[str, Any],
        patch: dict[str, Any],
        payload_updates: dict[str, Any],
    ) -> None:
        delivery = patch.get("delivery")
        if not isinstance(delivery, dict):
            return
        raw_mode = str(delivery.get("mode") or "").strip().lower()
        if raw_mode == "deliver":
            raw_mode = "announce"
        if raw_mode != "announce":
            return
        effective_channel = (
            payload_updates.get("cron_delivery_channel")
            if "cron_delivery_channel" in payload_updates
            else _task_payload_fields(task).get("cron_delivery_channel")
        )
        if str(effective_channel or "").strip():
            return
        enabled_channels = await self._enabled_notification_route_channels()
        if len(enabled_channels) > 1:
            raise ValueError(
                "invalid cron.update params: patch.delivery.channel is required when multiple "
                "delivery channels are enabled"
            )

    async def runs_page(
        self,
        *,
        scope: CronRunsScope,
        job_id: str | None,
        limit: int | None = None,
        offset: int | None = None,
        statuses: tuple[CronRunStatus, ...] | None = None,
        status: CronRunStatusFilter | None = None,
        delivery_statuses: tuple[CronDeliveryStatus, ...] | None = None,
        delivery_status: CronDeliveryStatus | None = None,
        query: str | None = None,
        sort_dir: CronSortDir = "desc",
    ) -> dict[str, Any]:
        task_records = [
            task
            for task in await self._database.list_task_blueprint_records()
            if _is_gateway_cron_task(task)
        ]
        tasks_by_id = {
            cast(int, task["id"]): task
            for task in task_records
            if isinstance(task.get("id"), int)
        }
        normalized_job_id = self._normalize_requested_job_id(job_id) if job_id is not None else None
        normalized_statuses = _normalized_run_statuses(statuses=statuses, status=status)
        normalized_delivery_statuses = _normalized_delivery_statuses(
            delivery_statuses=delivery_statuses,
            delivery_status=delivery_status,
        )
        normalized_query = str(query or "").strip().lower()
        outbound_deliveries_by_mission_id: dict[int, dict[str, Any]] = {}
        for delivery in await self._database.list_outbound_deliveries(limit=2000):
            event_payload = delivery.get("event_payload")
            if not isinstance(event_payload, dict):
                continue
            mission_id = _int_or_none(event_payload.get("missionId"))
            if mission_id is None or mission_id in outbound_deliveries_by_mission_id:
                continue
            outbound_deliveries_by_mission_id[mission_id] = delivery

        entries = [
            entry
            for mission in await self._database.list_missions()
            if (
                entry := self._mission_run_entry(
                    mission,
                    tasks_by_id=tasks_by_id,
                    outbound_deliveries_by_mission_id=outbound_deliveries_by_mission_id,
                    include_job_name=scope == "all",
                )
            )
            is not None
            and (normalized_job_id is None or entry["jobId"] == normalized_job_id)
            and _run_entry_matches_filters(
                entry,
                statuses=normalized_statuses,
                delivery_statuses=normalized_delivery_statuses,
                query=normalized_query,
            )
        ]
        entries.extend(
            entry
            for event in await self._database.list_events(limit=2000)
            if (
                entry := self._system_event_run_entry(
                    event,
                    tasks_by_id=tasks_by_id,
                    include_job_name=scope == "all",
                )
            )
            is not None
            and (normalized_job_id is None or entry["jobId"] == normalized_job_id)
            and _run_entry_matches_filters(
                entry,
                statuses=normalized_statuses,
                delivery_statuses=normalized_delivery_statuses,
                query=normalized_query,
            )
        )
        sorted_entries = sorted(
            entries,
            key=lambda entry: (
                int(entry.get("ts") or 0),
                str(entry.get("jobId") or ""),
                str(entry.get("sessionId") or ""),
            ),
            reverse=sort_dir == "desc",
        )
        total = len(sorted_entries)
        resolved_offset = min(max(offset or 0, 0), total)
        default_limit = 50 if total == 0 else total
        resolved_limit = min(max(limit or default_limit, 1), 200)
        page = sorted_entries[resolved_offset : resolved_offset + resolved_limit]
        next_offset = resolved_offset + len(page)
        has_more = next_offset < total
        return {
            "entries": page,
            "total": total,
            "offset": resolved_offset,
            "limit": resolved_limit,
            "hasMore": has_more,
            "nextOffset": next_offset if has_more else None,
        }

    def _job_payload(self, task: dict[str, Any]) -> dict[str, Any]:
        payload_state = _task_payload_fields(task)
        objective_template = str(payload_state.get("objective_template") or "").strip()
        payload = _cron_payload_object(payload_state, objective_template=objective_template)
        schedule = _cron_schedule_payload(task, payload_state=payload_state)
        if schedule is None:
            raise ValueError(f'unknown cron job "{_cron_job_id(cast(int, task["id"]))}"')
        job_payload = {
            "id": _cron_job_id(cast(int, task["id"])),
            "agentId": _GATEWAY_CRON_AGENT_ID,
            "name": str(task.get("name") or "").strip(),
            "description": str(task.get("summary") or "").strip() or None,
            "enabled": bool(task.get("enabled")),
            "createdAtMs": _timestamp_ms(task.get("created_at")),
            "updatedAtMs": _timestamp_ms(task.get("updated_at")),
            "schedule": schedule,
            "sessionTarget": _cron_session_target(payload_state),
            "wakeMode": _cron_wake_mode(payload_state),
            "payload": payload,
            "delivery": _cron_delivery_payload(payload_state),
            "state": self._state_payload(
                task,
                payload_state=payload_state,
            ),
        }
        session_key = _cron_session_key(payload_state)
        if session_key is not None:
            job_payload["sessionKey"] = session_key
        if bool(payload_state.get("cron_notify_enabled")):
            job_payload["notify"] = True
        failure_alert = payload_state.get("cron_failure_alert")
        if failure_alert is False:
            job_payload["failureAlert"] = False
        elif isinstance(failure_alert, dict):
            job_payload["failureAlert"] = dict(failure_alert)
        return job_payload

    def _mission_run_entry(
        self,
        mission: dict[str, Any],
        *,
        tasks_by_id: dict[int, dict[str, Any]],
        outbound_deliveries_by_mission_id: dict[int, dict[str, Any]],
        include_job_name: bool,
    ) -> dict[str, Any] | None:
        task_blueprint_id = _int_or_none(mission.get("task_blueprint_id"))
        if task_blueprint_id is None:
            return None
        task = tasks_by_id.get(task_blueprint_id)
        if task is None:
            return None
        run_status = _mission_run_status(mission)
        if run_status is None:
            return None

        created_at_ms = _timestamp_ms(mission.get("created_at"))
        updated_at_ms = (
            _timestamp_ms(mission.get("updated_at"))
            or _timestamp_ms(mission.get("last_activity_at"))
            or created_at_ms
        )
        if updated_at_ms is None:
            return None

        conversation_target = mission.get("conversation_target")
        outbound_delivery = outbound_deliveries_by_mission_id.get(int(mission["id"]))
        delivery_state = (
            str(outbound_delivery.get("delivery_state") or "").strip().lower()
            if outbound_delivery is not None
            else ""
        )
        delivery_status: CronDeliveryStatus
        if delivery_state == "delivered":
            delivery_status = "delivered"
        elif delivery_state == "failed":
            delivery_status = "not-delivered"
        else:
            delivery_status = (
                "unknown"
                if isinstance(conversation_target, dict) and bool(conversation_target)
                else "not-requested"
            )
        entry: dict[str, Any] = {
            "ts": updated_at_ms,
            "jobId": _cron_job_id(task_blueprint_id),
            "action": "finished",
            "status": run_status,
            "deliveryStatus": delivery_status,
        }
        summary = _mission_run_summary(mission)
        if summary is not None:
            entry["summary"] = summary
        last_error = _text_or_none(mission.get("last_error"))
        if run_status == "error" and last_error is not None:
            entry["error"] = last_error
        thread_id = _text_or_none(mission.get("thread_id"))
        if thread_id is not None:
            entry["sessionId"] = thread_id
        session_key = _text_or_none(mission.get("session_key"))
        if session_key is not None:
            entry["sessionKey"] = session_key
        if created_at_ms is not None:
            entry["runAtMs"] = created_at_ms
        if created_at_ms is not None and updated_at_ms >= created_at_ms:
            entry["durationMs"] = updated_at_ms - created_at_ms
        model = _text_or_none(mission.get("model"))
        if model is not None:
            entry["model"] = model
        if include_job_name:
            job_name = _text_or_none(task.get("name"))
            if job_name is not None:
                entry["jobName"] = job_name
        return entry

    def _system_event_run_entry(
        self,
        event: dict[str, Any],
        *,
        tasks_by_id: dict[int, dict[str, Any]],
        include_job_name: bool,
    ) -> dict[str, Any] | None:
        if str(event.get("method") or "").strip() != "system-event":
            return None
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return None
        reason = _text_or_none(payload.get("reason"))
        if reason is None or not reason.startswith("cron:"):
            return None
        task_blueprint_id = _int_or_none(reason.removeprefix("cron:"))
        if task_blueprint_id is None:
            return None
        task = tasks_by_id.get(task_blueprint_id)
        if task is None or not _task_routes_through_system_event_wake(task):
            return None
        created_at_ms = _timestamp_ms(event.get("created_at"))
        if created_at_ms is None:
            return None
        summary = _text_or_none(payload.get("text"))
        entry: dict[str, Any] = {
            "ts": created_at_ms,
            "jobId": _cron_job_id(task_blueprint_id),
            "action": "finished",
            "status": "ok",
            "deliveryStatus": "not-requested",
            "runAtMs": created_at_ms,
            "durationMs": 0,
        }
        if summary is not None:
            entry["summary"] = summary
        if include_job_name:
            job_name = _text_or_none(task.get("name"))
            if job_name is not None:
                entry["jobName"] = job_name
        return entry

    async def _task_has_active_mission(self, task_blueprint_id: int) -> bool:
        return any(
            _int_or_none(mission.get("task_blueprint_id")) == task_blueprint_id
            and str(mission.get("status") or "").strip().lower() in {"active", "blocked"}
            for mission in await self._database.list_missions()
        )

    def _normalize_requested_job_id(self, job_id: str) -> str:
        normalized_job_id = str(job_id).strip()
        if (
            not normalized_job_id
            or "/" in normalized_job_id
            or "\\" in normalized_job_id
            or not normalized_job_id.startswith("task-blueprint:")
        ):
            raise ValueError("invalid cron.runs params: invalid id")
        task_blueprint_id = _int_or_none(normalized_job_id.removeprefix("task-blueprint:"))
        if task_blueprint_id is None:
            raise ValueError("invalid cron.runs params: invalid id")
        return _cron_job_id(task_blueprint_id)

    def _task_blueprint_id_from_job_id(self, job_id: str) -> int:
        normalized_job_id = str(job_id).strip()
        if (
            not normalized_job_id
            or "/" in normalized_job_id
            or "\\" in normalized_job_id
            or not normalized_job_id.startswith("task-blueprint:")
        ):
            raise ValueError("invalid cron.run params: invalid id")
        task_blueprint_id = _int_or_none(normalized_job_id.removeprefix("task-blueprint:"))
        if task_blueprint_id is None:
            raise ValueError("invalid cron.run params: invalid id")
        return task_blueprint_id

    def _state_payload(
        self,
        task: dict[str, Any],
        *,
        payload_state: dict[str, Any],
    ) -> dict[str, Any]:
        state = _cron_state_payload(payload_state.get("cron_state"))
        last_run_at_ms = _timestamp_ms(payload_state.get("last_launched_at"))
        if last_run_at_ms is not None:
            state["lastRunAtMs"] = last_run_at_ms

        normalized_status = _normalized_status(payload_state.get("last_status"))
        if normalized_status is not None:
            state["lastRunStatus"] = normalized_status
            state["lastStatus"] = normalized_status
            if normalized_status == "running" and last_run_at_ms is not None:
                state["runningAtMs"] = last_run_at_ms

        if normalized_status == "error":
            last_error = str(payload_state.get("last_result_summary") or "").strip()
            if last_error:
                state["lastError"] = last_error

        if bool(task.get("enabled")):
            next_run_at_ms = _next_run_at_ms(
                last_launched_at=payload_state.get("last_launched_at"),
                created_at=task.get("created_at"),
                cadence_minutes=_int_or_none(task.get("cadence_minutes")),
                schedule_kind=_text_or_none(payload_state.get("schedule_kind")),
                schedule_at=payload_state.get("schedule_at"),
                schedule_cron_expr=payload_state.get("schedule_cron_expr"),
                schedule_cron_tz=payload_state.get("schedule_cron_tz"),
                last_status=payload_state.get("last_status"),
            )
            if next_run_at_ms is not None:
                state["nextRunAtMs"] = next_run_at_ms
        return state

    def _matches_enabled(self, job: dict[str, Any], enabled: CronEnabledFilter) -> bool:
        if enabled == "all":
            return True
        return bool(job["enabled"]) if enabled == "enabled" else not bool(job["enabled"])

    def _matches_query(self, job: dict[str, Any], query: str) -> bool:
        if not query:
            return True
        payload = cast(dict[str, Any], job.get("payload") or {})
        haystack = " ".join(
            part
            for part in (
                str(job.get("name") or ""),
                str(job.get("description") or ""),
                str(job.get("agentId") or ""),
                str(payload.get("message") or ""),
                str(payload.get("text") or ""),
            )
            if part
        ).lower()
        return query in haystack

    def _sort_key(self, job: dict[str, Any], sort_by: CronSortBy) -> tuple[object, ...]:
        if sort_by == "name":
            return (str(job.get("name") or "").lower(), str(job.get("id") or ""))
        if sort_by == "updatedAtMs":
            updated_at_ms = job.get("updatedAtMs")
            return (updated_at_ms is None, updated_at_ms or 0, str(job.get("id") or ""))
        next_run_at_ms = (job.get("state") or {}).get("nextRunAtMs")
        return (next_run_at_ms is None, next_run_at_ms or 0, str(job.get("id") or ""))


def _timestamp_ms(value: object) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return int(parsed.timestamp() * 1000)


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized_value = value.strip()
    if not normalized_value:
        return None
    try:
        parsed = datetime.fromisoformat(normalized_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _next_run_at_ms(
    *,
    last_launched_at: object,
    created_at: object | None = None,
    cadence_minutes: int | None,
    schedule_kind: str | None = None,
    schedule_at: object | None = None,
    schedule_cron_expr: object | None = None,
    schedule_cron_tz: object | None = None,
    last_status: object | None = None,
) -> int | None:
    normalized_schedule_kind = str(schedule_kind or "").strip().lower()
    if normalized_schedule_kind == "at":
        return _at_schedule_next_run_at_ms(
            schedule_at=schedule_at,
            last_launched_at=last_launched_at,
            last_status=last_status,
        )
    if normalized_schedule_kind == "cron":
        base = _parse_timestamp(last_launched_at) or _parse_timestamp(created_at)
        if base is None:
            base = datetime.now(UTC)
        return _cron_expression_next_run_at_ms(
            expr=schedule_cron_expr,
            tz=schedule_cron_tz,
            after=base,
        )
    if cadence_minutes is None:
        return None
    last_run_at = _parse_timestamp(last_launched_at)
    if last_run_at is None:
        return None
    return int((last_run_at + timedelta(minutes=cadence_minutes)).timestamp() * 1000)


def _task_is_due(task: dict[str, Any]) -> bool:
    if not bool(task.get("enabled")):
        return False
    schedule = _cron_schedule_payload(task)
    if schedule is None:
        return False
    if schedule["kind"] == "at":
        payload_state = _task_payload_fields(task)
        state_next_run_at_ms = _cron_state_payload(
            payload_state.get("cron_state")
        ).get("nextRunAtMs")
        if isinstance(state_next_run_at_ms, int) and not isinstance(
            state_next_run_at_ms, bool
        ):
            current_ms = int(datetime.now(UTC).timestamp() * 1000)
            return state_next_run_at_ms <= current_ms
        next_run_at_ms = _at_schedule_next_run_at_ms(
            schedule_at=schedule.get("at"),
            last_launched_at=payload_state.get("last_launched_at"),
            last_status=payload_state.get("last_status"),
        )
        current_ms = int(datetime.now(UTC).timestamp() * 1000)
        return next_run_at_ms is not None and next_run_at_ms <= current_ms
    if schedule["kind"] == "cron":
        payload_state = _task_payload_fields(task)
        base = _parse_timestamp(payload_state.get("last_launched_at")) or _parse_timestamp(
            task.get("created_at")
        )
        if base is None:
            return False
        next_run_at_ms = _cron_expression_next_run_at_ms(
            expr=schedule.get("expr"),
            tz=schedule.get("tz"),
            after=base,
        )
        current_ms = int(datetime.now(UTC).timestamp() * 1000)
        return next_run_at_ms is not None and next_run_at_ms <= current_ms
    cadence_minutes = _int_or_none(task.get("cadence_minutes"))
    if cadence_minutes is None or cadence_minutes < 1:
        return False
    last_run_at = _parse_timestamp(task.get("last_launched_at"))
    if last_run_at is None:
        return True
    return last_run_at + timedelta(minutes=cadence_minutes) <= datetime.now(UTC)


def _normalized_status(value: object) -> str | None:
    normalized_value = str(value or "").strip().lower()
    if not normalized_value:
        return None
    if normalized_value in {"completed", "ok", "success"}:
        return "ok"
    if normalized_value in {"failed", "error"}:
        return "error"
    if normalized_value in {"active", "running", "in_progress"}:
        return "running"
    if normalized_value in {"pending", "queued"}:
        return "pending"
    return normalized_value


def _cron_job_id(task_blueprint_id: int) -> str:
    return f"task-blueprint:{task_blueprint_id}"


def _text_or_none(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _mission_id_from_result(value: object) -> int | None:
    if isinstance(value, dict):
        return _int_or_none(value.get("id"))
    return _int_or_none(getattr(value, "id", None))


def _task_blueprint_id_from_result(value: object) -> int | None:
    if isinstance(value, dict):
        return _int_or_none(value.get("id"))
    return _int_or_none(getattr(value, "id", None))


def _task_payload_fields(task: dict[str, Any]) -> dict[str, Any]:
    payload = task.get("payload")
    if isinstance(payload, dict):
        return cast(dict[str, Any], payload)
    return task


def _patched_payload_value(
    payload_updates: dict[str, Any],
    task: dict[str, Any],
    field: str,
) -> Any:
    if field in payload_updates:
        return payload_updates[field]
    return _task_payload_fields(task).get(field)


def _stored_cron_session_key(payload_state: dict[str, Any]) -> str | None:
    session_key = str(payload_state.get("cron_session_key") or "").strip()
    return session_key or None


def _cron_session_key(payload_state: dict[str, Any]) -> str | None:
    stored_session_key = _stored_cron_session_key(payload_state)
    if stored_session_key is None:
        return None
    return to_agent_request_session_key(stored_session_key) or stored_session_key


def _normalized_cron_session_key(
    value: object,
    *,
    method: str,
    label: str,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid {method} params: {label} must be a string")
    requested_session_key = value.strip()
    if not requested_session_key:
        return None
    stored_session_key = to_agent_store_session_key(
        agent_id=_GATEWAY_CRON_AGENT_ID,
        request_key=requested_session_key,
    )
    if resolve_agent_id_from_session_key(stored_session_key) != _GATEWAY_CRON_AGENT_ID:
        return build_agent_main_session_key(agent_id=_GATEWAY_CRON_AGENT_ID)
    return stored_session_key


def _cron_session_target(payload_state: dict[str, Any]) -> str:
    session_target = str(payload_state.get("cron_session_target") or "").strip()
    normalized = _normalize_custom_cron_session_target(session_target)
    if normalized is not None:
        return normalized
    if session_target.lower() == "current":
        return "isolated"
    if session_target.lower() in {"main", "isolated"}:
        return session_target.lower()
    return "main"


def _cron_wake_mode(payload_state: dict[str, Any]) -> str:
    wake_mode = str(payload_state.get("cron_wake_mode") or "").strip().lower()
    if wake_mode in {"now", "next-heartbeat"}:
        return wake_mode
    return "now"


def _cron_payload_kind(payload_state: dict[str, Any]) -> str:
    payload_kind = str(payload_state.get("cron_payload_kind") or "").strip()
    if payload_kind in {"agentTurn", "systemEvent"}:
        return payload_kind
    return "agentTurn"


def _cron_payload_object(
    payload_state: dict[str, Any],
    *,
    objective_template: str,
) -> dict[str, Any]:
    payload_kind = _cron_payload_kind(payload_state)
    if payload_kind == "systemEvent":
        text = str(payload_state.get("cron_payload_text") or "").strip() or objective_template
        return {
            "kind": "systemEvent",
            "text": text,
        }
    model = str(payload_state.get("model") or "").strip()
    payload: dict[str, Any] = {
        "kind": "agentTurn",
        "message": objective_template,
    }
    if model:
        payload["model"] = model
    return payload


def _cron_delivery_mode(payload_state: dict[str, Any]) -> str:
    delivery_mode = str(payload_state.get("cron_delivery_mode") or "").strip().lower()
    if delivery_mode in {"announce", "none", "webhook"}:
        return delivery_mode
    if (
        _cron_payload_kind(payload_state) == "agentTurn"
        and _cron_session_target(payload_state) != "main"
    ):
        return "announce"
    return "none"


def _cron_delivery_payload(payload_state: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"mode": _cron_delivery_mode(payload_state)}
    channel = str(payload_state.get("cron_delivery_channel") or "").strip().lower()
    to = str(payload_state.get("cron_delivery_to") or "").strip()
    account_id = str(payload_state.get("cron_delivery_account_id") or "").strip()
    raw_thread_id = payload_state.get("cron_delivery_thread_id")
    best_effort = payload_state.get("cron_delivery_best_effort")
    failure_destination = payload_state.get("cron_delivery_failure_destination")
    if channel:
        payload["channel"] = channel
    if to:
        payload["to"] = to
    if account_id:
        payload["accountId"] = account_id
    if isinstance(raw_thread_id, int) and not isinstance(raw_thread_id, bool):
        payload["threadId"] = raw_thread_id
    else:
        thread_id = str(raw_thread_id or "").strip()
        if thread_id:
            payload["threadId"] = thread_id
    if isinstance(best_effort, bool):
        payload["bestEffort"] = best_effort
    if isinstance(failure_destination, dict) and failure_destination:
        payload["failureDestination"] = dict(failure_destination)
    return payload


def _task_routes_through_system_event_wake(task: dict[str, Any]) -> bool:
    payload_state = _task_payload_fields(task)
    return (
        _cron_session_target(payload_state) == "main"
        and _cron_payload_kind(payload_state) == "systemEvent"
    )


def _is_gateway_cron_task(task: dict[str, Any]) -> bool:
    payload_state = _task_payload_fields(task)
    schedule_kind = str(payload_state.get("schedule_kind") or "").strip().lower()
    if schedule_kind == "at":
        try:
            return _canonical_cron_schedule_at(
                payload_state.get("schedule_at"),
                error_message="invalid stored cron schedule.at",
            ) is not None
        except ValueError:
            return False
    if schedule_kind == "cron":
        try:
            return (
                _canonical_cron_expr(
                    payload_state.get("schedule_cron_expr"),
                    method="stored cron",
                    label="schedule.expr",
                )
                is not None
            )
        except ValueError:
            return False
    cadence_minutes = _int_or_none(task.get("cadence_minutes"))
    return cadence_minutes is not None and cadence_minutes >= 1


def _cron_schedule_payload(
    task: dict[str, Any],
    *,
    payload_state: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved_payload_state = payload_state or _task_payload_fields(task)
    schedule_kind = str(resolved_payload_state.get("schedule_kind") or "").strip().lower()
    if schedule_kind == "at":
        schedule_at = _canonical_cron_schedule_at(
            resolved_payload_state.get("schedule_at"),
            error_message="invalid stored cron schedule.at",
        )
        if schedule_at is None:
            return None
        return {
            "kind": "at",
            "at": schedule_at,
        }
    if schedule_kind == "cron":
        expr = _canonical_cron_expr(
            resolved_payload_state.get("schedule_cron_expr"),
            method="stored cron",
            label="schedule.expr",
        )
        if expr is None:
            return None
        cron_schedule: dict[str, Any] = {
            "kind": "cron",
            "expr": expr,
        }
        tz = _canonical_cron_tz(resolved_payload_state.get("schedule_cron_tz"))
        if tz is not None:
            cron_schedule["tz"] = tz
        stagger_ms = _canonical_cron_stagger_ms(
            resolved_payload_state.get("schedule_cron_stagger_ms"),
            method="stored cron",
            label="schedule.staggerMs",
        )
        if stagger_ms is not None:
            cron_schedule["staggerMs"] = stagger_ms
        return cron_schedule

    cadence_minutes = _int_or_none(task.get("cadence_minutes"))
    if cadence_minutes is None or cadence_minutes < 1:
        return None
    every_schedule: dict[str, Any] = {
        "kind": "every",
        "everyMs": cadence_minutes * 60_000,
    }
    anchor_ms = resolved_payload_state.get("schedule_anchor_ms")
    if isinstance(anchor_ms, int) and not isinstance(anchor_ms, bool) and anchor_ms >= 0:
        every_schedule["anchorMs"] = anchor_ms
    return every_schedule


def _at_schedule_next_run_at_ms(
    *,
    schedule_at: object,
    last_launched_at: object,
    last_status: object,
) -> int | None:
    normalized_at = _canonical_cron_schedule_at(
        schedule_at,
        error_message="invalid stored cron schedule.at",
    )
    if normalized_at is None:
        return None
    scheduled_at = _parse_timestamp(normalized_at)
    if scheduled_at is None:
        return None
    last_run_at = _parse_timestamp(last_launched_at)
    normalized_status = _normalized_status(last_status)
    if (
        last_run_at is not None
        and normalized_status in {"ok", "error"}
        and scheduled_at <= last_run_at
    ):
        return None
    return int(scheduled_at.timestamp() * 1000)


def _schedule_kind_from_object(
    schedule: dict[str, Any],
    *,
    kind_label: str,
    missing_error_message: str,
    require_kind: bool,
) -> str:
    kind = (
        _require_cron_add_string(schedule.get("kind"), label=kind_label)
        if require_kind
        else _optional_cron_add_string(schedule.get("kind"), label=kind_label)
    )
    if kind is None:
        if schedule.get("at") is not None:
            return "at"
        if schedule.get("everyMs") is not None or schedule.get("anchorMs") is not None:
            return "every"
        raise ValueError(missing_error_message)
    return kind


def _canonical_cron_schedule_at(value: object, *, error_message: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(error_message)
    parsed = _parse_timestamp(value)
    if parsed is None:
        raise ValueError(error_message)
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical_cron_expr(
    value: object,
    *,
    method: str,
    label: str,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid {method} params: {label} must be a non-empty string")
    expr = " ".join(value.strip().split())
    if not expr:
        raise ValueError(f"invalid {method} params: {label} must be a non-empty string")
    field_count = len(expr.split())
    if field_count not in {5, 6}:
        raise ValueError(
            f"invalid {method} params: {label} must be a 5-field or 6-field cron expression"
        )
    return expr


def _canonical_cron_tz(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _canonical_cron_stagger_ms(
    value: object,
    *,
    method: str,
    label: str,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"invalid {method} params: {label} must be a non-negative integer")
    return value


def _cron_expression_next_run_at_ms(
    *,
    expr: object,
    tz: object,
    after: datetime,
) -> int | None:
    normalized_expr = _canonical_cron_expr(
        expr,
        method="stored cron",
        label="schedule.expr",
    )
    if normalized_expr is None:
        return None
    try:
        schedule = _parse_cron_expression(normalized_expr)
    except ValueError:
        return None
    timezone = _cron_timezone(tz)
    start = (after.astimezone(timezone) + timedelta(seconds=1)).replace(microsecond=0)
    minute_cursor = start.replace(second=0)
    ordered_seconds = sorted(schedule.seconds)
    for _ in range(_CRON_LOOKAHEAD_MINUTES):
        if _cron_minute_matches(minute_cursor, schedule):
            for second in ordered_seconds:
                candidate = minute_cursor.replace(second=second)
                if candidate >= start:
                    return int(candidate.astimezone(UTC).timestamp() * 1000)
        minute_cursor += timedelta(minutes=1)
    return None


def cron_expression_next_run_at(
    *,
    expr: object,
    tz: object,
    after: datetime,
) -> str | None:
    next_run_at_ms = _cron_expression_next_run_at_ms(expr=expr, tz=tz, after=after)
    if next_run_at_ms is None:
        return None
    return datetime.fromtimestamp(next_run_at_ms / 1000, tz=UTC).isoformat()


def _cron_timezone(value: object) -> tzinfo:
    normalized_tz = _canonical_cron_tz(value)
    if normalized_tz is None:
        return UTC
    try:
        return ZoneInfo(normalized_tz)
    except ZoneInfoNotFoundError:
        return UTC


def _parse_cron_expression(expr: str) -> _ParsedCronSchedule:
    fields = expr.split()
    if len(fields) == 5:
        seconds = {0}
        minute_field, hour_field, day_field, month_field, weekday_field = fields
    elif len(fields) == 6:
        seconds = _parse_cron_field(fields[0], minimum=0, maximum=59)
        minute_field, hour_field, day_field, month_field, weekday_field = fields[1:]
    else:
        raise ValueError("cron expression must contain 5 or 6 fields")
    day_of_month_any = day_field in {"*", "?"}
    day_of_week_any = weekday_field in {"*", "?"}
    days_of_week = {
        0 if value == 7 else value
        for value in _parse_cron_field(weekday_field, minimum=0, maximum=7)
    }
    return _ParsedCronSchedule(
        seconds=seconds,
        minutes=_parse_cron_field(minute_field, minimum=0, maximum=59),
        hours=_parse_cron_field(hour_field, minimum=0, maximum=23),
        days_of_month=_parse_cron_field(day_field, minimum=1, maximum=31),
        months=_parse_cron_field(month_field, minimum=1, maximum=12),
        days_of_week=days_of_week,
        day_of_month_any=day_of_month_any,
        day_of_week_any=day_of_week_any,
    )


def _parse_cron_field(field: str, *, minimum: int, maximum: int) -> set[int]:
    normalized = field.strip()
    if normalized in {"*", "?"}:
        return set(range(minimum, maximum + 1))
    values: set[int] = set()
    for part in normalized.split(","):
        segment = part.strip()
        if not segment:
            raise ValueError("empty cron field segment")
        step = 1
        if "/" in segment:
            base, raw_step = segment.split("/", 1)
            if not raw_step.isdigit():
                raise ValueError("invalid cron field step")
            step = int(raw_step)
            if step < 1:
                raise ValueError("invalid cron field step")
        else:
            base = segment
        if base in {"*", "?"}:
            start, end = minimum, maximum
        elif "-" in base:
            raw_start, raw_end = base.split("-", 1)
            start = _parse_cron_int(raw_start, minimum=minimum, maximum=maximum)
            end = _parse_cron_int(raw_end, minimum=minimum, maximum=maximum)
            if end < start:
                raise ValueError("invalid cron field range")
        else:
            start = _parse_cron_int(base, minimum=minimum, maximum=maximum)
            end = start
        values.update(range(start, end + 1, step))
    if not values:
        raise ValueError("empty cron field")
    return values


def _parse_cron_int(value: str, *, minimum: int, maximum: int) -> int:
    raw = value.strip()
    if not raw.isdigit():
        raise ValueError("invalid cron field value")
    parsed = int(raw)
    if parsed < minimum or parsed > maximum:
        raise ValueError("cron field value out of range")
    return parsed


def _cron_minute_matches(moment: datetime, schedule: _ParsedCronSchedule) -> bool:
    cron_dow = (moment.weekday() + 1) % 7
    day_of_month_matches = moment.day in schedule.days_of_month
    day_of_week_matches = cron_dow in schedule.days_of_week
    if not schedule.day_of_month_any and not schedule.day_of_week_any:
        day_matches = day_of_month_matches or day_of_week_matches
    else:
        day_matches = day_of_month_matches and day_of_week_matches
    return (
        moment.minute in schedule.minutes
        and moment.hour in schedule.hours
        and moment.month in schedule.months
        and day_matches
    )


def build_gateway_cron_task_blueprint(job_create: dict[str, Any]) -> TaskBlueprintCreate:
    name = _require_cron_add_string(job_create.get("name"), label="name")
    description = _optional_cron_add_string(job_create.get("description"), label="description")
    agent_id = _optional_cron_add_string(job_create.get("agentId"), label="agentId")
    if agent_id is not None and agent_id != _GATEWAY_CRON_AGENT_ID:
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only agentId='openzues'"
        )
    cron_session_key = _normalized_cron_session_key(
        job_create.get("sessionKey"),
        method="cron.add",
        label="sessionKey",
    )
    if job_create.get("deleteAfterRun") not in {None, False}:
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only deleteAfterRun=false"
        )
    cron_failure_alert: dict[str, Any] | Literal[False] | None = None
    if "failureAlert" in job_create:
        cron_failure_alert = _normalized_cron_failure_alert(
            job_create.get("failureAlert"),
            method="cron.add",
            label="failureAlert",
        )
    notify = job_create.get("notify")
    if notify is not None and not isinstance(notify, bool):
        raise ValueError("invalid cron.add params: notify must be a boolean")

    requested_delivery_mode: str | None = None
    cron_delivery_mode: Literal["none", "announce", "webhook"] | None = None
    cron_delivery_channel: str | None = None
    cron_delivery_to: str | None = None
    cron_delivery_account_id: str | None = None
    cron_delivery_thread_id: str | int | None = None
    cron_delivery_best_effort: bool | None = None
    cron_delivery_failure_destination: dict[str, Any] | None = None
    delivery = job_create.get("delivery")
    if delivery is not None:
        if not isinstance(delivery, dict):
            raise ValueError("invalid cron.add params: delivery must be an object")
        _validate_gateway_cron_object_keys(
            delivery,
            method="cron.add",
            label="delivery",
            allowed_keys={
                "accountId",
                "bestEffort",
                "channel",
                "failureDestination",
                "mode",
                "threadId",
                "to",
            },
        )
        requested_delivery_mode = _optional_cron_add_string(
            delivery.get("mode"),
            label="delivery.mode",
        )
        if requested_delivery_mode is not None:
            requested_delivery_mode = requested_delivery_mode.lower()
            if requested_delivery_mode == "deliver":
                requested_delivery_mode = "announce"
        if requested_delivery_mode not in {None, "announce", "none", "webhook"}:
            raise ValueError(
                "invalid cron.add params: "
                "OpenZues currently supports only delivery.mode='announce', 'none', or 'webhook'"
            )
        if requested_delivery_mode is None:
            raise ValueError(
                "invalid cron.add params: delivery.mode must be one of: announce, none, webhook"
            )
        cron_delivery_channel = _validated_cron_delivery_channel(
            delivery.get("channel"),
            method="cron.add",
            label="delivery.channel",
        )
        cron_delivery_to = _optional_cron_add_string(
            delivery.get("to"),
            label="delivery.to",
        )
        cron_delivery_account_id = _optional_cron_add_string(
            delivery.get("accountId"),
            label="delivery.accountId",
        )
        cron_delivery_thread_id = _optional_cron_add_thread_value(
            delivery.get("threadId"),
            label="delivery.threadId",
        )
        if "bestEffort" in delivery:
            best_effort = delivery.get("bestEffort")
            if not isinstance(best_effort, bool):
                raise ValueError("invalid cron.add params: delivery.bestEffort must be a boolean")
            cron_delivery_best_effort = best_effort
        if "failureDestination" in delivery:
            cron_delivery_failure_destination = _normalized_cron_failure_destination(
                delivery.get("failureDestination"),
                method="cron.add",
                label="delivery.failureDestination",
            )

    schedule = job_create.get("schedule")
    if not isinstance(schedule, dict):
        raise ValueError("invalid cron.add params: schedule must be an object")
    schedule_kind = _schedule_kind_from_object(
        schedule,
        kind_label="schedule.kind",
        missing_error_message="invalid cron.add params: schedule.kind must be a non-empty string",
        require_kind=False,
    )
    cadence_minutes: int | None = None
    anchor_ms: int | None = None
    schedule_at: str | None = None
    schedule_cron_expr: str | None = None
    schedule_cron_tz: str | None = None
    schedule_cron_stagger_ms: int | None = None
    if schedule_kind == "every":
        _validate_gateway_cron_object_keys(
            schedule,
            method="cron.add",
            label="schedule",
            allowed_keys={"kind", "everyMs", "anchorMs"},
        )
        every_ms = schedule.get("everyMs")
        if isinstance(every_ms, bool) or not isinstance(every_ms, int):
            raise ValueError(
                "invalid cron.add params: "
                "schedule.everyMs must be a positive minute-aligned integer"
            )
        if every_ms < 60_000 or every_ms % 60_000 != 0:
            raise ValueError(
                "invalid cron.add params: "
                "schedule.everyMs must be a positive minute-aligned integer"
            )
        cadence_minutes = every_ms // 60_000
        if "anchorMs" in schedule:
            raw_anchor_ms = schedule.get("anchorMs")
            if (
                isinstance(raw_anchor_ms, bool)
                or not isinstance(raw_anchor_ms, int)
                or raw_anchor_ms < 0
            ):
                raise ValueError(
                    "invalid cron.add params: schedule.anchorMs must be a non-negative integer"
                )
            anchor_ms = raw_anchor_ms
    elif schedule_kind == "at":
        _validate_gateway_cron_object_keys(
            schedule,
            method="cron.add",
            label="schedule",
            allowed_keys={"kind", "at"},
        )
        schedule_at = _canonical_cron_schedule_at(
            schedule.get("at"),
            error_message="invalid cron.add params: schedule.at must be an ISO-8601 timestamp",
        )
        if schedule_at is None:
            raise ValueError("invalid cron.add params: schedule.at must be an ISO-8601 timestamp")
    elif schedule_kind == "cron":
        _validate_gateway_cron_object_keys(
            schedule,
            method="cron.add",
            label="schedule",
            allowed_keys={"kind", "expr", "tz", "staggerMs"},
        )
        schedule_cron_expr = _canonical_cron_expr(
            schedule.get("expr"),
            method="cron.add",
            label="schedule.expr",
        )
        if schedule_cron_expr is None:
            raise ValueError("invalid cron.add params: schedule.expr must be a non-empty string")
        schedule_cron_tz = _canonical_cron_tz(schedule.get("tz"))
        if "tz" in schedule and schedule_cron_tz is None:
            raise ValueError("invalid cron.add params: schedule.tz must be a string")
        schedule_cron_stagger_ms = _canonical_cron_stagger_ms(
            schedule.get("staggerMs"),
            method="cron.add",
            label="schedule.staggerMs",
        )
    else:
        raise ValueError(
            "invalid cron.add params: "
            "schedule.kind must be one of: at, cron, every"
        )

    session_target = _validated_cron_session_target(
        _require_cron_add_string(
            job_create.get("sessionTarget"),
            label="sessionTarget",
        ),
        method="cron.add",
        label="sessionTarget",
    )
    wake_mode = _require_cron_add_string(job_create.get("wakeMode"), label="wakeMode")
    if wake_mode not in {"now", "next-heartbeat"}:
        raise ValueError(
            "invalid cron.add params: wakeMode must be one of: next-heartbeat, now"
        )

    payload = job_create.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("invalid cron.add params: payload must be an object")
    payload_kind = _require_cron_add_string(payload.get("kind"), label="payload.kind")
    objective_template: str
    model: str | None = None
    cron_payload_text: str | None = None
    if payload_kind == "agentTurn":
        if session_target == "main":
            raise ValueError(
                "invalid cron.add params: "
                "payload.kind='agentTurn' requires sessionTarget to leave 'main'"
            )
        _validate_gateway_cron_object_keys(
            payload,
            method="cron.add",
            label="payload",
            allowed_keys={"kind", "message", "model"},
        )
        objective_template = _require_cron_add_string(
            payload.get("message"),
            label="payload.message",
        )
        model = _optional_cron_add_string(payload.get("model"), label="payload.model")
    elif payload_kind == "systemEvent":
        if session_target != "main":
            raise ValueError(
                "invalid cron.add params: payload.kind='systemEvent' requires sessionTarget='main'"
            )
        _validate_gateway_cron_object_keys(
            payload,
            method="cron.add",
            label="payload",
            allowed_keys={"kind", "text"},
        )
        objective_template = _require_cron_add_string(payload.get("text"), label="payload.text")
        cron_payload_text = objective_template
    else:
        raise ValueError(
            "invalid cron.add params: payload.kind must be one of: agentTurn, systemEvent"
        )
    if requested_delivery_mode == "announce":
        if payload_kind != "agentTurn" or session_target == "main":
            raise ValueError(
                "invalid cron.add params: "
                "delivery.mode='announce' requires payload.kind='agentTurn' "
                "and sessionTarget to leave 'main'"
            )
        cron_delivery_mode = None
    elif requested_delivery_mode == "webhook":
        if cron_delivery_to is None:
            raise ValueError(
                "invalid cron.add params: "
                "delivery.to must be a non-empty string when delivery.mode='webhook'"
            )
        cron_delivery_mode = "webhook"
    elif requested_delivery_mode == "none":
        cron_delivery_mode = "none"
    _validate_cron_delivery_targets(
        session_target=session_target,
        delivery_mode=cron_delivery_mode or "none",
        delivery_to=cron_delivery_to,
        failure_destination=cron_delivery_failure_destination,
        method="cron.add",
    )
    conversation_target = _cron_delivery_conversation_target(
        session_target=session_target,
        payload_kind=payload_kind,
        delivery_mode=cron_delivery_mode or "announce",
        delivery_channel=cron_delivery_channel,
        delivery_to=cron_delivery_to,
        delivery_account_id=cron_delivery_account_id,
    )

    enabled = job_create.get("enabled")
    if enabled is None:
        resolved_enabled = True
    elif isinstance(enabled, bool):
        resolved_enabled = enabled
    else:
        raise ValueError("invalid cron.add params: enabled must be a boolean")

    resolved_schedule_kind = cast(Literal["every", "at", "cron"], schedule_kind)

    return TaskBlueprintCreate(
        name=name,
        summary=description,
        objective_template=objective_template,
        conversation_target=conversation_target,
        cadence_minutes=cadence_minutes,
        schedule_anchor_ms=anchor_ms,
        schedule_kind=resolved_schedule_kind,
        schedule_at=schedule_at,
        schedule_cron_expr=schedule_cron_expr,
        schedule_cron_tz=schedule_cron_tz,
        schedule_cron_stagger_ms=schedule_cron_stagger_ms,
        cron_session_target=session_target,
        cron_session_key=cron_session_key,
        cron_wake_mode=cast(Literal["now", "next-heartbeat"], wake_mode),
        cron_payload_kind=cast(Literal["agentTurn", "systemEvent"], payload_kind),
        cron_payload_text=cron_payload_text,
        cron_delivery_mode=cron_delivery_mode,
        cron_delivery_channel=cron_delivery_channel,
        cron_delivery_to=cron_delivery_to,
        cron_delivery_account_id=cron_delivery_account_id,
        cron_delivery_thread_id=cron_delivery_thread_id,
        cron_delivery_best_effort=cron_delivery_best_effort,
        cron_delivery_failure_destination=cron_delivery_failure_destination,
        cron_failure_alert=cron_failure_alert,
        cron_notify_enabled=True if notify else None,
        model=model or "gpt-5.4",
        enabled=resolved_enabled,
    )


def build_gateway_cron_job_patch(
    task: dict[str, Any],
    patch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_gateway_cron_object_keys(
        patch,
        method="cron.update",
        label="patch",
        allowed_keys={
            "name",
            "agentId",
            "sessionKey",
            "notify",
            "description",
            "enabled",
            "deleteAfterRun",
            "schedule",
            "sessionTarget",
            "wakeMode",
            "payload",
            "delivery",
            "failureAlert",
            "state",
        },
    )
    row_updates: dict[str, Any] = {}
    payload_updates: dict[str, Any] = {}
    requested_delivery_mode: str | None = None

    if "name" in patch:
        row_updates["name"] = _require_cron_update_string(patch.get("name"), label="patch.name")
    if "description" in patch:
        description = patch.get("description")
        if description is not None and not isinstance(description, str):
            raise ValueError("invalid cron.update params: patch.description must be a string")
        row_updates["summary"] = (
            str(description).strip() or None if description is not None else None
        )
    if "enabled" in patch:
        enabled = patch.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("invalid cron.update params: patch.enabled must be a boolean")
        row_updates["enabled"] = int(enabled)

    if "agentId" in patch:
        agent_id = _optional_cron_update_string(patch.get("agentId"), label="patch.agentId")
        if agent_id is not None and agent_id != _GATEWAY_CRON_AGENT_ID:
            raise ValueError(
                "invalid cron.update params: "
                "OpenZues currently supports only patch.agentId='openzues'"
            )
    if "sessionKey" in patch:
        payload_updates["cron_session_key"] = _normalized_cron_session_key(
            patch.get("sessionKey"),
            method="cron.update",
            label="patch.sessionKey",
        )
    if patch.get("deleteAfterRun") not in {None, False}:
        raise ValueError(
            "invalid cron.update params: "
            "OpenZues currently supports only patch.deleteAfterRun=false"
        )
    if "failureAlert" in patch:
        payload_updates["cron_failure_alert"] = _merged_cron_failure_alert_patch(
            _task_payload_fields(task).get("cron_failure_alert"),
            patch.get("failureAlert"),
            label="patch.failureAlert",
        )
    if "state" in patch:
        payload_updates["cron_state"] = _merged_cron_state_patch(
            _task_payload_fields(task).get("cron_state"),
            patch.get("state"),
            label="patch.state",
        )
    if "notify" in patch:
        notify = patch.get("notify")
        if not isinstance(notify, bool):
            raise ValueError("invalid cron.update params: patch.notify must be a boolean")
        payload_updates["cron_notify_enabled"] = notify

    if "delivery" in patch:
        delivery = patch.get("delivery")
        if delivery is not None:
            if not isinstance(delivery, dict):
                raise ValueError("invalid cron.update params: patch.delivery must be an object")
            _validate_gateway_cron_object_keys(
                delivery,
                method="cron.update",
                label="patch.delivery",
                allowed_keys={
                    "accountId",
                    "bestEffort",
                    "channel",
                    "failureDestination",
                    "mode",
                    "threadId",
                    "to",
                },
            )
            requested_delivery_mode = _optional_cron_update_string(
                delivery.get("mode"),
                label="patch.delivery.mode",
            )
            if requested_delivery_mode is not None:
                requested_delivery_mode = requested_delivery_mode.lower()
                if requested_delivery_mode == "deliver":
                    requested_delivery_mode = "announce"
            if requested_delivery_mode not in {None, "announce", "none", "webhook"}:
                raise ValueError(
                    "invalid cron.update params: "
                    "OpenZues currently supports only "
                    "patch.delivery.mode='announce', 'none', or 'webhook'"
                )
            if "channel" in delivery:
                payload_updates["cron_delivery_channel"] = _validated_cron_delivery_channel(
                    delivery.get("channel"),
                    method="cron.update",
                    label="patch.delivery.channel",
                )
            if "to" in delivery:
                payload_updates["cron_delivery_to"] = _optional_cron_update_string(
                    delivery.get("to"),
                    label="patch.delivery.to",
                )
            if "accountId" in delivery:
                payload_updates["cron_delivery_account_id"] = _optional_cron_update_string(
                    delivery.get("accountId"),
                    label="patch.delivery.accountId",
                )
            if "threadId" in delivery:
                payload_updates["cron_delivery_thread_id"] = _optional_cron_update_thread_value(
                    delivery.get("threadId"),
                    label="patch.delivery.threadId",
                )
            if "bestEffort" in delivery:
                best_effort = delivery.get("bestEffort")
                if not isinstance(best_effort, bool):
                    raise ValueError(
                        "invalid cron.update params: patch.delivery.bestEffort must be a boolean"
                    )
                payload_updates["cron_delivery_best_effort"] = best_effort
            if "failureDestination" in delivery:
                payload_updates["cron_delivery_failure_destination"] = (
                    _merged_cron_failure_destination_patch(
                        _task_payload_fields(task).get("cron_delivery_failure_destination"),
                        delivery.get("failureDestination"),
                        label="patch.delivery.failureDestination",
                    )
                )

    if "schedule" in patch:
        schedule = patch.get("schedule")
        if not isinstance(schedule, dict):
            raise ValueError("invalid cron.update params: patch.schedule must be an object")
        schedule_kind = _optional_cron_update_string(
            schedule.get("kind"),
            label="patch.schedule.kind",
        )
        if schedule_kind is None:
            if schedule.get("at") is not None:
                schedule_kind = "at"
            elif schedule.get("everyMs") is not None or schedule.get("anchorMs") is not None:
                schedule_kind = "every"
            else:
                raise ValueError(
                    "invalid cron.update params: patch.schedule.kind must be a non-empty string"
                )
        if schedule_kind == "every":
            _validate_gateway_cron_object_keys(
                schedule,
                method="cron.update",
                label="patch.schedule",
                allowed_keys={"kind", "everyMs", "anchorMs"},
            )
            every_ms = schedule.get("everyMs")
            if isinstance(every_ms, bool) or not isinstance(every_ms, int):
                raise ValueError(
                    "invalid cron.update params: "
                    "patch.schedule.everyMs must be a positive minute-aligned integer"
                )
            if every_ms < 60_000 or every_ms % 60_000 != 0:
                raise ValueError(
                    "invalid cron.update params: "
                    "patch.schedule.everyMs must be a positive minute-aligned integer"
                )
            row_updates["cadence_minutes"] = every_ms // 60_000
            payload_updates["schedule_kind"] = "every"
            payload_updates["schedule_at"] = None
            payload_updates["schedule_cron_expr"] = None
            payload_updates["schedule_cron_tz"] = None
            payload_updates["schedule_cron_stagger_ms"] = None
            if "anchorMs" in schedule:
                raw_anchor_ms = schedule.get("anchorMs")
                if (
                    isinstance(raw_anchor_ms, bool)
                    or not isinstance(raw_anchor_ms, int)
                    or raw_anchor_ms < 0
                ):
                    raise ValueError(
                        "invalid cron.update params: "
                        "patch.schedule.anchorMs must be a non-negative integer"
                    )
                payload_updates["schedule_anchor_ms"] = raw_anchor_ms
            else:
                payload_updates["schedule_anchor_ms"] = None
        elif schedule_kind == "at":
            _validate_gateway_cron_object_keys(
                schedule,
                method="cron.update",
                label="patch.schedule",
                allowed_keys={"kind", "at"},
            )
            payload_updates["schedule_kind"] = "at"
            payload_updates["schedule_at"] = _canonical_cron_schedule_at(
                schedule.get("at"),
                error_message=(
                    "invalid cron.update params: "
                    "patch.schedule.at must be an ISO-8601 timestamp"
                ),
            )
            if payload_updates["schedule_at"] is None:
                raise ValueError(
                    "invalid cron.update params: patch.schedule.at must be an ISO-8601 timestamp"
            )
            payload_updates["schedule_anchor_ms"] = None
            payload_updates["schedule_cron_expr"] = None
            payload_updates["schedule_cron_tz"] = None
            payload_updates["schedule_cron_stagger_ms"] = None
            row_updates["cadence_minutes"] = None
        elif schedule_kind == "cron":
            _validate_gateway_cron_object_keys(
                schedule,
                method="cron.update",
                label="patch.schedule",
                allowed_keys={"kind", "expr", "tz", "staggerMs"},
            )
            schedule_cron_expr = _canonical_cron_expr(
                schedule.get("expr"),
                method="cron.update",
                label="patch.schedule.expr",
            )
            if schedule_cron_expr is None:
                raise ValueError(
                    "invalid cron.update params: patch.schedule.expr must be a non-empty string"
                )
            schedule_cron_tz = _canonical_cron_tz(schedule.get("tz"))
            if "tz" in schedule and schedule_cron_tz is None:
                raise ValueError("invalid cron.update params: patch.schedule.tz must be a string")
            payload_updates["schedule_kind"] = "cron"
            payload_updates["schedule_at"] = None
            payload_updates["schedule_anchor_ms"] = None
            payload_updates["schedule_cron_expr"] = schedule_cron_expr
            payload_updates["schedule_cron_tz"] = schedule_cron_tz
            payload_updates["schedule_cron_stagger_ms"] = _canonical_cron_stagger_ms(
                schedule.get("staggerMs"),
                method="cron.update",
                label="patch.schedule.staggerMs",
            )
            row_updates["cadence_minutes"] = None
        else:
            raise ValueError(
                "invalid cron.update params: "
                "patch.schedule.kind must be one of: at, cron, every"
            )

    if "sessionTarget" in patch:
        session_target = _validated_cron_session_target(
            _require_cron_update_string(
                patch.get("sessionTarget"),
                label="patch.sessionTarget",
            ),
            method="cron.update",
            label="patch.sessionTarget",
        )
        payload_updates["cron_session_target"] = session_target
    if "wakeMode" in patch:
        wake_mode = _require_cron_update_string(patch.get("wakeMode"), label="patch.wakeMode")
        if wake_mode not in {"now", "next-heartbeat"}:
            raise ValueError(
                "invalid cron.update params: patch.wakeMode must be one of: next-heartbeat, now"
            )
        payload_updates["cron_wake_mode"] = wake_mode

    if "payload" in patch:
        payload = patch.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("invalid cron.update params: patch.payload must be an object")
        payload_updates.setdefault(
            "cron_session_target",
            _cron_session_target(_task_payload_fields(task)),
        )
        next_payload_kind = (
            _require_cron_update_string(payload.get("kind"), label="patch.payload.kind")
            if "kind" in payload
            else _cron_payload_kind(_task_payload_fields(task))
        )
        if next_payload_kind == "agentTurn":
            _validate_gateway_cron_object_keys(
                payload,
                method="cron.update",
                label="patch.payload",
                allowed_keys={"kind", "message", "model"},
            )
            if "message" in payload:
                payload_updates["objective_template"] = _require_cron_update_string(
                    payload.get("message"),
                    label="patch.payload.message",
                )
            if "model" in payload:
                payload_updates["model"] = _require_cron_update_string(
                    payload.get("model"),
                    label="patch.payload.model",
                )
            payload_updates["cron_payload_kind"] = "agentTurn"
            payload_updates["cron_payload_text"] = None
        elif next_payload_kind == "systemEvent":
            _validate_gateway_cron_object_keys(
                payload,
                method="cron.update",
                label="patch.payload",
                allowed_keys={"kind", "text"},
            )
            if "text" in payload:
                payload_updates["objective_template"] = _require_cron_update_string(
                    payload.get("text"),
                    label="patch.payload.text",
                )
            payload_updates["cron_payload_kind"] = "systemEvent"
            payload_updates["cron_payload_text"] = (
                payload_updates.get("objective_template")
                or _require_cron_update_string(
                    task.get("objective_template"),
                    label="existing payload.text",
                )
            )
        else:
            raise ValueError(
                "invalid cron.update params: "
                "patch.payload.kind must be one of: agentTurn, systemEvent"
            )

    if "payload" in patch and not payload_updates:
        _require_cron_update_string(
            task.get("objective_template"),
            label="existing payload.message",
        )

    effective_session_target = str(
        _patched_payload_value(payload_updates, task, "cron_session_target")
        or _cron_session_target(_task_payload_fields(task))
    ).strip()
    effective_payload_kind = str(
        _patched_payload_value(payload_updates, task, "cron_payload_kind")
        or _cron_payload_kind(_task_payload_fields(task))
    ).strip()
    existing_session_target = _cron_session_target(_task_payload_fields(task))
    existing_payload_kind = _cron_payload_kind(_task_payload_fields(task))
    if effective_payload_kind == "systemEvent" and effective_session_target != "main":
        raise ValueError(
            "invalid cron.update params: "
            "patch.payload.kind='systemEvent' requires patch.sessionTarget='main'"
        )
    if (
        existing_session_target == "main"
        and existing_payload_kind == "systemEvent"
        and effective_session_target == "main"
        and effective_payload_kind == "agentTurn"
    ):
        raise ValueError(
            "invalid cron.update params: "
            "patch.payload.kind='agentTurn' requires patch.sessionTarget to leave 'main'"
        )
    if requested_delivery_mode == "announce":
        if effective_payload_kind != "agentTurn" or effective_session_target == "main":
            if effective_payload_kind == "systemEvent" and effective_session_target == "main":
                payload_updates["cron_delivery_mode"] = None
                payload_updates["cron_delivery_channel"] = None
                payload_updates["cron_delivery_to"] = None
                payload_updates["cron_delivery_account_id"] = None
                payload_updates["cron_delivery_best_effort"] = None
                payload_updates["cron_delivery_failure_destination"] = None
            else:
                raise ValueError(
                    "invalid cron.update params: "
                    "patch.delivery.mode='announce' requires patch.payload.kind='agentTurn' "
                    "and sessionTarget to leave 'main'"
                )
        else:
            payload_updates["cron_delivery_mode"] = None
    elif requested_delivery_mode == "webhook":
        effective_delivery_to = str(
            payload_updates.get("cron_delivery_to")
            if "cron_delivery_to" in payload_updates
            else _task_payload_fields(task).get("cron_delivery_to")
            or ""
        ).strip()
        if not effective_delivery_to:
            raise ValueError(
                "invalid cron.update params: "
                "patch.delivery.to must be a non-empty string when patch.delivery.mode='webhook'"
            )
        payload_updates["cron_delivery_mode"] = "webhook"
    elif requested_delivery_mode == "none":
        payload_updates["cron_delivery_mode"] = "none"
    effective_delivery_mode = str(
        _patched_payload_value(payload_updates, task, "cron_delivery_mode") or ""
    ).strip().lower()
    if effective_delivery_mode not in {"announce", "none", "webhook"}:
        effective_delivery_mode = _cron_delivery_mode(_task_payload_fields(task))
    effective_delivery_to_value: str | None = (
        str(_patched_payload_value(payload_updates, task, "cron_delivery_to") or "").strip()
        or None
    )
    effective_failure_destination = cast(
        dict[str, Any] | None,
        _patched_payload_value(payload_updates, task, "cron_delivery_failure_destination"),
    )
    _validate_cron_delivery_targets(
        session_target=effective_session_target,
        delivery_mode=effective_delivery_mode,
        delivery_to=effective_delivery_to_value,
        failure_destination=effective_failure_destination,
        method="cron.update",
    )
    if {"delivery", "payload", "sessionTarget"} & set(patch):
        effective_delivery_channel = (
            str(
                payload_updates.get("cron_delivery_channel")
                if "cron_delivery_channel" in payload_updates
                else _task_payload_fields(task).get("cron_delivery_channel")
                or ""
            ).strip()
            or None
        )
        effective_delivery_account_id = (
            str(
                payload_updates.get("cron_delivery_account_id")
                if "cron_delivery_account_id" in payload_updates
                else _task_payload_fields(task).get("cron_delivery_account_id")
                or ""
            ).strip()
            or None
        )
        conversation_target = _cron_delivery_conversation_target(
            session_target=effective_session_target,
            payload_kind=effective_payload_kind,
            delivery_mode=effective_delivery_mode,
            delivery_channel=effective_delivery_channel,
            delivery_to=effective_delivery_to_value,
            delivery_account_id=effective_delivery_account_id,
        )
        payload_updates["conversation_target"] = (
            conversation_target.model_dump(mode="json")
            if conversation_target is not None
            else None
        )

    return row_updates, payload_updates


def _require_cron_add_string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.add params: {label} must be a non-empty string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"invalid cron.add params: {label} must be a non-empty string")
    return trimmed


def _optional_cron_add_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.add params: {label} must be a string")
    trimmed = value.strip()
    return trimmed or None


def _require_cron_update_string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.update params: {label} must be a non-empty string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"invalid cron.update params: {label} must be a non-empty string")
    return trimmed


def _optional_cron_update_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.update params: {label} must be a string")
    trimmed = value.strip()
    return trimmed or None


def _optional_cron_add_thread_value(value: object, *, label: str) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid cron.add params: {label} must be a string or integer")
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.add params: {label} must be a string or integer")
    trimmed = value.strip()
    return trimmed or None


def _optional_cron_update_thread_value(value: object, *, label: str) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid cron.update params: {label} must be a string or integer")
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError(f"invalid cron.update params: {label} must be a string or integer")
    trimmed = value.strip()
    return trimmed or None


def _validated_cron_delivery_channel(
    value: object,
    *,
    method: str,
    label: str,
) -> str | None:
    channel = (
        _optional_cron_add_string(value, label=label)
        if method == "cron.add"
        else _optional_cron_update_string(value, label=label)
    )
    if channel is None:
        return None
    normalized = channel.lower()
    if normalized == "last":
        return normalized
    if _CRON_DELIVERY_CHANNEL_ID_RE.fullmatch(normalized) is None:
        raise ValueError(
            f"invalid {method} params: {label} must be a provider id, not a target id"
        )
    return normalized


def _cron_delivery_conversation_target(
    *,
    session_target: str,
    payload_kind: str,
    delivery_mode: str,
    delivery_channel: str | None,
    delivery_to: str | None,
    delivery_account_id: str | None,
) -> ConversationTargetView | None:
    if payload_kind != "agentTurn" or session_target == "main" or delivery_mode != "announce":
        return None
    channel = str(delivery_channel or "").strip().lower() or None
    if channel in {None, "last"}:
        return None
    assert channel is not None
    account_id = str(delivery_account_id or "").strip() or None
    peer_id = str(delivery_to or "").strip() or None
    return ConversationTargetView(
        channel=channel,
        account_id=account_id,
        peer_kind="channel" if peer_id else None,
        peer_id=peer_id,
    )


def _normalize_custom_cron_session_target(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw.lower().startswith("session:"):
        return None
    suffix = raw[len("session:") :]
    if not suffix:
        return None
    segments = suffix.split(":")
    if not segments or any(
        not segment or _CRON_CUSTOM_SESSION_SEGMENT_RE.fullmatch(segment) is None
        for segment in segments
    ):
        return None
    return "session:" + ":".join(segments)


def _validated_cron_session_target(value: str, *, method: str, label: str) -> str:
    normalized = str(value).strip()
    lowered = normalized.lower()
    if lowered == "current":
        return "isolated"
    if lowered in {"main", "isolated"}:
        return lowered
    custom_target = _normalize_custom_cron_session_target(normalized)
    if custom_target is not None:
        return custom_target
    if lowered.startswith("session:"):
        raise ValueError("invalid cron sessionTarget session id")
    raise ValueError(f"invalid {method} params: {label} must be one of: current, isolated, main")


def _validate_gateway_cron_object_keys(
    payload: dict[str, Any],
    *,
    method: str,
    label: str,
    allowed_keys: set[str],
) -> None:
    unexpected = sorted(set(payload) - allowed_keys)
    if unexpected:
        joined = ", ".join(unexpected)
        raise ValueError(f"invalid {method} params: {label} does not accept: {joined}")


def _normalized_http_webhook_url(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


def _normalized_cron_failure_destination(
    value: object,
    *,
    method: str,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid {method} params: {label} must be an object")
    _validate_gateway_cron_object_keys(
        value,
        method=method,
        label=label,
        allowed_keys={"accountId", "channel", "mode", "to"},
    )
    normalized: dict[str, Any] = {}
    if "channel" in value:
        channel = _validated_cron_delivery_channel(
            value.get("channel"),
            method=method,
            label=f"{label}.channel",
        )
        if channel is not None:
            normalized["channel"] = channel
    if "to" in value:
        to = (
            _optional_cron_add_string(value.get("to"), label=f"{label}.to")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("to"), label=f"{label}.to")
        )
        if to is not None:
            normalized["to"] = to
    if "accountId" in value:
        account_id = (
            _optional_cron_add_string(value.get("accountId"), label=f"{label}.accountId")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("accountId"), label=f"{label}.accountId")
        )
        if account_id is not None:
            normalized["accountId"] = account_id
    if "mode" in value:
        mode = (
            _optional_cron_add_string(value.get("mode"), label=f"{label}.mode")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("mode"), label=f"{label}.mode")
        )
        if mode is not None:
            lowered = mode.lower()
            if lowered == "deliver":
                lowered = "announce"
            if lowered not in {"announce", "webhook"}:
                raise ValueError(
                    f"invalid {method} params: {label}.mode must be one of: announce, webhook"
                )
            normalized["mode"] = lowered
    return normalized


def _merged_cron_failure_destination_patch(
    existing: object,
    patch: object,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise ValueError(f"invalid cron.update params: {label} must be an object")
    _validate_gateway_cron_object_keys(
        patch,
        method="cron.update",
        label=label,
        allowed_keys={"accountId", "channel", "mode", "to"},
    )
    merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    if "channel" in patch:
        channel = _validated_cron_delivery_channel(
            patch.get("channel"),
            method="cron.update",
            label=f"{label}.channel",
        )
        if channel is None:
            merged.pop("channel", None)
        else:
            merged["channel"] = channel
    if "to" in patch:
        to = _optional_cron_update_string(patch.get("to"), label=f"{label}.to")
        if to is None:
            merged.pop("to", None)
        else:
            merged["to"] = to
    if "accountId" in patch:
        account_id = _optional_cron_update_string(
            patch.get("accountId"),
            label=f"{label}.accountId",
        )
        if account_id is None:
            merged.pop("accountId", None)
        else:
            merged["accountId"] = account_id
    if "mode" in patch:
        mode = _optional_cron_update_string(patch.get("mode"), label=f"{label}.mode")
        if mode is None:
            merged.pop("mode", None)
        else:
            lowered = mode.lower()
            if lowered == "deliver":
                lowered = "announce"
            if lowered not in {"announce", "webhook"}:
                raise ValueError(
                    f"invalid cron.update params: {label}.mode must be one of: announce, webhook"
                )
            merged["mode"] = lowered
    return merged


def _normalized_cron_failure_alert(
    value: object,
    *,
    method: str,
    label: str,
) -> dict[str, Any] | Literal[False] | None:
    if value is None:
        return None
    if value is False:
        return False
    if not isinstance(value, dict):
        raise ValueError(f"invalid {method} params: {label} must be false or an object")
    _validate_gateway_cron_object_keys(
        value,
        method=method,
        label=label,
        allowed_keys={"accountId", "after", "channel", "cooldownMs", "mode", "to"},
    )
    normalized: dict[str, Any] = {}
    if "after" in value:
        after = value.get("after")
        if isinstance(after, bool) or not isinstance(after, int) or after < 1:
            raise ValueError(f"invalid {method} params: {label}.after must be a positive integer")
        normalized["after"] = after
    if "channel" in value:
        channel = (
            _optional_cron_add_string(value.get("channel"), label=f"{label}.channel")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("channel"), label=f"{label}.channel")
        )
        if channel is None:
            raise ValueError(
                f"invalid {method} params: {label}.channel must be a non-empty string"
            )
        normalized["channel"] = channel
    if "to" in value:
        to = (
            _optional_cron_add_string(value.get("to"), label=f"{label}.to")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("to"), label=f"{label}.to")
        )
        if to is not None:
            normalized["to"] = to
    if "cooldownMs" in value:
        cooldown_ms = value.get("cooldownMs")
        if isinstance(cooldown_ms, bool) or not isinstance(cooldown_ms, int) or cooldown_ms < 0:
            raise ValueError(
                f"invalid {method} params: {label}.cooldownMs must be a non-negative integer"
            )
        normalized["cooldownMs"] = cooldown_ms
    if "mode" in value:
        mode = (
            _optional_cron_add_string(value.get("mode"), label=f"{label}.mode")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("mode"), label=f"{label}.mode")
        )
        if mode is None or mode.lower() not in {"announce", "webhook"}:
            raise ValueError(
                f"invalid {method} params: {label}.mode must be one of: announce, webhook"
            )
        normalized["mode"] = mode.lower()
    if "accountId" in value:
        account_id = (
            _optional_cron_add_string(value.get("accountId"), label=f"{label}.accountId")
            if method == "cron.add"
            else _optional_cron_update_string(value.get("accountId"), label=f"{label}.accountId")
        )
        if account_id is None:
            raise ValueError(
                f"invalid {method} params: {label}.accountId must be a non-empty string"
            )
        normalized["accountId"] = account_id
    return normalized


def _cron_state_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key in _CRON_STATE_INT_FIELDS:
        candidate = value.get(key)
        if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate < 0:
            continue
        normalized[key] = candidate
    for key in _CRON_STATE_TEXT_FIELDS:
        candidate = value.get(key)
        if isinstance(candidate, str):
            normalized[key] = candidate
    for key in _CRON_STATE_RUN_STATUS_FIELDS:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate in _CRON_RUN_STATUS_VALUES:
            normalized[key] = candidate
    candidate = value.get("lastErrorReason")
    if isinstance(candidate, str) and candidate in _CRON_FAILOVER_REASON_VALUES:
        normalized["lastErrorReason"] = candidate
    candidate = value.get("lastDelivered")
    if isinstance(candidate, bool):
        normalized["lastDelivered"] = candidate
    candidate = value.get("lastDeliveryStatus")
    if isinstance(candidate, str) and candidate in _CRON_DELIVERY_STATUS_VALUES:
        normalized["lastDeliveryStatus"] = candidate
    return normalized


def _normalized_cron_state_patch(
    value: object,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid cron.update params: {label} must be an object")
    _validate_gateway_cron_object_keys(
        value,
        method="cron.update",
        label=label,
        allowed_keys=_CRON_STATE_ALLOWED_KEYS,
    )
    normalized: dict[str, Any] = {}
    for key in _CRON_STATE_INT_FIELDS:
        if key not in value:
            continue
        candidate = value.get(key)
        if isinstance(candidate, bool) or not isinstance(candidate, int) or candidate < 0:
            raise ValueError(
                f"invalid cron.update params: {label}.{key} must be a non-negative integer"
            )
        normalized[key] = candidate
    for key in _CRON_STATE_TEXT_FIELDS:
        if key not in value:
            continue
        candidate = value.get(key)
        if not isinstance(candidate, str):
            raise ValueError(f"invalid cron.update params: {label}.{key} must be a string")
        normalized[key] = candidate
    for key in _CRON_STATE_RUN_STATUS_FIELDS:
        if key not in value:
            continue
        candidate = value.get(key)
        if not isinstance(candidate, str) or candidate not in _CRON_RUN_STATUS_VALUES:
            raise ValueError(
                f"invalid cron.update params: {label}.{key} must be one of: "
                "ok, error, skipped"
            )
        normalized[key] = candidate
    if "lastErrorReason" in value:
        candidate = value.get("lastErrorReason")
        if not isinstance(candidate, str) or candidate not in _CRON_FAILOVER_REASON_VALUES:
            raise ValueError(
                f"invalid cron.update params: {label}.lastErrorReason must be one of: "
                "auth, format, rate_limit, billing, timeout, model_not_found, unknown"
            )
        normalized["lastErrorReason"] = candidate
    if "lastDelivered" in value:
        candidate = value.get("lastDelivered")
        if not isinstance(candidate, bool):
            raise ValueError(
                f"invalid cron.update params: {label}.lastDelivered must be a boolean"
            )
        normalized["lastDelivered"] = candidate
    if "lastDeliveryStatus" in value:
        candidate = value.get("lastDeliveryStatus")
        if not isinstance(candidate, str) or candidate not in _CRON_DELIVERY_STATUS_VALUES:
            raise ValueError(
                f"invalid cron.update params: {label}.lastDeliveryStatus must be one of: "
                "delivered, not-delivered, not-requested, unknown"
            )
        normalized["lastDeliveryStatus"] = candidate
    return normalized


def _merged_cron_state_patch(
    existing: object,
    patch: object,
    *,
    label: str,
) -> dict[str, Any]:
    merged = _cron_state_payload(existing)
    merged.update(_normalized_cron_state_patch(patch, label=label))
    return merged


def _merged_cron_failure_alert_patch(
    existing: object,
    patch: object,
    *,
    label: str,
) -> dict[str, Any] | Literal[False] | None:
    if patch is False:
        return False
    if patch is None:
        if existing is False:
            return False
        return dict(existing) if isinstance(existing, dict) else None
    normalized = _normalized_cron_failure_alert(
        patch,
        method="cron.update",
        label=label,
    )
    if normalized is False or normalized is None:
        return normalized
    merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    assert isinstance(patch, dict)
    for key in ("after", "channel", "to", "cooldownMs", "mode", "accountId"):
        if key not in patch:
            continue
        if key in normalized:
            merged[key] = normalized[key]
        else:
            merged.pop(key, None)
    return merged


def _validate_cron_delivery_targets(
    *,
    session_target: str,
    delivery_mode: str,
    delivery_to: str | None,
    failure_destination: dict[str, Any] | None,
    method: str,
    update_label_prefix: str = "patch.",
) -> None:
    if delivery_mode == "webhook":
        target = _normalized_http_webhook_url(delivery_to)
        if target is None:
            prefix = update_label_prefix if method == "cron.update" else ""
            raise ValueError(
                f"invalid {method} params: {prefix}delivery.to must be a valid http(s) URL "
                "when "
                f"{prefix}delivery.mode='webhook'"
            )
    if not failure_destination:
        return
    if session_target == "main" and delivery_mode != "webhook":
        raise ValueError(
            'cron delivery.failureDestination is only supported for sessionTarget="isolated" '
            'unless delivery.mode="webhook"'
        )
    if failure_destination.get("mode") == "webhook":
        target = _normalized_http_webhook_url(str(failure_destination.get("to") or "").strip())
        if target is None:
            raise ValueError(
                "cron failure destination webhook requires delivery.failureDestination.to "
                "to be a valid http(s) URL"
            )
        failure_destination["to"] = target


def _maybe_task_blueprint_id_from_job_id(job_id: str) -> int | None:
    normalized_job_id = str(job_id).strip()
    if not normalized_job_id.startswith("task-blueprint:"):
        return None
    return _int_or_none(normalized_job_id.removeprefix("task-blueprint:"))


def _mission_run_status(mission: dict[str, Any]) -> CronRunStatus | None:
    normalized_status = str(mission.get("status") or "").strip().lower()
    if normalized_status == "completed":
        return "ok"
    if normalized_status == "failed":
        return "error"
    return None


def _mission_run_summary(mission: dict[str, Any]) -> str | None:
    for candidate in (
        mission.get("last_checkpoint"),
        mission.get("last_error"),
        mission.get("objective"),
    ):
        summary = _text_or_none(candidate)
        if summary is not None:
            return summary
    return None


def _normalized_run_statuses(
    *,
    statuses: tuple[CronRunStatus, ...] | None,
    status: CronRunStatusFilter | None,
) -> tuple[CronRunStatus, ...] | None:
    if statuses:
        return tuple(dict.fromkeys(statuses))
    if status == "ok":
        return ("ok",)
    if status == "error":
        return ("error",)
    if status == "skipped":
        return ("skipped",)
    return None


def _normalized_delivery_statuses(
    *,
    delivery_statuses: tuple[CronDeliveryStatus, ...] | None,
    delivery_status: CronDeliveryStatus | None,
) -> tuple[CronDeliveryStatus, ...] | None:
    if delivery_statuses:
        return tuple(dict.fromkeys(delivery_statuses))
    if delivery_status is not None:
        return (delivery_status,)
    return None


def _run_entry_matches_filters(
    entry: dict[str, Any],
    *,
    statuses: tuple[CronRunStatus, ...] | None,
    delivery_statuses: tuple[CronDeliveryStatus, ...] | None,
    query: str,
) -> bool:
    entry_status = entry.get("status")
    if statuses is not None and entry_status not in statuses:
        return False
    delivery_status = cast(CronDeliveryStatus, str(entry.get("deliveryStatus") or "not-requested"))
    if delivery_statuses is not None and delivery_status not in delivery_statuses:
        return False
    if not query:
        return True
    haystack = " ".join(
        part
        for part in (
            str(entry.get("summary") or ""),
            str(entry.get("error") or ""),
            str(entry.get("jobId") or ""),
            str(entry.get("jobName") or ""),
        )
        if part
    ).lower()
    return query in haystack
