from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from openzues.database import Database
from openzues.schemas import TaskBlueprintCreate

CronEnabledFilter = Literal["all", "enabled", "disabled"]
CronSortBy = Literal["nextRunAtMs", "updatedAtMs", "name"]
CronSortDir = Literal["asc", "desc"]
CronRunMode = Literal["due", "force"]
CronRunsScope = Literal["job", "all"]
CronRunStatus = Literal["ok", "error", "skipped"]
CronRunStatusFilter = Literal["all", "ok", "error", "skipped"]
CronDeliveryStatus = Literal["delivered", "not-delivered", "unknown", "not-requested"]


class GatewayCronService:
    def __init__(
        self,
        database: Database,
        *,
        create_task_blueprint: Callable[[TaskBlueprintCreate], Awaitable[object]] | None = None,
        run_task_blueprint_now: Callable[..., Awaitable[object]] | None = None,
        delete_task_blueprint: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self._database = database
        self._create_task_blueprint = create_task_blueprint
        self._run_task_blueprint_now = run_task_blueprint_now
        self._delete_task_blueprint = delete_task_blueprint

    @property
    def can_add_jobs(self) -> bool:
        return self._create_task_blueprint is not None

    @property
    def can_run_jobs(self) -> bool:
        return self._run_task_blueprint_now is not None

    @property
    def can_remove_jobs(self) -> bool:
        return self._delete_task_blueprint is not None

    async def status(self) -> dict[str, Any]:
        jobs = [
            self._job_payload(task)
            for task in await self._database.list_task_blueprint_records()
            if isinstance(task.get("cadence_minutes"), int)
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
            if isinstance(task.get("cadence_minutes"), int)
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
        created = await self._create_task_blueprint(build_gateway_cron_task_blueprint(job_create))
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
        if self._run_task_blueprint_now is None:
            raise RuntimeError("cron.run is unavailable until scheduled task launch is wired")
        task_blueprint_id = self._task_blueprint_id_from_job_id(job_id)
        task = await self._database.get_task_blueprint(task_blueprint_id)
        if task is None or not isinstance(task.get("cadence_minutes"), int):
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')
        if await self._task_has_active_mission(task_blueprint_id):
            return {"ok": True, "ran": False, "reason": "already-running"}
        if mode == "due" and not _task_is_due(task):
            return {"ok": True, "ran": False, "reason": "not-due"}
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
        if task is None or not isinstance(task.get("cadence_minutes"), int):
            return {"ok": True, "removed": False}
        await self._delete_task_blueprint(task_blueprint_id)
        return {"ok": True, "removed": True}

    async def update(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        task_blueprint_id = self._task_blueprint_id_from_job_id(job_id)
        task = await self._database.get_task_blueprint(task_blueprint_id)
        if task is None or not isinstance(task.get("cadence_minutes"), int):
            raise ValueError(f'unknown cron job "{_cron_job_id(task_blueprint_id)}"')

        row_updates, payload_updates = build_gateway_cron_job_patch(task, patch)
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
            if isinstance(task.get("cadence_minutes"), int)
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

        entries = [
            entry
            for mission in await self._database.list_missions()
            if (
                entry := self._mission_run_entry(
                    mission,
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
        ]
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
        cadence_minutes = cast(int, task["cadence_minutes"])
        payload_state = cast(dict[str, Any], task.get("payload") or {})
        objective_template = str(payload_state.get("objective_template") or "").strip()
        model = str(payload_state.get("model") or "").strip()
        payload: dict[str, Any] = {
            "kind": "agentTurn",
            "message": objective_template,
        }
        if model:
            payload["model"] = model
        return {
            "id": _cron_job_id(cast(int, task["id"])),
            "agentId": "openzues",
            "name": str(task.get("name") or "").strip(),
            "description": str(task.get("summary") or "").strip() or None,
            "enabled": bool(task.get("enabled")),
            "createdAtMs": _timestamp_ms(task.get("created_at")),
            "updatedAtMs": _timestamp_ms(task.get("updated_at")),
            "schedule": {"kind": "every", "everyMs": cadence_minutes * 60_000},
            "sessionTarget": "main",
            "wakeMode": "now",
            "payload": payload,
            "delivery": {"mode": "none"},
            "state": self._state_payload(
                task,
                payload_state=payload_state,
                cadence_minutes=cadence_minutes,
            ),
        }

    def _mission_run_entry(
        self,
        mission: dict[str, Any],
        *,
        tasks_by_id: dict[int, dict[str, Any]],
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
        delivery_status: CronDeliveryStatus = (
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
        cadence_minutes: int,
    ) -> dict[str, Any]:
        state: dict[str, Any] = {}
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
            next_run_at_ms = _next_run_at_ms(payload_state.get("last_launched_at"), cadence_minutes)
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
        haystack = " ".join(
            part
            for part in (
                str(job.get("name") or ""),
                str(job.get("description") or ""),
                str(job.get("agentId") or ""),
                str((job.get("payload") or {}).get("message") or ""),
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


def _next_run_at_ms(last_launched_at: object, cadence_minutes: int) -> int | None:
    last_run_at = _parse_timestamp(last_launched_at)
    if last_run_at is None:
        return None
    return int((last_run_at + timedelta(minutes=cadence_minutes)).timestamp() * 1000)


def _task_is_due(task: dict[str, Any]) -> bool:
    if not bool(task.get("enabled")):
        return False
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


def build_gateway_cron_task_blueprint(job_create: dict[str, Any]) -> TaskBlueprintCreate:
    name = _require_cron_add_string(job_create.get("name"), label="name")
    description = _optional_cron_add_string(job_create.get("description"), label="description")
    agent_id = _optional_cron_add_string(job_create.get("agentId"), label="agentId")
    if agent_id is not None and agent_id != "openzues":
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only agentId='openzues'"
        )
    if job_create.get("sessionKey") is not None:
        raise ValueError("invalid cron.add params: OpenZues does not support sessionKey routing")
    if job_create.get("deleteAfterRun") not in {None, False}:
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only deleteAfterRun=false"
        )
    if job_create.get("failureAlert") not in {None, False}:
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only failureAlert=false"
        )

    delivery = job_create.get("delivery")
    if delivery is not None:
        if not isinstance(delivery, dict):
            raise ValueError("invalid cron.add params: delivery must be an object")
        _validate_gateway_cron_object_keys(
            delivery,
            method="cron.add",
            label="delivery",
            allowed_keys={"mode"},
        )
        delivery_mode = _optional_cron_add_string(delivery.get("mode"), label="delivery.mode")
        if delivery_mode != "none":
            raise ValueError(
                "invalid cron.add params: OpenZues currently supports only delivery.mode='none'"
            )

    schedule = job_create.get("schedule")
    if not isinstance(schedule, dict):
        raise ValueError("invalid cron.add params: schedule must be an object")
    schedule_kind = _require_cron_add_string(schedule.get("kind"), label="schedule.kind")
    if schedule_kind != "every":
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only schedule.kind='every'"
        )
    _validate_gateway_cron_object_keys(
        schedule,
        method="cron.add",
        label="schedule",
        allowed_keys={"kind", "everyMs"},
    )
    every_ms = schedule.get("everyMs")
    if isinstance(every_ms, bool) or not isinstance(every_ms, int):
        raise ValueError(
            "invalid cron.add params: schedule.everyMs must be a positive minute-aligned integer"
        )
    if every_ms < 60_000 or every_ms % 60_000 != 0:
        raise ValueError(
            "invalid cron.add params: schedule.everyMs must be a positive minute-aligned integer"
        )

    session_target = _require_cron_add_string(
        job_create.get("sessionTarget"),
        label="sessionTarget",
    )
    if session_target != "main":
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only sessionTarget='main'"
        )
    wake_mode = _require_cron_add_string(job_create.get("wakeMode"), label="wakeMode")
    if wake_mode != "now":
        raise ValueError("invalid cron.add params: OpenZues currently supports only wakeMode='now'")

    payload = job_create.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("invalid cron.add params: payload must be an object")
    payload_kind = _require_cron_add_string(payload.get("kind"), label="payload.kind")
    if payload_kind != "agentTurn":
        raise ValueError(
            "invalid cron.add params: OpenZues currently supports only payload.kind='agentTurn'"
        )
    _validate_gateway_cron_object_keys(
        payload,
        method="cron.add",
        label="payload",
        allowed_keys={"kind", "message", "model"},
    )
    message = _require_cron_add_string(payload.get("message"), label="payload.message")
    model = _optional_cron_add_string(payload.get("model"), label="payload.model")

    enabled = job_create.get("enabled")
    if enabled is None:
        resolved_enabled = True
    elif isinstance(enabled, bool):
        resolved_enabled = enabled
    else:
        raise ValueError("invalid cron.add params: enabled must be a boolean")

    return TaskBlueprintCreate(
        name=name,
        summary=description,
        objective_template=message,
        cadence_minutes=every_ms // 60_000,
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
        if agent_id is not None and agent_id != "openzues":
            raise ValueError(
                "invalid cron.update params: "
                "OpenZues currently supports only patch.agentId='openzues'"
            )
    if patch.get("sessionKey") is not None:
        raise ValueError("invalid cron.update params: OpenZues does not support patch.sessionKey")
    if patch.get("deleteAfterRun") not in {None, False}:
        raise ValueError(
            "invalid cron.update params: "
            "OpenZues currently supports only patch.deleteAfterRun=false"
        )
    if patch.get("failureAlert") not in {None, False}:
        raise ValueError(
            "invalid cron.update params: OpenZues currently supports only patch.failureAlert=false"
        )
    if "state" in patch:
        raise ValueError("invalid cron.update params: OpenZues does not support patch.state")

    if "delivery" in patch:
        delivery = patch.get("delivery")
        if delivery is not None:
            if not isinstance(delivery, dict):
                raise ValueError("invalid cron.update params: patch.delivery must be an object")
            _validate_gateway_cron_object_keys(
                delivery,
                method="cron.update",
                label="patch.delivery",
                allowed_keys={"mode"},
            )
            delivery_mode = _optional_cron_update_string(
                delivery.get("mode"),
                label="patch.delivery.mode",
            )
            if delivery_mode != "none":
                raise ValueError(
                    "invalid cron.update params: "
                    "OpenZues currently supports only patch.delivery.mode='none'"
                )

    if "schedule" in patch:
        schedule = patch.get("schedule")
        if not isinstance(schedule, dict):
            raise ValueError("invalid cron.update params: patch.schedule must be an object")
        schedule_kind = _require_cron_update_string(
            schedule.get("kind"),
            label="patch.schedule.kind",
        )
        if schedule_kind != "every":
            raise ValueError(
                "invalid cron.update params: "
                "OpenZues currently supports only patch.schedule.kind='every'"
            )
        _validate_gateway_cron_object_keys(
            schedule,
            method="cron.update",
            label="patch.schedule",
            allowed_keys={"kind", "everyMs"},
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

    if "sessionTarget" in patch:
        session_target = _require_cron_update_string(
            patch.get("sessionTarget"),
            label="patch.sessionTarget",
        )
        if session_target != "main":
            raise ValueError(
                "invalid cron.update params: "
                "OpenZues currently supports only patch.sessionTarget='main'"
            )
    if "wakeMode" in patch:
        wake_mode = _require_cron_update_string(patch.get("wakeMode"), label="patch.wakeMode")
        if wake_mode != "now":
            raise ValueError(
                "invalid cron.update params: OpenZues currently supports only patch.wakeMode='now'"
            )

    if "payload" in patch:
        payload = patch.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("invalid cron.update params: patch.payload must be an object")
        if "kind" in payload:
            payload_kind = _require_cron_update_string(
                payload.get("kind"),
                label="patch.payload.kind",
            )
            if payload_kind != "agentTurn":
                raise ValueError(
                    "invalid cron.update params: "
                    "OpenZues currently supports only patch.payload.kind='agentTurn'"
                )
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

    if "payload" in patch and not payload_updates:
        _require_cron_update_string(
            task.get("objective_template"),
            label="existing payload.message",
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
