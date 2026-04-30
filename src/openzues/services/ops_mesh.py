from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from openzues.database import Database, utcnow
from openzues.schemas import (
    ConversationTargetPeerKind,
    ConversationTargetView,
    DashboardAccessPostureView,
    DashboardAuthPostureView,
    DashboardIntegrationInventoryItemView,
    DashboardIntegrationLaneView,
    DashboardIntegrationsInventoryView,
    DashboardOpsMeshView,
    DashboardSkillbookView,
    DashboardSkillGapView,
    DashboardSkillRegistryLaneView,
    DashboardSkillRegistryProjectView,
    DashboardSkillRegistrySkillView,
    DashboardSkillsRegistryView,
    DashboardTaskInboxItemView,
    DashboardTaskInboxView,
    DashboardTaskView,
    InstanceView,
    IntegrationCreate,
    IntegrationInventoryReadiness,
    IntegrationInventorySourceKind,
    IntegrationView,
    LaneCapabilityStatus,
    LaneSnapshotView,
    MissionCreate,
    MissionDraftView,
    MissionReflexRun,
    MissionView,
    NotificationRouteCreate,
    NotificationRouteTestResultView,
    NotificationRouteView,
    OperatorView,
    OutboundDeliveryReplayBatchView,
    OutboundDeliveryReplayResultView,
    OutboundDeliveryView,
    PlaybookRun,
    PlaybookView,
    ProjectView,
    RemoteRequestView,
    SignalLevel,
    SkillPinCreate,
    SkillPinView,
    TaskBlueprintCreate,
    TaskBlueprintView,
    TaskStatus,
    TeamView,
    VaultSecretCreate,
    VaultSecretView,
)
from openzues.services.continuity import build_continuity_packet
from openzues.services.ecc_catalog import build_ecc_workspace_lines
from openzues.services.gateway_canvas_documents import resolve_canvas_http_path_to_local_path
from openzues.services.gateway_cron import cron_expression_next_run_at
from openzues.services.gateway_message_actions import GatewayMessageActionDispatchRequest
from openzues.services.gateway_outbound_runtime import (
    GatewayOutboundRuntimeMessageRequest,
    GatewayOutboundRuntimePollRequest,
    GatewayOutboundRuntimeService,
    GatewayOutboundRuntimeUnavailableError,
)
from openzues.services.gateway_wake import GatewayWakeService
from openzues.services.hermes_runtime_profile import (
    DEFAULT_HERMES_EXECUTOR,
    DEFAULT_HERMES_MEMORY_PROVIDER,
    build_executor_profile_lines,
    build_memory_provider_lines,
    build_runtime_profile_summary,
    executor_label,
    load_saved_runtime_preferences,
    memory_provider_label,
)
from openzues.services.hermes_skills import is_local_skill_source_available
from openzues.services.hermes_toolsets import (
    build_hermes_tool_policy,
    build_hermes_tool_policy_lines,
    infer_hermes_toolsets,
)
from openzues.services.hub import BroadcastHub
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import (
    MEMPALACE_WRITEBACK_ACTION,
    build_mempalace_protocol_lines,
    has_mempalace_integration,
    is_mempalace_integration,
)
from openzues.services.missions import MissionService
from openzues.services.playbooks import PlaybookService, summarize_playbook_result
from openzues.services.reflexes import build_reflex_deck
from openzues.services.scope_enforcer import build_scope_assessment
from openzues.services.session_keys import (
    DEFAULT_ACCOUNT_ID,
    build_launch_session_key,
    canonicalize_session_key,
    normalize_optional_account_id,
    resolve_thread_session_keys,
)
from openzues.services.skillbook import materialize_skillbook_pins
from openzues.services.vault import VaultDecryptionError, VaultService, mask_secret

logger = logging.getLogger(__name__)
DEFAULT_TASK_COMPLETION_MARKER = "TASK COMPLETE"
OPENCLAW_PARITY_CHECKPOINT_LEDGER = "docs/openclaw-parity-checkpoint-2026-04-10.md"
OPENCLAW_PARITY_OLD_INVENTORY_SENTENCE = (
    "First inventory the OpenClaw surface area across gateway, onboarding, CLI, channels, "
    "routing, voice, canvas, nodes, skills, browser, packaging, and companion apps."
)
OPENCLAW_PARITY_OLD_SLICE_SENTENCE = (
    "Then choose the highest-leverage missing parity slice in OpenZues, implement it end to end "
    "in production quality, run the relevant verification, and leave a checkpoint that names "
    "what was completed, what remains, and the next best slice."
)
OPENCLAW_PARITY_BASELINE_TOOLSETS = (
    "debugging",
    "delegation",
    "memory",
    "session_search",
)
OUTBOUND_DELIVERY_MAX_RETRIES = 5
OUTBOUND_DELIVERY_BACKOFF_SECONDS = (5, 25, 120, 600)
SLACK_API_BASE_URL = "https://slack.com/api"
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
ZALO_API_BASE_URL = "https://bot-api.zaloplatforms.com"
NATIVE_PROVIDER_ROUTE_KINDS = {"slack", "telegram", "discord", "whatsapp", "zalo"}
PROBEABLE_NATIVE_PROVIDER_ROUTE_KINDS = {"slack", "telegram", "discord"}
DEFAULT_CRON_FAILURE_ALERT_AFTER = 2
DEFAULT_CRON_FAILURE_ALERT_COOLDOWN_MS = 60 * 60_000
DEFAULT_CRON_RETRY_MAX_ATTEMPTS = 3
DEFAULT_CRON_RETRY_BACKOFF_MS = (30_000, 60_000, 5 * 60_000)
DEFAULT_CRON_RETRY_ON = (
    "rate_limit",
    "overloaded",
    "network",
    "timeout",
    "server_error",
)
OUTBOUND_DELIVERY_PERMANENT_ERROR_PATTERNS = (
    re.compile(r"chat not found", re.IGNORECASE),
    re.compile(r"user not found", re.IGNORECASE),
    re.compile(r"recipient is not a valid", re.IGNORECASE),
    re.compile(r"outbound not configured for channel", re.IGNORECASE),
    re.compile(r"user .* not in room", re.IGNORECASE),
)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(UTC) - parsed).total_seconds() // 60))


def _timestamp_ms(value: datetime | str | None) -> int | None:
    parsed: datetime | None
    if isinstance(value, datetime):
        parsed = value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    else:
        parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return int(parsed.timestamp() * 1000)


def _requires_secret(auth_scheme: str) -> bool:
    return auth_scheme.strip().lower() not in {"", "none", "anonymous"}


def _format_cadence(cadence_minutes: int | None) -> str:
    if cadence_minutes is None:
        return "Manual only"
    if cadence_minutes % 60 == 0:
        hours = cadence_minutes // 60
        return f"Every {hours}h"
    return f"Every {cadence_minutes}m"


def _task_completion_marker(task: TaskBlueprintView) -> str:
    marker = (task.completion_marker or "").strip()
    return marker or DEFAULT_TASK_COMPLETION_MARKER


def _task_targets_openclaw_parity(task: TaskBlueprintView) -> bool:
    values = (
        task.name,
        task.summary,
        task.objective_template,
        task.completion_marker,
    )
    blob = " ".join(str(value or "") for value in values).lower()
    return "parity" in blob and ("openclaw" in blob or "parity complete" in blob)


def _normalized_task_objective_template(task: TaskBlueprintView) -> str:
    objective = str(task.objective_template or "").strip()
    if not objective or not _task_targets_openclaw_parity(task):
        return objective
    replacement = (
        f"Resume from the verified checkpoint in `{OPENCLAW_PARITY_CHECKPOINT_LEDGER}` "
        "instead of rebuilding the full source inventory. Choose the next bounded missing seam "
        "named there, implement it end to end in production quality, run the focused "
        "verification for that seam, and leave a checkpoint that names what was completed, "
        "what remains, and the next best slice."
    )
    old_block = (
        f"{OPENCLAW_PARITY_OLD_INVENTORY_SENTENCE} {OPENCLAW_PARITY_OLD_SLICE_SENTENCE}"
    )
    if old_block in objective:
        return objective.replace(old_block, replacement)
    if OPENCLAW_PARITY_OLD_INVENTORY_SENTENCE in objective:
        return objective.replace(OPENCLAW_PARITY_OLD_INVENTORY_SENTENCE, replacement)
    return objective


def _openclaw_parity_task_toolsets(task: TaskBlueprintView) -> list[str]:
    toolsets: list[str] = []
    if task.run_verification:
        toolsets.append("debugging")
    if task.use_builtin_agents:
        toolsets.append("delegation")
    toolsets.extend(
        toolset
        for toolset in OPENCLAW_PARITY_BASELINE_TOOLSETS
        if toolset not in toolsets
    )
    return toolsets


def _task_has_terminal_completion(
    task: TaskBlueprintView,
    summary: str | None,
) -> bool:
    if not task.run_until_complete:
        return False
    marker = _task_completion_marker(task).lower()
    return bool(summary and marker in summary.lower())


def _task_continuation_next_run_at(task: TaskBlueprintView) -> str | None:
    if not task.enabled or not task.run_until_complete:
        return None
    if _task_has_terminal_completion(task, task.last_result_summary):
        return None
    last = _parse_timestamp(task.last_launched_at)
    if last is None:
        return utcnow()
    if task.last_status in {None, "", "idle", "active"}:
        return None
    if task.last_status in {"completed", "failed"}:
        return (last + timedelta(minutes=task.continuation_cooldown_minutes)).isoformat()
    return None


def _task_scheduled_next_run_at(task: TaskBlueprintView) -> str | None:
    if not task.enabled:
        return None
    if task.schedule_kind == "at":
        scheduled_at = _parse_timestamp(task.schedule_at)
        if scheduled_at is None:
            return None
        last = _parse_timestamp(task.last_launched_at)
        status = str(task.last_status or "").strip().lower()
        retry_at = _task_cron_state_next_run_at(task)
        if status == "failed" and retry_at is not None:
            return retry_at.isoformat()
        if last is not None and status in {"completed", "failed"} and scheduled_at <= last:
            return None
        return scheduled_at.isoformat()
    if task.schedule_kind == "cron":
        base = _parse_timestamp(task.last_launched_at) or task.created_at
        return cron_expression_next_run_at(
            expr=task.schedule_cron_expr,
            tz=task.schedule_cron_tz,
            after=base,
        )
    if task.cadence_minutes is None:
        return None
    last = _parse_timestamp(task.last_launched_at)
    if last is None:
        return utcnow()
    return (last + timedelta(minutes=task.cadence_minutes)).isoformat()


def _task_cron_session_target(task: TaskBlueprintView) -> str:
    session_target = str(task.cron_session_target or "").strip()
    lowered = session_target.lower()
    if lowered == "current":
        return "isolated"
    if lowered in {"main", "isolated"}:
        return lowered
    if lowered.startswith("session:"):
        suffix = session_target[len("session:") :]
        segments = suffix.split(":")
        if suffix and all(
            segment
            and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", segment, re.IGNORECASE) is not None
            for segment in segments
        ):
            return "session:" + ":".join(segments)
    return "main"


def _task_cron_session_key(task: TaskBlueprintView) -> str | None:
    session_key = str(task.cron_session_key or "").strip()
    return session_key or None


def _task_cron_wake_mode(task: TaskBlueprintView) -> str:
    wake_mode = str(task.cron_wake_mode or "").strip().lower()
    if wake_mode in {"now", "next-heartbeat"}:
        return wake_mode
    return "now"


def _task_cron_payload_kind(task: TaskBlueprintView) -> str:
    payload_kind = str(task.cron_payload_kind or "").strip()
    if payload_kind in {"agentTurn", "systemEvent"}:
        return payload_kind
    return "agentTurn"


def _task_routes_through_gateway_wake(task: TaskBlueprintView) -> bool:
    return (
        _task_cron_session_target(task) == "main"
        and _task_cron_payload_kind(task) == "systemEvent"
    )


def _task_cron_payload_text(task: TaskBlueprintView) -> str:
    text = str(task.cron_payload_text or "").strip()
    return text or str(task.objective_template or "").strip()


def _task_cron_delivery_mode(task: TaskBlueprintView) -> str:
    delivery_mode = str(task.cron_delivery_mode or "").strip().lower()
    if delivery_mode in {"announce", "webhook"}:
        return delivery_mode
    return "none"


def _task_cron_delivery_to(task: TaskBlueprintView) -> str | None:
    target = str(task.cron_delivery_to or "").strip()
    return target or None


def _task_cron_delivery_account_id(task: TaskBlueprintView) -> str | None:
    account_id = str(task.cron_delivery_account_id or "").strip()
    return account_id or None


def _task_cron_delivery_thread_id(
    task: TaskBlueprintView,
) -> str | int | None:
    raw_thread_id = task.cron_delivery_thread_id
    if isinstance(raw_thread_id, int) and not isinstance(raw_thread_id, bool):
        return raw_thread_id
    thread_id = str(raw_thread_id or "").strip()
    return thread_id or None


def _task_cron_delivery_channel(task: TaskBlueprintView) -> str | None:
    channel = str(task.cron_delivery_channel or "").strip().lower()
    return channel or None


def _task_cron_notify_enabled(task: TaskBlueprintView) -> bool:
    return bool(task.cron_notify_enabled)


def _task_cron_failure_destination(task: TaskBlueprintView) -> dict[str, Any] | None:
    value = task.cron_delivery_failure_destination
    return dict(value) if isinstance(value, dict) else None


def _task_cron_failure_alert(task: TaskBlueprintView) -> dict[str, Any] | None:
    value = task.cron_failure_alert
    return dict(value) if isinstance(value, dict) else None


def _task_cron_delete_after_run(task: TaskBlueprintView) -> bool:
    return task.cron_delete_after_run is True


def _task_is_gateway_cron_task(task: TaskBlueprintView) -> bool:
    return (
        task.cadence_minutes is not None
        or task.schedule_kind in {"at", "cron", "every"}
        or task.cron_failure_alert is not None
    )


def _task_cron_state(task: TaskBlueprintView) -> dict[str, Any]:
    value = task.cron_state
    return dict(value) if isinstance(value, dict) else {}


def _task_cron_state_next_run_at(task: TaskBlueprintView) -> datetime | None:
    value = _task_cron_state(task).get("nextRunAtMs")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _cron_failure_alert_int(value: object, fallback: int, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return fallback
    return value if value >= minimum else fallback


def _cron_failure_alert_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _cron_result_status(status: object) -> Literal["ok", "error", "skipped"] | None:
    normalized = str(status or "").strip().lower()
    if normalized == "completed":
        return "ok"
    if normalized == "failed":
        return "error"
    if normalized == "skipped":
        return "skipped"
    return None


def _cron_result_error_text(mission: dict[str, Any]) -> str | None:
    error = str(mission.get("last_error") or mission.get("last_checkpoint") or "").strip()
    return error or None


def _cron_error_reason(error: str | None) -> str | None:
    lowered = str(error or "").strip().lower()
    if not lowered:
        return None
    if any(token in lowered for token in ("timeout", "timed out", "etimedout")):
        return "timeout"
    if any(token in lowered for token in ("401", "403", "auth", "unauthorized", "api key")):
        return "auth"
    if any(token in lowered for token in ("429", "rate limit", "too many requests")):
        return "rate_limit"
    if any(token in lowered for token in ("billing", "quota", "credit", "payment")):
        return "billing"
    if any(token in lowered for token in ("json", "schema", "parse", "format")):
        return "format"
    if any(token in lowered for token in ("model not found", "unknown model", "no such model")):
        return "model_not_found"
    return None


def _resolve_cron_retry_config(config: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(config) if isinstance(config, dict) else {}
    max_attempts_value = raw.get("maxAttempts")
    max_attempts = (
        max(0, min(10, max_attempts_value))
        if isinstance(max_attempts_value, int) and not isinstance(max_attempts_value, bool)
        else DEFAULT_CRON_RETRY_MAX_ATTEMPTS
    )
    raw_backoff = raw.get("backoffMs")
    backoff_ms = (
        tuple(
            value
            for value in raw_backoff
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        )
        if isinstance(raw_backoff, list)
        else ()
    )
    if not backoff_ms:
        backoff_ms = DEFAULT_CRON_RETRY_BACKOFF_MS
    raw_retry_on = raw.get("retryOn")
    retry_on = (
        tuple(
            str(value).strip()
            for value in raw_retry_on
            if str(value).strip() in DEFAULT_CRON_RETRY_ON
        )
        if isinstance(raw_retry_on, list)
        else ()
    )
    return {
        "maxAttempts": max_attempts,
        "backoffMs": backoff_ms,
        "retryOn": retry_on or DEFAULT_CRON_RETRY_ON,
    }


def _cron_error_backoff_ms(consecutive_errors: int, schedule_ms: tuple[int, ...]) -> int:
    if not schedule_ms:
        return DEFAULT_CRON_RETRY_BACKOFF_MS[0]
    index = min(max(0, consecutive_errors - 1), len(schedule_ms) - 1)
    return schedule_ms[index]


def _is_transient_cron_error(error: str | None, retry_on: tuple[str, ...]) -> bool:
    lowered = str(error or "").strip().lower()
    if not lowered:
        return False
    patterns: dict[str, tuple[str, ...]] = {
        "rate_limit": (
            "rate_limit",
            "rate limit",
            "too many requests",
            "429",
            "resource has been exhausted",
            "cloudflare",
            "tokens per day",
        ),
        "overloaded": (
            "529",
            "overloaded",
            "high demand",
            "temporarily overloaded",
            "temporary overloaded",
            "capacity exceeded",
        ),
        "network": ("network", "econnreset", "econnrefused", "fetch failed", "socket"),
        "timeout": ("timeout", "timed out", "etimedout"),
        "server_error": ("500", "502", "503", "504", "505", "506", "507", "508", "509"),
    }
    return any(
        any(token in lowered for token in patterns.get(reason, ()))
        for reason in retry_on
    )


def _cron_runtime_window_ms(
    task: TaskBlueprintView,
    mission: dict[str, Any],
) -> tuple[int, int]:
    started_at_ms = (
        _timestamp_ms(task.last_launched_at)
        or _timestamp_ms(str(mission.get("created_at") or "") or None)
        or _timestamp_ms(datetime.now(UTC))
        or 0
    )
    ended_at_ms = (
        _timestamp_ms(str(mission.get("last_activity_at") or "") or None)
        or _timestamp_ms(str(mission.get("updated_at") or "") or None)
        or started_at_ms
    )
    return started_at_ms, max(started_at_ms, ended_at_ms)


def _cron_delivery_state(
    task: TaskBlueprintView,
    *,
    error: str | None,
) -> dict[str, Any]:
    if _task_cron_delivery_mode(task) == "none" and not _task_cron_notify_enabled(task):
        return {"lastDeliveryStatus": "not-requested"}
    return {
        "lastDeliveryStatus": "unknown",
        "lastDeliveryError": error,
    }


def _resolve_cron_failure_alert(
    task: TaskBlueprintView,
    global_config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if task.cron_failure_alert is False:
        return None
    job_config = _task_cron_failure_alert(task)
    global_alert_config = dict(global_config) if isinstance(global_config, dict) else None
    if job_config is None and not (
        isinstance(global_alert_config, dict)
        and global_alert_config.get("enabled") is True
    ):
        return None
    config = job_config or {}
    mode = _cron_failure_alert_text(config.get("mode")) or _cron_failure_alert_text(
        None if global_alert_config is None else global_alert_config.get("mode")
    )
    explicit_to = _cron_failure_alert_text(config.get("to"))
    channel = (
        _cron_failure_alert_text(config.get("channel"))
        or _task_cron_delivery_channel(task)
        or "last"
    )
    return {
        "after": _cron_failure_alert_int(
            config.get(
                "after",
                None if global_alert_config is None else global_alert_config.get("after"),
            ),
            DEFAULT_CRON_FAILURE_ALERT_AFTER,
            minimum=1,
        ),
        "cooldownMs": _cron_failure_alert_int(
            config.get(
                "cooldownMs",
                None
                if global_alert_config is None
                else global_alert_config.get("cooldownMs"),
            ),
            DEFAULT_CRON_FAILURE_ALERT_COOLDOWN_MS,
            minimum=0,
        ),
        "channel": channel,
        "to": explicit_to if mode == "webhook" else explicit_to or _task_cron_delivery_to(task),
        "mode": mode,
        "accountId": _cron_failure_alert_text(config.get("accountId"))
        or _cron_failure_alert_text(
            None if global_alert_config is None else global_alert_config.get("accountId")
        ),
    }


def _cron_failure_alert_message(
    task: TaskBlueprintView,
    *,
    consecutive_errors: int,
    error: str | None,
) -> str:
    truncated_error = (str(error or "").strip() or "unknown error")[:200]
    return (
        f'Cron job "{task.name or task.id}" failed {consecutive_errors} times\n'
        f"Last error: {truncated_error}"
    )


def _build_explicit_announce_conversation_target(
    *,
    channel: str | None,
    to: str | None,
    account_id: str | None,
) -> ConversationTargetView | None:
    normalized_channel = str(channel or "").strip().lower()
    if not normalized_channel or normalized_channel == "last":
        return None
    peer_id = str(to or "").strip() or None
    normalized_account_id = str(account_id or "").strip() or None
    return ConversationTargetView(
        channel=normalized_channel,
        account_id=normalized_account_id,
        peer_kind=_provider_peer_kind_from_target(peer_id) if peer_id else None,
        peer_id=peer_id,
    )


def _task_explicit_announce_conversation_target(
    task: TaskBlueprintView,
) -> ConversationTargetView | None:
    if (
        _task_cron_payload_kind(task) != "agentTurn"
        or _task_cron_delivery_mode(task) == "webhook"
    ):
        return None
    return _build_explicit_announce_conversation_target(
        channel=_task_cron_delivery_channel(task),
        to=_task_cron_delivery_to(task),
        account_id=_task_cron_delivery_account_id(task),
    )


def _failure_destination_explicit_announce_target(
    failure_destination: dict[str, Any] | None,
) -> ConversationTargetView | None:
    if not failure_destination:
        return None
    if str(failure_destination.get("mode") or "").strip().lower() != "announce":
        return None
    return _build_explicit_announce_conversation_target(
        channel=(
            str(failure_destination.get("channel") or "").strip().lower() or None
        ),
        to=str(failure_destination.get("to") or "").strip() or None,
        account_id=str(failure_destination.get("accountId") or "").strip() or None,
    )


def _announce_delivery_session_key(
    conversation_target: ConversationTargetView,
    *,
    thread_id: str | None = None,
) -> str:
    base_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=conversation_target,
    )
    return resolve_thread_session_keys(
        base_session_key=base_session_key,
        thread_id=thread_id,
    ).session_key


def _normalized_delivery_thread_id(
    thread_id: str | int | None,
) -> str | None:
    if isinstance(thread_id, int) and not isinstance(thread_id, bool):
        return str(thread_id)
    normalized = str(thread_id or "").strip()
    return normalized or None


def _normalized_http_webhook_url(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


def _http_error_detail(exc: HTTPError) -> str | None:
    try:
        body = exc.read().strip()
    except Exception:
        return None
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        detail = body.decode("utf-8", errors="replace").strip()
        return detail[:180] if detail else None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("message", "code", "type"):
                detail = str(error.get(key) or "").strip()
                if detail:
                    return detail[:180]
        if error not in (None, "", [], {}):
            return str(error).strip()[:180]
        for key in ("message", "detail", "description"):
            detail = str(payload.get(key) or "").strip()
            if detail:
                return detail[:180]
    return str(payload).strip()[:180]


def _http_error_message(prefix: str, exc: HTTPError) -> str:
    detail = _http_error_detail(exc)
    message = f"{prefix} {exc.code}"
    return f"{message}: {detail}" if detail else message


def _slack_api_endpoint(target: str | None, method: str) -> str:
    normalized = str(target or "").strip() or SLACK_API_BASE_URL
    if normalized.rstrip("/").endswith(f"/{method}"):
        endpoint = normalized
    else:
        endpoint = f"{normalized.rstrip('/')}/{method}"
    if _normalized_http_webhook_url(endpoint) is None:
        raise RuntimeError("Slack route target must be an http(s) Slack API base URL.")
    return endpoint


def _slack_bearer_token(secret_token: str | None) -> str:
    token = str(secret_token or "").strip()
    if not token:
        raise RuntimeError("Slack route is missing a bot token secret.")
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _slack_channel_id(target: str | None) -> str | None:
    normalized = str(target or "").strip()
    while ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        if prefix.strip().lower() in {"channel", "group", "dm", "direct", "slack"}:
            normalized = suffix.strip()
            continue
        break
    return normalized or None


def _slack_reaction_name(raw: str | None) -> str:
    normalized = str(raw or "").strip()
    if not normalized:
        raise RuntimeError("Emoji is required for Slack reactions")
    return normalized.strip(":")


def _message_action_param_string(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
    allow_empty: bool = False,
) -> str | None:
    value = params.get(key)
    if value is None:
        if required:
            raise RuntimeError(f"{key} is required.")
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"{key} must be a string.")
    trimmed = value.strip()
    if required and not trimmed and not allow_empty:
        raise RuntimeError(f"{key} is required.")
    if not trimmed and not allow_empty:
        return None
    return trimmed


def _message_action_param_string_or_number(
    params: dict[str, Any],
    key: str,
    *,
    required: bool = False,
) -> str | None:
    value = params.get(key)
    if value is None:
        if required:
            raise RuntimeError(f"{key} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise RuntimeError(f"{key} must be a string or number.")
    trimmed = str(value).strip()
    if required and not trimmed:
        raise RuntimeError(f"{key} is required.")
    return trimmed or None


def _message_action_param_positive_int(
    params: dict[str, Any],
    *keys: str,
) -> int | None:
    for key in keys:
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, bool):
            raise RuntimeError(f"{key} must be a positive integer.")
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            try:
                parsed = int(trimmed)
            except ValueError as exc:
                raise RuntimeError(f"{key} must be a positive integer.") from exc
        else:
            raise RuntimeError(f"{key} must be a positive integer.")
        if parsed <= 0:
            raise RuntimeError(f"{key} must be a positive integer.")
        return parsed
    return None


def _provider_peer_kind_from_target(target: str | None) -> ConversationTargetPeerKind:
    normalized = str(target or "").strip().lower()
    if normalized.startswith(("direct:", "dm:")):
        return "direct"
    if normalized.startswith("group:"):
        return "group"
    return "channel"


def _slack_message_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    candidate = result.get("ts")
    message = result.get("message")
    if candidate is None and isinstance(message, dict):
        candidate = message.get("ts")
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _slack_channel_from_result(result: object, fallback: str) -> str:
    if isinstance(result, dict):
        candidate = result.get("channel")
        message = result.get("message")
        if candidate is None and isinstance(message, dict):
            candidate = message.get("channel")
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return fallback


def _parse_slack_channel_resolve_input(raw: str) -> dict[str, str]:
    trimmed = raw.strip()
    if not trimmed:
        return {}
    mention = re.match(r"^<#([A-Z0-9]+)(?:\|([^>]+))?>$", trimmed, re.IGNORECASE)
    if mention:
        parsed: dict[str, str] = {"id": str(mention.group(1)).upper()}
        name = str(mention.group(2) or "").strip()
        if name:
            parsed["name"] = name
        return parsed
    prefixed = re.sub(r"^(slack:|channel:)", "", trimmed, flags=re.IGNORECASE)
    if re.match(r"^[CG][A-Z0-9]+$", prefixed, re.IGNORECASE):
        return {"id": prefixed.upper()}
    name = prefixed.removeprefix("#").strip()
    return {"name": name} if name else {}


def _unresolved_channel_target(input_value: str, note: str) -> dict[str, object]:
    return {
        "input": input_value,
        "resolved": False,
        "note": note,
    }


def _resolve_slack_channel_target(
    input_value: str,
    channels: list[dict[str, object]],
) -> dict[str, object]:
    parsed = _parse_slack_channel_resolve_input(input_value)
    parsed_id = parsed.get("id")
    if parsed_id:
        match = next(
            (
                channel
                for channel in channels
                if str(channel.get("id") or "").strip().upper() == parsed_id
            ),
            None,
        )
        payload: dict[str, object] = {
            "input": input_value,
            "resolved": True,
            "id": parsed_id,
        }
        name = str((match or {}).get("name") or parsed.get("name") or "").strip()
        if name:
            payload["name"] = name
        if bool((match or {}).get("archived")):
            payload["note"] = "archived"
        return payload
    parsed_name = str(parsed.get("name") or "").strip().lower()
    if parsed_name:
        matches = [
            channel
            for channel in channels
            if str(channel.get("name") or "").strip().lower() == parsed_name
        ]
        if matches:
            match = next(
                (channel for channel in matches if not bool(channel.get("archived"))),
                matches[0],
            )
            payload = {
                "input": input_value,
                "resolved": True,
                "id": str(match.get("id") or ""),
                "name": str(match.get("name") or ""),
            }
            if bool(match.get("archived")):
                payload["note"] = "archived"
            return payload
    return {
        "input": input_value,
        "resolved": False,
    }


def _parse_slack_user_resolve_input(raw: str) -> dict[str, str]:
    trimmed = raw.strip()
    if not trimmed:
        return {}
    mention = re.match(r"^<@([A-Z0-9]+)>$", trimmed, re.IGNORECASE)
    if mention:
        return {"id": str(mention.group(1)).upper()}
    prefixed = re.sub(r"^(slack:|user:)", "", trimmed, flags=re.IGNORECASE)
    if re.match(r"^[A-Z][A-Z0-9]+$", prefixed, re.IGNORECASE):
        return {"id": prefixed.upper()}
    if "@" in trimmed and not trimmed.startswith("@"):
        return {"email": trimmed.lower()}
    name = trimmed.removeprefix("@").strip()
    return {"name": name} if name else {}


def _slack_user_display_name(user: dict[str, object] | None) -> str:
    if user is None:
        return ""
    for key in ("displayName", "realName", "name"):
        value = str(user.get(key) or "").strip()
        if value:
            return value
    return ""


def _score_slack_user(user: dict[str, object], parsed: dict[str, str]) -> int:
    score = 0
    if not bool(user.get("deleted")):
        score += 3
    if not bool(user.get("isBot")) and not bool(user.get("isAppUser")):
        score += 2
    parsed_email = str(parsed.get("email") or "").strip().lower()
    if parsed_email and str(user.get("email") or "").strip().lower() == parsed_email:
        score += 5
    parsed_name = str(parsed.get("name") or "").strip().lower()
    if parsed_name:
        candidates = {
            str(user.get("name") or "").strip().lower(),
            str(user.get("displayName") or "").strip().lower(),
            str(user.get("realName") or "").strip().lower(),
        }
        if parsed_name in candidates:
            score += 2
    return score


def _resolve_slack_user_from_matches(
    input_value: str,
    matches: list[dict[str, object]],
    parsed: dict[str, str],
) -> dict[str, object]:
    best = sorted(
        matches,
        key=lambda user: _score_slack_user(user, parsed),
        reverse=True,
    )[0]
    payload: dict[str, object] = {
        "input": input_value,
        "resolved": True,
        "id": str(best.get("id") or ""),
    }
    name = _slack_user_display_name(best)
    if name:
        payload["name"] = name
    if len(matches) > 1:
        payload["note"] = "multiple matches; chose best"
    return payload


def _resolve_slack_user_target(
    input_value: str,
    users: list[dict[str, object]],
) -> dict[str, object]:
    parsed = _parse_slack_user_resolve_input(input_value)
    parsed_id = parsed.get("id")
    if parsed_id:
        match = next(
            (
                user
                for user in users
                if str(user.get("id") or "").strip().upper() == parsed_id
            ),
            None,
        )
        payload: dict[str, object] = {
            "input": input_value,
            "resolved": True,
            "id": parsed_id,
        }
        name = _slack_user_display_name(match)
        if name:
            payload["name"] = name
        return payload
    parsed_email = str(parsed.get("email") or "").strip().lower()
    if parsed_email:
        matches = [
            user
            for user in users
            if str(user.get("email") or "").strip().lower() == parsed_email
        ]
        if matches:
            return _resolve_slack_user_from_matches(input_value, matches, parsed)
    parsed_name = str(parsed.get("name") or "").strip().lower()
    if parsed_name:
        matches = [
            user
            for user in users
            if parsed_name
            in {
                str(user.get("name") or "").strip().lower(),
                str(user.get("displayName") or "").strip().lower(),
                str(user.get("realName") or "").strip().lower(),
            }
        ]
        if matches:
            return _resolve_slack_user_from_matches(input_value, matches, parsed)
    return {
        "input": input_value,
        "resolved": False,
    }


def _slack_media_filename(media_url: str, index: int) -> str:
    parsed = urlparse(media_url)
    name = unquote(Path(parsed.path).name).strip()
    if name and "." in name:
        return name[:120]
    return f"openzues-media-{index}.bin"


def _telegram_bot_token(secret_token: str | None) -> str:
    token = str(secret_token or "").strip()
    if token.lower().startswith("bot"):
        token = token[3:].strip()
    if not token:
        raise RuntimeError("Telegram route is missing a bot token secret.")
    return token


def _telegram_api_endpoint(target: str | None, token: str, method: str) -> str:
    base_url = str(target or "").strip() or TELEGRAM_API_BASE_URL
    if f"/bot{token}/" in base_url:
        endpoint = f"{base_url.rstrip('/')}/{method}"
    else:
        endpoint = f"{base_url.rstrip('/')}/bot{token}/{method}"
    if _normalized_http_webhook_url(endpoint) is None:
        raise RuntimeError("Telegram route target must be an http(s) Bot API base URL.")
    return endpoint


def _strip_telegram_target_prefixes(target: str | None) -> str:
    normalized = str(target or "").strip()
    while ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        if prefix.strip().lower() in {
            "channel",
            "group",
            "dm",
            "direct",
            "telegram",
            "tg",
        }:
            normalized = suffix.strip()
            continue
        break
    return normalized


def _parse_telegram_delivery_target(target: str | None) -> dict[str, str]:
    normalized = _strip_telegram_target_prefixes(target)
    topic_match = re.match(r"^(.+?):topic:(\d+)$", normalized)
    if topic_match:
        return {
            "chatId": str(topic_match.group(1)).strip(),
            "threadId": str(topic_match.group(2)).strip(),
        }
    colon_match = re.match(r"^(.+):(\d+)$", normalized)
    if colon_match:
        return {
            "chatId": str(colon_match.group(1)).strip(),
            "threadId": str(colon_match.group(2)).strip(),
        }
    return {"chatId": normalized}


def _telegram_chat_id(target: str | None) -> str | None:
    chat_id = _parse_telegram_delivery_target(target).get("chatId")
    return str(chat_id or "").strip() or None


def _telegram_result_items(result: object) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    payload = result.get("result")
    if isinstance(payload, dict):
        return [cast(dict[str, Any], payload)]
    if isinstance(payload, list):
        return [cast(dict[str, Any], item) for item in payload if isinstance(item, dict)]
    return []


def _telegram_result_payload(result: object) -> dict[str, Any]:
    items = _telegram_result_items(result)
    return items[0] if items else {}


def _telegram_message_id(result: object) -> str | None:
    payload = _telegram_result_payload(result)
    candidate = payload.get("message_id")
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _telegram_chat_from_result(result: object, fallback: str) -> str:
    payload = _telegram_result_payload(result)
    chat = payload.get("chat")
    if isinstance(chat, dict):
        candidate = chat.get("id") or chat.get("username")
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return fallback


def _telegram_poll_id(result: object) -> str | None:
    payload = _telegram_result_payload(result)
    poll = payload.get("poll")
    if isinstance(poll, dict):
        candidate = poll.get("id")
        if candidate is not None:
            return str(candidate).strip() or None
    return None


def _telegram_media_ids(result: object) -> list[str]:
    media_ids: list[str] = []
    for payload in _telegram_result_items(result):
        photos = payload.get("photo")
        photo_ids: list[str] = []
        if isinstance(photos, list):
            for photo in photos:
                if not isinstance(photo, dict):
                    continue
                file_id = str(photo.get("file_id") or "").strip()
                if file_id:
                    photo_ids.append(file_id)
        if photo_ids:
            media_ids.append(photo_ids[-1])
            continue
        for media_key in ("document", "video", "animation", "audio", "voice"):
            media = payload.get(media_key)
            if not isinstance(media, dict):
                continue
            file_id = str(media.get("file_id") or "").strip()
            if file_id:
                media_ids.append(file_id)
                break
    return media_ids


DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_APP_FLAG_GATEWAY_PRESENCE = 1 << 12
DISCORD_APP_FLAG_GATEWAY_PRESENCE_LIMITED = 1 << 13
DISCORD_APP_FLAG_GATEWAY_GUILD_MEMBERS = 1 << 14
DISCORD_APP_FLAG_GATEWAY_GUILD_MEMBERS_LIMITED = 1 << 15
DISCORD_APP_FLAG_GATEWAY_MESSAGE_CONTENT = 1 << 18
DISCORD_APP_FLAG_GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19


def _discord_api_endpoint(path: str) -> str:
    normalized = str(path or "").strip().lstrip("/")
    if not normalized:
        raise RuntimeError("Discord API path is missing.")
    return f"{DISCORD_API_BASE}/{normalized}"


def _discord_bot_authorization(secret_token: str | None) -> str:
    token = str(secret_token or "").strip()
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    if not token:
        raise RuntimeError("Discord route is missing a bot token secret.")
    return f"Bot {token}"


def _discord_action_channel_id(raw: str | None) -> str | None:
    resolved = _parse_discord_channel_resolve_input(str(raw or ""))
    channel_id = resolved.get("channelId")
    return str(channel_id or "").strip() or None


def _discord_reaction_identifier(raw: str | None) -> str:
    trimmed = str(raw or "").strip()
    if not trimmed:
        raise RuntimeError("Emoji is required for Discord reactions.")
    custom_match = re.match(r"^<a?:([^:>]+):(\d+)>$", trimmed)
    identifier = (
        f"{custom_match.group(1)}:{custom_match.group(2)}"
        if custom_match
        else re.sub("[\ufe0e\ufe0f]", "", trimmed)
    )
    return quote(identifier, safe="")


def _discord_reaction_identifier_from_payload(emoji: object) -> str | None:
    if not isinstance(emoji, dict):
        return None
    raw_name = emoji.get("name")
    name = str(raw_name).strip() if raw_name is not None else ""
    raw_id = emoji.get("id")
    emoji_id = str(raw_id).strip() if raw_id is not None else ""
    if name and emoji_id:
        return f"{name}:{emoji_id}"
    return name or None


def _parse_discord_channel_resolve_input(raw: str) -> dict[str, object]:
    trimmed = raw.strip()
    if not trimmed:
        return {}
    mention = re.match(r"^<#(\d+)>$", trimmed)
    if mention:
        return {"channelId": str(mention.group(1))}
    channel_prefix = re.match(r"^(?:channel:|discord:)?(\d+)$", trimmed, re.IGNORECASE)
    if channel_prefix:
        return {"channelId": str(channel_prefix.group(1))}
    guild_prefix = re.match(r"^(?:guild:|server:)(\d+)$", trimmed, re.IGNORECASE)
    if guild_prefix:
        return {"guildId": str(guild_prefix.group(1)), "guildOnly": True}
    split = trimmed.split("/") if "/" in trimmed else trimmed.split("#")
    if len(split) >= 2:
        guild = str(split[0] or "").strip()
        channel = "#".join(split[1:]).strip()
        if not channel:
            return {"guild": guild, "guildOnly": True} if guild else {}
        if guild.isdigit():
            payload: dict[str, object] = {"guildId": guild}
            if channel.isdigit():
                payload["channelId"] = channel
            else:
                payload["channel"] = channel
            return payload
        return {"guild": guild, "channel": channel}
    return {"guild": trimmed, "guildOnly": True}


def _parse_discord_user_resolve_input(raw: str) -> dict[str, str]:
    trimmed = raw.strip()
    if not trimmed:
        return {}
    mention = re.match(r"^<@!?(\d+)>$", trimmed)
    if mention:
        return {"userId": str(mention.group(1))}
    prefixed = re.match(r"^(?:user:|discord:)?(\d+)$", trimmed, re.IGNORECASE)
    if prefixed:
        return {"userId": str(prefixed.group(1))}
    split = trimmed.split("/") if "/" in trimmed else trimmed.split("#")
    if len(split) >= 2:
        guild = str(split[0] or "").strip()
        user_name = "#".join(split[1:]).strip()
        if guild.isdigit():
            return {"guildId": guild, "userName": user_name}
        return {"guildName": guild, "userName": user_name}
    return {"userName": trimmed.removeprefix("@")}


def _normalize_discord_slug(value: str) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.removeprefix("#")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _discord_guild_match(
    guilds: list[dict[str, object]],
    *,
    guild_id: str | None = None,
    guild_name: str | None = None,
) -> dict[str, object] | None:
    normalized_guild_id = str(guild_id or "").strip()
    if normalized_guild_id:
        return next(
            (
                guild
                for guild in guilds
                if str(guild.get("id") or "").strip() == normalized_guild_id
            ),
            None,
        )
    slug = _normalize_discord_slug(str(guild_name or ""))
    if not slug:
        return None
    return next(
        (
            guild
            for guild in guilds
            if str(guild.get("slug") or "").strip() == slug
        ),
        None,
    )


def _prefer_active_discord_channel(
    channels: list[dict[str, object]],
) -> dict[str, object] | None:
    if not channels:
        return None

    def score(channel: dict[str, object]) -> int:
        channel_type = channel.get("type")
        is_thread = channel_type in {11, 12}
        archived = bool(channel.get("archived"))
        return (0 if archived else 2) + (0 if is_thread else 1)

    return sorted(channels, key=score, reverse=True)[0]


def _score_discord_member(member: dict[str, object], query: str) -> int:
    normalized_query = str(query or "").strip().lower()
    if not normalized_query:
        return 0
    user = member.get("user")
    if not isinstance(user, dict):
        return 0
    candidates = [
        str(user.get("username") or "").strip().lower(),
        str(user.get("global_name") or "").strip().lower(),
        str(member.get("nick") or "").strip().lower(),
    ]
    candidates = [candidate for candidate in candidates if candidate]
    score = 0
    if any(candidate == normalized_query for candidate in candidates):
        score += 3
    if any(normalized_query in candidate for candidate in candidates):
        score += 1
    if not bool(user.get("bot")):
        score += 1
    return score


def _discord_member_display_name(member: dict[str, object]) -> str:
    user = member.get("user")
    user_payload = user if isinstance(user, dict) else {}
    for value in (
        member.get("nick"),
        user_payload.get("global_name"),
        user_payload.get("username"),
    ):
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return ""


def _discord_privileged_intents_from_flags(flags: int) -> dict[str, str]:
    def resolve(enabled_bit: int, limited_bit: int) -> str:
        if flags & enabled_bit:
            return "enabled"
        if flags & limited_bit:
            return "limited"
        return "disabled"

    return {
        "presence": resolve(
            DISCORD_APP_FLAG_GATEWAY_PRESENCE,
            DISCORD_APP_FLAG_GATEWAY_PRESENCE_LIMITED,
        ),
        "guildMembers": resolve(
            DISCORD_APP_FLAG_GATEWAY_GUILD_MEMBERS,
            DISCORD_APP_FLAG_GATEWAY_GUILD_MEMBERS_LIMITED,
        ),
        "messageContent": resolve(
            DISCORD_APP_FLAG_GATEWAY_MESSAGE_CONTENT,
            DISCORD_APP_FLAG_GATEWAY_MESSAGE_CONTENT_LIMITED,
        ),
    }


def _discord_webhook_url(target: str | None) -> str:
    normalized = str(target or "").strip()
    if _normalized_http_webhook_url(normalized) is None:
        raise RuntimeError("Discord route target must be an http(s) webhook URL.")
    if "wait=" in (urlparse(normalized).query or ""):
        return normalized
    separator = "&" if "?" in normalized else "?"
    return f"{normalized}{separator}wait=true"


def _discord_message_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    candidate = result.get("id")
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _discord_channel_id(result: object, fallback: str) -> str:
    if isinstance(result, dict):
        normalized = str(result.get("channel_id") or "").strip()
        if normalized:
            return normalized
    return fallback


def _discord_poll_duration_hours(event: dict[str, Any]) -> int:
    duration_hours = _optional_int_payload_value(event, "durationHours")
    if duration_hours is not None:
        return max(1, duration_hours)
    duration_seconds = _optional_int_payload_value(event, "durationSeconds")
    if duration_seconds is not None:
        return max(1, (duration_seconds + 3599) // 3600)
    return 24


def _validate_telegram_poll_duration_options(
    *,
    duration_seconds: int | None,
    duration_hours: int | None,
) -> None:
    if duration_seconds is not None and duration_hours is not None:
        raise ValueError("durationSeconds and durationHours are mutually exclusive")
    if duration_seconds is None and duration_hours is not None:
        raise ValueError(
            "Telegram poll durationHours is not supported. "
            "Use durationSeconds (5-600) instead."
        )
    if duration_seconds is not None and not 5 <= duration_seconds <= 600:
        raise ValueError("Telegram poll durationSeconds must be between 5 and 600")


def _normalize_direct_channel_poll_options(options: list[str]) -> list[str]:
    return [normalized for option in options if (normalized := str(option).strip())]


def _validate_direct_channel_poll_shape(question: str, options: list[str]) -> None:
    if not question.strip():
        raise ValueError("Poll question is required")
    if len([option for option in options if option.strip()]) < 2:
        raise ValueError("Poll requires at least 2 options")


def _direct_channel_poll_max_options(channel: str) -> int:
    normalized = channel.strip().lower()
    if normalized in {"discord", "telegram"}:
        return 10
    return 12


def _validate_direct_channel_poll_option_count(
    channel: str,
    options: list[str],
) -> None:
    max_options = _direct_channel_poll_max_options(channel)
    cleaned = [option.strip() for option in options if option.strip()]
    if len(cleaned) > max_options:
        raise ValueError(f"Poll supports at most {max_options} options")


def _validate_direct_channel_poll_max_selections(
    options: list[str],
    max_selections: int | None,
) -> None:
    if max_selections is None:
        return
    cleaned = [option.strip() for option in options if option.strip()]
    if max_selections > len(cleaned):
        raise ValueError("maxSelections cannot exceed option count")


def _validate_direct_channel_poll_duration_exclusivity(
    *,
    duration_seconds: int | None,
    duration_hours: int | None,
) -> None:
    if duration_seconds is not None and duration_hours is not None:
        raise ValueError("durationSeconds and durationHours are mutually exclusive")


def _whatsapp_messages_endpoint(target: str | None) -> str:
    normalized = str(target or "").strip()
    if _normalized_http_webhook_url(normalized) is None:
        raise RuntimeError("WhatsApp route target must be an http(s) messages endpoint.")
    if normalized.rstrip("/").endswith("/messages"):
        return normalized
    return f"{normalized.rstrip('/')}/messages"


def _whatsapp_bearer_token(secret_token: str | None) -> str:
    token = str(secret_token or "").strip()
    if not token:
        raise RuntimeError("WhatsApp route is missing an access token secret.")
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _whatsapp_recipient_id(target: str | None) -> str | None:
    normalized = str(target or "").strip()
    while ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        if prefix.strip().lower() in {"whatsapp", "wa", "dm", "direct", "phone"}:
            normalized = suffix.strip()
            continue
        break
    normalized = normalized.replace(" ", "")
    return normalized or None


def _whatsapp_action_recipient_id(target: str | None) -> str | None:
    normalized = _whatsapp_recipient_id(target)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered.endswith("@g.us"):
        group_id = lowered.removesuffix("@g.us")
        if re.fullmatch(r"\d+(?:-\d+)*", group_id):
            return f"{group_id}@g.us"
        return None
    for pattern in (
        r"^(\d+)(?::\d+)?@s\.whatsapp\.net$",
        r"^(\d+)@c\.us$",
        r"^(\d+)@lid$",
    ):
        match = re.fullmatch(pattern, normalized, flags=re.IGNORECASE)
        if match is not None:
            return f"+{match.group(1)}"
    if "@" in normalized:
        return None
    digits = re.sub(r"\D", "", normalized)
    return f"+{digits}" if digits else None


def _whatsapp_reaction_context_message_id(
    request: GatewayMessageActionDispatchRequest,
    chat_target: str,
) -> str | None:
    tool_context = request.tool_context
    if tool_context is None:
        return None
    if str(tool_context.get("currentChannelProvider") or "") != "whatsapp":
        return None
    current_channel_id = tool_context.get("currentChannelId")
    if not isinstance(current_channel_id, str):
        return None
    current_target = _whatsapp_action_recipient_id(current_channel_id)
    requested_target = _whatsapp_action_recipient_id(chat_target)
    if current_target is None or requested_target is None or current_target != requested_target:
        return None
    current_message_id = tool_context.get("currentMessageId")
    if current_message_id is None:
        return None
    if isinstance(current_message_id, bool) or not isinstance(
        current_message_id,
        (str, int, float),
    ):
        raise RuntimeError("toolContext.currentMessageId must be a string or number.")
    return str(current_message_id).strip() or None


def _whatsapp_message_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    messages = result.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            message_id = str(message.get("id") or "").strip()
            if message_id:
                return message_id
    return None


def _whatsapp_contact_id(result: object, fallback: str) -> str:
    if isinstance(result, dict):
        contacts = result.get("contacts")
        if isinstance(contacts, list):
            for contact in contacts:
                if not isinstance(contact, dict):
                    continue
                candidate = str(contact.get("wa_id") or contact.get("input") or "").strip()
                if candidate:
                    return candidate
    return fallback


def _whatsapp_apply_reply_context(payload: dict[str, Any], reply_to_id: str) -> None:
    normalized_reply_to_id = reply_to_id.strip()
    if normalized_reply_to_id:
        payload["context"] = {"message_id": normalized_reply_to_id}


def _fixed_text_chunks(text: str, *, limit: int) -> list[str]:
    if not text:
        return [""]
    safe_limit = max(1, limit)
    return [text[index : index + safe_limit] for index in range(0, len(text), safe_limit)]


def _whatsapp_text_chunks(text: str, *, limit: int = 4000) -> list[str]:
    return _fixed_text_chunks(text, limit=limit)


def _zalo_text_chunks(text: str, *, limit: int = 2000) -> list[str]:
    return _fixed_text_chunks(text, limit=limit)


def _zalo_bot_token(secret_token: str | None) -> str:
    token = str(secret_token or "").strip()
    if not token:
        raise RuntimeError("Zalo route is missing a bot token secret.")
    return token


def _zalo_api_endpoint(target: str | None, token: str, method: str) -> str:
    base_url = str(target or "").strip() or ZALO_API_BASE_URL
    if f"/bot{token}/" in base_url:
        endpoint = f"{base_url.rstrip('/')}/{method}"
    else:
        endpoint = f"{base_url.rstrip('/')}/bot{token}/{method}"
    if _normalized_http_webhook_url(endpoint) is None:
        raise RuntimeError("Zalo route target must be an http(s) Bot API base URL.")
    return endpoint


def _zalo_chat_id(target: str | None) -> str | None:
    normalized = str(target or "").strip()
    while ":" in normalized:
        prefix, suffix = normalized.split(":", 1)
        if prefix.strip().lower() in {"channel", "group", "dm", "direct", "zalo"}:
            normalized = suffix.strip()
            continue
        break
    return normalized or None


def _zalo_message_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    payload = result.get("result")
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("message_id")
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _zalo_chat_from_result(result: object, fallback: str) -> str:
    if isinstance(result, dict):
        payload = result.get("result")
        if isinstance(payload, dict):
            chat = payload.get("chat")
            if isinstance(chat, dict):
                candidate = str(chat.get("id") or "").strip()
                if candidate:
                    return candidate
    return fallback


def _cron_delivery_summary(mission: dict[str, Any]) -> str | None:
    summary = str(mission.get("last_checkpoint") or "").strip()
    return summary or None


def _cron_run_status(status: str) -> Literal["ok", "error"]:
    return "ok" if status == "completed" else "error"


def _cron_job_id(task_id: int) -> str:
    return f"task-blueprint:{task_id}"


def _cron_direct_delivery_idempotency_key(
    *,
    task: TaskBlueprintView,
    mission: dict[str, Any],
    event_type: str,
    conversation_target: ConversationTargetView,
    thread_id: str | int | None = None,
) -> str:
    started_at_ms, _ = _cron_runtime_window_ms(task, mission)
    job_id = _cron_job_id(int(task.id))
    execution_id = f"cron:{job_id}:{started_at_ms}"
    channel = str(conversation_target.channel or "").strip().lower()
    account_id = normalize_optional_account_id(conversation_target.account_id) or ""
    target = str(conversation_target.peer_id or "").strip()
    normalized_thread_id = _normalized_delivery_thread_id(thread_id) or ""
    normalized_event_type = str(event_type or "").strip().lower()
    return (
        "cron-direct-delivery:v1:"
        f"{normalized_event_type}:{execution_id}:{channel}:"
        f"{account_id}:{target}:{normalized_thread_id}"
    )


def _cron_failure_message(task: TaskBlueprintView, mission: dict[str, Any]) -> str:
    error = str(mission.get("last_error") or "").strip() or "unknown error"
    return f'Cron job "{task.name}" failed: {error}'


def _cron_failure_announce_message(
    task: TaskBlueprintView,
    mission: dict[str, Any],
) -> str:
    return f"\u26a0\ufe0f {_cron_failure_message(task, mission)}"


def _next_run_at(task: TaskBlueprintView) -> str | None:
    candidates = [
        value
        for value in (
            _task_continuation_next_run_at(task),
            _task_scheduled_next_run_at(task),
        )
        if value is not None
    ]
    if not candidates:
        return None
    return min(candidates)


def _playbook_next_run_at(playbook: PlaybookView) -> str | None:
    if playbook.cadence_minutes is None or not playbook.enabled:
        return None
    last = _parse_timestamp(playbook.last_run_at)
    if last is None:
        return utcnow()
    return (last + timedelta(minutes=playbook.cadence_minutes)).isoformat()


def _format_task_cadence(task: TaskBlueprintView) -> str:
    if task.schedule_kind == "cron" and task.schedule_cron_expr:
        cadence_label = f"Cron {task.schedule_cron_expr}"
    else:
        cadence_label = _format_cadence(task.cadence_minutes)
    if not task.run_until_complete:
        return cadence_label
    continuation_label = f"Continuous relay ({task.continuation_cooldown_minutes}m cooldown)"
    if task.cadence_minutes is None:
        return continuation_label
    return f"{continuation_label} + {_format_cadence(task.cadence_minutes).lower()} backstop"


def _matches_event(pattern: str, event_type: str) -> bool:
    if pattern.endswith("*"):
        return event_type.startswith(pattern[:-1])
    return event_type == pattern


def _sample_event_type_for_route(
    events: list[str] | None,
    *,
    explicit_event_type: str | None = None,
) -> str:
    explicit = str(explicit_event_type or "").strip()
    if explicit:
        return explicit

    for raw_pattern in events or []:
        pattern = str(raw_pattern or "").strip()
        if not pattern:
            continue
        if pattern.endswith("*"):
            prefix = pattern[:-1].rstrip("/")
            return f"{prefix}/test" if prefix else "ops/inbox/test"
        return pattern
    return "ops/inbox/test"


def _summarize_outbound_event(event_type: str, event: dict[str, Any]) -> str:
    for key in ("summary", "message", "title", "headline"):
        value = str(event.get(key) or "").strip()
        if value:
            return value[:240]
    return f"Outbound delivery for {event_type}"[:240]


def _saved_outbound_delivery_replay_message(delivery_row: dict[str, Any]) -> str | None:
    event_type = str(delivery_row.get("event_type") or "").strip().lower()
    payload = delivery_row.get("event_payload")
    if isinstance(payload, dict):
        if event_type == "gateway/send":
            replay_message = _format_direct_channel_send_replay_message(payload)
            if replay_message:
                return replay_message
        if event_type == "gateway/poll":
            replay_message = _format_direct_channel_poll_replay_message(payload)
            if replay_message:
                return replay_message
        if event_type == "cron/failure":
            message = str(payload.get("message") or "").strip()
            if message:
                return f"\u26a0\ufe0f {message}"
        for key in ("summary", "message", "title", "headline"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
    summary = str(delivery_row.get("message_summary") or "").strip()
    return summary or None


def _normalize_direct_channel_media_urls(
    *,
    media_url: str | None = None,
    media_urls: list[str] | None = None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    candidates: list[str] = []
    if media_url is not None:
        candidates.append(media_url)
    if media_urls is not None:
        candidates.extend(media_urls)
    for candidate in candidates:
        trimmed = str(candidate).strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized


def _normalize_gateway_client_scopes(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(scope).strip() for scope in value if str(scope).strip())


def _normalize_optional_payload_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _optional_int_payload_value(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _optional_bool_payload_value(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _summarize_direct_channel_media(media_urls: list[str]) -> str:
    item_label = "item" if len(media_urls) == 1 else "items"
    return f"Media delivery ({len(media_urls)} {item_label})"


def _format_direct_channel_send_message(
    *,
    message: str,
    media_urls: list[str],
    gif_playback: bool | None = None,
) -> str:
    if not media_urls:
        return message
    lines: list[str] = []
    if message.strip():
        lines.extend((message, ""))
    lines.append("Media:")
    lines.extend(f"{index}. {url}" for index, url in enumerate(media_urls, start=1))
    settings: list[str] = []
    if gif_playback is not None:
        settings.append(f"gifPlayback={str(gif_playback).lower()}")
    if settings:
        lines.extend(("", "Settings: " + ", ".join(settings)))
    return "\n".join(lines)


def _format_direct_channel_send_replay_message(payload: dict[str, Any]) -> str | None:
    message = str(payload.get("message") or "")
    raw_media_urls = payload.get("mediaUrls")
    media_urls = _normalize_direct_channel_media_urls(
        media_url=(
            str(payload.get("mediaUrl"))
            if isinstance(payload.get("mediaUrl"), str)
            else None
        ),
        media_urls=(
            [str(entry) for entry in raw_media_urls]
            if isinstance(raw_media_urls, list)
            else None
        ),
    )
    if not message.strip() and not media_urls:
        return None
    gif_playback = payload.get("gifPlayback")
    resolved_gif_playback = gif_playback if isinstance(gif_playback, bool) else None
    return _format_direct_channel_send_message(
        message=message,
        media_urls=media_urls,
        gif_playback=resolved_gif_playback,
    )


def _format_direct_channel_poll_replay_message(payload: dict[str, Any]) -> str | None:
    question = str(payload.get("question") or payload.get("summary") or "").strip()
    raw_options = payload.get("options")
    options = (
        [str(entry).strip() for entry in raw_options if str(entry).strip()]
        if isinstance(raw_options, list)
        else []
    )
    if not question:
        return None
    max_selections = payload.get("maxSelections")
    resolved_max_selections = (
        max_selections
        if isinstance(max_selections, int) and not isinstance(max_selections, bool)
        else None
    )
    duration_seconds = payload.get("durationSeconds")
    resolved_duration_seconds = (
        duration_seconds
        if isinstance(duration_seconds, int) and not isinstance(duration_seconds, bool)
        else None
    )
    duration_hours = payload.get("durationHours")
    resolved_duration_hours = (
        duration_hours
        if isinstance(duration_hours, int) and not isinstance(duration_hours, bool)
        else None
    )
    silent = payload.get("silent")
    resolved_silent = silent if isinstance(silent, bool) else None
    is_anonymous = payload.get("isAnonymous")
    resolved_is_anonymous = is_anonymous if isinstance(is_anonymous, bool) else None
    return _format_direct_channel_poll_message(
        question=question,
        options=options,
        max_selections=resolved_max_selections,
        duration_seconds=resolved_duration_seconds,
        duration_hours=resolved_duration_hours,
        silent=resolved_silent,
        is_anonymous=resolved_is_anonymous,
    )


def _format_direct_channel_poll_message(
    *,
    question: str,
    options: list[str],
    max_selections: int | None,
    duration_seconds: int | None,
    duration_hours: int | None,
    silent: bool | None,
    is_anonymous: bool | None,
) -> str:
    lines = [f"Poll: {question}"]
    lines.extend(f"{index}. {option}" for index, option in enumerate(options, start=1))
    settings: list[str] = []
    if max_selections is not None:
        settings.append(f"maxSelections={max_selections}")
    if duration_seconds is not None:
        settings.append(f"durationSeconds={duration_seconds}")
    if duration_hours is not None:
        settings.append(f"durationHours={duration_hours}")
    if silent is not None:
        settings.append(f"silent={str(silent).lower()}")
    if is_anonymous is not None:
        settings.append(f"isAnonymous={str(is_anonymous).lower()}")
    if settings:
        lines.extend(("", "Settings: " + ", ".join(settings)))
    return "\n".join(lines)


def _build_direct_channel_transport(
    *,
    channel: str | None,
    target: str | None,
    account_id: str | None,
    thread_id: str | int | None,
    session_key: str | None,
    runtime: str = "session-backed",
) -> dict[str, str]:
    transport: dict[str, str] = {"runtime": str(runtime or "session-backed")}
    normalized_channel = str(channel or "").strip().lower()
    if normalized_channel:
        transport["channel"] = normalized_channel
    normalized_target = str(target or "").strip()
    if normalized_target:
        transport["target"] = normalized_target
    normalized_account_id = normalize_optional_account_id(account_id)
    if normalized_account_id is not None:
        transport["account_id"] = normalized_account_id
    normalized_thread_id = _normalized_delivery_thread_id(thread_id)
    if normalized_thread_id is not None:
        transport["thread_id"] = normalized_thread_id
    normalized_session_key = str(session_key or "").strip()
    if normalized_session_key:
        transport["session_key"] = normalized_session_key
    return transport


def _direct_channel_transport_from_delivery_row(
    delivery_row: dict[str, Any],
) -> dict[str, str] | None:
    route_scope = delivery_row.get("route_scope")
    if not isinstance(route_scope, dict):
        return None
    source = str(route_scope.get("source") or "").strip().lower()
    if source not in {"gateway.send", "gateway.poll"}:
        return None
    event_payload = delivery_row.get("event_payload")
    if not isinstance(event_payload, dict):
        event_payload = {}
    conversation_target = _normalize_conversation_target(
        delivery_row.get("conversation_target")
    ) or _normalize_conversation_target(event_payload.get("conversationTarget"))
    channel = str(
        event_payload.get("channel") or (conversation_target or {}).get("channel") or ""
    ).strip().lower() or None
    target = str(
        event_payload.get("to") or (conversation_target or {}).get("peer_id") or ""
    ).strip() or None
    account_id = str(
        event_payload.get("accountId")
        or (conversation_target or {}).get("account_id")
        or route_scope.get("resolved_account_id")
        or ""
    ).strip() or None
    thread_id = event_payload.get("threadId")
    if thread_id is None:
        thread_id = route_scope.get("thread_id")
    session_key = (
        str(route_scope.get("runtime_session_key") or delivery_row.get("session_key") or "").strip()
        or None
    )
    runtime = str(route_scope.get("transport_runtime") or "").strip() or "session-backed"
    return _build_direct_channel_transport(
        channel=channel,
        target=target,
        account_id=account_id,
        thread_id=thread_id,
        session_key=session_key,
        runtime=runtime,
    )


def _serialize_gateway_direct_channel_transport(
    transport: dict[str, Any],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "runtime": str(transport.get("runtime") or "session-backed"),
    }
    channel = str(transport.get("channel") or "").strip().lower()
    if channel:
        payload["channel"] = channel
    target = str(transport.get("target") or "").strip()
    if target:
        payload["target"] = target
    account_id = str(transport.get("account_id") or "").strip()
    if account_id:
        payload["accountId"] = account_id
    thread_id = str(transport.get("thread_id") or "").strip()
    if thread_id:
        payload["threadId"] = thread_id
    session_key = str(transport.get("session_key") or "").strip()
    if session_key:
        payload["sessionKey"] = session_key
    return payload


def _serialize_gateway_provider_result(result: dict[str, Any]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key in (
        "runtime",
        "messageId",
        "channel",
        "chatId",
        "channelId",
        "roomId",
        "toJid",
        "conversationId",
        "timestamp",
        "pollId",
        "mediaId",
        "mediaIds",
        "mediaUrl",
        "mediaUrls",
        "meta",
    ):
        value = result.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (str, int, float, bool, list, dict)):
            payload[key] = value
        else:
            payload[key] = str(value)
    return payload


def _serialize_gateway_response_provider_result(
    result: dict[str, Any],
) -> dict[str, object]:
    payload = _serialize_gateway_provider_result(result)
    payload.pop("runtime", None)
    return payload


def _direct_channel_provider_result_from_delivery_row(
    delivery_row: dict[str, Any],
) -> dict[str, object] | None:
    route_scope = delivery_row.get("route_scope")
    if not isinstance(route_scope, dict):
        return None
    provider_result = route_scope.get("provider_result")
    if not isinstance(provider_result, dict):
        return None
    payload = _serialize_gateway_provider_result(provider_result)
    return payload or None


def _saved_provider_route_event_payload(
    *,
    event_type: str,
    event_payload: dict[str, Any],
    conversation_target: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(event_payload)
    if conversation_target is not None:
        payload.setdefault("conversationTarget", conversation_target)
        payload.setdefault("routeConversationTarget", conversation_target)
        payload.setdefault("to", conversation_target.get("peer_id"))
        if conversation_target.get("account_id") and "accountId" not in payload:
            payload["accountId"] = conversation_target.get("account_id")
    summary = str(payload.get("summary") or "OpenZues test delivery ping.").strip()
    if event_type == "gateway/send" and not str(payload.get("message") or "").strip():
        payload["message"] = summary
    if event_type == "gateway/poll":
        if not str(payload.get("question") or "").strip():
            payload["question"] = summary
        raw_options = payload.get("options")
        options = (
            [str(option).strip() for option in raw_options if str(option).strip()]
            if isinstance(raw_options, list)
            else []
        )
        if not options:
            payload["options"] = ["Acknowledged", "Needs attention"]
    return payload


def _session_delivery_message_id(result: object) -> str | None:
    if isinstance(result, dict):
        candidate = result.get("messageId") or result.get("id")
    else:
        candidate = getattr(result, "messageId", None) or getattr(result, "id", None)
    if candidate is None:
        return None
    return str(candidate).strip() or None


def _serialize_task(row: dict[str, Any]) -> TaskBlueprintView:
    return TaskBlueprintView.model_validate(row)


def _resolve_task_toolsets(
    task: TaskBlueprintView,
    *,
    project_label: str | None = None,
    project_path: str | None = None,
) -> list[str]:
    if _task_targets_openclaw_parity(task):
        return _openclaw_parity_task_toolsets(task)
    return infer_hermes_toolsets(
        _normalized_task_objective_template(task),
        explicit_toolsets=task.toolsets,
        project_label=project_label,
        project_path=project_path or task.cwd,
        setup_mode="local",
        use_builtin_agents=task.use_builtin_agents,
        run_verification=task.run_verification,
        cadence_minutes=task.cadence_minutes,
    )


def _attach_task_tool_policy(
    task: TaskBlueprintView,
    *,
    project_label: str | None = None,
    project_path: str | None = None,
) -> TaskBlueprintView:
    toolsets = _resolve_task_toolsets(
        task,
        project_label=project_label,
        project_path=project_path,
    )
    return task.model_copy(
        update={
            "toolsets": toolsets,
            "tool_policy": build_hermes_tool_policy(toolsets, setup_mode="local"),
        }
    )


def _serialize_route(
    row: dict[str, Any],
    *,
    vault_secret_label: str | None = None,
    secret_preview: str | None = None,
    has_secret: bool | None = None,
) -> NotificationRouteView:
    if has_secret is None:
        has_secret, secret_preview = mask_secret(str(row.get("secret_token") or ""))
    return NotificationRouteView.model_validate(
        {
            **row,
            "vault_secret_label": vault_secret_label,
            "has_secret": has_secret,
            "secret_preview": secret_preview,
        }
    )


def _serialize_outbound_delivery(row: dict[str, Any]) -> OutboundDeliveryView:
    replay_ready, next_retry_at, max_retries_reached = _outbound_delivery_replay_state(row)
    return OutboundDeliveryView.model_validate(
        {
            **row,
            "transport": _direct_channel_transport_from_delivery_row(row),
            "replay_ready": replay_ready,
            "next_retry_at": next_retry_at,
            "max_retries_reached": max_retries_reached,
        }
    )


def _saved_delivery_is_ad_hoc_webhook(row: dict[str, Any]) -> bool:
    route_scope = row.get("route_scope")
    if not isinstance(route_scope, dict):
        return False
    if str(row.get("route_kind") or "").strip().lower() != "webhook":
        return False
    if "route_match" in route_scope or "matched_value" in route_scope:
        return False
    route_target = str(route_scope.get("route_target") or row.get("route_target") or "")
    return bool(route_target.strip())


def _saved_outbound_delivery_route_view(
    row: dict[str, Any],
    *,
    delivery_enabled: bool,
    last_error: str | None = None,
) -> NotificationRouteView:
    route_scope = row.get("route_scope")
    if not isinstance(route_scope, dict):
        route_scope = {}
    route_kind = str(route_scope.get("route_kind") or row.get("route_kind") or "").strip().lower()
    if route_kind not in {"announce", "session", "webhook"}:
        route_kind = "webhook"
    route_name = (
        str(route_scope.get("route_name") or row.get("route_name") or "").strip()
        or "Saved delivery"
    )
    route_target = (
        str(route_scope.get("route_target") or row.get("route_target") or "").strip()
        or str(row.get("session_key") or "").strip()
    )
    secret_header_name = str(route_scope.get("secret_header_name") or "").strip() or None
    vault_secret_id = route_scope.get("vault_secret_id")
    has_secret = secret_header_name is not None or vault_secret_id is not None
    return NotificationRouteView.model_validate(
        {
            "id": 0,
            "name": route_name,
            "kind": route_kind,
            "target": route_target,
            "events": [],
            "conversation_target": row.get("conversation_target"),
            "enabled": delivery_enabled,
            "secret_header_name": secret_header_name,
            "vault_secret_id": vault_secret_id,
            "vault_secret_label": None,
            "has_secret": has_secret,
            "secret_preview": None,
            "last_delivery_at": None,
            "last_result": None,
            "last_error": last_error,
            "created_at": row.get("created_at") or utcnow(),
            "updated_at": row.get("updated_at") or utcnow(),
        }
    )


def _outbound_delivery_backoff_seconds(attempt_count: int) -> int:
    if attempt_count < 0:
        return 0
    if not OUTBOUND_DELIVERY_BACKOFF_SECONDS:
        return 0
    return OUTBOUND_DELIVERY_BACKOFF_SECONDS[
        min(attempt_count, len(OUTBOUND_DELIVERY_BACKOFF_SECONDS) - 1)
    ]


def _next_outbound_retry_at(row: dict[str, Any]) -> datetime | None:
    state = str(row.get("delivery_state") or "").strip().lower()
    if state == "delivered":
        return None
    attempt_count = max(0, int(row.get("attempt_count") or 0))
    if attempt_count >= OUTBOUND_DELIVERY_MAX_RETRIES:
        return None
    last_attempt_at = _parse_timestamp(str(row.get("last_attempt_at") or ""))
    if attempt_count == 0 and last_attempt_at is None:
        return None
    baseline = last_attempt_at or _parse_timestamp(str(row.get("created_at") or ""))
    if baseline is None:
        return None
    return baseline + timedelta(seconds=_outbound_delivery_backoff_seconds(attempt_count))


def _outbound_delivery_replay_state(
    row: dict[str, Any],
    *,
    now: datetime | None = None,
) -> tuple[bool, datetime | None, bool]:
    state = str(row.get("delivery_state") or "").strip().lower()
    if state == "delivered":
        return False, None, False
    attempt_count = max(0, int(row.get("attempt_count") or 0))
    if attempt_count >= OUTBOUND_DELIVERY_MAX_RETRIES:
        return False, None, True
    retry_at = _next_outbound_retry_at(row)
    if retry_at is None:
        return True, None, False
    active_now = now or datetime.now(UTC)
    if retry_at <= active_now:
        return True, None, False
    return False, retry_at, False


def _is_permanent_outbound_delivery_error(message: str) -> bool:
    return any(pattern.search(message) for pattern in OUTBOUND_DELIVERY_PERMANENT_ERROR_PATTERNS)


def _normalize_conversation_target(
    target: dict[str, Any] | ConversationTargetView | None,
) -> dict[str, Any] | None:
    if target is None:
        return None
    try:
        raw = (
            target
            if isinstance(target, ConversationTargetView)
            else ConversationTargetView.model_validate(target)
        )
    except Exception:
        return None
    channel = str(raw.channel or "").strip().lower()
    if not channel:
        return None
    account_id = normalize_optional_account_id(raw.account_id)
    peer_id = str(raw.peer_id or "").strip().lower() or None
    peer_kind = raw.peer_kind if peer_id else None
    return ConversationTargetView(
        channel=channel,
        account_id=account_id,
        peer_kind=peer_kind,
        peer_id=peer_id if peer_kind else None,
    ).model_dump(mode="json")


def _conversation_target_key(
    target: dict[str, Any] | ConversationTargetView | None,
) -> tuple[str, str, str, str] | None:
    normalized = _normalize_conversation_target(target)
    if normalized is None:
        return None
    channel = str(normalized.get("channel") or "").strip().lower()
    if not channel:
        return None
    return (
        channel,
        str(normalized.get("account_id") or "").strip().lower(),
        str(normalized.get("peer_kind") or "").strip().lower(),
        str(normalized.get("peer_id") or "").strip().lower(),
    )


def _conversation_target_peer_id_matches(
    *,
    channel: str,
    route_peer_id: str,
    event_peer_id: str,
) -> bool:
    if route_peer_id == event_peer_id:
        return True
    if channel != "telegram":
        return False
    route_target = _parse_telegram_delivery_target(route_peer_id)
    event_target = _parse_telegram_delivery_target(event_peer_id)
    route_chat_id = str(route_target.get("chatId") or "").strip().lower()
    event_chat_id = str(event_target.get("chatId") or "").strip().lower()
    if not route_chat_id or route_chat_id != event_chat_id:
        return False
    route_thread_id = str(route_target.get("threadId") or "").strip()
    event_thread_id = str(event_target.get("threadId") or "").strip()
    return not route_thread_id or route_thread_id == event_thread_id


def _conversation_target_route_match(
    route_target: dict[str, Any] | ConversationTargetView | None,
    event_target: dict[str, Any] | ConversationTargetView | None,
) -> str | None:
    route_key = _conversation_target_key(route_target)
    event_key = _conversation_target_key(event_target)
    if route_key is None or event_key is None:
        return None

    route_channel, route_account, route_peer_kind, route_peer_id = route_key
    event_channel, event_account, event_peer_kind, event_peer_id = event_key
    if route_channel != event_channel:
        return None

    if route_account not in {"", "*"} and route_account != event_account:
        return None

    if route_peer_kind not in {"", "*"} and route_peer_kind != event_peer_kind:
        return None
    if route_peer_id not in {"", "*"} and not _conversation_target_peer_id_matches(
        channel=route_channel,
        route_peer_id=route_peer_id,
        event_peer_id=event_peer_id,
    ):
        return None

    if route_peer_kind not in {"", "*"} or route_peer_id not in {"", "*"}:
        return "peer"
    if route_account not in {"", "*"}:
        return "account"
    return "channel"


def _serialize_integration(
    row: dict[str, Any],
    *,
    vault_secret_label: str | None = None,
    secret_preview: str | None = None,
    has_secret: bool | None = None,
    auth_status: str = "missing",
    auth_detail: str | None = None,
) -> IntegrationView:
    if has_secret is None:
        has_secret, secret_preview = mask_secret(str(row.get("secret_value") or ""))
    return IntegrationView.model_validate(
        {
            **row,
            "vault_secret_label": vault_secret_label,
            "has_secret": has_secret,
            "secret_preview": secret_preview,
            "auth_status": auth_status,
            "auth_detail": auth_detail,
        }
    )


def _serialize_skill_pin(row: dict[str, Any]) -> SkillPinView:
    return SkillPinView.model_validate(row)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(Path(value).expanduser()).replace("\\", "/").rstrip("/").lower()
    except (TypeError, ValueError):
        return None


def _path_matches_project(candidate: str | None, project_path: str | None) -> bool:
    candidate_norm = _normalize_path(candidate)
    project_norm = _normalize_path(project_path)
    if not candidate_norm or not project_norm:
        return False
    return (
        candidate_norm == project_norm
        or candidate_norm.startswith(f"{project_norm}/")
        or project_norm.startswith(f"{candidate_norm}/")
    )


def _skill_identity(name: str | None, source: str | None = None) -> tuple[str, str]:
    return (_normalize_text(name), _normalize_text(source))


def _coerce_skill_row(skill: dict[str, Any]) -> dict[str, str | None]:
    return {
        "name": str(skill.get("name") or "").strip(),
        "source": str(skill.get("source") or "").strip() or None,
        "status": str(skill.get("status") or "").strip() or None,
    }


def _skill_matches_pin(skill: dict[str, str | None], pin: SkillPinView) -> bool:
    skill_name = _normalize_text(skill.get("name"))
    skill_source = _normalize_text(skill.get("source"))
    pin_name = _normalize_text(pin.name)
    pin_source = _normalize_text(pin.source)
    if skill_name and pin_name and skill_name == pin_name:
        return True
    return bool(skill_source and pin_source and skill_source == pin_source)


def _mission_skill_text(mission: MissionView) -> str:
    parts = [
        mission.objective,
        mission.current_command,
        mission.last_checkpoint,
        mission.suggested_action,
    ]
    return _normalize_text(" ".join(part for part in parts if part))


def _project_ids_for_lane(
    instance: InstanceView,
    *,
    projects: list[ProjectView],
    missions: list[MissionView],
) -> list[int]:
    project_ids = {
        mission.project_id
        for mission in missions
        if mission.project_id is not None and mission.instance_id == instance.id
    }
    project_ids.update(
        project.id for project in projects if _path_matches_project(instance.cwd, project.path)
    )
    return sorted(project_id for project_id in project_ids if project_id is not None)


CAPABILITY_STOPWORDS = {
    "app",
    "apps",
    "plugin",
    "plugins",
    "server",
    "servers",
    "integration",
    "integrations",
    "connector",
    "connectors",
    "openai",
    "curated",
    "remote",
    "local",
    "token",
    "oauth",
    "auth",
    "api",
    "sdk",
    "service",
}


def _capability_terms(*values: str | None) -> set[str]:
    terms: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        terms.add(normalized)
        for token in re.split(r"[^a-z0-9]+", normalized):
            if len(token) >= 4 and token not in CAPABILITY_STOPWORDS:
                terms.add(token)
    return terms


def _capability_terms_for_url(value: str | None) -> set[str]:
    if not value:
        return set()
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if not host:
        return set()
    parts = [part for part in host.split(".") if part and part not in {"www", "api"}]
    terms = _capability_terms(host)
    if len(parts) >= 2:
        terms.add(parts[-2])
    terms.update(_capability_terms(*parts))
    return terms


def _capability_aliases(
    *,
    name: str | None,
    kind: str | None = None,
    source: str | None = None,
    base_url: str | None = None,
) -> set[str]:
    return {
        *_capability_terms(name, kind, source),
        *_capability_terms_for_url(base_url),
    }


def _capability_primary_key(
    *,
    name: str | None,
    kind: str | None = None,
    source: str | None = None,
    base_url: str | None = None,
) -> str:
    aliases = sorted(
        alias
        for alias in _capability_aliases(name=name, kind=kind, source=source, base_url=base_url)
        if " " not in alias
    )
    if aliases:
        return aliases[0]
    for candidate in (name, kind, source):
        normalized = _normalize_text(candidate)
        if normalized:
            return normalized
    return "capability"


def _catalog_capability_status(
    source_kind: IntegrationInventorySourceKind,
    item: dict[str, Any],
    *,
    connected: bool,
) -> LaneCapabilityStatus:
    if not connected:
        return "offline"
    if source_kind in {"app", "plugin"}:
        enabled = item.get("enabled")
        return "ready" if enabled is not False else "disabled"
    status = _normalize_text(str(item.get("status") or ""))
    if not status or status in {"ready", "ok", "connected", "enabled", "healthy", "active"}:
        return "ready"
    if status in {"disabled", "stopped"}:
        return "disabled"
    return "degraded"


def _catalog_capability_summary(
    source_kind: IntegrationInventorySourceKind,
    status: LaneCapabilityStatus,
    item: dict[str, Any],
) -> str:
    label = source_kind.replace("_", " ")
    if status == "ready":
        if source_kind == "mcp_server":
            raw_status = _normalize_text(str(item.get("status") or "ready"))
            return f"{label.title()} is published and reporting {raw_status or 'ready'}."
        return f"{label.title()} is published on this lane."
    if status == "disabled":
        return f"{label.title()} is installed but disabled on this lane."
    if status == "offline":
        return "Lane is offline."
    raw_status = _normalize_text(str(item.get("status") or "unavailable"))
    return f"{label.title()} is visible but reporting {raw_status}."


def _collect_lane_capabilities(instance: InstanceView) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    collections: list[tuple[IntegrationInventorySourceKind, list[dict[str, Any]]]] = [
        ("app", instance.apps),
        ("plugin", instance.plugins),
        ("mcp_server", instance.mcp_servers),
    ]
    for source_kind, rows in collections:
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            source = str(row.get("source") or "").strip() or None
            if not name and not source:
                continue
            status = _catalog_capability_status(source_kind, row, connected=instance.connected)
            catalog.append(
                {
                    "key": (
                        source_kind,
                        _normalize_text(name),
                        _normalize_text(source),
                    ),
                    "primary_key": _capability_primary_key(
                        name=name or source,
                        source=source,
                    ),
                    "name": name or source or "Unnamed capability",
                    "kind": source_kind,
                    "source": source,
                    "aliases": _capability_aliases(name=name, source=source),
                    "status": status,
                    "summary": _catalog_capability_summary(source_kind, status, row),
                }
            )
    return catalog


def _integration_lane_status(
    *,
    integration: IntegrationView,
    lane: InstanceView,
    matches: list[dict[str, Any]],
) -> tuple[LaneCapabilityStatus, str]:
    if not lane.connected:
        return ("offline", "Lane is offline, so this capability is not usable right now.")
    if integration.enabled is False:
        return ("disabled", "Tracked integration is disabled in the inventory.")
    ready_matches = [match for match in matches if match["status"] == "ready"]
    if integration.auth_status == "degraded":
        return ("degraded", integration.auth_detail or "Repair the referenced secret first.")
    if integration.auth_status == "missing" and ready_matches:
        return (
            "auth_gap",
            integration.auth_detail or "Attach credentials before this lane can use it.",
        )
    if ready_matches:
        match_types = ", ".join(
            sorted({match["kind"].replace("_", " ") for match in ready_matches})
        )
        return ("ready", f"Lane has live {match_types} support and auth is satisfied.")
    if matches:
        status_words = ", ".join(sorted({match["status"] for match in matches}))
        return ("degraded", f"Capability is present but reporting {status_words}.")
    return ("missing", "No matching app, plugin, or MCP server is visible on this lane.")


def _integration_recommended_action(
    *,
    integration: IntegrationView,
    relevant_instances: list[InstanceView],
    lane_ready_count: int,
    lane_match_count: int,
) -> str:
    if integration.enabled is False:
        return "Enable this integration when operators want it included in live mission context."
    if integration.auth_status == "degraded":
        return integration.auth_detail or "Repair the referenced vault secret before launch."
    if integration.auth_status == "missing" and lane_match_count:
        return "Attach a vault secret so the published lane capability can authenticate cleanly."
    if not relevant_instances and integration.project_id is not None:
        return (
            "Attach the project to a connected lane or move the next mission onto a lane carrying "
            "this workspace."
        )
    if relevant_instances and not any(instance.connected for instance in relevant_instances):
        return "Reconnect a relevant lane or fail work over before depending on this capability."
    if relevant_instances and lane_match_count == 0:
        if is_mempalace_integration(integration):
            return (
                "Install MemPalace on the lane host, expose `python -m mempalace.mcp_server`, "
                "and reconnect the lane before relying on project memory."
            )
        return (
            "Install or enable the matching plugin, app, or MCP server on a relevant lane before "
            "launching work that depends on it."
        )
    if lane_ready_count:
        return "Ready now. Prefer one of the listed lanes when the next mission needs this."
    return "Track the next lane that proves this capability live so the operator map stays current."


def _lane_capability_sort_rank(status: LaneCapabilityStatus) -> int:
    return {
        "ready": 0,
        "auth_gap": 1,
        "degraded": 2,
        "missing": 3,
        "disabled": 4,
        "offline": 5,
    }.get(status, 9)


def _build_integrations_inventory(
    *,
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    integrations: list[IntegrationView],
    access_posture: DashboardAccessPostureView,
) -> DashboardIntegrationsInventoryView:
    project_by_id = {project.id: project for project in projects}
    missions_by_instance: dict[int, list[MissionView]] = {}
    for mission in missions:
        missions_by_instance.setdefault(mission.instance_id, []).append(mission)

    lane_project_ids = {
        instance.id: _project_ids_for_lane(
            instance,
            projects=projects,
            missions=missions_by_instance.get(instance.id, []),
        )
        for instance in instances
    }
    lane_capabilities = {
        instance.id: _collect_lane_capabilities(instance) for instance in instances
    }

    items: list[DashboardIntegrationInventoryItemView] = []
    matched_capability_keys: set[tuple[IntegrationInventorySourceKind, str, str]] = set()

    for integration in integrations:
        relevant_instances = (
            [
                instance
                for instance in instances
                if integration.project_id in lane_project_ids.get(instance.id, [])
            ]
            if integration.project_id is not None
            else list(instances)
        )
        aliases = _capability_aliases(
            name=integration.name,
            kind=integration.kind,
            base_url=integration.base_url,
        )
        lane_views: list[DashboardIntegrationLaneView] = []
        capability_labels: set[str] = set()
        lane_ready_count = 0
        lane_match_count = 0

        for instance in relevant_instances:
            matches = [
                capability
                for capability in lane_capabilities.get(instance.id, [])
                if aliases.intersection(capability["aliases"])
            ]
            if matches:
                lane_match_count += 1
                for match in matches:
                    matched_capability_keys.add(match["key"])
                    capability_labels.add(f"{match['kind'].replace('_', ' ')}: {match['name']}")
            status, summary = _integration_lane_status(
                integration=integration,
                lane=instance,
                matches=matches,
            )
            if status == "ready":
                lane_ready_count += 1
            lane_views.append(
                DashboardIntegrationLaneView(
                    instance_id=instance.id,
                    instance_name=instance.name,
                    connected=instance.connected,
                    status=status,
                    match_types=sorted({match["kind"] for match in matches}),
                    summary=summary,
                )
            )

        if integration.enabled is False:
            readiness: IntegrationInventoryReadiness = "disabled"
            level: SignalLevel = "info"
            summary = "Tracked in the inventory, but currently disabled."
        elif integration.auth_status == "degraded":
            readiness = "degraded"
            level = "critical"
            summary = (
                integration.auth_detail
                or "Auth is degraded until the secret reference is repaired."
            )
        elif lane_ready_count:
            readiness = "ready"
            level = "ready"
            summary = f"{lane_ready_count} lane(s) can use this capability right now."
        elif integration.auth_status == "missing" and lane_match_count:
            readiness = "auth_gap"
            level = "warn"
            summary = (
                f"{lane_match_count} lane(s) publish the capability, but credentials are "
                "still missing."
            )
        elif relevant_instances and not any(instance.connected for instance in relevant_instances):
            readiness = "lane_gap"
            level = "warn"
            summary = "Relevant lanes exist, but they are all offline right now."
        elif relevant_instances:
            readiness = "lane_gap"
            level = "warn"
            summary = (
                "Relevant lanes are connected, but none currently expose the matching plugin, app, "
                "or MCP server."
            )
        else:
            readiness = "lane_gap"
            level = "warn"
            summary = "No live lane is currently carrying the workspace that owns this integration."

        project_labels = []
        if integration.project_id is not None and integration.project_id in project_by_id:
            project_labels = [project_by_id[integration.project_id].label]

        items.append(
            DashboardIntegrationInventoryItemView(
                id=f"integration:{integration.id}",
                name=integration.name,
                kind=integration.kind,
                tracked=True,
                source_kinds=sorted(
                    {
                        "integration",
                        *(match_type for lane in lane_views for match_type in lane.match_types),
                    }
                ),
                project_labels=project_labels,
                base_url=integration.base_url,
                auth_scheme=integration.auth_scheme,
                auth_status=integration.auth_status,
                readiness=readiness,
                level=level,
                lane_ready_count=lane_ready_count,
                lane_match_count=lane_match_count,
                summary=summary,
                recommended_action=_integration_recommended_action(
                    integration=integration,
                    relevant_instances=relevant_instances,
                    lane_ready_count=lane_ready_count,
                    lane_match_count=lane_match_count,
                ),
                notes=integration.notes,
                capabilities=sorted(capability_labels),
                lanes=sorted(
                    lane_views,
                    key=lambda lane: (
                        _lane_capability_sort_rank(lane.status),
                        0 if lane.connected else 1,
                        lane.instance_name.lower(),
                    ),
                ),
            )
        )

    observed_groups: dict[str, dict[str, Any]] = {}
    for instance in instances:
        lane_projects = [
            project_by_id[project_id].label
            for project_id in lane_project_ids.get(instance.id, [])
            if project_id in project_by_id
        ]
        for capability in lane_capabilities.get(instance.id, []):
            if capability["key"] in matched_capability_keys:
                continue
            bucket = observed_groups.setdefault(
                capability["primary_key"],
                {
                    "name": capability["name"],
                    "kind": capability["kind"].replace("_", " "),
                    "project_labels": set(),
                    "source_kinds": set(),
                    "capabilities": set(),
                    "lanes": [],
                    "ready_count": 0,
                },
            )
            bucket["project_labels"].update(lane_projects)
            bucket["source_kinds"].add(capability["kind"])
            bucket["capabilities"].add(
                f"{capability['kind'].replace('_', ' ')}: {capability['name']}"
            )
            bucket["lanes"].append(
                DashboardIntegrationLaneView(
                    instance_id=instance.id,
                    instance_name=instance.name,
                    connected=instance.connected,
                    status=capability["status"],
                    match_types=[capability["kind"]],
                    summary=capability["summary"],
                )
            )
            if capability["status"] == "ready":
                bucket["ready_count"] += 1

    for bucket_key, bucket in observed_groups.items():
        ready_count = int(bucket["ready_count"])
        lanes = sorted(
            bucket["lanes"],
            key=lambda lane: (
                _lane_capability_sort_rank(lane.status),
                0 if lane.connected else 1,
                lane.instance_name.lower(),
            ),
        )
        if ready_count:
            observed_readiness: IntegrationInventoryReadiness = "observed"
            observed_level: SignalLevel = "info"
            summary = (
                f"Observed live on {ready_count} lane(s), but not yet tracked in the "
                "operator inventory."
            )
            next_action = (
                "Add a tracked integration entry with auth notes if operators depend on "
                "this capability."
            )
        elif any(lane.connected for lane in lanes):
            observed_readiness = "degraded"
            observed_level = "warn"
            summary = (
                "Observed on connected lanes, but the published capability is not healthy yet."
            )
            next_action = "Repair or re-enable the lane-side capability before relying on it."
        else:
            observed_readiness = "lane_gap"
            observed_level = "warn"
            summary = "Only offline lanes currently advertise this capability."
            next_action = "Reconnect the lane or record a durable integration entry before launch."

        items.append(
            DashboardIntegrationInventoryItemView(
                id=f"capability:{bucket_key}",
                name=str(bucket["name"]),
                kind=str(bucket["kind"]),
                tracked=False,
                source_kinds=sorted(bucket["source_kinds"]),
                project_labels=sorted(bucket["project_labels"]),
                readiness=observed_readiness,
                level=observed_level,
                lane_ready_count=ready_count,
                lane_match_count=len(lanes),
                summary=summary,
                recommended_action=next_action,
                capabilities=sorted(bucket["capabilities"]),
                lanes=lanes,
            )
        )

    tracked_count = sum(item.tracked for item in items)
    observed_count = sum(not item.tracked for item in items)
    ready_count = sum(item.readiness == "ready" for item in items)
    gap_count = sum(
        item.tracked and item.readiness in {"auth_gap", "lane_gap", "degraded"} for item in items
    )

    if gap_count:
        headline = "Integration inventory has live gaps"
        summary = (
            f"{gap_count} tracked capability(ies) still need auth repair, lane coverage, or "
            f"lane-side plugins/MCP servers. {access_posture.summary}"
        )
    elif tracked_count or observed_count:
        headline = "Integration inventory is active"
        summary = (
            f"{ready_count} tracked capability(ies) are ready, and {observed_count} more are only "
            f"observed live. {access_posture.summary}"
        )
    else:
        headline = "Integration inventory is idle"
        summary = (
            "Add integrations or connect lanes with live apps, plugins, and MCP servers to build "
            "the readiness map."
        )

    level_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    readiness_rank = {
        "degraded": 0,
        "auth_gap": 1,
        "lane_gap": 2,
        "ready": 3,
        "observed": 4,
        "disabled": 5,
    }
    return DashboardIntegrationsInventoryView(
        headline=headline,
        summary=summary,
        ready_count=ready_count,
        gap_count=gap_count,
        tracked_count=tracked_count,
        observed_count=observed_count,
        items=sorted(
            items,
            key=lambda item: (
                0 if item.tracked else 1,
                level_rank[item.level],
                readiness_rank[item.readiness],
                item.name.lower(),
            ),
        )[:16],
    )


def _build_skills_registry(
    *,
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    skill_pins: list[SkillPinView],
) -> DashboardSkillsRegistryView:
    project_by_id = {project.id: project for project in projects}
    pins_by_project: dict[int, list[SkillPinView]] = {}
    for pin in skill_pins:
        if pin.enabled:
            pins_by_project.setdefault(pin.project_id, []).append(pin)

    missions_by_instance: dict[int, list[MissionView]] = {}
    missions_by_project: dict[int, list[MissionView]] = {}
    successful_missions_by_project: dict[int, list[MissionView]] = {}
    for mission in missions:
        missions_by_instance.setdefault(mission.instance_id, []).append(mission)
        if mission.project_id is None:
            continue
        missions_by_project.setdefault(mission.project_id, []).append(mission)
        if mission.status == "completed":
            successful_missions_by_project.setdefault(mission.project_id, []).append(mission)

    gap_views: list[DashboardSkillGapView] = []
    gap_counts_by_instance: dict[int, int] = {}
    skill_success_counts: dict[tuple[int | None, str, str], int] = {}
    lane_project_ids: dict[int, list[int]] = {}
    lane_skill_rows: dict[int, list[dict[str, str | None]]] = {}
    lane_skill_identities: dict[int, set[tuple[str, str]]] = {}

    for instance in instances:
        lane_project_ids[instance.id] = _project_ids_for_lane(
            instance,
            projects=projects,
            missions=missions_by_instance.get(instance.id, []),
        )
        skill_rows = [
            _coerce_skill_row(skill)
            for skill in instance.skills
            if str(skill.get("name") or "").strip()
        ]
        lane_skill_rows[instance.id] = sorted(skill_rows, key=lambda item: item["name"] or "")
        lane_skill_identities[instance.id] = {
            _skill_identity(skill["name"], skill["source"]) for skill in skill_rows
        }

    for project_id, completed_missions in successful_missions_by_project.items():
        pins = pins_by_project.get(project_id, [])
        if not pins:
            continue
        for mission in completed_missions:
            mission_text = _mission_skill_text(mission)
            if not mission_text:
                continue
            for pin in pins:
                if _normalize_text(pin.name) and _normalize_text(pin.name) in mission_text:
                    key = (project_id, *_skill_identity(pin.name, pin.source))
                    skill_success_counts[key] = skill_success_counts.get(key, 0) + 1
                elif _normalize_text(pin.source) and _normalize_text(pin.source) in mission_text:
                    key = (project_id, *_skill_identity(pin.name, pin.source))
                    skill_success_counts[key] = skill_success_counts.get(key, 0) + 1

    for mission in missions:
        if mission.project_id is None or mission.status not in {"active", "blocked", "failed"}:
            continue
        pins = pins_by_project.get(mission.project_id, [])
        if not pins:
            continue
        lane_skill_catalog = lane_skill_rows.get(mission.instance_id, [])
        missing_skills = [
            pin.name
            for pin in pins
            if not any(_skill_matches_pin(skill, pin) for skill in lane_skill_catalog)
        ]
        if not missing_skills:
            continue
        gap_counts_by_instance[mission.instance_id] = (
            gap_counts_by_instance.get(mission.instance_id, 0) + 1
        )
        gap_views.append(
            DashboardSkillGapView(
                mission_id=mission.id,
                mission_name=mission.name,
                lane_label=next(
                    (instance.name for instance in instances if instance.id == mission.instance_id),
                    mission.instance_name,
                ),
                project_label=mission.project_label
                or (
                    project_by_id[mission.project_id].label
                    if mission.project_id in project_by_id
                    else None
                ),
                missing_skills=missing_skills,
                recommended_action=(
                    mission.suggested_action
                    or (
                        "Move the mission onto a lane with the missing repo skills or update "
                        "the skillbook."
                    )
                ),
            )
        )

    lane_views: list[DashboardSkillRegistryLaneView] = []
    for instance in instances:
        project_ids = lane_project_ids.get(instance.id, [])
        project_labels = [
            project_by_id[project_id].label
            for project_id in project_ids
            if project_id in project_by_id
        ]
        lane_skills: list[DashboardSkillRegistrySkillView] = []
        relevant_skill_count = 0
        for skill in lane_skill_rows.get(instance.id, []):
            pinned_projects = sorted(
                {
                    project_by_id[project_id].label
                    for project_id in project_ids
                    if project_id in project_by_id
                    and any(
                        _skill_matches_pin(skill, pin)
                        for pin in pins_by_project.get(project_id, [])
                    )
                }
            )
            if pinned_projects:
                relevant_skill_count += 1
            success_count = sum(
                count
                for (project_id, name_key, source_key), count in skill_success_counts.items()
                if project_id in project_ids
                and (name_key, source_key) == _skill_identity(skill["name"], skill["source"])
            )
            lane_skills.append(
                DashboardSkillRegistrySkillView(
                    name=skill["name"] or "Unnamed skill",
                    source=skill["source"],
                    status=skill["status"],
                    lane_count=1,
                    lanes=[instance.name],
                    successful_run_count=success_count,
                    pinned_projects=pinned_projects,
                )
            )
        lane_views.append(
            DashboardSkillRegistryLaneView(
                instance_id=instance.id,
                instance_name=instance.name,
                connected=instance.connected,
                cwd=instance.cwd,
                project_labels=project_labels,
                skill_count=len(lane_skills),
                relevant_skill_count=relevant_skill_count,
                successful_run_count=sum(
                    len(successful_missions_by_project.get(project_id, []))
                    for project_id in project_ids
                ),
                gap_count=gap_counts_by_instance.get(instance.id, 0),
                skills=sorted(lane_skills, key=lambda skill: skill.name.lower()),
            )
        )

    project_views: list[DashboardSkillRegistryProjectView] = []
    for project in projects:
        project_pins = sorted(
            pins_by_project.get(project.id, []),
            key=lambda pin: pin.name.lower(),
        )
        relevant_instances = [
            instance
            for instance in instances
            if project.id in lane_project_ids.get(instance.id, [])
        ]
        live_skill_map: dict[tuple[str, str], DashboardSkillRegistrySkillView] = {}
        for instance in relevant_instances:
            for skill in lane_skill_rows.get(instance.id, []):
                identity = _skill_identity(skill["name"], skill["source"])
                if not identity[0]:
                    continue
                view = live_skill_map.get(identity)
                if view is None:
                    view = DashboardSkillRegistrySkillView(
                        name=skill["name"] or "Unnamed skill",
                        source=skill["source"],
                        status=skill["status"],
                        lane_count=0,
                        lanes=[],
                        successful_run_count=skill_success_counts.get((project.id, *identity), 0),
                        pinned_projects=[],
                    )
                    live_skill_map[identity] = view
                view.lane_count += 1
                if instance.name not in view.lanes:
                    view.lanes.append(instance.name)
                if any(_skill_matches_pin(skill, pin) for pin in project_pins):
                    view.pinned_projects = [project.label]

        matched_skill_count = sum(
            any(
                any(
                    _skill_matches_pin(skill, pin) for skill in lane_skill_rows.get(instance.id, [])
                )
                for instance in relevant_instances
            )
            for pin in project_pins
        )
        missing_skills = [
            pin.name
            for pin in project_pins
            if not any(
                any(
                    _skill_matches_pin(skill, pin) for skill in lane_skill_rows.get(instance.id, [])
                )
                for instance in relevant_instances
            )
        ]
        project_views.append(
            DashboardSkillRegistryProjectView(
                project_id=project.id,
                project_label=project.label,
                lane_count=len(relevant_instances),
                mission_count=len(missions_by_project.get(project.id, [])),
                successful_run_count=len(successful_missions_by_project.get(project.id, [])),
                pinned_skill_count=len(project_pins),
                live_skill_count=len(live_skill_map),
                matched_skill_count=matched_skill_count,
                missing_skills=missing_skills,
                skills=sorted(
                    live_skill_map.values(),
                    key=lambda skill: (skill.successful_run_count * -1, skill.name.lower()),
                ),
            )
        )

    total_live_skills = sum(lane.skill_count for lane in lane_views)
    if gap_views:
        headline = "Skills registry has live gaps"
        summary = (
            f"{len(gap_views)} mission(s) are running on lanes that do not appear to carry one or "
            "more pinned repo skills."
        )
    elif total_live_skills:
        headline = "Skills registry is active"
        summary = (
            f"{total_live_skills} live skill(s) are mapped across {len(lane_views)} lane(s) and "
            f"{len(project_views)} project workspace(s)."
        )
    else:
        headline = "Skills registry is idle"
        summary = (
            "Connect a lane with live skills to turn repo skill coverage into an operator map."
        )

    return DashboardSkillsRegistryView(
        headline=headline,
        summary=summary,
        lanes=sorted(
            lane_views,
            key=lambda lane: (
                lane.gap_count * -1,
                lane.relevant_skill_count * -1,
                lane.instance_name.lower(),
            ),
        ),
        projects=sorted(
            project_views,
            key=lambda project: (
                len(project.missing_skills) * -1,
                project.live_skill_count * -1,
                project.project_label.lower(),
            ),
        ),
        gaps=sorted(
            gap_views,
            key=lambda gap: (
                len(gap.missing_skills) * -1,
                gap.mission_name.lower(),
            ),
        )[:8],
    )


def _build_auth_posture(integrations: list[IntegrationView]) -> DashboardAuthPostureView:
    enabled_integrations = [integration for integration in integrations if integration.enabled]
    satisfied_count = sum(
        integration.auth_status == "satisfied" for integration in enabled_integrations
    )
    missing_count = sum(
        integration.auth_status == "missing" for integration in enabled_integrations
    )
    degraded_count = sum(
        integration.auth_status == "degraded" for integration in enabled_integrations
    )

    if degraded_count:
        headline = "Integration auth is degraded"
        summary = (
            f"{degraded_count} integration(s) have broken vault references or unreadable secrets."
        )
    elif missing_count:
        headline = "Integration auth has gaps"
        summary = f"{missing_count} integration(s) still need credentials attached."
    elif enabled_integrations:
        headline = "Integration auth is satisfied"
        summary = "Enabled integrations have usable credentials or explicitly require none."
    else:
        headline = "Integration auth is idle"
        summary = "Add integrations to start tracking credential posture."

    return DashboardAuthPostureView(
        headline=headline,
        summary=summary,
        satisfied_count=satisfied_count,
        missing_count=missing_count,
        degraded_count=degraded_count,
    )


def _empty_access_posture() -> DashboardAccessPostureView:
    return DashboardAccessPostureView(
        headline="Remote ingress is local-only",
        summary=(
            "No operator API keys are active yet. The browser workflow stays available, "
            "but external control is still closed."
        ),
        team_count=0,
        operator_count=0,
        api_key_count=0,
        recent_remote_request_count=0,
    )


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
            "approvals_pending_count": int(summary.get("approvals_pending_count") or 0),
            "mission_id": summary.get("mission_id"),
            "mission_name": summary.get("mission_name"),
            "project_label": summary.get("project_label"),
            "thread_id": summary.get("thread_id"),
            "mission_status": summary.get("mission_status"),
            "phase": summary.get("phase"),
            "current_command": summary.get("current_command"),
            "command_burn": int(summary.get("command_burn") or 0),
            "token_burn": int(summary.get("token_burn") or 0),
            "last_checkpoint_summary": summary.get("last_checkpoint_summary"),
            "continuity_state": summary.get("continuity_state"),
            "continuity_score": summary.get("continuity_score"),
            "safest_handoff": summary.get("safest_handoff"),
            "note": summary.get("note"),
            "created_at": row["created_at"],
        }
    )


def _pick_lane_snapshot_mission(missions: list[MissionView]) -> MissionView | None:
    if not missions:
        return None
    status_rank = {
        "active": 0,
        "blocked": 1,
        "paused": 2,
        "failed": 3,
        "completed": 4,
    }

    def sort_timestamp(mission: MissionView) -> float:
        parsed = _parse_timestamp(mission.last_activity_at or mission.updated_at.isoformat())
        return parsed.timestamp() if parsed is not None else 0.0

    return sorted(
        missions,
        key=lambda mission: (
            status_rank.get(mission.status, 9),
            -sort_timestamp(mission),
        ),
    )[0]


def _task_status(
    task: TaskBlueprintView,
    latest_mission: MissionView | None,
) -> TaskStatus:
    if not task.enabled:
        return "disabled"
    latest_summary = (
        latest_mission.last_checkpoint
        if latest_mission is not None and latest_mission.last_checkpoint
        else task.last_result_summary
    )
    if _task_has_terminal_completion(task, latest_summary):
        return "completed"
    if latest_mission is not None:
        if latest_mission.status == "active":
            return "running"
        if latest_mission.status in {"blocked", "failed"}:
            return "attention"
    next_run = _parse_timestamp(_next_run_at(task))
    if next_run is not None and next_run <= datetime.now(UTC):
        return "due"
    if latest_mission is not None and latest_mission.status == "completed":
        return "completed"
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


def _summarize_text(value: str | None, *, limit: int = 220) -> str:
    cleaned = " ".join((value or "").split())
    if not cleaned:
        return ""
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _mission_lane_label(
    mission: MissionView,
    instance_by_id: dict[int, InstanceView],
) -> str | None:
    instance = instance_by_id.get(mission.instance_id)
    return instance.name if instance is not None else mission.instance_name


def _mission_action(mission: MissionView, fallback: str) -> str:
    return mission.suggested_action or fallback


def _build_task_objective(
    task: TaskBlueprintView,
    *,
    skill_pins: list[SkillPinView],
    integrations: list[IntegrationView],
    toolsets: list[str],
    preferred_memory_provider: str = DEFAULT_HERMES_MEMORY_PROVIDER,
    preferred_executor: str = DEFAULT_HERMES_EXECUTOR,
    instance_name: str | None = None,
    instance_cwd: str | None = None,
    project_path: str | None = None,
) -> str:
    is_openclaw_parity = _task_targets_openclaw_parity(task)
    sections = [_normalized_task_objective_template(task)]
    if task.run_until_complete:
        marker = _task_completion_marker(task)
        sections.extend(
            [
                "",
                "Continuous loop contract:",
                (
                    "- This blueprint should keep chaining forward until the requested "
                    "outcome is genuinely complete."
                ),
                (
                    f"- If the target is fully complete, start the final checkpoint with "
                    f"`{marker}` so OpenZues can stop relaunching this task."
                ),
                (
                    "- If the target is not complete, leave the next smallest verified "
                    "slice so the next autonomous cycle can continue immediately."
                ),
            ]
        )
    if is_openclaw_parity:
        sections.extend(
            [
                "",
                "OpenClaw parity anchor:",
                (
                    f"- Resume from `{OPENCLAW_PARITY_CHECKPOINT_LEDGER}` instead of rebuilding "
                    "the global source inventory."
                ),
                (
                    "- Lock one unfinished seam from the latest checkpoint, name the target "
                    "files, land the change, run focused verification, and checkpoint that "
                    "slice."
                ),
                (
                    "- Detailed skill, tool, runtime, integration, and workspace posture is "
                    "injected at mission turn time. Do not spend the first move rereading "
                    "advisory local SKILL.md files unless the chosen seam directly needs one."
                ),
            ]
        )
        return "\n".join(sections)
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
        if any(
            skill.enabled and is_local_skill_source_available(skill.source) for skill in skill_pins
        ):
            sections.append(
                "- If a skill includes a Source path, open that SKILL.md before running the "
                "workflow so the procedure stays grounded."
            )
    tool_policy_lines = build_hermes_tool_policy_lines(
        build_hermes_tool_policy(toolsets, setup_mode="local")
    )
    if tool_policy_lines:
        sections.extend(["", *tool_policy_lines])
    executor_lines = build_executor_profile_lines(
        preferred_executor,
        instance_name=instance_name,
        cwd=instance_cwd or project_path or task.cwd,
    )
    memory_provider_lines = build_memory_provider_lines(
        preferred_memory_provider,
        integrations=integrations,
        toolsets=toolsets,
        cwd=instance_cwd or project_path or task.cwd,
    )
    sections.extend(
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
    if integrations:
        sections.extend(
            [
                "",
                "Known integration inventory:",
                *[
                    f"- {integration.name} ({integration.kind})"
                    + (f" at {integration.base_url}" if integration.base_url else "")
                    + (
                        f". Auth: {integration.auth_status}. {integration.auth_detail}"
                        if integration.auth_detail
                        else ""
                    )
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
    memory_protocol_lines = build_mempalace_protocol_lines(
        integration for integration in integrations if integration.enabled
    )
    if memory_protocol_lines:
        sections.extend(["", *memory_protocol_lines])
    ecc_workspace_lines = build_ecc_workspace_lines(project_path or task.cwd)
    if ecc_workspace_lines:
        sections.extend(["", *ecc_workspace_lines])
    return "\n".join(sections)


def _project_skillbook_pins(
    project: ProjectView,
    *,
    explicit_pins: list[SkillPinView],
    missions: list[MissionView],
    task_blueprints: list[TaskBlueprintView],
) -> list[SkillPinView]:
    context = "\n".join(
        [
            project.label,
            project.path,
            *[mission.objective for mission in missions],
            *[task.objective_template for task in task_blueprints],
        ]
    )
    return materialize_skillbook_pins(
        project.id,
        context,
        explicit_pins=explicit_pins,
        project_label=project.label,
        project_path=project.path,
        toolsets=sorted(
            {
                *{toolset for mission in missions for toolset in mission.toolsets},
                *{toolset for task in task_blueprints for toolset in task.toolsets},
            }
        ),
    )


def _build_task_views(
    *,
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    task_blueprints: list[TaskBlueprintView],
    skill_pins: list[SkillPinView],
    integrations: list[IntegrationView],
    preferred_memory_provider: str = DEFAULT_HERMES_MEMORY_PROVIDER,
    preferred_executor: str = DEFAULT_HERMES_EXECUTOR,
) -> list[DashboardTaskView]:
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
        task = _attach_task_tool_policy(
            task,
            project_label=project.label if project is not None else None,
            project_path=project.path if project is not None else None,
        )
        scoped_skills = materialize_skillbook_pins(
            task.project_id or 0,
            task.objective_template,
            explicit_pins=skills_by_project.get(task.project_id or -1, []),
            project_label=project.label if project is not None else None,
            project_path=project.path if project is not None else None,
            toolsets=task.toolsets,
        )
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
                toolsets=task.toolsets,
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
                instance_name=instance.name if instance is not None else None,
                instance_cwd=task.cwd or (project.path if project is not None else None),
                project_path=project.path if project is not None else task.cwd,
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
            toolsets=task.toolsets,
            start_immediately=True,
            tool_policy=task.tool_policy,
            preferred_memory_provider=preferred_memory_provider,
            preferred_memory_provider_label=memory_provider_label(preferred_memory_provider),
            preferred_executor=preferred_executor,
            preferred_executor_label=executor_label(preferred_executor),
            runtime_profile_summary=build_runtime_profile_summary(
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
        )
        tasks.append(
            DashboardTaskView(
                id=task.id,
                name=task.name,
                summary=task.summary or _summarize_objective(task.objective_template),
                status=_task_status(task, latest_mission),
                cadence_label=_format_task_cadence(task),
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
    return sorted(tasks, key=lambda task: (rank[task.status], task.name.lower()))


def _build_task_inbox_items(
    *,
    instances: list[InstanceView],
    missions: list[MissionView],
    tasks: list[DashboardTaskView],
    playbooks: list[PlaybookView],
    projects: list[ProjectView],
    integrations: list[IntegrationView],
) -> list[DashboardTaskInboxItemView]:
    items: list[DashboardTaskInboxItemView] = []
    instance_by_id = {instance.id: instance for instance in instances}
    mission_by_id = {mission.id: mission for mission in missions}
    mission_by_thread = {mission.thread_id: mission for mission in missions if mission.thread_id}
    represented_missions: set[int] = set()

    def add_item(
        *,
        item_id: str,
        kind: str,
        source: str,
        urgency: SignalLevel,
        title: str,
        summary: str,
        recommended_action: str,
        jump_label: str,
        lane_label: str | None = None,
        project_label: str | None = None,
        mission_id: int | None = None,
        task_id: int | None = None,
        playbook_id: int | None = None,
        instance_id: int | None = None,
        request_id: str | None = None,
        freshness_minutes: int | None = None,
        reflex: MissionReflexRun | None = None,
    ) -> None:
        items.append(
            DashboardTaskInboxItemView(
                id=item_id,
                kind=kind,
                source=source,
                urgency=urgency,
                lane_label=lane_label,
                project_label=project_label,
                title=title,
                summary=summary,
                recommended_action=recommended_action,
                jump_label=jump_label,
                mission_id=mission_id,
                task_id=task_id,
                playbook_id=playbook_id,
                instance_id=instance_id,
                request_id=request_id,
                freshness_minutes=freshness_minutes,
                reflex=reflex,
            )
        )

    for mission in sorted(missions, key=lambda item: item.updated_at, reverse=True):
        freshness_minutes = _minutes_since(mission.last_activity_at)
        lane_label = _mission_lane_label(mission, instance_by_id)
        last_error = str(mission.last_error or "")

        if mission.status == "blocked" and mission.phase == "approval":
            add_item(
                item_id=f"mission:{mission.id}:approval",
                kind="approval_required",
                source="Approvals",
                urgency="critical",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=f"Approval waiting for {mission.name}",
                summary=_summarize_text(
                    last_error or "Codex paused for an explicit approval gate."
                ),
                recommended_action=_mission_action(
                    mission,
                    "Review the approval and decide whether the mission can continue.",
                ),
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=freshness_minutes,
            )
            represented_missions.add(mission.id)
            continue

        if mission.phase == "offline" or last_error.startswith("Instance is offline"):
            add_item(
                item_id=f"mission:{mission.id}:offline",
                kind="mission_offline",
                source="Missions",
                urgency="critical",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=f"{mission.name} lost its lane",
                summary=_summarize_text(
                    last_error or "The mission cannot move again until the lane reconnects."
                ),
                recommended_action=_mission_action(
                    mission,
                    "Reconnect the lane or fail this mission over before autonomy stalls.",
                ),
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=freshness_minutes,
            )
            represented_missions.add(mission.id)
            continue

        if mission.status == "failed":
            add_item(
                item_id=f"mission:{mission.id}:failed",
                kind="mission_failed",
                source="Missions",
                urgency="critical",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=f"{mission.name} failed its last cycle",
                summary=_summarize_text(
                    last_error or "The last mission cycle exited with an unrecovered error."
                ),
                recommended_action=_mission_action(
                    mission,
                    "Inspect the failure context, choose the safest repair, then rerun it.",
                ),
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=freshness_minutes,
            )
            represented_missions.add(mission.id)
            continue

        if mission.status == "blocked":
            add_item(
                item_id=f"mission:{mission.id}:blocked",
                kind="mission_blocked",
                source="Missions",
                urgency="warn",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=f"{mission.name} is blocked",
                summary=_summarize_text(
                    last_error or "The mission is waiting on an operator or lane-side condition."
                ),
                recommended_action=_mission_action(
                    mission,
                    "Clear the blocker, then resume the mission from the same thread.",
                ),
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=freshness_minutes,
            )
            represented_missions.add(mission.id)
            continue

        if mission.status in {"paused", "completed"} and mission.last_checkpoint:
            uses_mempalace = has_mempalace_integration(
                integrations,
                project_id=mission.project_id,
            )
            add_item(
                item_id=f"mission:{mission.id}:handoff",
                kind="checkpoint_ready",
                source="Checkpoints",
                urgency="ready",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=(
                    f"Handoff and memory writeback ready from {mission.name}"
                    if uses_mempalace
                    else f"Handoff ready from {mission.name}"
                ),
                summary=_summarize_text(mission.last_checkpoint),
                recommended_action=_mission_action(
                    mission,
                    (
                        MEMPALACE_WRITEBACK_ACTION
                        if uses_mempalace
                        else "Review the checkpoint and resume only when the next slice is clear."
                    ),
                ),
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=freshness_minutes,
            )
            represented_missions.add(mission.id)

    for instance in instances:
        for request in instance.unresolved_requests:
            request_mission = mission_by_thread.get(str(request.get("thread_id") or ""))
            if request_mission is not None:
                continue
            payload_preview = _summarize_text(
                json.dumps(request.get("payload", {}), sort_keys=True)
            )
            add_item(
                item_id=f"instance:{instance.id}:request:{request['request_id']}",
                kind="approval_orphaned",
                source="Approvals",
                urgency="warn",
                lane_label=instance.name,
                title=f"Unassigned approval waiting on {instance.name}",
                summary=_summarize_text(
                    f"{request.get('method', 'request')} is pending without a tracked mission. "
                    f"{payload_preview}"
                ),
                recommended_action=(
                    "Resolve the request or attach the related thread to a mission before it "
                    "stales out."
                ),
                jump_label="View lane",
                instance_id=instance.id,
                request_id=str(request["request_id"]),
                freshness_minutes=_minutes_since(str(request.get("created_at") or "")),
            )

    for mission in missions:
        if mission.id in represented_missions:
            continue
        scope = build_scope_assessment(mission, checkpoints=mission.checkpoints)
        if scope.drift_level in {"drifting", "critical"}:
            add_item(
                item_id=f"mission:{mission.id}:scope",
                kind="scope_drift",
                source="Scope",
                urgency="critical" if scope.drift_level == "critical" else "warn",
                lane_label=_mission_lane_label(mission, instance_by_id),
                project_label=mission.project_label,
                title=f"Scope drift detected for {mission.name}",
                summary=_summarize_text(scope.drift_summary),
                recommended_action=scope.recommended_action,
                jump_label="View mission",
                mission_id=mission.id,
                instance_id=mission.instance_id,
                freshness_minutes=_minutes_since(mission.last_activity_at),
            )
            represented_missions.add(mission.id)
            continue
        lane_instance = instance_by_id.get(mission.instance_id)
        packet = build_continuity_packet(
            mission,
            instance_connected=lane_instance.connected if lane_instance is not None else False,
            checkpoints=mission.checkpoints,
            project_label=mission.project_label,
        )
        if packet.state != "fragile":
            continue
        add_item(
            item_id=f"mission:{mission.id}:continuity",
            kind="continuity_fragile",
            source="Continuity",
            urgency="warn",
            lane_label=_mission_lane_label(mission, instance_by_id),
            project_label=mission.project_label,
            title=f"Continuity is fragile for {mission.name}",
            summary=_summarize_text(packet.drift),
            recommended_action=packet.next_handoff,
            jump_label="View mission",
            mission_id=mission.id,
            instance_id=mission.instance_id,
            freshness_minutes=packet.freshness_minutes,
        )
        represented_missions.add(mission.id)

    reflex_deck = build_reflex_deck(instances, missions, projects)
    for reflex in reflex_deck.reflexes:
        if reflex.mission_id in represented_missions:
            continue
        reflex_mission = mission_by_id.get(reflex.mission_id)
        add_item(
            item_id=f"mission:{reflex.mission_id}:reflex:{reflex.kind}",
            kind="reflex_armed",
            source="Reflexes",
            urgency=reflex.level,
            lane_label=(
                _mission_lane_label(reflex_mission, instance_by_id)
                if reflex_mission is not None
                else None
            ),
            project_label=reflex.project_label,
            title=reflex.title,
            summary=_summarize_text(reflex.summary),
            recommended_action=(
                "Fire the synthesized reflex or inspect the mission before drift grows."
            ),
            jump_label="View mission",
            mission_id=reflex.mission_id,
            instance_id=reflex_mission.instance_id if reflex_mission is not None else None,
            freshness_minutes=(
                _minutes_since(reflex_mission.last_activity_at)
                if reflex_mission is not None
                else None
            ),
            reflex=MissionReflexRun(
                kind=reflex.kind,
                title=reflex.title,
                prompt=reflex.prompt,
            ),
        )

    for task in tasks:
        if task.status not in {"due", "attention"}:
            continue
        summary = task.last_result_summary or task.summary
        recommended_action = (
            "Launch the scheduled draft now or load it into the composer before the cadence slips."
            if task.status == "due"
            else (
                "Review the latest mission result, then relaunch the schedule once the path "
                "is clear."
            )
        )
        add_item(
            item_id=f"task:{task.id}:{task.status}",
            kind="task_due" if task.status == "due" else "task_attention",
            source="Schedules",
            urgency="ready" if task.status == "due" else "warn",
            lane_label=task.instance_name,
            project_label=task.project_label,
            title=(
                f"Scheduled launch due: {task.name}"
                if task.status == "due"
                else f"Scheduled workflow needs repair: {task.name}"
            ),
            summary=_summarize_text(summary),
            recommended_action=recommended_action,
            jump_label="Load draft",
            task_id=task.id,
            freshness_minutes=_minutes_since(task.next_run_at or datetime.now(UTC).isoformat()),
        )

    for playbook in playbooks:
        if playbook.cadence_minutes is None or not playbook.enabled:
            continue
        if playbook.last_status != "failed":
            continue
        add_item(
            item_id=f"playbook:{playbook.id}:failed",
            kind="playbook_attention",
            source="Playbooks",
            urgency="warn",
            title=f"Scheduled playbook needs repair: {playbook.name}",
            summary=_summarize_text(
                playbook.last_result_summary
                or "The last scheduled playbook run failed before it could complete."
            ),
            recommended_action=(
                "Inspect the saved playbook inputs, lane target, or thread target before the "
                "next cadence fires."
            ),
            jump_label="View playbook",
            playbook_id=playbook.id,
            freshness_minutes=_minutes_since(playbook.last_run_at),
        )

    urgency_rank = {"critical": 0, "warn": 1, "ready": 2, "info": 3}
    return sorted(
        items,
        key=lambda item: (
            urgency_rank[item.urgency],
            item.freshness_minutes if item.freshness_minutes is not None else 99999,
            item.title.lower(),
        ),
    )[:12]


def build_ops_mesh(
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    playbooks: list[PlaybookView],
    task_blueprints: list[TaskBlueprintView],
    skill_pins: list[SkillPinView],
    vault_secrets: list[VaultSecretView],
    integrations: list[IntegrationView],
    notification_routes: list[NotificationRouteView],
    lane_snapshots: list[LaneSnapshotView],
    *,
    outbound_deliveries: list[OutboundDeliveryView] | None = None,
    access_posture: DashboardAccessPostureView | None = None,
    teams: list[TeamView] | None = None,
    operators: list[OperatorView] | None = None,
    remote_requests: list[RemoteRequestView] | None = None,
    preferred_memory_provider: str = DEFAULT_HERMES_MEMORY_PROVIDER,
    preferred_executor: str = DEFAULT_HERMES_EXECUTOR,
) -> DashboardOpsMeshView:
    skills_by_project: dict[int, list[SkillPinView]] = {}
    missions_by_project: dict[int, list[MissionView]] = {}
    tasks_by_project: dict[int, list[TaskBlueprintView]] = {}
    for skill in skill_pins:
        skills_by_project.setdefault(skill.project_id, []).append(skill)
    for mission in missions:
        if mission.project_id is not None:
            missions_by_project.setdefault(mission.project_id, []).append(mission)
    for task in task_blueprints:
        if task.project_id is not None:
            tasks_by_project.setdefault(task.project_id, []).append(task)

    tasks = _build_task_views(
        instances=instances,
        missions=missions,
        projects=projects,
        task_blueprints=task_blueprints,
        skill_pins=skill_pins,
        integrations=integrations,
        preferred_memory_provider=preferred_memory_provider,
        preferred_executor=preferred_executor,
    )
    inbox_items = _build_task_inbox_items(
        instances=instances,
        missions=missions,
        tasks=tasks,
        playbooks=playbooks,
        projects=projects,
        integrations=integrations,
    )

    attention = sum(task.status == "attention" for task in tasks)
    due = sum(task.status == "due" for task in tasks)
    running = sum(task.status == "running" for task in tasks)
    critical_items = sum(item.urgency == "critical" for item in inbox_items)
    warning_items = sum(item.urgency == "warn" for item in inbox_items)
    ready_items = sum(item.urgency == "ready" for item in inbox_items)
    if critical_items:
        headline = "Ops mesh needs attention"
        summary = (
            f"{critical_items} critical operator item(s) are waiting across approvals, "
            "missions, or lane health."
        )
    elif attention:
        headline = "Ops mesh needs attention"
        summary = (
            f"{attention} scheduled workflow(s) are blocked or degraded. "
            "Clear those first so the always-on layer stays trustworthy."
        )
    elif warning_items:
        headline = "Ops mesh is active"
        summary = (
            f"{warning_items} operator item(s) need steering before they become true blockers."
        )
    elif due or running or ready_items:
        headline = "Ops mesh is active"
        summary = (
            f"{running} workflow(s) are live, {due} schedules are due, and "
            f"{ready_items} inbox item(s) are ready for review."
        )
    else:
        headline = "Ops mesh is ready"
        summary = (
            "Recurring workflows, notifications, skillbooks, and lane history are "
            "configured and waiting for the next run."
        )

    if inbox_items:
        task_headline = "Operator inbox is active"
        task_summary = (
            f"{critical_items} critical, {warning_items} watch, and {ready_items} ready item(s) "
            "are synthesized from approvals, mission state, continuity, reflexes, and schedules."
        )
    elif tasks:
        task_headline = "Operator inbox is quiet"
        task_summary = (
            "No high-urgency interrupts are active right now. Scheduled task blueprints and "
            "playbooks remain available below for repeated launches."
        )
    else:
        task_headline = "No task blueprints yet"
        task_summary = (
            "Create a task blueprint to turn a repeated objective into a durable mission loop."
        )

    skillbooks: list[DashboardSkillbookView] = []
    for project in projects:
        project_skills = sorted(
            _project_skillbook_pins(
                project,
                explicit_pins=skills_by_project.get(project.id, []),
                missions=missions_by_project.get(project.id, []),
                task_blueprints=tasks_by_project.get(project.id, []),
            ),
            key=lambda skill: skill.name.lower(),
        )
        if not project_skills:
            continue
        skillbooks.append(
            DashboardSkillbookView(
                project_id=project.id,
                project_label=project.label,
                skills=project_skills,
            )
        )
    skills_registry = _build_skills_registry(
        instances=instances,
        missions=missions,
        projects=projects,
        skill_pins=skill_pins,
    )
    auth_posture = _build_auth_posture(integrations)
    active_access_posture = access_posture or _empty_access_posture()
    integrations_inventory = _build_integrations_inventory(
        instances=instances,
        missions=missions,
        projects=projects,
        integrations=integrations,
        access_posture=active_access_posture,
    )

    return DashboardOpsMeshView(
        headline=headline,
        summary=summary,
        task_inbox=DashboardTaskInboxView(
            headline=task_headline,
            summary=task_summary,
            items=inbox_items,
            tasks=tasks,
        ),
        auth_posture=auth_posture,
        access_posture=active_access_posture,
        integrations_inventory=integrations_inventory,
        skills_registry=skills_registry,
        skillbooks=skillbooks,
        teams=teams or [],
        operators=operators or [],
        remote_requests=remote_requests or [],
        vault_secrets=vault_secrets,
        integrations=integrations,
        notification_routes=notification_routes,
        outbound_deliveries=outbound_deliveries or [],
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
    vault: VaultService
    wake_service: GatewayWakeService | None = None
    playbooks: PlaybookService = field(default_factory=PlaybookService)
    launch_routing: LaunchRoutingService | None = None
    cron_webhook_url: str | None = None
    cron_webhook_token: str | None = None
    cron_failure_alert: dict[str, Any] | None = None
    cron_retry: dict[str, Any] | None = None
    poll_interval_seconds: float = 20.0
    snapshot_interval_seconds: float = 1800.0
    parity_checkpoint_path: Path | None = None
    outbound_runtime_service: GatewayOutboundRuntimeService | None = None
    session_delivery_service: Callable[[str, str], Awaitable[object]] | None = None
    canvas_state_dir: Path | None = None
    _task: asyncio.Task[None] | None = field(init=False, default=None)
    _stop_event: asyncio.Event = field(init=False, default_factory=asyncio.Event)
    _notified_inbox_items: dict[str, str] = field(init=False, default_factory=dict)
    _direct_delivery_inflight: dict[tuple[str, str], asyncio.Task[dict[str, object]]] = field(
        init=False,
        default_factory=dict,
    )
    _direct_delivery_inflight_lock: asyncio.Lock = field(
        init=False,
        default_factory=asyncio.Lock,
    )

    async def start(self) -> None:
        if self._task is not None:
            return
        await self._migrate_legacy_secret_refs()
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

    def _resolve_outbound_runtime_service(self) -> GatewayOutboundRuntimeService | None:
        runtime = self.outbound_runtime_service
        if runtime is None:
            runtime = GatewayOutboundRuntimeService(
                session_deliverer=self.session_delivery_service,
                provider_message_deliverer=self._deliver_route_backed_provider_message,
                provider_poll_deliverer=self._deliver_route_backed_provider_poll,
            )
            self.outbound_runtime_service = runtime
            return runtime
        if self.session_delivery_service is not None and not runtime.is_message_available():
            runtime.bind_session_deliverer(self.session_delivery_service)
        if not runtime.has_provider_message_deliverer():
            runtime.bind_provider_message_deliverer(
                self._deliver_route_backed_provider_message
            )
        if not runtime.has_provider_poll_deliverer():
            runtime.bind_provider_poll_deliverer(self._deliver_route_backed_provider_poll)
        return runtime

    def _outbound_runtime_available(self) -> bool:
        runtime = self._resolve_outbound_runtime_service()
        return runtime is not None and runtime.is_available()

    def _session_outbound_runtime_available(self) -> bool:
        runtime = self._resolve_outbound_runtime_service()
        return runtime is not None and runtime.has_session_deliverer()

    async def list_task_blueprint_views(self) -> list[TaskBlueprintView]:
        projects = {int(project["id"]): project for project in await self.database.list_projects()}
        tasks: list[TaskBlueprintView] = []
        for row in await self.database.list_task_blueprints():
            task = _serialize_task(row)
            project = projects.get(task.project_id) if task.project_id is not None else None
            tasks.append(
                await self._hydrate_task_blueprint_view(
                    task,
                    project_label=str(project["label"]) if project is not None else None,
                    project_path=str(project["path"]) if project is not None else None,
                )
            )
        return tasks

    async def list_vault_secret_views(self) -> list[VaultSecretView]:
        return await self.vault.list_secret_views()

    async def create_vault_secret(self, payload: VaultSecretCreate) -> VaultSecretView:
        return await self.vault.create_secret(payload)

    async def delete_vault_secret(self, secret_id: int) -> None:
        await self.vault.delete_secret(secret_id)

    async def list_notification_route_views(self) -> list[NotificationRouteView]:
        await self._migrate_legacy_secret_refs()
        secrets_by_id = {secret.id: secret for secret in await self.vault.list_secret_views()}
        routes: list[NotificationRouteView] = []
        for row in await self.database.list_notification_routes():
            secret_id = row.get("vault_secret_id")
            secret = secrets_by_id.get(int(secret_id)) if secret_id is not None else None
            has_secret = bool(secret) or bool(row.get("secret_token"))
            secret_preview = (
                secret.secret_preview
                if secret is not None
                else mask_secret(str(row.get("secret_token") or ""))[1]
            )
            routes.append(
                _serialize_route(
                    row,
                    vault_secret_label=secret.label if secret is not None else None,
                    secret_preview=secret_preview,
                    has_secret=has_secret,
                )
            )
        return routes

    async def list_outbound_delivery_views(
        self,
        *,
        limit: int = 25,
        states: list[str] | None = None,
        newest_first: bool = True,
    ) -> list[OutboundDeliveryView]:
        rows = await self.database.list_outbound_deliveries(
            limit=limit,
            states=states,
            newest_first=newest_first,
        )
        return [_serialize_outbound_delivery(row) for row in rows]

    async def _get_notification_route_row(self, route_id: int) -> dict[str, Any] | None:
        for row in await self.database.list_notification_routes():
            if int(row["id"]) == route_id:
                return row
        return None

    async def _serialize_notification_route_row(self, row: dict[str, Any]) -> NotificationRouteView:
        secret_id = row.get("vault_secret_id")
        secret = await self.vault.get_secret_view(int(secret_id)) if secret_id is not None else None
        has_secret = bool(secret) or bool(row.get("secret_token"))
        secret_preview = (
            secret.secret_preview
            if secret is not None
            else mask_secret(str(row.get("secret_token") or ""))[1]
        )
        return _serialize_route(
            row,
            vault_secret_label=secret.label if secret is not None else None,
            secret_preview=secret_preview,
            has_secret=has_secret,
        )

    async def _deliver_saved_outbound_delivery_row(
        self,
        delivery_row: dict[str, Any],
        route: dict[str, Any],
        *,
        result_suffix: str = "",
    ) -> tuple[bool, str | None]:
        delivery_id = int(delivery_row["id"])
        route_id = int(route["id"])
        event_type = str(delivery_row.get("event_type") or "")
        event_payload = dict(delivery_row.get("event_payload") or {})
        route_kind = str(route.get("kind") or delivery_row.get("route_kind") or "").strip().lower()
        route_conversation_target = _normalize_conversation_target(
            route.get("conversation_target")
        ) or _normalize_conversation_target(delivery_row.get("conversation_target"))
        attempt_started_at = utcnow()
        existing_attempts = max(0, int(delivery_row.get("attempt_count") or 0))
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        native_provider_delivery = (
            route_kind in NATIVE_PROVIDER_ROUTE_KINDS
            and event_type in {"gateway/send", "gateway/poll"}
        )
        result: object | None = None
        try:
            secret_id = route.get("vault_secret_id")
            secret_token = (
                await self.vault.get_secret_value(int(secret_id))
                if secret_id is not None
                else (str(route.get("secret_token")) if route.get("secret_token") else None)
            )
            if native_provider_delivery:
                event_payload = _saved_provider_route_event_payload(
                    event_type=event_type,
                    event_payload=event_payload,
                    conversation_target=route_conversation_target,
                )
            result = await asyncio.to_thread(
                self._provider_event_poster(route_kind)
                if native_provider_delivery
                else self._post_webhook,
                route,
                event_type,
                event_payload,
                secret_token,
            )
        except Exception as exc:
            error = str(exc)[:240]
            attempt_count = existing_attempts + 1
            if _is_permanent_outbound_delivery_error(error):
                attempt_count = max(attempt_count, OUTBOUND_DELIVERY_MAX_RETRIES)
            await self.database.update_notification_route(
                route_id,
                last_delivery_at=utcnow(),
                last_result=f"Failed {event_type}{result_suffix}",
                last_error=error,
            )
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=attempt_count,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        route_scope = dict(delivery_row.get("route_scope") or {})
        delivery_message_id = _session_delivery_message_id(result)
        if native_provider_delivery:
            route_scope["transport_runtime"] = "native-provider-backed"
            if isinstance(result, dict):
                provider_result = _serialize_gateway_provider_result(result)
                if provider_result:
                    route_scope["provider_result"] = provider_result
        await self.database.update_notification_route(
            route_id,
            last_delivery_at=utcnow(),
            last_result=f"Delivered {event_type}{result_suffix}",
            last_error=None,
        )
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=existing_attempts + 1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
            delivery_message_id=delivery_message_id,
            route_scope=route_scope,
        )
        return True, None

    async def _deliver_saved_session_like_outbound_delivery_row(
        self,
        delivery_row: dict[str, Any],
    ) -> tuple[bool, str | None]:
        delivery_id = int(delivery_row["id"])
        route_kind = str(delivery_row.get("route_kind") or "").strip().lower() or "session"
        event_type = str(delivery_row.get("event_type") or "").strip().lower()
        session_key = str(delivery_row.get("session_key") or "").strip()
        event_payload = delivery_row.get("event_payload")
        payload = event_payload if isinstance(event_payload, dict) else {}
        route_scope = dict(delivery_row.get("route_scope") or {})
        conversation_target = _normalize_conversation_target(
            delivery_row.get("conversation_target")
        ) or _normalize_conversation_target(payload.get("conversationTarget"))
        replay_message = _saved_outbound_delivery_replay_message(delivery_row)
        runtime = self._resolve_outbound_runtime_service()
        attempt_started_at = utcnow()
        existing_attempts = max(0, int(delivery_row.get("attempt_count") or 0))
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        if runtime is None or not runtime.is_available():
            error = f"Saved {route_kind} delivery is unavailable for replay."
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        if not session_key:
            error = f"Saved {route_kind} delivery is missing its session key."
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        if not replay_message:
            error = f"Saved {route_kind} delivery is missing its replay message."
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        try:
            if event_type == "gateway/poll":
                raw_options = payload.get("options")
                poll_options = (
                    tuple(str(option).strip() for option in raw_options if str(option).strip())
                    if isinstance(raw_options, list)
                    else ()
                )
                runtime_result = await runtime.deliver_poll(
                    session_key=session_key,
                    message=replay_message,
                    channel=str(
                        payload.get("channel")
                        or (conversation_target or {}).get("channel")
                        or ""
                    ).strip()
                    or None,
                    target=str(
                        payload.get("to")
                        or (conversation_target or {}).get("peer_id")
                        or ""
                    ).strip()
                    or None,
                    question=str(payload.get("question") or payload.get("summary") or ""),
                    options=poll_options,
                    max_selections=_optional_int_payload_value(payload, "maxSelections"),
                    duration_seconds=_optional_int_payload_value(
                        payload,
                        "durationSeconds",
                    ),
                    duration_hours=_optional_int_payload_value(payload, "durationHours"),
                    silent=_optional_bool_payload_value(payload, "silent"),
                    is_anonymous=_optional_bool_payload_value(payload, "isAnonymous"),
                    account_id=str(
                        payload.get("accountId")
                        or (conversation_target or {}).get("account_id")
                        or route_scope.get("resolved_account_id")
                        or ""
                    ).strip()
                    or None,
                    thread_id=str(
                        payload.get("threadId") or route_scope.get("thread_id") or ""
                    ).strip()
                    or None,
                )
            elif event_type == "gateway/send":
                raw_media_url = payload.get("mediaUrl")
                raw_media_urls = payload.get("mediaUrls")
                media_url = raw_media_url if isinstance(raw_media_url, str) else None
                media_urls = (
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                )
                runtime_result = await runtime.deliver_message(
                    session_key=session_key,
                    message=replay_message,
                    channel=str(
                        payload.get("channel")
                        or (conversation_target or {}).get("channel")
                        or ""
                    ).strip()
                    or None,
                    target=str(
                        payload.get("to")
                        or (conversation_target or {}).get("peer_id")
                        or ""
                    ).strip()
                    or None,
                    media_urls=tuple(
                        _normalize_direct_channel_media_urls(
                            media_url=media_url,
                            media_urls=media_urls,
                        )
                    ),
                    gif_playback=_optional_bool_payload_value(payload, "gifPlayback"),
                    reply_to_id=str(payload.get("replyToId") or "").strip() or None,
                    silent=_optional_bool_payload_value(payload, "silent"),
                    force_document=_optional_bool_payload_value(payload, "forceDocument"),
                    account_id=str(
                        payload.get("accountId")
                        or (conversation_target or {}).get("account_id")
                        or route_scope.get("resolved_account_id")
                        or ""
                    ).strip()
                    or None,
                    thread_id=str(
                        payload.get("threadId") or route_scope.get("thread_id") or ""
                    ).strip()
                    or None,
                    agent_id=str(payload.get("agentId") or "").strip() or None,
                )
            else:
                runtime_result = await runtime.deliver_message(
                    session_key=session_key,
                    message=replay_message,
                )
        except (GatewayOutboundRuntimeUnavailableError, Exception) as exc:
            error = str(exc)[:240]
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=existing_attempts + 1,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        delivered_route_scope = dict(route_scope)
        delivered_route_scope["transport_runtime"] = runtime_result.transport.runtime
        provider_result = _serialize_gateway_provider_result(runtime_result.native_result)
        if provider_result:
            delivered_route_scope["provider_result"] = provider_result
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=existing_attempts + 1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
            delivery_message_id=runtime_result.message_id,
            route_scope=delivered_route_scope,
        )
        return True, None

    async def _deliver_saved_ad_hoc_webhook_delivery_row(
        self,
        delivery_row: dict[str, Any],
    ) -> tuple[bool, str | None]:
        delivery_id = int(delivery_row["id"])
        route_target = str(delivery_row.get("route_target") or "").strip()
        route_scope = dict(delivery_row.get("route_scope") or {})
        event_payload = dict(delivery_row.get("event_payload") or {})
        attempt_started_at = utcnow()
        existing_attempts = max(0, int(delivery_row.get("attempt_count") or 0))
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        if not route_target:
            error = "Saved webhook delivery is missing its target."
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        secret_header_name = str(route_scope.get("secret_header_name") or "").strip() or None
        secret_token: str | None = None
        raw_secret_id = route_scope.get("vault_secret_id")
        if raw_secret_id is not None:
            try:
                secret_id = int(raw_secret_id)
            except (TypeError, ValueError):
                error = "Saved webhook delivery has an invalid replay secret reference."
                await self.database.update_outbound_delivery(
                    delivery_id,
                    delivery_state="failed",
                    attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                    last_attempt_at=attempt_started_at,
                    delivered_at=None,
                    last_error=error,
                )
                return False, error
            try:
                secret_token = await self.vault.get_secret_value(secret_id)
            except KeyError:
                error = f"Saved webhook delivery replay secret {secret_id} is missing."
                await self.database.update_outbound_delivery(
                    delivery_id,
                    delivery_state="failed",
                    attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                    last_attempt_at=attempt_started_at,
                    delivered_at=None,
                    last_error=error,
                )
                return False, error
            except VaultDecryptionError:
                error = f"Saved webhook delivery replay secret {secret_id} cannot be decrypted."
                await self.database.update_outbound_delivery(
                    delivery_id,
                    delivery_state="failed",
                    attempt_count=max(existing_attempts + 1, OUTBOUND_DELIVERY_MAX_RETRIES),
                    last_attempt_at=attempt_started_at,
                    delivered_at=None,
                    last_error=error,
                )
                return False, error
        try:
            await asyncio.to_thread(
                self._post_json_webhook,
                route_target,
                event_payload,
                secret_header_name=secret_header_name,
                secret_token=secret_token,
            )
        except Exception as exc:
            error = str(exc)[:240]
            attempt_count = existing_attempts + 1
            if _is_permanent_outbound_delivery_error(error):
                attempt_count = max(attempt_count, OUTBOUND_DELIVERY_MAX_RETRIES)
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=attempt_count,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return False, error
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=existing_attempts + 1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
        )
        return True, None

    async def replay_outbound_deliveries(
        self,
        *,
        limit: int = 25,
    ) -> OutboundDeliveryReplayBatchView:
        rows = await self.database.list_outbound_deliveries(
            limit=limit,
            states=["pending", "failed"],
            newest_first=False,
        )
        attempted = 0
        replayed = 0
        failed = 0
        deferred = 0
        skipped_max_retries = 0
        results: list[OutboundDeliveryReplayResultView] = []
        for row in rows:
            delivery_view = _serialize_outbound_delivery(row)
            if delivery_view.max_retries_reached:
                skipped_max_retries += 1
                continue
            if not delivery_view.replay_ready:
                deferred += 1
                continue
            attempted += 1
            route_id = row.get("route_id")
            route_kind = str(row.get("route_kind") or "").strip().lower()
            if route_id is None and (
                route_kind in {"announce", "session"}
                or (
                    route_kind == "webhook"
                    and _saved_delivery_is_ad_hoc_webhook(row)
                )
            ):
                if route_kind == "webhook":
                    ok, delivery_error = await self._deliver_saved_ad_hoc_webhook_delivery_row(
                        row
                    )
                else:
                    ok, delivery_error = (
                        await self._deliver_saved_session_like_outbound_delivery_row(row)
                    )
                refreshed_row = await self.database.get_outbound_delivery(int(row["id"]))
                route_view = _saved_outbound_delivery_route_view(
                    refreshed_row or row,
                    delivery_enabled=(
                        True
                        if route_kind == "webhook"
                        else self._outbound_runtime_available()
                    ),
                    last_error=delivery_error,
                )
                if refreshed_row is None:
                    refreshed_view = None
                else:
                    refreshed_view = _serialize_outbound_delivery(refreshed_row)
                if ok:
                    replayed += 1
                else:
                    failed += 1
                results.append(
                    OutboundDeliveryReplayResultView(
                        ok=ok,
                        delivery_id=int(row["id"]),
                        route_id=0,
                        route_name=str(row.get("route_name") or route_view.name),
                        target=str(row.get("route_target") or route_view.target),
                        event_type=str(row.get("event_type") or ""),
                        summary=(
                            delivery_error
                            or str(row.get("message_summary") or "").strip()
                            or f"Replayed {route_kind} delivery"
                        ),
                        delivery=refreshed_view,
                        error=delivery_error,
                        route=route_view,
                    )
                )
                continue
            route_row = (
                await self._get_notification_route_row(int(route_id))
                if route_id is not None
                else None
            )
            if route_row is None or not bool(route_row.get("enabled")):
                route_error = (
                    f"Notification route {route_id} is unavailable for replay."
                    if route_id is not None
                    else "Saved delivery is missing its notification route."
                )
                await self.database.update_outbound_delivery(
                    int(row["id"]),
                    delivery_state="failed",
                    attempt_count=max(
                        max(0, int(row.get("attempt_count") or 0)),
                        OUTBOUND_DELIVERY_MAX_RETRIES,
                    ),
                    last_error=route_error,
                )
                refreshed_row = await self.database.get_outbound_delivery(int(row["id"]))
                route_view = (
                    await self._serialize_notification_route_row(route_row)
                    if route_row is not None
                    else NotificationRouteView.model_validate(
                        {
                            "id": int(route_id or 0),
                            "name": str(row.get("route_name") or f"Route {route_id or 0}"),
                            "kind": str(row.get("route_kind") or "webhook"),
                            "target": str(row.get("route_target") or ""),
                            "events": [],
                            "conversation_target": row.get("conversation_target"),
                            "enabled": False,
                            "secret_header_name": None,
                            "vault_secret_id": None,
                            "vault_secret_label": None,
                            "has_secret": False,
                            "secret_preview": None,
                            "last_delivery_at": None,
                            "last_result": None,
                            "last_error": route_error,
                            "created_at": utcnow(),
                            "updated_at": utcnow(),
                        }
                    )
                )
                failed += 1
                results.append(
                    OutboundDeliveryReplayResultView(
                        ok=False,
                        delivery_id=int(row["id"]),
                        route_id=int(route_id or 0),
                        route_name=str(row.get("route_name") or route_view.name),
                        target=str(row.get("route_target") or route_view.target),
                        event_type=str(row.get("event_type") or ""),
                        summary=route_error,
                        error=route_error,
                        route=route_view,
                        delivery=(
                            _serialize_outbound_delivery(refreshed_row)
                            if refreshed_row is not None
                            else None
                        ),
                    )
                )
                continue
            ok, delivery_error = await self._deliver_saved_outbound_delivery_row(
                row,
                route_row,
                result_suffix=" (replay)",
            )
            refreshed_row = await self.database.get_outbound_delivery(int(row["id"]))
            route_view = await self._serialize_notification_route_row(route_row)
            if ok:
                replayed += 1
                summary = f"Replayed {row.get('event_type') or 'event'} for `{route_view.name}`."
            else:
                failed += 1
                summary = (
                    f"Replay failed for {row.get('event_type') or 'event'} on `{route_view.name}`."
                )
            results.append(
                OutboundDeliveryReplayResultView(
                    ok=ok,
                    delivery_id=int(row["id"]),
                    route_id=route_view.id,
                    route_name=route_view.name,
                    target=route_view.target,
                    event_type=str(row.get("event_type") or ""),
                    summary=summary,
                    error=delivery_error,
                    route=route_view,
                    delivery=(
                        _serialize_outbound_delivery(refreshed_row)
                        if refreshed_row is not None
                        else None
                    ),
                )
            )
        summary = (
            f"Replayed {replayed} delivery(s); {failed} failed, {deferred} deferred by backoff, "
            f"and {skipped_max_retries} hit max retries."
        )
        return OutboundDeliveryReplayBatchView(
            ok=failed == 0,
            summary=summary,
            attempted_count=attempted,
            replayed_count=replayed,
            failed_count=failed,
            deferred_count=deferred,
            skipped_max_retries_count=skipped_max_retries,
            deliveries=results,
        )

    async def list_integration_views(self) -> list[IntegrationView]:
        await self._migrate_legacy_secret_refs()
        secrets_by_id = {secret.id: secret for secret in await self.vault.list_secret_views()}
        secret_probe: dict[int, str | None] = {}
        integrations: list[IntegrationView] = []
        for row in await self.database.list_integrations():
            auth_scheme = str(row.get("auth_scheme") or "token")
            secret_id = row.get("vault_secret_id")
            secret = secrets_by_id.get(int(secret_id)) if secret_id is not None else None
            secret_error: str | None = None
            if secret_id is not None:
                cache_key = int(secret_id)
                if cache_key not in secret_probe:
                    secret_probe[cache_key] = await self.vault.probe_secret(cache_key)
                secret_error = secret_probe[cache_key]

            auth_status = "satisfied"
            auth_detail = "No credentials required."
            if _requires_secret(auth_scheme):
                if secret is None and secret_id is not None:
                    auth_status = "degraded"
                    auth_detail = "Referenced vault secret is missing."
                elif secret_error:
                    auth_status = "degraded"
                    auth_detail = secret_error
                elif secret is None:
                    auth_status = "missing"
                    auth_detail = "Attach a vault secret before using this integration."
                else:
                    auth_status = "satisfied"
                    auth_detail = f"Vault secret '{secret.label}' is attached."

            integrations.append(
                _serialize_integration(
                    row,
                    vault_secret_label=secret.label if secret is not None else None,
                    secret_preview=secret.secret_preview if secret is not None else None,
                    has_secret=secret is not None,
                    auth_status=auth_status,
                    auth_detail=auth_detail,
                )
            )
        return integrations

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
        project = (
            await self.database.get_project(payload.project_id)
            if payload.project_id is not None
            else None
        )
        resolved_toolsets = infer_hermes_toolsets(
            payload.objective_template,
            explicit_toolsets=payload.toolsets,
            project_label=str(project["label"]) if project is not None else None,
            project_path=(str(project["path"]) if project is not None else payload.cwd),
            setup_mode="local",
            use_builtin_agents=payload.use_builtin_agents,
            run_verification=payload.run_verification,
            cadence_minutes=payload.cadence_minutes,
        )
        payload = payload.model_copy(update={"toolsets": resolved_toolsets})
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
        return await self._hydrate_task_blueprint_view(
            _serialize_task(row),
            project_label=str(project["label"]) if project is not None else None,
            project_path=str(project["path"]) if project is not None else None,
        )

    async def _hydrate_task_blueprint_view(
        self,
        task: TaskBlueprintView,
        *,
        project_label: str | None = None,
        project_path: str | None = None,
    ) -> TaskBlueprintView:
        hydrated = _attach_task_tool_policy(
            task,
            project_label=project_label,
            project_path=project_path,
        )
        mission_draft: MissionDraftView | None = None
        try:
            mission_draft = await self._build_draft_for_task(hydrated)
        except ValueError:
            # Keep task listings readable even when no lane can currently launch the task.
            mission_draft = None
        return hydrated.model_copy(update={"mission_draft": mission_draft})

    async def delete_task_blueprint(self, task_id: int) -> None:
        await self.database.delete_task_blueprint(task_id)

    async def create_notification_route(
        self,
        payload: NotificationRouteCreate,
    ) -> NotificationRouteView:
        await self._migrate_legacy_secret_refs()
        if payload.vault_secret_id is not None and payload.secret_token:
            raise ValueError("Provide either vault_secret_id or secret_token, not both.")
        vault_secret_id = payload.vault_secret_id
        if payload.secret_token:
            created_secret = await self.vault.create_secret_value(
                label=f"{payload.name} webhook secret",
                value=payload.secret_token,
                kind="webhook-token",
                notes=payload.target,
            )
            vault_secret_id = created_secret.id
        elif payload.vault_secret_id is not None:
            existing_secret = await self.vault.get_secret_view(payload.vault_secret_id)
            if existing_secret is None:
                raise ValueError(f"Unknown vault secret {payload.vault_secret_id}")
        route_id = await self.database.create_notification_route(
            name=payload.name,
            kind=payload.kind,
            target=payload.target,
            events=payload.events,
            conversation_target=(
                payload.conversation_target.model_dump(mode="json")
                if payload.conversation_target is not None
                else None
            ),
            enabled=payload.enabled,
            secret_header_name=payload.secret_header_name,
            secret_token=None,
            vault_secret_id=vault_secret_id,
        )
        route = next(
            route for route in await self.list_notification_route_views() if route.id == route_id
        )
        return route

    async def delete_notification_route(self, route_id: int) -> None:
        await self.database.delete_notification_route(route_id)

    async def _resolve_event_session_key(self, event: dict[str, Any]) -> str | None:
        explicit = str(event.get("sessionKey") or "").strip()
        if explicit:
            return explicit
        mission_id = event.get("missionId")
        if isinstance(mission_id, int):
            mission = await self.database.get_mission(mission_id)
            value = str(mission.get("session_key") or "").strip() if mission is not None else ""
            if value:
                return value
        return None

    async def test_notification_route(
        self,
        route_id: int,
        *,
        event_type: str | None = None,
    ) -> NotificationRouteTestResultView:
        await self._migrate_legacy_secret_refs()
        route = next(
            (
                row
                for row in await self.database.list_notification_routes()
                if int(row["id"]) == route_id
            ),
            None,
        )
        if route is None:
            raise ValueError(f"Unknown notification route {route_id}")

        selected_event_type = _sample_event_type_for_route(
            route.get("events"),
            explicit_event_type=event_type,
        )
        delivered_at = utcnow()
        route_conversation_target = _normalize_conversation_target(route.get("conversation_target"))
        route_scope: dict[str, Any] = {
            "route_id": route_id,
            "route_name": str(route.get("name") or f"Route {route_id}"),
            "route_kind": str(route.get("kind") or "webhook"),
            "route_target": str(route.get("target") or ""),
            "route_match": "test",
        }
        payload = {
            "type": selected_event_type,
            "createdAt": delivered_at,
            "test": True,
            "routeId": route_id,
            "routeName": str(route.get("name") or f"Route {route_id}"),
            "summary": "OpenZues test delivery ping.",
            "target": str(route.get("target") or ""),
        }
        if route_conversation_target is not None:
            payload["conversationTarget"] = route_conversation_target
            payload["routeConversationTarget"] = route_conversation_target
        delivery_id = await self.database.create_outbound_delivery(
            route_id=route_id,
            route_name=route_scope["route_name"],
            route_kind=route_scope["route_kind"],
            route_target=route_scope["route_target"],
            event_type=selected_event_type,
            session_key=None,
            conversation_target=route_conversation_target,
            route_scope=route_scope,
            event_payload=payload,
            message_summary=_summarize_outbound_event(selected_event_type, payload),
            test_delivery=True,
            delivery_state="pending",
            attempt_count=0,
        )

        delivery_row = await self.database.get_outbound_delivery(delivery_id)
        assert delivery_row is not None
        ok, error = await self._deliver_saved_outbound_delivery_row(
            delivery_row,
            route,
            result_suffix=" (test)",
        )
        if ok:
            summary = (
                f"Delivered a test ping for `{selected_event_type}` to "
                f"`{route.get('name') or f'Route {route_id}'}`."
            )
        else:
            summary = (
                f"Test delivery for `{selected_event_type}` failed on "
                f"`{route.get('name') or f'Route {route_id}'}`."
            )

        refreshed_route = next(
            route_view
            for route_view in await self.list_notification_route_views()
            if route_view.id == route_id
        )
        delivery_row = await self.database.get_outbound_delivery(delivery_id)
        return NotificationRouteTestResultView(
            ok=ok,
            route_id=route_id,
            route_name=refreshed_route.name,
            target=refreshed_route.target,
            event_type=selected_event_type,
            summary=summary,
            error=error,
            route=refreshed_route,
            delivery=(
                _serialize_outbound_delivery(delivery_row)
                if delivery_row is not None
                else None
            ),
        )

    async def create_integration(self, payload: IntegrationCreate) -> IntegrationView:
        await self._migrate_legacy_secret_refs()
        if payload.vault_secret_id is not None and payload.secret_value:
            raise ValueError("Provide either vault_secret_id or secret_value, not both.")

        vault_secret_id = payload.vault_secret_id
        secret_label = payload.secret_label
        if payload.secret_value:
            created_secret = await self.vault.create_secret_value(
                label=payload.secret_label or f"{payload.name} credential",
                value=payload.secret_value,
                kind=payload.auth_scheme,
                notes=payload.notes,
            )
            vault_secret_id = created_secret.id
            secret_label = created_secret.label
        elif payload.vault_secret_id is not None:
            existing_secret = await self.vault.get_secret_view(payload.vault_secret_id)
            if existing_secret is None:
                raise ValueError(f"Unknown vault secret {payload.vault_secret_id}")
            secret_label = existing_secret.label

        integration_id = await self.database.create_integration(
            name=payload.name,
            kind=payload.kind,
            project_id=payload.project_id,
            base_url=payload.base_url,
            auth_scheme=payload.auth_scheme,
            vault_secret_id=vault_secret_id,
            secret_label=secret_label,
            secret_value=None,
            notes=payload.notes,
            enabled=payload.enabled,
        )
        integration = next(
            item for item in await self.list_integration_views() if item.id == integration_id
        )
        return integration

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
            skill for skill in await self.database.list_skill_pins() if int(skill["id"]) == skill_id
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
        missions = [
            mission
            for mission in await self.missions.list_views()
            if mission.instance_id == instance_id
        ]
        mission = _pick_lane_snapshot_mission(missions)
        continuity = (
            build_continuity_packet(
                mission,
                instance_connected=view.connected,
                checkpoints=mission.checkpoints,
                project_label=mission.project_label,
            )
            if mission is not None
            else None
        )
        snapshot_id = await self.database.append_lane_snapshot(
            instance_id=instance_id,
            snapshot_kind=snapshot_kind,
            summary={
                "connected": view.connected,
                "transport": view.transport,
                "model_count": len(view.models),
                "skill_count": len(view.skills),
                "thread_count": len(view.threads),
                "approvals_pending_count": len(view.unresolved_requests),
                "mission_id": mission.id if mission is not None else None,
                "mission_name": mission.name if mission is not None else None,
                "project_label": mission.project_label if mission is not None else None,
                "thread_id": mission.thread_id if mission is not None else None,
                "mission_status": mission.status if mission is not None else None,
                "phase": mission.phase if mission is not None else None,
                "current_command": mission.current_command if mission is not None else None,
                "command_burn": mission.command_count if mission is not None else 0,
                "token_burn": mission.total_tokens if mission is not None else 0,
                "last_checkpoint_summary": (
                    _summarize_text(mission.last_checkpoint, limit=240)
                    if mission is not None
                    else None
                ),
                "continuity_state": continuity.state if continuity is not None else None,
                "continuity_score": continuity.score if continuity is not None else None,
                "safest_handoff": continuity.next_handoff if continuity is not None else None,
                "note": note,
            },
        )
        row = next(
            snapshot
            for snapshot in await self.database.list_lane_snapshots()
            if int(snapshot["id"]) == snapshot_id
        )
        return _build_lane_snapshot_view(row, {view.id: view.name})

    async def _migrate_legacy_secret_refs(self) -> None:
        for integration in await self.database.list_integrations():
            legacy_secret = str(integration.get("secret_value") or "")
            vault_secret_id = integration.get("vault_secret_id")
            if vault_secret_id is not None and legacy_secret:
                await self.database.update_integration(
                    int(integration["id"]),
                    secret_value=None,
                )
                continue
            if vault_secret_id is not None or not legacy_secret:
                continue
            secret = await self.vault.create_secret_value(
                label=str(integration.get("secret_label") or f"{integration['name']} credential"),
                value=legacy_secret,
                kind=str(integration.get("auth_scheme") or "token"),
                notes=str(integration.get("notes") or "") or None,
            )
            await self.database.update_integration(
                int(integration["id"]),
                vault_secret_id=secret.id,
                secret_label=secret.label,
                secret_value=None,
            )

        for route in await self.database.list_notification_routes():
            legacy_secret = str(route.get("secret_token") or "")
            vault_secret_id = route.get("vault_secret_id")
            if vault_secret_id is not None and legacy_secret:
                await self.database.update_notification_route(
                    int(route["id"]),
                    secret_token=None,
                )
                continue
            if vault_secret_id is not None or not legacy_secret:
                continue
            secret = await self.vault.create_secret_value(
                label=f"{route['name']} webhook secret",
                value=legacy_secret,
                kind="webhook-token",
                notes=str(route.get("target") or "") or None,
            )
            await self.database.update_notification_route(
                int(route["id"]),
                vault_secret_id=secret.id,
                secret_token=None,
            )

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

    async def dispatch_cron_system_event_task(
        self,
        task_id: int,
        *,
        trigger: str = "manual",
    ) -> str:
        task_row = await self.database.get_task_blueprint(task_id)
        if task_row is None:
            raise ValueError(f"Unknown task blueprint {task_id}")
        task = _serialize_task(task_row)
        if not _task_routes_through_gateway_wake(task):
            raise ValueError(f"Task blueprint {task_id} does not route through gateway wake")
        if self.wake_service is None:
            raise RuntimeError("gateway wake service unavailable")

        message = _task_cron_payload_text(task)
        session_key = _task_cron_session_key(task)
        await self.wake_service.wake(
            mode=cast(Literal["now", "next-heartbeat"], _task_cron_wake_mode(task)),
            text=message,
            reason=f"cron:{task.id}",
            session_key=session_key,
        )
        launched_at = utcnow()
        update_fields: dict[str, Any] = {
            "last_launched_at": launched_at,
            "last_status": "completed",
            "last_result_summary": message[:240],
        }
        if task.enabled and task.schedule_kind == "at":
            update_fields["enabled"] = 0
        await self.database.update_task_blueprint(task_id, **update_fields)
        await self._record_cron_system_event_result_state(task, launched_at=launched_at)
        await self._publish_ops_event(
            "task/launched",
            {
                "taskId": task_id,
                "taskName": task.name,
                "runId": f"wake:{task_id}",
                "trigger": trigger,
            },
        )
        return f"wake:{task_id}"

    async def handle_mission_event(self, event_type: str, event: dict[str, Any]) -> None:
        mission_id = event.get("missionId")
        if isinstance(mission_id, int):
            mission = await self.database.get_mission(mission_id)
            if mission is not None and mission.get("task_blueprint_id") is not None:
                task_id = int(mission["task_blueprint_id"])
                task_row = await self.database.get_task_blueprint(task_id)
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
                if task_row is not None:
                    task = _serialize_task(task_row)
                    delete_consumed_one_shot = False
                    if status == "completed" and _task_has_terminal_completion(task, summary):
                        if task.schedule_kind == "at" and _task_cron_delete_after_run(task):
                            delete_consumed_one_shot = True
                        else:
                            await self.database.update_task_blueprint(
                                task_id,
                                enabled=0,
                                last_status="completed",
                                last_result_summary=summary[:240],
                            )
                        await self._publish_ops_event(
                            "task/completed-terminal",
                            {
                                "taskId": task_id,
                                "taskName": task.name,
                                "missionId": mission_id,
                                "marker": _task_completion_marker(task),
                            },
                        )
                    elif (
                        status == "completed"
                        and task.schedule_kind == "at"
                        and task.enabled
                    ):
                        scheduled_at = _parse_timestamp(task.schedule_at)
                        last_run_at = _parse_timestamp(task.last_launched_at)
                        if (
                            scheduled_at is not None
                            and last_run_at is not None
                            and scheduled_at <= last_run_at
                        ):
                            if _task_cron_delete_after_run(task):
                                delete_consumed_one_shot = True
                            else:
                                await self.database.update_task_blueprint(
                                    task_id,
                                    enabled=0,
                                    last_status="completed",
                                    last_result_summary=summary[:240],
                                )
                    await self._record_cron_mission_result_state(
                        event_type,
                        mission,
                        task,
                    )
                    await self._deliver_cron_finished_delivery(
                        event_type,
                        mission,
                        task,
                    )
                    if delete_consumed_one_shot:
                        await self.database.delete_task_blueprint(task_id)
                await self._maybe_append_parity_checkpoint_ledger(mission, task=task_row)
            elif mission is not None:
                await self._maybe_append_parity_checkpoint_ledger(mission, task=None)
        await self._deliver_notifications(event_type, event)
        await self._publish_derived_task_inbox_notifications()

    async def _send_ad_hoc_webhook_delivery(
        self,
        *,
        route_name: str,
        route_target: str,
        event_type: str,
        payload: dict[str, Any],
        session_key: str | None,
        conversation_target: dict[str, Any] | None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        route_scope: dict[str, Any] = {
            "route_name": route_name,
            "route_kind": "webhook",
            "route_target": route_target,
        }
        if secret_header_name and secret_token:
            replay_secret = await self.vault.create_secret_value(
                label=f"{route_name} replay webhook secret",
                value=secret_token,
                kind="webhook-token",
                notes=route_target,
            )
            route_scope["secret_header_name"] = secret_header_name
            route_scope["vault_secret_id"] = replay_secret.id
        delivery_id = await self.database.create_outbound_delivery(
            route_id=None,
            route_name=route_name,
            route_kind="webhook",
            route_target=route_target,
            event_type=event_type,
            session_key=session_key,
            conversation_target=conversation_target,
            route_scope=route_scope,
            event_payload=payload,
            message_summary=_summarize_outbound_event(event_type, payload),
            test_delivery=False,
            delivery_state="pending",
            attempt_count=0,
        )
        attempt_started_at = utcnow()
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        try:
            await asyncio.to_thread(
                self._post_json_webhook,
                route_target,
                payload,
                secret_header_name=secret_header_name,
                secret_token=secret_token,
            )
        except Exception as exc:
            error = str(exc)[:240]
            attempt_count = 1
            if _is_permanent_outbound_delivery_error(error):
                attempt_count = max(attempt_count, OUTBOUND_DELIVERY_MAX_RETRIES)
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=attempt_count,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
        )

    async def _send_ad_hoc_session_delivery(
        self,
        *,
        route_name: str,
        session_key: str,
        event_type: str,
        payload: dict[str, Any],
        conversation_target: dict[str, Any] | None,
        message: str,
    ) -> None:
        route_scope = {
            "route_name": route_name,
            "route_kind": "session",
            "route_target": session_key,
            "route_match": "sessionKey",
        }
        delivery_id = await self.database.create_outbound_delivery(
            route_id=None,
            route_name=route_name,
            route_kind="session",
            route_target=session_key,
            event_type=event_type,
            session_key=session_key,
            conversation_target=conversation_target,
            route_scope=route_scope,
            event_payload=payload,
            message_summary=_summarize_outbound_event(event_type, payload),
            test_delivery=False,
            delivery_state="pending",
            attempt_count=0,
        )
        attempt_started_at = utcnow()
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        try:
            runtime = self._resolve_outbound_runtime_service()
            if runtime is None:
                raise GatewayOutboundRuntimeUnavailableError(
                    "gateway outbound runtime is unavailable"
                )
            runtime_result = await runtime.deliver_message(
                session_key=session_key,
                message=message,
            )
        except (GatewayOutboundRuntimeUnavailableError, Exception) as exc:
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=1,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=str(exc)[:240],
            )
            return
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
            delivery_message_id=runtime_result.message_id,
        )

    async def _send_ad_hoc_announce_delivery(
        self,
        *,
        route_name: str,
        conversation_target: ConversationTargetView,
        thread_id: str | int | None = None,
        event_type: str,
        payload: dict[str, Any],
        message: str,
        request_idempotency_key: str | None = None,
    ) -> None:
        await self._deliver_direct_channel_message(
            route_name=route_name,
            conversation_target=conversation_target,
            thread_id=thread_id,
            event_type=event_type,
            payload=payload,
            message=message,
            request_idempotency_key=request_idempotency_key,
        )

    async def _send_cron_failure_alert(
        self,
        *,
        task: TaskBlueprintView,
        mission: dict[str, Any],
        alert_config: dict[str, Any],
        message: str,
        session_key: str | None,
    ) -> None:
        payload = {
            "missionId": int(mission["id"]),
            "taskId": int(task.id),
            "jobId": _cron_job_id(int(task.id)),
            "jobName": task.name,
            "message": message,
            "status": "error",
            "error": str(mission.get("last_error") or "").strip() or None,
        }
        mode = str(alert_config.get("mode") or "").strip().lower()
        to = str(alert_config.get("to") or "").strip() or None
        channel = str(alert_config.get("channel") or "").strip().lower() or "last"
        account_id = str(alert_config.get("accountId") or "").strip() or None

        if mode == "webhook":
            webhook_target = _normalized_http_webhook_url(to)
            if webhook_target is not None:
                await self._send_ad_hoc_webhook_delivery(
                    route_name=f"Cron failure alert for {task.name}",
                    route_target=webhook_target,
                    event_type="cron/failure-alert",
                    payload=payload,
                    session_key=session_key,
                    conversation_target=None,
                )
                return

        conversation_target = _build_explicit_announce_conversation_target(
            channel=channel,
            to=to,
            account_id=account_id,
        )
        if conversation_target is not None and self._session_outbound_runtime_available():
            await self._send_ad_hoc_announce_delivery(
                route_name=f"Cron failure alert for {task.name}",
                conversation_target=conversation_target,
                event_type="cron/failure-alert",
                payload=payload,
                message=message,
                request_idempotency_key=_cron_direct_delivery_idempotency_key(
                    task=task,
                    mission=mission,
                    event_type="cron/failure-alert",
                    conversation_target=conversation_target,
                ),
            )
            return
        if session_key is not None and self._session_outbound_runtime_available():
            session_payload = dict(payload)
            session_payload["sessionKey"] = session_key
            await self._send_ad_hoc_session_delivery(
                route_name=f"Cron failure alert for {task.name}",
                session_key=session_key,
                event_type="cron/failure-alert",
                payload=session_payload,
                conversation_target=None,
                message=message,
            )
            return
        notify_event = dict(payload)
        if session_key is not None:
            notify_event["sessionKey"] = session_key
        await self._deliver_notifications("cron/failure-alert", notify_event)

    async def _resolve_default_channel_account_id(
        self,
        channel: str,
    ) -> str | None:
        normalized_channel = str(channel or "").strip().lower()
        if not normalized_channel:
            return None
        account_ids: set[str] = set()
        for row in await self.database.list_notification_routes():
            target = _normalize_conversation_target(row.get("conversation_target"))
            if target is None:
                continue
            if str(target.get("channel") or "").strip().lower() != normalized_channel:
                continue
            account_id = normalize_optional_account_id(
                str(target.get("account_id") or "").strip()
            )
            account_ids.add(account_id or DEFAULT_ACCOUNT_ID)
        if not account_ids:
            return None
        if DEFAULT_ACCOUNT_ID in account_ids:
            return DEFAULT_ACCOUNT_ID
        return sorted(account_ids)[0]

    async def _provider_route_for_channel_account(
        self,
        *,
        channel: str,
        account_id: str,
    ) -> dict[str, Any] | None:
        normalized_channel = str(channel or "").strip().lower()
        normalized_account_id = (
            normalize_optional_account_id(str(account_id or "").strip())
            or DEFAULT_ACCOUNT_ID
        )
        if not normalized_channel:
            return None
        for route in await self.database.list_notification_routes():
            if not bool(route.get("enabled")):
                continue
            route_kind = str(route.get("kind") or "").strip().lower()
            if route_kind != normalized_channel or route_kind not in NATIVE_PROVIDER_ROUTE_KINDS:
                continue
            route_target = _normalize_conversation_target(route.get("conversation_target"))
            if route_target is None:
                if normalized_account_id == DEFAULT_ACCOUNT_ID:
                    return route
                continue
            route_channel = str(route_target.get("channel") or "").strip().lower()
            if route_channel != normalized_channel:
                continue
            route_account_id = (
                normalize_optional_account_id(
                    str(route_target.get("account_id") or "").strip()
                )
                or DEFAULT_ACCOUNT_ID
            )
            if route_account_id == normalized_account_id:
                return route
        return None

    async def probe_channel_account(
        self,
        *,
        channel: str,
        account_id: str,
        timeout_ms: int,
    ) -> dict[str, Any]:
        normalized_channel = str(channel or "").strip().lower()
        normalized_account_id = (
            normalize_optional_account_id(str(account_id or "").strip())
            or DEFAULT_ACCOUNT_ID
        )
        route = await self._provider_route_for_channel_account(
            channel=normalized_channel,
            account_id=normalized_account_id,
        )
        if route is None:
            return {
                "ok": False,
                "status": "unavailable",
                "reason": "native_provider_route_unavailable",
                "provider": normalized_channel,
                "accountId": normalized_account_id,
                "summary": "No enabled native provider route is configured for this account.",
                "timeoutMs": timeout_ms,
            }
        route_kind = str(route.get("kind") or "").strip().lower()
        if route_kind not in PROBEABLE_NATIVE_PROVIDER_ROUTE_KINDS:
            return {
                "status": "unsupported",
                "reason": "native_provider_probe_unsupported",
                "provider": route_kind,
                "accountId": normalized_account_id,
                "summary": "This channel does not expose an upstream account probe hook.",
                "timeoutMs": timeout_ms,
            }
        secret_token = await self._notification_route_secret_token(route)
        if not secret_token:
            return {
                "ok": False,
                "status": "unavailable",
                "reason": "native_provider_secret_unavailable",
                "provider": route_kind,
                "accountId": normalized_account_id,
                "summary": "Native provider route is missing a credential secret.",
                "timeoutMs": timeout_ms,
            }
        if route_kind == "telegram":
            try:
                return await asyncio.to_thread(
                    self._probe_telegram_provider_route,
                    route,
                    secret_token,
                    timeout_ms,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "status": "error",
                    "provider": route_kind,
                    "runtime": "native-provider-backed",
                    "accountId": normalized_account_id,
                    "error": str(exc).strip() or type(exc).__name__,
                    "timeoutMs": timeout_ms,
                }
        if route_kind == "discord":
            try:
                return await asyncio.to_thread(
                    self._probe_discord_provider_route,
                    route,
                    secret_token,
                    timeout_ms,
                )
            except Exception as exc:
                return {
                    "ok": False,
                    "status": "error",
                    "provider": route_kind,
                    "runtime": "native-provider-backed",
                    "accountId": normalized_account_id,
                    "error": str(exc).strip() or type(exc).__name__,
                    "timeoutMs": timeout_ms,
                }
        try:
            return await asyncio.to_thread(
                self._probe_slack_provider_route,
                route,
                secret_token,
                timeout_ms,
            )
        except Exception as exc:
            return {
                "ok": False,
                "status": "error",
                "provider": route_kind,
                "runtime": "native-provider-backed",
                "accountId": normalized_account_id,
                "error": str(exc).strip() or type(exc).__name__,
                "timeoutMs": timeout_ms,
            }

    def _probe_slack_provider_route(
        self,
        route: dict[str, Any],
        secret_token: str,
        timeout_ms: int,
    ) -> dict[str, Any]:
        result = self._post_json_webhook(
            _slack_api_endpoint(str(route.get("target") or ""), "auth.test"),
            {},
            secret_header_name="Authorization",
            secret_token=_slack_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            return {
                "ok": False,
                "status": "error",
                "provider": "slack",
                "runtime": "native-provider-backed",
                "error": error,
                "timeoutMs": timeout_ms,
            }
        return {
            "ok": True,
            "status": "ok",
            "provider": "slack",
            "runtime": "native-provider-backed",
            "team": str(result.get("team") or ""),
            "teamId": str(result.get("team_id") or ""),
            "user": str(result.get("user") or ""),
            "userId": str(result.get("user_id") or ""),
            "timeoutMs": timeout_ms,
        }

    def _probe_telegram_provider_route(
        self,
        route: dict[str, Any],
        secret_token: str,
        timeout_ms: int,
    ) -> dict[str, Any]:
        token = _telegram_bot_token(secret_token)
        result = self._post_json_webhook(
            _telegram_api_endpoint(str(route.get("target") or ""), token, "getMe"),
            {},
        )
        if not isinstance(result, dict):
            raise RuntimeError("Telegram API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("description") or result.get("error_code") or "unknown")
            return {
                "ok": False,
                "status": "error",
                "provider": "telegram",
                "runtime": "native-provider-backed",
                "error": error,
                "timeoutMs": timeout_ms,
            }
        bot = result.get("result")
        if not isinstance(bot, dict):
            bot = {}
        return {
            "ok": True,
            "status": "ok",
            "provider": "telegram",
            "runtime": "native-provider-backed",
            "botId": str(bot.get("id") or ""),
            "username": str(bot.get("username") or ""),
            "firstName": str(bot.get("first_name") or ""),
            "timeoutMs": timeout_ms,
        }

    async def resolve_channel_targets(
        self,
        *,
        channel: str | None,
        account_id: str | None,
        kind: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        normalized_inputs = [str(input_value).strip() for input_value in inputs]
        normalized_inputs = [input_value for input_value in normalized_inputs if input_value]
        if not normalized_inputs:
            return []
        normalized_channel = str(channel or "").strip().lower()
        normalized_kind = str(kind or "").strip().lower()
        if normalized_channel == "telegram":
            return await self._resolve_telegram_channel_targets(
                account_id=account_id,
                kind=normalized_kind,
                inputs=normalized_inputs,
            )
        if normalized_channel == "discord":
            return await self._resolve_discord_channel_targets(
                account_id=account_id,
                kind=normalized_kind,
                inputs=normalized_inputs,
            )
        if normalized_channel != "slack" or normalized_kind not in {
            "auto",
            "channel",
            "group",
            "user",
        }:
            return [
                _unresolved_channel_target(input_value, "native provider resolver unavailable")
                for input_value in normalized_inputs
            ]
        normalized_account_id = (
            normalize_optional_account_id(str(account_id or "").strip())
            or DEFAULT_ACCOUNT_ID
        )
        route = await self._provider_route_for_channel_account(
            channel=normalized_channel,
            account_id=normalized_account_id,
        )
        if route is None:
            return [
                _unresolved_channel_target(input_value, "missing Slack route")
                for input_value in normalized_inputs
            ]
        secret_token = await self._notification_route_secret_token(route)
        if not secret_token:
            return [
                _unresolved_channel_target(input_value, "missing Slack token")
                for input_value in normalized_inputs
            ]
        if normalized_kind == "user":
            return await asyncio.to_thread(
                self._resolve_slack_user_targets,
                route,
                secret_token,
                normalized_inputs,
            )
        return await asyncio.to_thread(
            self._resolve_slack_channel_targets,
            route,
            secret_token,
            normalized_inputs,
        )

    def _resolve_slack_channel_targets(
        self,
        route: dict[str, Any],
        secret_token: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        channels: list[dict[str, object]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, object] = {
                "types": "public_channel,private_channel",
                "exclude_archived": False,
                "limit": 1000,
            }
            if cursor:
                payload["cursor"] = cursor
            result = self._post_json_webhook(
                _slack_api_endpoint(str(route.get("target") or ""), "conversations.list"),
                payload,
                secret_header_name="Authorization",
                secret_token=_slack_bearer_token(secret_token),
            )
            if not isinstance(result, dict):
                raise RuntimeError("Slack API returned a non-JSON response.")
            if result.get("ok") is False:
                error = str(result.get("error") or "unknown_error")
                raise RuntimeError(f"Slack API returned {error}.")
            raw_channels = result.get("channels")
            if isinstance(raw_channels, list):
                for channel in raw_channels:
                    if not isinstance(channel, dict):
                        continue
                    channel_id = str(channel.get("id") or "").strip()
                    channel_name = str(channel.get("name") or "").strip()
                    if not channel_id or not channel_name:
                        continue
                    channels.append(
                        {
                            "id": channel_id,
                            "name": channel_name,
                            "archived": bool(channel.get("is_archived")),
                        }
                    )
            metadata = result.get("response_metadata")
            cursor = (
                str(metadata.get("next_cursor") or "").strip()
                if isinstance(metadata, dict)
                else ""
            ) or None
            if cursor is None:
                break
        return [_resolve_slack_channel_target(input_value, channels) for input_value in inputs]

    def _resolve_slack_user_targets(
        self,
        route: dict[str, Any],
        secret_token: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        users: list[dict[str, object]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, object] = {"limit": 200}
            if cursor:
                payload["cursor"] = cursor
            result = self._post_json_webhook(
                _slack_api_endpoint(str(route.get("target") or ""), "users.list"),
                payload,
                secret_header_name="Authorization",
                secret_token=_slack_bearer_token(secret_token),
            )
            if not isinstance(result, dict):
                raise RuntimeError("Slack API returned a non-JSON response.")
            if result.get("ok") is False:
                error = str(result.get("error") or "unknown_error")
                raise RuntimeError(f"Slack API returned {error}.")
            members = result.get("members")
            if isinstance(members, list):
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    user_id = str(member.get("id") or "").strip()
                    user_name = str(member.get("name") or "").strip()
                    if not user_id or not user_name:
                        continue
                    profile = member.get("profile")
                    if not isinstance(profile, dict):
                        profile = {}
                    users.append(
                        {
                            "id": user_id,
                            "name": user_name,
                            "displayName": str(
                                profile.get("display_name") or ""
                            ).strip(),
                            "realName": str(
                                profile.get("real_name")
                                or member.get("real_name")
                                or ""
                            ).strip(),
                            "email": str(profile.get("email") or "").strip().lower(),
                            "deleted": bool(member.get("deleted")),
                            "isBot": bool(member.get("is_bot")),
                            "isAppUser": bool(member.get("is_app_user")),
                        }
                    )
            metadata = result.get("response_metadata")
            cursor = (
                str(metadata.get("next_cursor") or "").strip()
                if isinstance(metadata, dict)
                else ""
            ) or None
            if cursor is None:
                break
        return [_resolve_slack_user_target(input_value, users) for input_value in inputs]

    async def _resolve_telegram_channel_targets(
        self,
        *,
        account_id: str | None,
        kind: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        if kind != "user":
            return [
                _unresolved_channel_target(
                    input_value,
                    "Telegram runtime target resolution only supports usernames for "
                    "direct-message lookups.",
                )
                for input_value in inputs
            ]
        normalized_account_id = (
            normalize_optional_account_id(str(account_id or "").strip())
            or DEFAULT_ACCOUNT_ID
        )
        route = await self._provider_route_for_channel_account(
            channel="telegram",
            account_id=normalized_account_id,
        )
        if route is None:
            return [
                _unresolved_channel_target(input_value, "missing Telegram route")
                for input_value in inputs
            ]
        secret_token = await self._notification_route_secret_token(route)
        if not secret_token:
            return [
                _unresolved_channel_target(
                    input_value,
                    "Telegram bot token is required to resolve @username targets.",
                )
                for input_value in inputs
            ]
        return await asyncio.to_thread(
            self._resolve_telegram_user_targets,
            route,
            secret_token,
            inputs,
        )

    def _resolve_telegram_user_targets(
        self,
        route: dict[str, Any],
        secret_token: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        token = _telegram_bot_token(secret_token)
        results: list[dict[str, object]] = []
        for input_value in inputs:
            trimmed = input_value.strip()
            if not trimmed:
                results.append(
                    _unresolved_channel_target(input_value, "Telegram target is required.")
                )
                continue
            normalized = trimmed if trimmed.startswith("@") else f"@{trimmed}"
            try:
                result = self._get_json_provider_url(
                    f"{_telegram_api_endpoint(str(route.get('target') or ''), token, 'getChat')}"
                    f"?{urlencode({'chat_id': normalized})}",
                )
            except RuntimeError as exc:
                results.append(_unresolved_channel_target(input_value, str(exc)))
                continue
            payload = _telegram_result_payload(result)
            chat_id = payload.get("id")
            if chat_id is None:
                results.append(
                    _unresolved_channel_target(
                        input_value,
                        "Telegram username could not be resolved by the configured bot.",
                    )
                )
                continue
            results.append(
                {
                    "input": input_value,
                    "resolved": True,
                    "id": str(chat_id),
                    "name": normalized,
                }
            )
        return results

    async def _resolve_discord_channel_targets(
        self,
        *,
        account_id: str | None,
        kind: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        if kind not in {"auto", "channel", "group", "user"}:
            return [
                _unresolved_channel_target(
                    input_value,
                    "native provider resolver unavailable",
                )
                for input_value in inputs
            ]
        normalized_account_id = (
            normalize_optional_account_id(str(account_id or "").strip())
            or DEFAULT_ACCOUNT_ID
        )
        route = await self._provider_route_for_channel_account(
            channel="discord",
            account_id=normalized_account_id,
        )
        if route is None:
            return [
                _unresolved_channel_target(input_value, "missing Discord route")
                for input_value in inputs
            ]
        secret_token = await self._notification_route_secret_token(route)
        if not secret_token:
            return [
                _unresolved_channel_target(input_value, "missing Discord token")
                for input_value in inputs
            ]
        if kind == "user":
            return await asyncio.to_thread(
                self._resolve_discord_user_targets,
                secret_token,
                inputs,
            )
        return await asyncio.to_thread(
            self._resolve_discord_group_targets,
            secret_token,
            inputs,
        )

    def _list_discord_guilds(self, authorization: str) -> list[dict[str, object]]:
        guilds_result = self._get_json_provider_url(
            _discord_api_endpoint("users/@me/guilds"),
            secret_header_name="Authorization",
            secret_token=authorization,
        )
        guilds: list[dict[str, object]] = []
        if not isinstance(guilds_result, list):
            return guilds
        for guild in guilds_result:
            if not isinstance(guild, dict):
                continue
            guild_id = str(guild.get("id") or "").strip()
            guild_name = str(guild.get("name") or "").strip()
            if guild_id:
                guilds.append(
                    {
                        "id": guild_id,
                        "name": guild_name,
                        "slug": _normalize_discord_slug(guild_name),
                    }
                )
        return guilds

    def _resolve_discord_group_targets(
        self,
        secret_token: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        authorization = _discord_bot_authorization(secret_token)
        guilds = self._list_discord_guilds(authorization)

        results: list[dict[str, object]] = []
        for input_value in inputs:
            parsed = _parse_discord_channel_resolve_input(input_value)
            channel_id = str(parsed.get("channelId") or "").strip()
            channel_query = str(parsed.get("channel") or "").strip()
            guild_query_id = str(parsed.get("guildId") or "").strip()
            guild_query_name = str(parsed.get("guild") or "").strip()
            if channel_query and (guild_query_id or guild_query_name):
                guild = _discord_guild_match(
                    guilds,
                    guild_id=guild_query_id,
                    guild_name=guild_query_name,
                )
                if guild is None:
                    results.append(
                        _unresolved_channel_target(input_value, "Discord guild not found.")
                    )
                    continue
                channels = self._list_discord_guild_channels(
                    authorization,
                    str(guild.get("id") or ""),
                )
                normalized_channel_query = _normalize_discord_slug(channel_query)
                if channel_query.isdigit():
                    matches = [
                        channel
                        for channel in channels
                        if str(channel.get("id") or "") == channel_query
                    ]
                    if not matches:
                        matches = [
                            channel
                            for channel in channels
                            if str(channel.get("slug") or "") == normalized_channel_query
                        ]
                else:
                    matches = [
                        channel
                        for channel in channels
                        if str(channel.get("slug") or "") == normalized_channel_query
                    ]
                match = _prefer_active_discord_channel(matches)
                if match is None:
                    guild_name = str(guild.get("name") or "").strip()
                    note = (
                        f"channel not found in guild {guild_name}"
                        if guild_name
                        else "channel not found"
                    )
                    results.append(_unresolved_channel_target(input_value, note))
                    continue
                guild_channel_payload: dict[str, object] = {
                    "input": input_value,
                    "resolved": True,
                    "id": str(match.get("id") or ""),
                }
                channel_name = str(match.get("name") or "").strip()
                if channel_name:
                    guild_channel_payload["name"] = channel_name
                results.append(guild_channel_payload)
                continue
            if channel_query:
                normalized_channel_query = _normalize_discord_slug(channel_query)
                candidates: list[dict[str, object]] = []
                for guild in guilds:
                    channels = self._list_discord_guild_channels(
                        authorization,
                        str(guild.get("id") or ""),
                    )
                    for channel in channels:
                        if str(channel.get("slug") or "") == normalized_channel_query:
                            candidates.append(channel)
                match = _prefer_active_discord_channel(candidates)
                if match is None:
                    results.append(
                        _unresolved_channel_target(input_value, "channel not found")
                    )
                    continue
                match_guild_id = str(match.get("guildId") or "").strip()
                guild = next(
                    (
                        entry
                        for entry in guilds
                        if str(entry.get("id") or "").strip() == match_guild_id
                    ),
                    None,
                )
                global_channel_payload: dict[str, object] = {
                    "input": input_value,
                    "resolved": True,
                    "id": str(match.get("id") or ""),
                }
                channel_name = str(match.get("name") or "").strip()
                if channel_name:
                    global_channel_payload["name"] = channel_name
                guild_name = str((guild or {}).get("name") or "").strip()
                if len(candidates) > 1 and guild_name:
                    global_channel_payload["note"] = f"matched multiple; chose {guild_name}"
                results.append(global_channel_payload)
                continue
            if not channel_id:
                results.append(
                    _unresolved_channel_target(
                        input_value,
                        "Discord route-backed resolver currently supports channel ids.",
                    )
                )
                continue
            try:
                channel_result = self._get_json_provider_url(
                    _discord_api_endpoint(f"channels/{channel_id}"),
                    secret_header_name="Authorization",
                    secret_token=authorization,
                )
            except RuntimeError as exc:
                results.append(_unresolved_channel_target(input_value, str(exc)))
                continue
            if not isinstance(channel_result, dict):
                results.append(_unresolved_channel_target(input_value, "channel not found"))
                continue
            resolved_channel_id = str(channel_result.get("id") or "").strip()
            guild_id = str(channel_result.get("guild_id") or "").strip()
            if not resolved_channel_id or not guild_id:
                results.append(_unresolved_channel_target(input_value, "channel not found"))
                continue
            guild = next(
                (entry for entry in guilds if str(entry.get("id") or "") == guild_id),
                None,
            )
            expected_guild_id = str(parsed.get("guildId") or "").strip()
            channel_name = str(channel_result.get("name") or "").strip()
            if expected_guild_id and expected_guild_id != guild_id:
                note = (
                    f"channel belongs to guild {guild.get('name')}"
                    if guild and str(guild.get("name") or "").strip()
                    else "channel belongs to a different guild"
                )
                results.append(_unresolved_channel_target(input_value, note))
                continue
            payload: dict[str, object] = {
                "input": input_value,
                "resolved": True,
                "id": resolved_channel_id,
            }
            if channel_name:
                payload["name"] = channel_name
            results.append(payload)
        return results

    def _resolve_discord_user_targets(
        self,
        secret_token: str,
        inputs: list[str],
    ) -> list[dict[str, object]]:
        authorization = _discord_bot_authorization(secret_token)
        guilds: list[dict[str, object]] | None = None
        results: list[dict[str, object]] = []
        for input_value in inputs:
            parsed = _parse_discord_user_resolve_input(input_value)
            user_id = str(parsed.get("userId") or "").strip()
            if user_id:
                results.append(
                    {
                        "input": input_value,
                        "resolved": True,
                        "id": user_id,
                    }
                )
                continue
            query = str(parsed.get("userName") or "").strip()
            if not query:
                results.append({"input": input_value, "resolved": False})
                continue
            if guilds is None:
                guilds = self._list_discord_guilds(authorization)
            guild_list = guilds
            parsed_guild_id = str(parsed.get("guildId") or "").strip()
            parsed_guild_name = str(parsed.get("guildName") or "").strip()
            if parsed_guild_id or parsed_guild_name:
                guild = _discord_guild_match(
                    guilds,
                    guild_id=parsed_guild_id,
                    guild_name=parsed_guild_name,
                )
                guild_list = [guild] if guild is not None else []

            best_member: dict[str, object] | None = None
            best_score = -1
            match_count = 0
            for guild in guild_list:
                guild_id = str(guild.get("id") or "").strip()
                if not guild_id:
                    continue
                members_result = self._get_json_provider_url(
                    _discord_api_endpoint(
                        f"guilds/{guild_id}/members/search?"
                        f"{urlencode({'query': query, 'limit': '25'})}"
                    ),
                    secret_header_name="Authorization",
                    secret_token=authorization,
                )
                if not isinstance(members_result, list):
                    continue
                for member in members_result:
                    if not isinstance(member, dict):
                        continue
                    score = _score_discord_member(member, query)
                    if score == 0:
                        continue
                    match_count += 1
                    if score > best_score:
                        best_member = member
                        best_score = score
            if best_member is None:
                results.append({"input": input_value, "resolved": False})
                continue
            user = best_member.get("user")
            user_payload = user if isinstance(user, dict) else {}
            resolved_user_id = str(user_payload.get("id") or "").strip()
            payload: dict[str, object] = {
                "input": input_value,
                "resolved": True,
                "id": resolved_user_id,
            }
            name = _discord_member_display_name(best_member)
            if name:
                payload["name"] = name
            if match_count > 1:
                payload["note"] = "multiple matches; chose best"
            results.append(payload)
        return results

    def _list_discord_guild_channels(
        self,
        authorization: str,
        guild_id: str,
    ) -> list[dict[str, object]]:
        channels_result = self._get_json_provider_url(
            _discord_api_endpoint(f"guilds/{guild_id}/channels"),
            secret_header_name="Authorization",
            secret_token=authorization,
        )
        channels: list[dict[str, object]] = []
        if not isinstance(channels_result, list):
            return channels
        for channel in channels_result:
            if not isinstance(channel, dict):
                continue
            channel_id = str(channel.get("id") or "").strip()
            channel_name = str(channel.get("name") or "").strip()
            if not channel_id or not channel_name:
                continue
            thread_metadata = channel.get("thread_metadata")
            archived = (
                bool(thread_metadata.get("archived"))
                if isinstance(thread_metadata, dict)
                else False
            )
            channels.append(
                {
                    "id": channel_id,
                    "name": channel_name,
                    "slug": _normalize_discord_slug(channel_name),
                    "guildId": guild_id,
                    "type": channel.get("type"),
                    "archived": archived,
                }
            )
        return channels

    def _probe_discord_provider_route(
        self,
        route: dict[str, Any],
        secret_token: str,
        timeout_ms: int,
    ) -> dict[str, Any]:
        del route
        authorization = _discord_bot_authorization(secret_token)
        timeout_seconds = max(float(timeout_ms) / 1000.0, 0.001)
        bot_result = self._get_json_provider_url(
            _discord_api_endpoint("users/@me"),
            secret_header_name="Authorization",
            secret_token=authorization,
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(bot_result, dict):
            raise RuntimeError("Discord API returned a non-JSON bot response.")
        bot = {
            "id": str(bot_result.get("id") or ""),
            "username": str(bot_result.get("username") or ""),
        }
        payload: dict[str, Any] = {
            "ok": True,
            "status": "ok",
            "provider": "discord",
            "runtime": "native-provider-backed",
            "bot": bot,
            "timeoutMs": timeout_ms,
        }
        try:
            application_result = self._get_json_provider_url(
                _discord_api_endpoint("oauth2/applications/@me"),
                secret_header_name="Authorization",
                secret_token=authorization,
                timeout_seconds=timeout_seconds,
            )
        except Exception:
            application_result = None
        if isinstance(application_result, dict):
            application: dict[str, Any] = {
                "id": str(application_result.get("id") or ""),
            }
            flags = application_result.get("flags")
            if isinstance(flags, int) and not isinstance(flags, bool):
                application["flags"] = flags
                application["intents"] = _discord_privileged_intents_from_flags(flags)
            payload["application"] = application
        return payload

    async def _resolve_explicit_delivery_conversation_target(
        self,
        conversation_target: ConversationTargetView,
    ) -> ConversationTargetView:
        normalized = _normalize_conversation_target(conversation_target)
        if normalized is None:
            raise ValueError("send requires an explicit channel target")
        resolved_target = ConversationTargetView.model_validate(normalized)
        if resolved_target.account_id is not None:
            return resolved_target
        default_account_id = await self._resolve_default_channel_account_id(
            resolved_target.channel
        )
        if default_account_id is None:
            return resolved_target
        return ConversationTargetView(
            channel=resolved_target.channel,
            account_id=default_account_id,
            peer_kind=resolved_target.peer_kind,
            peer_id=resolved_target.peer_id,
        )

    async def _provider_route_for_target(
        self,
        *,
        event_type: str,
        conversation_target: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None] | None:
        for route in await self.database.list_notification_routes():
            if not bool(route.get("enabled")):
                continue
            route_kind = str(route.get("kind") or "").strip().lower()
            if route_kind not in {"webhook", *NATIVE_PROVIDER_ROUTE_KINDS}:
                continue
            events = route.get("events", [])
            if not isinstance(events, list) or not any(
                _matches_event(str(pattern), event_type) for pattern in events
            ):
                continue
            route_conversation_target = _normalize_conversation_target(
                route.get("conversation_target")
            )
            if route_conversation_target is None:
                return route, None
            route_match = _conversation_target_route_match(
                route_conversation_target,
                conversation_target,
            )
            if route_match is not None:
                return route, route_match
        return None

    async def _notification_route_secret_token(self, route: dict[str, Any]) -> str | None:
        secret_id = route.get("vault_secret_id")
        if secret_id is not None:
            return await self.vault.get_secret_value(int(secret_id))
        secret_token = route.get("secret_token")
        return str(secret_token) if secret_token else None

    def _provider_event_poster(
        self,
        route_kind: str,
    ) -> Callable[[dict[str, Any], str, dict[str, Any], str | None], object | None]:
        if route_kind == "slack":
            return self._post_slack_provider_event
        if route_kind == "telegram":
            return self._post_telegram_provider_event
        if route_kind == "discord":
            return self._post_discord_provider_event
        if route_kind == "whatsapp":
            return self._post_whatsapp_provider_event
        if route_kind == "zalo":
            return self._post_zalo_provider_event
        return self._post_webhook

    async def dispatch_message_action(
        self,
        request: GatewayMessageActionDispatchRequest,
    ) -> dict[str, object] | None:
        channel = request.channel.strip().lower()
        action = request.action.strip()
        if channel == "zalo" and action == "send":
            return await self._dispatch_zalo_send_message_action(request)
        if channel == "whatsapp" and action == "react":
            route = await self._provider_route_for_channel_account(
                channel=channel,
                account_id=request.account_id or DEFAULT_ACCOUNT_ID,
            )
            if route is None:
                raise GatewayOutboundRuntimeUnavailableError(
                    "No native WhatsApp route is configured for message.action react."
                )
            secret_token = await self._notification_route_secret_token(route)
            return await asyncio.to_thread(
                self._dispatch_whatsapp_react_message_action,
                route,
                request,
                secret_token,
            )
        if channel == "telegram" and action == "react":
            route = await self._provider_route_for_channel_account(
                channel=channel,
                account_id=request.account_id or DEFAULT_ACCOUNT_ID,
            )
            if route is None:
                raise GatewayOutboundRuntimeUnavailableError(
                    "No native Telegram route is configured for message.action react."
                )
            secret_token = await self._notification_route_secret_token(route)
            return await asyncio.to_thread(
                self._dispatch_telegram_react_message_action,
                route,
                request,
                secret_token,
            )
        if channel == "discord" and action in {"react", "reactions"}:
            route = await self._provider_route_for_channel_account(
                channel=channel,
                account_id=request.account_id or DEFAULT_ACCOUNT_ID,
            )
            if route is None:
                raise GatewayOutboundRuntimeUnavailableError(
                    f"No native Discord route is configured for message.action {action}."
                )
            secret_token = await self._notification_route_secret_token(route)
            if action == "reactions":
                return await asyncio.to_thread(
                    self._dispatch_discord_reactions_message_action,
                    route,
                    request,
                    secret_token,
                )
            return await asyncio.to_thread(
                self._dispatch_discord_react_message_action,
                route,
                request,
                secret_token,
            )
        if channel != "slack" or action not in {"react", "reactions"}:
            return None
        route = await self._provider_route_for_channel_account(
            channel=channel,
            account_id=request.account_id or DEFAULT_ACCOUNT_ID,
        )
        if route is None:
            raise GatewayOutboundRuntimeUnavailableError(
                f"No native Slack route is configured for message.action {action}."
            )
        secret_token = await self._notification_route_secret_token(route)
        if action == "reactions":
            return await asyncio.to_thread(
                self._dispatch_slack_reactions_message_action,
                route,
                request,
                secret_token,
            )
        return await asyncio.to_thread(
            self._dispatch_slack_react_message_action,
            route,
            request,
            secret_token,
        )

    async def _dispatch_zalo_send_message_action(
        self,
        request: GatewayMessageActionDispatchRequest,
    ) -> dict[str, object]:
        target = _message_action_param_string(request.params, "to", required=True)
        if target is None:
            raise RuntimeError("Zalo send requires to.")
        message = (
            _message_action_param_string(
                request.params,
                "message",
                required=True,
                allow_empty=True,
            )
            or ""
        )
        conversation_target = _normalize_conversation_target(
            ConversationTargetView(
                channel="zalo",
                account_id=request.account_id,
                peer_kind=_provider_peer_kind_from_target(target),
                peer_id=target,
            )
        )
        if conversation_target is None:
            raise GatewayOutboundRuntimeUnavailableError(
                "gateway outbound provider route is missing a conversation target"
            )
        payload: dict[str, Any] = {
            "channel": "zalo",
            "to": target,
            "message": message,
        }
        media = request.params.get("media")
        if media is not None:
            if not isinstance(media, str):
                raise RuntimeError("media must be a string.")
            if media.strip():
                payload["mediaUrl"] = media
        if request.account_id is not None:
            payload["accountId"] = request.account_id
        if request.session_key is not None:
            payload["sessionKey"] = request.session_key
        if request.agent_id is not None:
            payload["agentId"] = request.agent_id
        result = await self._post_provider_route_event(
            event_type="gateway/send",
            conversation_target=conversation_target,
            payload=payload,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Zalo API returned a non-JSON response.")
        message_id = str(result.get("messageId") or "").strip()
        if not message_id:
            raise RuntimeError("Zalo API response did not include a message id.")
        return {"ok": True, "to": target, "messageId": message_id}

    def _dispatch_whatsapp_react_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object]:
        chat_target = _message_action_param_string(request.params, "chatJid")
        if chat_target is None:
            chat_target = _message_action_param_string(
                request.params,
                "to",
                required=True,
            )
        if chat_target is None:
            raise RuntimeError("WhatsApp react requires chatJid.")
        recipient_id = _whatsapp_action_recipient_id(chat_target)
        if recipient_id is None:
            raise RuntimeError("WhatsApp react requires chatJid.")
        message_id = _message_action_param_string_or_number(request.params, "messageId")
        if message_id is None:
            message_id = _whatsapp_reaction_context_message_id(request, chat_target)
        if message_id is None:
            _message_action_param_string_or_number(
                request.params,
                "messageId",
                required=True,
            )
        remove = request.params.get("remove") is True
        emoji = (
            _message_action_param_string(
                request.params,
                "emoji",
                required=True,
                allow_empty=True,
            )
            or ""
        )
        if remove and not emoji:
            raise RuntimeError("Emoji is required to remove a WhatsApp reaction.")
        resolved_emoji = "" if remove else emoji
        result = self._post_json_webhook(
            _whatsapp_messages_endpoint(str(route.get("target") or "")),
            {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "reaction",
                "reaction": {
                    "message_id": message_id,
                    "emoji": resolved_emoji,
                },
            },
            secret_header_name="Authorization",
            secret_token=_whatsapp_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("WhatsApp API returned a non-JSON response.")
        if result.get("error"):
            error = result.get("error")
            if isinstance(error, dict):
                detail = str(error.get("message") or error.get("code") or "unknown")
            else:
                detail = str(error)
            raise RuntimeError(f"WhatsApp API returned {detail}.")
        if remove or not emoji:
            return {"ok": True, "removed": True}
        return {"ok": True, "added": emoji}

    def _dispatch_slack_react_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object]:
        channel_id = _slack_channel_id(
            _message_action_param_string(request.params, "channelId", required=True)
        )
        if channel_id is None:
            raise RuntimeError("Slack react requires channelId.")
        message_id = _message_action_param_string(
            request.params,
            "messageId",
            required=True,
        )
        remove = request.params.get("remove") is True
        emoji_value = _message_action_param_string(
            request.params,
            "emoji",
            required=True,
            allow_empty=True,
        )
        if remove and not emoji_value:
            raise RuntimeError("Emoji is required to remove a Slack reaction.")
        if not remove and not emoji_value:
            removed = self._remove_own_slack_reactions(
                route=route,
                channel_id=channel_id,
                message_id=message_id or "",
                secret_token=secret_token,
            )
            return {"ok": True, "removed": removed}
        emoji = _slack_reaction_name(emoji_value)
        result = self._post_json_webhook(
            _slack_api_endpoint(
                str(route.get("target") or ""),
                "reactions.remove" if remove else "reactions.add",
            ),
            {
                "channel": channel_id,
                "timestamp": message_id or "",
                "name": emoji,
            },
            secret_header_name="Authorization",
            secret_token=_slack_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        return {"ok": True, "removed" if remove else "added": emoji}

    def _dispatch_slack_reactions_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object]:
        channel_id = _slack_channel_id(
            _message_action_param_string(request.params, "channelId", required=True)
        )
        if channel_id is None:
            raise RuntimeError("Slack reactions requires channelId.")
        message_id = _message_action_param_string(
            request.params,
            "messageId",
            required=True,
        )
        result = self._post_json_webhook(
            _slack_api_endpoint(str(route.get("target") or ""), "reactions.get"),
            {
                "channel": channel_id,
                "timestamp": message_id or "",
                "full": True,
            },
            secret_header_name="Authorization",
            secret_token=_slack_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        message = result.get("message")
        reactions: object = []
        if isinstance(message, dict):
            raw_reactions = message.get("reactions")
            if isinstance(raw_reactions, list):
                reactions = raw_reactions
        return {"ok": True, "reactions": reactions}

    def _remove_own_slack_reactions(
        self,
        *,
        route: dict[str, Any],
        channel_id: str,
        message_id: str,
        secret_token: str | None,
    ) -> list[str]:
        bearer_token = _slack_bearer_token(secret_token)
        auth_result = self._post_json_webhook(
            _slack_api_endpoint(str(route.get("target") or ""), "auth.test"),
            {},
            secret_header_name="Authorization",
            secret_token=bearer_token,
        )
        if not isinstance(auth_result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if auth_result.get("ok") is False:
            error = str(auth_result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        bot_user_id = str(auth_result.get("user_id") or "").strip()
        if not bot_user_id:
            raise RuntimeError("Failed to resolve Slack bot user id.")
        result = self._post_json_webhook(
            _slack_api_endpoint(str(route.get("target") or ""), "reactions.get"),
            {
                "channel": channel_id,
                "timestamp": message_id,
                "full": True,
            },
            secret_header_name="Authorization",
            secret_token=bearer_token,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        message = result.get("message")
        raw_reactions = message.get("reactions") if isinstance(message, dict) else []
        removed: list[str] = []
        if isinstance(raw_reactions, list):
            seen: set[str] = set()
            for reaction in raw_reactions:
                if not isinstance(reaction, dict):
                    continue
                name = str(reaction.get("name") or "").strip()
                users = reaction.get("users")
                if (
                    name
                    and name not in seen
                    and isinstance(users, list)
                    and bot_user_id in {str(user) for user in users}
                ):
                    seen.add(name)
                    removed.append(name)
        for name in removed:
            remove_result = self._post_json_webhook(
                _slack_api_endpoint(str(route.get("target") or ""), "reactions.remove"),
                {
                    "channel": channel_id,
                    "timestamp": message_id,
                    "name": name,
                },
                secret_header_name="Authorization",
                secret_token=bearer_token,
            )
            if not isinstance(remove_result, dict):
                raise RuntimeError("Slack API returned a non-JSON response.")
            if remove_result.get("ok") is False:
                error = str(remove_result.get("error") or "unknown_error")
                raise RuntimeError(f"Slack API returned {error}.")
        return removed

    def _dispatch_telegram_react_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object]:
        chat_id = _telegram_chat_id(
            _message_action_param_string(request.params, "chatId", required=True)
        )
        if chat_id is None:
            raise RuntimeError("Telegram react requires chatId.")
        message_id = _message_action_param_positive_int(
            request.params,
            "messageId",
            "message_id",
        )
        if message_id is None:
            return {
                "ok": False,
                "reason": "missing_message_id",
                "hint": (
                    "Telegram reaction requires a valid messageId "
                    "(or inbound context fallback). Do not retry."
                ),
            }
        remove = request.params.get("remove") is True
        emoji = (
            _message_action_param_string(
                request.params,
                "emoji",
                required=True,
                allow_empty=True,
            )
            or ""
        )
        if remove and not emoji:
            raise RuntimeError("Emoji is required to remove a Telegram reaction.")
        reaction: list[dict[str, str]] = []
        if not remove and emoji:
            reaction.append({"type": "emoji", "emoji": emoji})
        token = _telegram_bot_token(secret_token)
        result = self._post_json_webhook(
            _telegram_api_endpoint(
                str(route.get("target") or ""),
                token,
                "setMessageReaction",
            ),
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "reaction": reaction,
            },
        )
        if not isinstance(result, dict):
            raise RuntimeError("Telegram API returned a non-JSON response.")
        if result.get("ok") is False:
            description = str(result.get("description") or "")
            is_invalid = "REACTION_INVALID" in description
            return {
                "ok": False,
                "reason": "REACTION_INVALID" if is_invalid else "error",
                "emoji": emoji,
                "hint": (
                    "This emoji is not supported for Telegram reactions. "
                    "Add it to your reaction disallow list so you do not try it again."
                    if is_invalid
                    else "Reaction failed. Do not retry."
                ),
            }
        if remove or not emoji:
            return {"ok": True, "removed": True}
        return {"ok": True, "added": emoji}

    def _dispatch_discord_react_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object] | None:
        del route
        remove = request.params.get("remove") is True
        emoji = _message_action_param_string(
            request.params,
            "emoji",
            required=True,
            allow_empty=True,
        )
        if remove and not emoji:
            raise RuntimeError("Emoji is required to remove a Discord reaction.")
        if not emoji:
            removed = self._remove_own_discord_reactions(
                channel_id=_discord_action_channel_id(
                    _message_action_param_string(
                        request.params,
                        "channelId",
                        required=True,
                    )
                ),
                message_id=_message_action_param_string(
                    request.params,
                    "messageId",
                    required=True,
                ),
                secret_token=secret_token,
            )
            return {"ok": True, "removed": removed}
        channel_id = _discord_action_channel_id(
            _message_action_param_string(request.params, "channelId", required=True)
        )
        if channel_id is None:
            raise RuntimeError("Discord react requires channelId.")
        message_id = _message_action_param_string(
            request.params,
            "messageId",
            required=True,
        )
        encoded_emoji = _discord_reaction_identifier(emoji)
        result = self._request_json_provider_url(
            _discord_api_endpoint(
                f"channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
            ),
            method="DELETE" if remove else "PUT",
            secret_header_name="Authorization",
            secret_token=_discord_bot_authorization(secret_token),
        )
        if isinstance(result, dict) and result.get("error"):
            raise RuntimeError(str(result.get("error")))
        if remove:
            return {"ok": True, "removed": emoji}
        return {"ok": True, "added": emoji}

    def _remove_own_discord_reactions(
        self,
        *,
        channel_id: str | None,
        message_id: str | None,
        secret_token: str | None,
    ) -> list[str]:
        if channel_id is None:
            raise RuntimeError("Discord react requires channelId.")
        if message_id is None:
            raise RuntimeError("messageId is required.")
        authorization = _discord_bot_authorization(secret_token)
        message = self._request_json_provider_url(
            _discord_api_endpoint(f"channels/{channel_id}/messages/{message_id}"),
            method="GET",
            secret_header_name="Authorization",
            secret_token=authorization,
        )
        raw_reactions = message.get("reactions") if isinstance(message, dict) else []
        removed: list[str] = []
        if isinstance(raw_reactions, list):
            seen: set[str] = set()
            for reaction in raw_reactions:
                if not isinstance(reaction, dict):
                    continue
                identifier = _discord_reaction_identifier_from_payload(
                    reaction.get("emoji")
                )
                if identifier and identifier not in seen:
                    seen.add(identifier)
                    removed.append(identifier)
        for identifier in removed:
            result = self._request_json_provider_url(
                _discord_api_endpoint(
                    "channels/"
                    f"{channel_id}/messages/{message_id}/reactions/"
                    f"{_discord_reaction_identifier(identifier)}/@me"
                ),
                method="DELETE",
                secret_header_name="Authorization",
                secret_token=authorization,
            )
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(str(result.get("error")))
        return removed

    def _dispatch_discord_reactions_message_action(
        self,
        route: dict[str, Any],
        request: GatewayMessageActionDispatchRequest,
        secret_token: str | None,
    ) -> dict[str, object]:
        del route
        channel_id = _discord_action_channel_id(
            _message_action_param_string(request.params, "channelId", required=True)
        )
        if channel_id is None:
            raise RuntimeError("Discord reactions requires channelId.")
        message_id = _message_action_param_string(
            request.params,
            "messageId",
            required=True,
        )
        if message_id is None:
            raise RuntimeError("messageId is required.")
        limit = _message_action_param_positive_int(request.params, "limit") or 100
        limit = min(max(limit, 1), 100)
        authorization = _discord_bot_authorization(secret_token)
        message = self._request_json_provider_url(
            _discord_api_endpoint(f"channels/{channel_id}/messages/{message_id}"),
            method="GET",
            secret_header_name="Authorization",
            secret_token=authorization,
        )
        raw_reactions = message.get("reactions") if isinstance(message, dict) else []
        summaries: list[dict[str, object]] = []
        if not isinstance(raw_reactions, list):
            return {"ok": True, "reactions": summaries}
        for reaction in raw_reactions:
            if not isinstance(reaction, dict):
                continue
            raw_emoji = reaction.get("emoji")
            identifier = _discord_reaction_identifier_from_payload(raw_emoji)
            if not identifier:
                continue
            emoji_payload = raw_emoji if isinstance(raw_emoji, dict) else {}
            emoji_id = emoji_payload.get("id")
            emoji_name = emoji_payload.get("name")
            encoded = _discord_reaction_identifier(identifier)
            users_result = self._request_json_provider_url(
                _discord_api_endpoint(
                    "channels/"
                    f"{channel_id}/messages/{message_id}/reactions/{encoded}"
                    f"?{urlencode({'limit': limit})}"
                ),
                method="GET",
                secret_header_name="Authorization",
                secret_token=authorization,
            )
            users: list[dict[str, object]] = []
            if isinstance(users_result, list):
                for user in users_result:
                    if not isinstance(user, dict):
                        continue
                    user_id = str(user.get("id") or "").strip()
                    if not user_id:
                        continue
                    user_summary: dict[str, object] = {"id": user_id}
                    username = str(user.get("username") or "").strip()
                    discriminator = str(user.get("discriminator") or "").strip()
                    if username:
                        user_summary["username"] = username
                        user_summary["tag"] = (
                            f"{username}#{discriminator}" if discriminator else username
                        )
                    users.append(user_summary)
            count = reaction.get("count")
            summaries.append(
                {
                    "emoji": {
                        "id": str(emoji_id) if emoji_id is not None else None,
                        "name": str(emoji_name) if emoji_name is not None else None,
                        "raw": identifier,
                    },
                    "count": count if isinstance(count, int) else 0,
                    "users": users,
                }
            )
        return {"ok": True, "reactions": summaries}

    async def _post_provider_route_event(
        self,
        *,
        event_type: str,
        conversation_target: dict[str, Any],
        payload: dict[str, Any],
    ) -> object:
        route_entry = await self._provider_route_for_target(
            event_type=event_type,
            conversation_target=conversation_target,
        )
        if route_entry is None:
            channel = str(conversation_target.get("channel") or "").strip() or "unknown"
            peer_id = str(conversation_target.get("peer_id") or "").strip() or "unknown"
            raise GatewayOutboundRuntimeUnavailableError(
                f"No provider route is subscribed to {event_type} for {channel}:{peer_id}."
            )
        route, route_match = route_entry
        route_id = int(route["id"])
        event_payload = dict(payload)
        event_payload["conversationTarget"] = conversation_target
        if route_match is not None:
            event_payload["routeMatch"] = route_match
        secret_token = await self._notification_route_secret_token(route)
        route_kind = str(route.get("kind") or "").strip().lower()
        try:
            result = await asyncio.to_thread(
                self._provider_event_poster(route_kind),
                route,
                event_type,
                event_payload,
                secret_token,
            )
        except Exception as exc:
            await self.database.update_notification_route(
                route_id,
                last_delivery_at=utcnow(),
                last_result=f"Failed {event_type} provider runtime",
                last_error=str(exc)[:240],
            )
            raise
        await self.database.update_notification_route(
            route_id,
            last_delivery_at=utcnow(),
            last_result=f"Delivered {event_type} provider runtime",
            last_error=None,
        )
        return result

    async def _deliver_route_backed_provider_message(
        self,
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> object:
        conversation_target = _normalize_conversation_target(
            ConversationTargetView(
                channel=request.channel,
                account_id=request.account_id,
                peer_kind=_provider_peer_kind_from_target(request.target),
                peer_id=request.target,
            )
        )
        if conversation_target is None:
            raise GatewayOutboundRuntimeUnavailableError(
                "gateway outbound provider route is missing a conversation target"
            )
        payload: dict[str, Any] = {
            "channel": request.channel,
            "to": request.target,
            "message": request.message,
        }
        if request.media_urls:
            if len(request.media_urls) == 1:
                payload["mediaUrl"] = request.media_urls[0]
            payload["mediaUrls"] = list(request.media_urls)
        if request.gif_playback is not None:
            payload["gifPlayback"] = request.gif_playback
        if request.reply_to_id is not None:
            payload["replyToId"] = request.reply_to_id
        if request.silent is not None:
            payload["silent"] = request.silent
        if request.force_document is not None:
            payload["forceDocument"] = request.force_document
        if request.account_id is not None:
            payload["accountId"] = request.account_id
        if request.thread_id is not None:
            payload["threadId"] = request.thread_id
        if request.session_key is not None:
            payload["sessionKey"] = request.session_key
        if request.agent_id is not None:
            payload["agentId"] = request.agent_id
        if request.requester_session_key is not None:
            payload["requesterSessionKey"] = request.requester_session_key
        if request.requester_account_id is not None:
            payload["requesterAccountId"] = request.requester_account_id
        if request.requester_sender_id is not None:
            payload["requesterSenderId"] = request.requester_sender_id
        if request.requester_sender_name is not None:
            payload["requesterSenderName"] = request.requester_sender_name
        if request.requester_sender_username is not None:
            payload["requesterSenderUsername"] = request.requester_sender_username
        if request.requester_sender_e164 is not None:
            payload["requesterSenderE164"] = request.requester_sender_e164
        payload["gatewayClientScopes"] = list(request.gateway_client_scopes)
        return await self._post_provider_route_event(
            event_type="gateway/send",
            conversation_target=conversation_target,
            payload=payload,
        )

    async def _deliver_route_backed_provider_poll(
        self,
        request: GatewayOutboundRuntimePollRequest,
    ) -> object:
        conversation_target = _normalize_conversation_target(
            ConversationTargetView(
                channel=request.channel,
                account_id=request.account_id,
                peer_kind=_provider_peer_kind_from_target(request.target),
                peer_id=request.target,
            )
        )
        if conversation_target is None:
            raise GatewayOutboundRuntimeUnavailableError(
                "gateway outbound provider route is missing a conversation target"
            )
        question = request.question.strip()
        options = _normalize_direct_channel_poll_options(list(request.options))
        _validate_direct_channel_poll_shape(question, options)
        payload: dict[str, Any] = {
            "channel": request.channel,
            "to": request.target,
            "question": question,
            "options": options,
        }
        if request.max_selections is not None:
            payload["maxSelections"] = request.max_selections
        if request.duration_seconds is not None:
            payload["durationSeconds"] = request.duration_seconds
        if request.duration_hours is not None:
            payload["durationHours"] = request.duration_hours
        if request.silent is not None:
            payload["silent"] = request.silent
        if request.is_anonymous is not None:
            payload["isAnonymous"] = request.is_anonymous
        if request.account_id is not None:
            payload["accountId"] = request.account_id
        if request.thread_id is not None:
            payload["threadId"] = request.thread_id
        if request.session_key is not None:
            payload["sessionKey"] = request.session_key
        payload["gatewayClientScopes"] = list(request.gateway_client_scopes)
        return await self._post_provider_route_event(
            event_type="gateway/poll",
            conversation_target=conversation_target,
            payload=payload,
        )

    def _cached_direct_channel_delivery_result(
        self,
        delivery_row: dict[str, Any],
    ) -> dict[str, object]:
        delivery_id = int(delivery_row["id"])
        session_key = str(delivery_row.get("session_key") or "").strip()
        message_id = str(delivery_row.get("delivery_message_id") or "").strip() or None
        run_id = str(delivery_row.get("request_idempotency_key") or "").strip() or None
        transport = _direct_channel_transport_from_delivery_row(delivery_row)
        provider_result = _direct_channel_provider_result_from_delivery_row(delivery_row)
        channel = (
            str((transport or {}).get("channel") or "").strip().lower()
            if transport is not None
            else ""
        )
        delivery_state = str(delivery_row.get("delivery_state") or "").strip().lower()
        base_result: dict[str, object] = {
            "delivery_id": delivery_id,
            "session_key": session_key or None,
            "message_id": message_id,
        }
        if run_id is not None:
            base_result["run_id"] = run_id
        if channel:
            base_result["channel"] = channel
        if transport is not None:
            base_result["transport"] = transport
        if provider_result is not None:
            base_result["provider_result"] = provider_result
        if delivery_state == "delivered" and session_key:
            return {"ok": True, **base_result}
        error = str(delivery_row.get("last_error") or "").strip()
        if not error:
            if delivery_state == "pending":
                error = "Channel-target delivery is already pending for this idempotency key."
            elif delivery_state:
                error = (
                    "Channel-target delivery is already "
                    f"{delivery_state} for this idempotency key."
                )
            else:
                error = "Channel-target delivery is unavailable for this idempotency key."
        return {"ok": False, **base_result, "error": error}

    async def _run_idempotent_direct_channel_delivery(
        self,
        *,
        event_type: str,
        request_idempotency_key: str | None,
        delivery_factory: Callable[[], Coroutine[Any, Any, dict[str, object]]],
    ) -> dict[str, object]:
        if request_idempotency_key is None:
            return await delivery_factory()
        cache_key = (event_type, request_idempotency_key)
        created_task = False
        async with self._direct_delivery_inflight_lock:
            inflight = self._direct_delivery_inflight.get(cache_key)
            if inflight is None:
                cached_delivery = (
                    await self.database.find_outbound_delivery_by_request_idempotency_key(
                        event_type=event_type,
                        request_idempotency_key=request_idempotency_key,
                    )
                )
                if cached_delivery is not None:
                    return self._cached_direct_channel_delivery_result(cached_delivery)
                inflight = asyncio.create_task(
                    delivery_factory(),
                    name=f"openzues-{event_type.replace('/', '-')}-delivery",
                )
                self._direct_delivery_inflight[cache_key] = inflight
                created_task = True
        try:
            return dict(await inflight)
        finally:
            if created_task:
                async with self._direct_delivery_inflight_lock:
                    if self._direct_delivery_inflight.get(cache_key) is inflight:
                        self._direct_delivery_inflight.pop(cache_key, None)

    async def _deliver_direct_channel_message(
        self,
        *,
        route_name: str,
        conversation_target: ConversationTargetView,
        thread_id: str | int | None,
        event_type: str,
        payload: dict[str, Any],
        message: str,
        route_scope_extra: dict[str, Any] | None = None,
        request_idempotency_key: str | None = None,
    ) -> dict[str, object]:
        async def perform_delivery() -> dict[str, object]:
            return await self._deliver_direct_channel_message_once(
                route_name=route_name,
                conversation_target=conversation_target,
                thread_id=thread_id,
                event_type=event_type,
                payload=payload,
                message=message,
                route_scope_extra=route_scope_extra,
                request_idempotency_key=request_idempotency_key,
            )

        return await self._run_idempotent_direct_channel_delivery(
            event_type=event_type,
            request_idempotency_key=request_idempotency_key,
            delivery_factory=perform_delivery,
        )

    async def _deliver_direct_channel_message_once(
        self,
        *,
        route_name: str,
        conversation_target: ConversationTargetView,
        thread_id: str | int | None,
        event_type: str,
        payload: dict[str, Any],
        message: str,
        route_scope_extra: dict[str, Any] | None = None,
        request_idempotency_key: str | None = None,
    ) -> dict[str, object]:
        requested_account_id = normalize_optional_account_id(conversation_target.account_id)
        resolved_target = await self._resolve_explicit_delivery_conversation_target(
            conversation_target
        )
        serialized_target = resolved_target.model_dump(mode="json")
        normalized_thread_id = _normalized_delivery_thread_id(thread_id)
        announce_session_key = _announce_delivery_session_key(
            resolved_target,
            thread_id=normalized_thread_id,
        )
        source_session_key = canonicalize_session_key(payload.get("sourceSessionKey"))
        runtime_session_key = source_session_key or announce_session_key
        route_target = (
            str(serialized_target.get("summary") or "").strip() or announce_session_key
        )
        route_scope: dict[str, Any] = {
            "route_name": route_name,
            "route_kind": "announce",
            "route_target": route_target,
            "route_match": "explicitTarget",
        }
        payload_with_target = dict(payload)
        payload_with_target["sessionKey"] = announce_session_key
        payload_with_target["conversationTarget"] = serialized_target
        if source_session_key is not None:
            payload_with_target["sourceSessionKey"] = source_session_key
        if "accountId" not in payload_with_target and resolved_target.account_id is not None:
            payload_with_target["accountId"] = resolved_target.account_id
        if thread_id is not None:
            payload_with_target["threadId"] = thread_id
        if normalized_thread_id is not None:
            route_scope["thread_id"] = normalized_thread_id
        if requested_account_id is None and resolved_target.account_id is not None:
            route_scope["resolved_account_id"] = resolved_target.account_id
        gateway_client_scopes = _normalize_gateway_client_scopes(
            payload.get("gatewayClientScopes")
        )
        requester_session_key = canonicalize_session_key(payload.get("requesterSessionKey"))
        requester_account_id = _normalize_optional_payload_string(
            payload.get("requesterAccountId")
        )
        requester_sender_id = _normalize_optional_payload_string(
            payload.get("requesterSenderId")
        )
        requester_sender_name = _normalize_optional_payload_string(
            payload.get("requesterSenderName")
        )
        requester_sender_username = _normalize_optional_payload_string(
            payload.get("requesterSenderUsername")
        )
        requester_sender_e164 = _normalize_optional_payload_string(
            payload.get("requesterSenderE164")
        )
        if route_scope_extra:
            for key, value in route_scope_extra.items():
                if value is not None:
                    route_scope[key] = value
        if source_session_key is not None:
            route_scope["source_session_key"] = source_session_key
            route_scope["runtime_session_key"] = runtime_session_key
        delivery_id = await self.database.create_outbound_delivery(
            route_id=None,
            route_name=route_name,
            route_kind="announce",
            route_target=route_target,
            event_type=event_type,
            session_key=announce_session_key,
            conversation_target=serialized_target,
            route_scope=route_scope,
            event_payload=payload_with_target,
            request_idempotency_key=request_idempotency_key,
            message_summary=_summarize_outbound_event(event_type, payload),
            test_delivery=False,
            delivery_state="pending",
            attempt_count=0,
        )
        attempt_started_at = utcnow()
        await self.database.update_outbound_delivery(
            delivery_id,
            last_attempt_at=attempt_started_at,
        )
        runtime_target = (
            str(payload.get("to") or resolved_target.peer_id or "").strip() or None
        )
        try:
            runtime = self._resolve_outbound_runtime_service()
            if runtime is None:
                raise GatewayOutboundRuntimeUnavailableError(
                    "gateway outbound runtime is unavailable"
                )
            if event_type == "gateway/poll":
                raw_options = payload.get("options")
                poll_options = (
                    tuple(str(option).strip() for option in raw_options if str(option).strip())
                    if isinstance(raw_options, list)
                    else ()
                )
                runtime_result = await runtime.deliver_poll(
                    session_key=runtime_session_key,
                    message=message,
                    channel=resolved_target.channel,
                    target=runtime_target,
                    question=str(payload.get("question") or payload.get("summary") or ""),
                    options=poll_options,
                    max_selections=_optional_int_payload_value(payload, "maxSelections"),
                    duration_seconds=_optional_int_payload_value(
                        payload,
                        "durationSeconds",
                    ),
                    duration_hours=_optional_int_payload_value(payload, "durationHours"),
                    silent=_optional_bool_payload_value(payload, "silent"),
                    is_anonymous=_optional_bool_payload_value(payload, "isAnonymous"),
                    account_id=resolved_target.account_id,
                    thread_id=normalized_thread_id,
                    gateway_client_scopes=gateway_client_scopes,
                )
            else:
                raw_media_url = payload.get("mediaUrl")
                raw_media_urls = payload.get("mediaUrls")
                media_url = raw_media_url if isinstance(raw_media_url, str) else None
                media_urls = (
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                )
                normalized_media_urls = tuple(
                    _normalize_direct_channel_media_urls(
                        media_url=media_url,
                        media_urls=media_urls,
                    )
                )
                runtime_message = message
                if (
                    resolved_target.channel.lower() in {"whatsapp", "zalo"}
                    and normalized_media_urls
                ):
                    runtime_message = str(payload.get("message") or "").strip()
                runtime_result = await runtime.deliver_message(
                    session_key=runtime_session_key,
                    message=runtime_message,
                    channel=resolved_target.channel,
                    target=runtime_target,
                    media_urls=normalized_media_urls,
                    gif_playback=_optional_bool_payload_value(payload, "gifPlayback"),
                    reply_to_id=str(payload.get("replyToId") or "").strip() or None,
                    silent=_optional_bool_payload_value(payload, "silent"),
                    force_document=_optional_bool_payload_value(payload, "forceDocument"),
                    account_id=resolved_target.account_id,
                    thread_id=normalized_thread_id,
                    agent_id=str(payload.get("agentId") or "").strip() or None,
                    requester_session_key=requester_session_key,
                    requester_account_id=requester_account_id,
                    requester_sender_id=requester_sender_id,
                    requester_sender_name=requester_sender_name,
                    requester_sender_username=requester_sender_username,
                    requester_sender_e164=requester_sender_e164,
                    gateway_client_scopes=gateway_client_scopes,
                )
        except (GatewayOutboundRuntimeUnavailableError, Exception) as exc:
            error = str(exc)[:240]
            await self.database.update_outbound_delivery(
                delivery_id,
                delivery_state="failed",
                attempt_count=1,
                last_attempt_at=attempt_started_at,
                delivered_at=None,
                last_error=error,
            )
            return {
                "ok": False,
                "delivery_id": delivery_id,
                "session_key": announce_session_key,
                "message_id": None,
                "run_id": request_idempotency_key,
                "channel": resolved_target.channel,
                "transport": _build_direct_channel_transport(
                    channel=resolved_target.channel,
                    target=runtime_target,
                    account_id=resolved_target.account_id,
                    thread_id=normalized_thread_id,
                    session_key=runtime_session_key,
                ),
                "error": error,
            }
        message_id = runtime_result.message_id
        transport = runtime_result.transport.as_payload()
        provider_result = _serialize_gateway_provider_result(runtime_result.native_result)
        delivered_route_scope = dict(route_scope)
        delivered_route_scope["transport_runtime"] = runtime_result.transport.runtime
        if provider_result:
            delivered_route_scope["provider_result"] = provider_result
        await self.database.update_outbound_delivery(
            delivery_id,
            delivery_state="delivered",
            attempt_count=1,
            last_attempt_at=attempt_started_at,
            delivered_at=utcnow(),
            last_error=None,
            delivery_message_id=message_id,
            route_scope=delivered_route_scope,
        )
        result: dict[str, object] = {
            "ok": True,
            "delivery_id": delivery_id,
            "session_key": announce_session_key,
            "message_id": message_id,
            "run_id": request_idempotency_key,
            "channel": resolved_target.channel,
            "transport": transport,
        }
        if provider_result:
            result["provider_result"] = provider_result
        return result

    async def send_direct_channel_message(
        self,
        *,
        channel: str,
        to: str,
        message: str,
        media_urls: list[str] | None = None,
        gif_playback: bool | None = None,
        reply_to_id: str | None = None,
        silent: bool | None = None,
        force_document: bool | None = None,
        account_id: str | None = None,
        agent_id: str | None = None,
        thread_id: str | int | None = None,
        session_key: str | None = None,
        requester_session_key: str | None = None,
        requester_account_id: str | None = None,
        requester_sender_id: str | None = None,
        requester_sender_name: str | None = None,
        requester_sender_username: str | None = None,
        requester_sender_e164: str | None = None,
        gateway_client_scopes: list[str] | tuple[str, ...] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        if not self._outbound_runtime_available():
            raise ValueError(
                "send is unavailable until channel-target outbound delivery is wired"
            )
        conversation_target = _build_explicit_announce_conversation_target(
            channel=channel,
            to=to,
            account_id=account_id,
        )
        if conversation_target is None:
            raise ValueError("send requires an explicit channel target")
        normalized_media_urls = _normalize_direct_channel_media_urls(media_urls=media_urls)
        if not message.strip() and not normalized_media_urls:
            raise ValueError("send requires text or media")
        payload: dict[str, Any] = {
            "message": message,
            "channel": conversation_target.channel,
            "to": str(to).strip(),
            "gatewayClientScopes": list(_normalize_gateway_client_scopes(gateway_client_scopes)),
        }
        if normalized_media_urls:
            if len(normalized_media_urls) == 1:
                payload["mediaUrl"] = normalized_media_urls[0]
            payload["mediaUrls"] = normalized_media_urls
            if gif_playback is not None:
                payload["gifPlayback"] = gif_playback
            if not message.strip():
                payload["summary"] = _summarize_direct_channel_media(normalized_media_urls)
        normalized_reply_to_id = str(reply_to_id or "").strip() or None
        if normalized_reply_to_id is not None:
            payload["replyToId"] = normalized_reply_to_id
        if silent is not None:
            payload["silent"] = silent
        if force_document is not None:
            payload["forceDocument"] = force_document
        if account_id is not None:
            payload["accountId"] = account_id
        if agent_id is not None:
            payload["agentId"] = agent_id
        source_session_key = canonicalize_session_key(session_key)
        if source_session_key is not None:
            payload["sourceSessionKey"] = source_session_key
        normalized_requester_session_key = canonicalize_session_key(requester_session_key)
        if normalized_requester_session_key is not None:
            payload["requesterSessionKey"] = normalized_requester_session_key
        normalized_requester_account_id = _normalize_optional_payload_string(
            requester_account_id
        )
        if normalized_requester_account_id is None and any(
            _normalize_optional_payload_string(value) is not None
            for value in (
                requester_session_key,
                requester_sender_id,
                requester_sender_name,
                requester_sender_username,
                requester_sender_e164,
            )
        ):
            normalized_requester_account_id = _normalize_optional_payload_string(account_id)
        if normalized_requester_account_id is not None:
            payload["requesterAccountId"] = normalized_requester_account_id
        requester_sender_fields = {
            "requesterSenderId": requester_sender_id,
            "requesterSenderName": requester_sender_name,
            "requesterSenderUsername": requester_sender_username,
            "requesterSenderE164": requester_sender_e164,
        }
        for key, value in requester_sender_fields.items():
            normalized_value = _normalize_optional_payload_string(value)
            if normalized_value is not None:
                payload[key] = normalized_value
        if idempotency_key is not None:
            payload["idempotencyKey"] = idempotency_key
        result = await self._deliver_direct_channel_message(
            route_name=f"Gateway send to {conversation_target.summary or str(to).strip()}",
            conversation_target=conversation_target,
            thread_id=thread_id,
            event_type="gateway/send",
            payload=payload,
            message=_format_direct_channel_send_message(
                message=message,
                media_urls=normalized_media_urls,
                gif_playback=gif_playback if normalized_media_urls else None,
            ),
            route_scope_extra={
                "source": "gateway.send",
                "source_session_key": source_session_key,
                "agent_id": agent_id,
                "idempotency_key": idempotency_key,
            },
            request_idempotency_key=idempotency_key,
        )
        if result.get("ok") is not True:
            raise ValueError(str(result.get("error") or "Channel-target delivery failed."))
        delivery_id_value = result.get("delivery_id")
        if not isinstance(delivery_id_value, int):
            raise ValueError("Channel-target delivery did not report a delivery id.")
        response: dict[str, object] = {
            "ok": True,
            "sessionKey": str(result["session_key"]),
            "deliveryId": delivery_id_value,
            "channel": str(result.get("channel") or conversation_target.channel),
        }
        run_id = str(result.get("run_id") or "").strip()
        if run_id:
            response["runId"] = run_id
        transport = result.get("transport")
        if isinstance(transport, dict):
            response["transport"] = _serialize_gateway_direct_channel_transport(transport)
        provider_result = result.get("provider_result")
        if isinstance(provider_result, dict):
            response.update(_serialize_gateway_response_provider_result(provider_result))
        message_id = str(result.get("message_id") or "").strip()
        if message_id:
            response["messageId"] = message_id
        return response

    async def send_direct_channel_poll(
        self,
        *,
        channel: str,
        to: str,
        question: str,
        options: list[str],
        max_selections: int | None = None,
        duration_seconds: int | None = None,
        duration_hours: int | None = None,
        silent: bool | None = None,
        is_anonymous: bool | None = None,
        account_id: str | None = None,
        thread_id: str | int | None = None,
        gateway_client_scopes: list[str] | tuple[str, ...] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        if not self._outbound_runtime_available():
            raise ValueError(
                "poll is unavailable until channel-target poll delivery is wired"
            )
        conversation_target = _build_explicit_announce_conversation_target(
            channel=channel,
            to=to,
            account_id=account_id,
        )
        if conversation_target is None:
            raise ValueError("poll requires an explicit channel target")
        normalized_question = str(question).strip()
        normalized_options = _normalize_direct_channel_poll_options(options)
        _validate_direct_channel_poll_shape(normalized_question, normalized_options)
        resolved_max_selections = max_selections if max_selections is not None else 1
        _validate_direct_channel_poll_option_count(
            conversation_target.channel,
            normalized_options,
        )
        _validate_direct_channel_poll_max_selections(
            normalized_options,
            resolved_max_selections,
        )
        _validate_direct_channel_poll_duration_exclusivity(
            duration_seconds=duration_seconds,
            duration_hours=duration_hours,
        )
        if conversation_target.channel == "telegram":
            _validate_telegram_poll_duration_options(
                duration_seconds=duration_seconds,
                duration_hours=duration_hours,
            )
        payload: dict[str, Any] = {
            "summary": normalized_question,
            "question": normalized_question,
            "options": normalized_options,
            "channel": conversation_target.channel,
            "to": str(to).strip(),
            "gatewayClientScopes": list(_normalize_gateway_client_scopes(gateway_client_scopes)),
        }
        if account_id is not None:
            payload["accountId"] = account_id
        payload["maxSelections"] = resolved_max_selections
        if duration_seconds is not None:
            payload["durationSeconds"] = duration_seconds
        if duration_hours is not None:
            payload["durationHours"] = duration_hours
        if silent is not None:
            payload["silent"] = silent
        if is_anonymous is not None:
            payload["isAnonymous"] = is_anonymous
        result = await self._deliver_direct_channel_message(
            route_name=f"Gateway poll to {conversation_target.summary or str(to).strip()}",
            conversation_target=conversation_target,
            thread_id=thread_id,
            event_type="gateway/poll",
            payload=payload,
            message=_format_direct_channel_poll_message(
                question=normalized_question,
                options=normalized_options,
                max_selections=resolved_max_selections,
                duration_seconds=duration_seconds,
                duration_hours=duration_hours,
                silent=silent,
                is_anonymous=is_anonymous,
            ),
            route_scope_extra={
                "source": "gateway.poll",
                "idempotency_key": idempotency_key,
            },
            request_idempotency_key=idempotency_key,
        )
        if result.get("ok") is not True:
            raise ValueError(str(result.get("error") or "Channel-target poll delivery failed."))
        delivery_id_value = result.get("delivery_id")
        if not isinstance(delivery_id_value, int):
            raise ValueError("Channel-target poll delivery did not report a delivery id.")
        response: dict[str, object] = {
            "ok": True,
            "sessionKey": str(result["session_key"]),
            "deliveryId": delivery_id_value,
            "channel": str(result.get("channel") or conversation_target.channel),
        }
        run_id = str(result.get("run_id") or "").strip()
        if run_id:
            response["runId"] = run_id
        transport = result.get("transport")
        if isinstance(transport, dict):
            response["transport"] = _serialize_gateway_direct_channel_transport(transport)
        provider_result = result.get("provider_result")
        if isinstance(provider_result, dict):
            response.update(_serialize_gateway_response_provider_result(provider_result))
        message_id = str(result.get("message_id") or "").strip()
        if message_id:
            response["messageId"] = message_id
        return response

    async def _record_cron_mission_result_state(
        self,
        event_type: str,
        mission: dict[str, Any],
        task: TaskBlueprintView,
    ) -> None:
        if not _task_is_gateway_cron_task(task):
            return
        result_status = _cron_result_status(mission.get("status"))
        if result_status is None or event_type not in {"mission/completed", "mission/failed"}:
            return

        started_at_ms, ended_at_ms = _cron_runtime_window_ms(task, mission)
        error = _cron_result_error_text(mission) if result_status == "error" else None
        state = _task_cron_state(task)
        state.pop("runningAtMs", None)
        state["lastRunAtMs"] = started_at_ms
        state["lastRunStatus"] = result_status
        state["lastStatus"] = result_status
        state["lastDurationMs"] = max(0, ended_at_ms - started_at_ms)
        if error:
            state["lastError"] = error
        else:
            state.pop("lastError", None)
        error_reason = _cron_error_reason(error) if result_status == "error" else None
        if error_reason is not None:
            state["lastErrorReason"] = error_reason
        else:
            state.pop("lastErrorReason", None)

        delivery_state = _cron_delivery_state(task, error=error)
        state.pop("lastDelivered", None)
        state.pop("lastDeliveryError", None)
        state.update(
            {
                key: value
                for key, value in delivery_state.items()
                if value is not None
            }
        )

        if result_status == "error":
            previous_errors = state.get("consecutiveErrors")
            consecutive_errors = (
                previous_errors + 1
                if isinstance(previous_errors, int) and not isinstance(previous_errors, bool)
                else 1
            )
            state["consecutiveErrors"] = consecutive_errors
            alert_config = _resolve_cron_failure_alert(task, self.cron_failure_alert)
            if (
                alert_config is not None
                and not bool(task.cron_delivery_best_effort)
                and consecutive_errors >= int(alert_config["after"])
            ):
                last_alert = state.get("lastFailureAlertAtMs")
                cooldown_ms = int(alert_config["cooldownMs"])
                in_cooldown = (
                    isinstance(last_alert, int)
                    and not isinstance(last_alert, bool)
                    and ended_at_ms - last_alert < max(0, cooldown_ms)
                )
                if not in_cooldown:
                    session_key = str(mission.get("session_key") or "").strip() or None
                    await self._send_cron_failure_alert(
                        task=task,
                        mission=mission,
                        alert_config=alert_config,
                        message=_cron_failure_alert_message(
                            task,
                            consecutive_errors=consecutive_errors,
                            error=error,
                        ),
                        session_key=session_key,
                    )
                    state["lastFailureAlertAtMs"] = ended_at_ms
            if task.schedule_kind == "at":
                retry_config = _resolve_cron_retry_config(self.cron_retry)
                backoff_ms = cast(tuple[int, ...], retry_config["backoffMs"])
                retry_on = cast(tuple[str, ...], retry_config["retryOn"])
                max_attempts = int(retry_config["maxAttempts"])
                if (
                    _is_transient_cron_error(error, retry_on)
                    and consecutive_errors <= max_attempts
                ):
                    state["nextRunAtMs"] = ended_at_ms + _cron_error_backoff_ms(
                        consecutive_errors,
                        backoff_ms,
                    )
                else:
                    state.pop("nextRunAtMs", None)
                    await self.database.update_task_blueprint(task.id, enabled=0)
        else:
            state["consecutiveErrors"] = 0
            state.pop("lastFailureAlertAtMs", None)
            if task.schedule_kind == "at":
                state.pop("nextRunAtMs", None)

        await self.database.update_task_blueprint_payload(task.id, cron_state=state)

    async def _record_cron_system_event_result_state(
        self,
        task: TaskBlueprintView,
        *,
        launched_at: str,
    ) -> None:
        if not _task_is_gateway_cron_task(task):
            return
        launched_at_ms = _timestamp_ms(launched_at)
        if launched_at_ms is None:
            return
        state = _task_cron_state(task)
        state.pop("runningAtMs", None)
        state["lastRunAtMs"] = launched_at_ms
        state["lastRunStatus"] = "ok"
        state["lastStatus"] = "ok"
        state["lastDurationMs"] = 0
        state.pop("lastError", None)
        state.pop("lastErrorReason", None)
        state.pop("lastDelivered", None)
        state.pop("lastDeliveryError", None)
        state["lastDeliveryStatus"] = "not-requested"
        state["consecutiveErrors"] = 0
        state.pop("lastFailureAlertAtMs", None)
        await self.database.update_task_blueprint_payload(task.id, cron_state=state)

    async def _deliver_cron_finished_delivery(
        self,
        event_type: str,
        mission: dict[str, Any],
        task: TaskBlueprintView,
    ) -> None:
        mission_status = str(mission.get("status") or "").strip().lower()
        conversation_target = _normalize_conversation_target(
            mission.get("conversation_target") or task.conversation_target
        )
        session_key = str(mission.get("session_key") or "").strip() or None
        task_id = int(task.id)

        if event_type == "mission/completed" and mission_status == "completed":
            summary = _cron_delivery_summary(mission)
            if summary is None:
                return
            secret_header_name: str | None = None
            secret_token: str | None = None
            if _task_cron_delivery_mode(task) == "webhook":
                webhook_target = _normalized_http_webhook_url(_task_cron_delivery_to(task))
            elif _task_cron_notify_enabled(task):
                webhook_target = _normalized_http_webhook_url(self.cron_webhook_url)
                if self.cron_webhook_token:
                    secret_header_name = "Authorization"
                    secret_token = f"Bearer {self.cron_webhook_token}"
            else:
                return
            if webhook_target is None:
                return
            payload: dict[str, Any] = {
                "action": "finished",
                "missionId": int(mission["id"]),
                "taskId": task_id,
                "jobId": _cron_job_id(task_id),
                "jobName": task.name,
                "status": _cron_run_status(str(mission.get("status") or "")),
                "summary": summary,
            }
            await self._send_ad_hoc_webhook_delivery(
                route_name=f"Cron webhook for {task.name}",
                route_target=webhook_target,
                event_type="cron/finished",
                payload=payload,
                session_key=session_key,
                conversation_target=conversation_target,
                secret_header_name=secret_header_name,
                secret_token=secret_token,
            )
            return

        if event_type == "mission/failed" and mission_status == "failed":
            if bool(task.cron_delivery_best_effort):
                return
            failure_message = _cron_failure_message(task, mission)
            announce_message = _cron_failure_announce_message(task, mission)
            payload = {
                "missionId": int(mission["id"]),
                "taskId": task_id,
                "jobId": _cron_job_id(task_id),
                "jobName": task.name,
                "message": failure_message,
                "status": "error",
                "error": str(mission.get("last_error") or "").strip() or None,
            }
            delivery_session_key = _task_cron_session_key(task) or session_key
            failure_destination = _task_cron_failure_destination(task) or {}
            failure_destination_mode = (
                str(failure_destination.get("mode") or "").strip().lower()
            )
            failure_destination_channel = (
                str(failure_destination.get("channel") or "").strip().lower() or None
            )
            failure_destination_target = _failure_destination_explicit_announce_target(
                failure_destination
            )
            explicit_announce_target = _task_explicit_announce_conversation_target(
                task
            )
            if failure_destination_mode != "webhook":
                if (
                    failure_destination_target is not None
                    and self._session_outbound_runtime_available()
                ):
                    await self._send_ad_hoc_announce_delivery(
                        route_name=(
                            f"Announce failure destination for {task.name}"
                        ),
                        conversation_target=failure_destination_target,
                        event_type="cron/failure",
                        payload=payload,
                        message=announce_message,
                        request_idempotency_key=_cron_direct_delivery_idempotency_key(
                            task=task,
                            mission=mission,
                            event_type="cron/failure",
                            conversation_target=failure_destination_target,
                        ),
                    )
                    return
                if (
                    failure_destination_mode == "announce"
                    and failure_destination_channel == "last"
                    and delivery_session_key is not None
                    and self._session_outbound_runtime_available()
                ):
                    session_payload = dict(payload)
                    session_payload["sessionKey"] = delivery_session_key
                    await self._send_ad_hoc_session_delivery(
                        route_name=f"Session delivery for {task.name}",
                        session_key=delivery_session_key,
                        event_type="cron/failure",
                        payload=session_payload,
                        conversation_target=conversation_target,
                        message=announce_message,
                    )
                    return
                if (
                    explicit_announce_target is not None
                    and self._session_outbound_runtime_available()
                ):
                    explicit_thread_id = _task_cron_delivery_thread_id(task)
                    await self._send_ad_hoc_announce_delivery(
                        route_name=f"Announce delivery for {task.name}",
                        conversation_target=explicit_announce_target,
                        thread_id=explicit_thread_id,
                        event_type="cron/failure",
                        payload=payload,
                        message=announce_message,
                        request_idempotency_key=_cron_direct_delivery_idempotency_key(
                            task=task,
                            mission=mission,
                            event_type="cron/failure",
                            conversation_target=explicit_announce_target,
                            thread_id=explicit_thread_id,
                        ),
                    )
                    return
                if (
                    _task_cron_payload_kind(task) == "agentTurn"
                    and _task_cron_delivery_mode(task) != "webhook"
                    and _task_cron_delivery_channel(task) == "last"
                    and delivery_session_key is not None
                    and self._session_outbound_runtime_available()
                ):
                    session_payload = dict(payload)
                    session_payload["sessionKey"] = delivery_session_key
                    await self._send_ad_hoc_session_delivery(
                        route_name=f"Session delivery for {task.name}",
                        session_key=delivery_session_key,
                        event_type="cron/failure",
                        payload=session_payload,
                        conversation_target=conversation_target,
                        message=announce_message,
                    )
                    return
                if (
                    _task_cron_payload_kind(task) == "agentTurn"
                    and _task_cron_delivery_mode(task) != "webhook"
                ):
                    notify_event = dict(payload)
                    notify_event["sessionKey"] = delivery_session_key
                    fallback_target = (
                        failure_destination_target.model_dump(mode="json")
                        if failure_destination_target is not None
                        else conversation_target
                    )
                    if fallback_target is not None:
                        notify_event["conversationTarget"] = fallback_target
                    await self._deliver_notifications("cron/failure", notify_event)
                return
            webhook_target = _normalized_http_webhook_url(
                str(failure_destination.get("to") or "").strip()
            )
            if webhook_target is None:
                return
            await self._send_ad_hoc_webhook_delivery(
                route_name=f"Cron failure destination for {task.name}",
                route_target=webhook_target,
                event_type="cron/failure",
                payload=payload,
                session_key=session_key,
                conversation_target=conversation_target,
            )

    def _mission_targets_openclaw_parity(
        self,
        mission: dict[str, Any],
        *,
        task: dict[str, Any] | None,
    ) -> bool:
        values = [
            mission.get("name"),
            mission.get("objective"),
            mission.get("last_checkpoint"),
        ]
        if task is not None:
            values.extend(
                [
                    task.get("name"),
                    task.get("summary"),
                    task.get("objective_template"),
                    task.get("completion_marker"),
                ]
            )
        blob = " ".join(str(value or "") for value in values).lower()
        return "parity" in blob and ("openclaw" in blob or "parity complete" in blob)

    def _checkpoint_is_verified_parity_handoff(self, summary: str) -> bool:
        lowered = summary.lower()
        return (
            "verified:" in lowered
            and "tool evidence:" in lowered
            and ("next step:" in lowered or "blockers:" in lowered)
        )

    def _resolve_parity_checkpoint_path(self, mission: dict[str, Any]) -> Path | None:
        if self.parity_checkpoint_path is not None:
            return self.parity_checkpoint_path
        cwd = str(mission.get("cwd") or "").strip()
        if not cwd:
            return None
        docs_dir = Path(cwd) / "docs"
        if not docs_dir.exists():
            return None
        candidates = sorted(
            docs_dir.glob("openclaw-parity-checkpoint-*.md"),
            key=lambda path: path.stat().st_mtime_ns,
        )
        if candidates:
            return candidates[-1]
        return None

    def _build_parity_checkpoint_entry(
        self,
        mission: dict[str, Any],
        *,
        mission_view: MissionView | None = None,
    ) -> str:
        mission_id = int(mission["id"])
        title = str(mission.get("name") or "Parity Slice").strip() or "Parity Slice"
        updated = _parse_timestamp(str(mission.get("updated_at") or "")) or datetime.now(UTC)
        summary = str(mission.get("last_checkpoint") or "").strip()
        lines = [
            f"<!-- OPENZUES_PARITY_MISSION:{mission_id} -->",
            "",
            f"## Update: {title}",
            "",
            f"Date: {updated.date().isoformat()}",
            "",
            "### Operator handoff",
            "",
            summary,
        ]
        tool_evidence = mission_view.tool_evidence if mission_view is not None else None
        if tool_evidence is not None and tool_evidence.expected_toolsets:
            lines.extend(
                [
                    "",
                    "### Observed tool evidence",
                    "",
                    f"- {tool_evidence.summary}",
                ]
            )
            for item in tool_evidence.items:
                status_label = "observed" if item.status == "observed" else "unproven"
                example = item.examples[0] if item.examples else None
                line = f"- {item.toolset}: {status_label}"
                if example:
                    line += f" ({example})"
                lines.append(line)
        return "\n".join(lines)

    async def _maybe_append_parity_checkpoint_ledger(
        self,
        mission: dict[str, Any],
        *,
        task: dict[str, Any] | None,
    ) -> None:
        if str(mission.get("status") or "") != "completed":
            return
        summary = str(mission.get("last_checkpoint") or "").strip()
        if not summary or not self._checkpoint_is_verified_parity_handoff(summary):
            return
        if not self._mission_targets_openclaw_parity(mission, task=task):
            return
        path = self._resolve_parity_checkpoint_path(mission)
        if path is None:
            return
        mission_view: MissionView | None = None
        get_view = getattr(self.missions, "get_view", None)
        if callable(get_view):
            try:
                maybe_view = await get_view(int(mission["id"]))
            except Exception:
                logger.exception(
                    "Failed to load mission view for parity checkpoint evidence (%s).",
                    mission["id"],
                )
            else:
                if isinstance(maybe_view, MissionView):
                    mission_view = maybe_view
        marker = f"<!-- OPENZUES_PARITY_MISSION:{int(mission['id'])} -->"
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if marker in existing:
                return
            base = existing.rstrip()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            base = "# OpenClaw Parity Checkpoint"
        entry = self._build_parity_checkpoint_entry(mission, mission_view=mission_view)
        content = f"{base}\n\n{entry}\n"
        path.write_text(content, encoding="utf-8")
        await self._publish_ops_event(
            "parity/checkpoint-updated",
            {
                "missionId": int(mission["id"]),
                "missionName": str(mission.get("name") or ""),
                "path": str(path),
            },
        )

    async def tick_once(self) -> None:
        tasks = await self.list_task_blueprint_views()
        missions = await self.missions.list_views()
        instances = await self.manager.list_views()
        playbooks = [
            PlaybookView.model_validate(row) for row in await self.database.list_playbooks()
        ]

        for task in tasks:
            if not task.enabled:
                continue
            next_run = _parse_timestamp(_next_run_at(task))
            if next_run is None or next_run > datetime.now(UTC):
                continue
            active = any(
                mission.task_blueprint_id == task.id and mission.status in {"active", "blocked"}
                for mission in missions
            )
            if active:
                continue
            try:
                if _task_routes_through_gateway_wake(task):
                    await self.dispatch_cron_system_event_task(task.id, trigger="schedule")
                else:
                    await self.run_task_blueprint_now(task.id, trigger="schedule")
            except Exception:
                logger.exception("Scheduled task launch failed for %s", task.name)

        for playbook in playbooks:
            next_run = _parse_timestamp(_playbook_next_run_at(playbook))
            if next_run is None or next_run > datetime.now(UTC):
                continue
            started_at = utcnow()
            try:
                result = await self.playbooks.execute(
                    playbook.model_dump(),
                    PlaybookRun(),
                    self.manager,
                )
                await self.database.update_playbook(
                    playbook.id,
                    last_run_at=started_at,
                    last_status="completed",
                    last_result_summary=summarize_playbook_result(
                        playbook.model_dump(),
                        result,
                    )[:240],
                )
                await self._publish_ops_event(
                    "playbook/completed",
                    {
                        "playbookId": playbook.id,
                        "playbookName": playbook.name,
                        "trigger": "schedule",
                    },
                )
            except Exception as exc:
                await self.database.update_playbook(
                    playbook.id,
                    last_run_at=started_at,
                    last_status="failed",
                    last_result_summary=str(exc)[:240],
                )
                await self._publish_ops_event(
                    "playbook/failed",
                    {
                        "playbookId": playbook.id,
                        "playbookName": playbook.name,
                        "trigger": "schedule",
                        "error": str(exc)[:240],
                    },
                )
                logger.exception("Scheduled playbook run failed for %s", playbook.name)

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
        await self._publish_derived_task_inbox_notifications(
            task_blueprints=tasks,
            missions=missions,
            instances=instances,
            playbooks=playbooks,
        )

    async def _build_draft_for_task(self, task: TaskBlueprintView) -> MissionDraftView:
        projects = {int(project["id"]): project for project in await self.database.list_projects()}
        project = projects.get(task.project_id) if task.project_id is not None else None
        task = _attach_task_tool_policy(
            task,
            project_label=str(project["label"]) if project is not None else None,
            project_path=str(project["path"]) if project is not None else None,
        )
        skill_pins = [
            skill
            for skill in await self.list_skill_pin_views()
            if skill.project_id == task.project_id and skill.enabled
        ]
        integrations = [
            integration
            for integration in await self.list_integration_views()
            if integration.enabled and integration.project_id in {None, task.project_id}
        ]
        skill_pins = materialize_skillbook_pins(
            task.project_id or 0,
            task.objective_template,
            explicit_pins=skill_pins,
            project_label=str(project["label"]) if project is not None else None,
            project_path=str(project["path"]) if project is not None else None,
            toolsets=task.toolsets,
        )
        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        session_key = None
        thread_id = None
        instance_id: int | None
        resolved_instance_name: str | None = None
        resolved_instance_cwd: str | None = None
        if self.launch_routing is not None:
            launch_route = await self.launch_routing.describe(task=task)
            session_key = launch_route.session_key
            if (
                launch_route.conversation_reuse is not None
                and launch_route.conversation_reuse.reusable
            ):
                thread_id = launch_route.conversation_reuse.thread_id
            if launch_route.resolved_instance is not None:
                instance_id = launch_route.resolved_instance.id
                resolved_instance_name = launch_route.resolved_instance.label
                selected_instance = next(
                    (item for item in await self.manager.list_views() if item.id == instance_id),
                    None,
                )
                if selected_instance is not None:
                    resolved_instance_cwd = selected_instance.cwd
            else:
                raise ValueError("No instance is available for this task blueprint.")
        else:
            instances = await self.manager.list_views()
            instance_id = task.instance_id
            if instance_id is None:
                connected = next((item.id for item in instances if item.connected), None)
                instance_id = connected or (instances[0].id if instances else None)
            if instance_id is None:
                raise ValueError("No instance is available for this task blueprint.")
            selected_instance = next((item for item in instances if item.id == instance_id), None)
            if selected_instance is not None:
                resolved_instance_name = selected_instance.name
                resolved_instance_cwd = selected_instance.cwd

        return MissionDraftView(
            name=task.name,
            objective=_build_task_objective(
                task,
                skill_pins=skill_pins,
                integrations=integrations,
                toolsets=task.toolsets,
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
                instance_name=resolved_instance_name,
                instance_cwd=task.cwd
                or (str(project["path"]) if project is not None else resolved_instance_cwd),
                project_path=str(project["path"]) if project is not None else task.cwd,
            ),
            instance_id=instance_id,
            project_id=task.project_id,
            task_blueprint_id=task.id,
            cwd=task.cwd or (str(project["path"]) if project is not None else None),
            thread_id=thread_id,
            session_key=session_key,
            conversation_target=launch_route.conversation_target
            if self.launch_routing is not None
            else task.conversation_target,
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
            toolsets=task.toolsets,
            start_immediately=True,
            tool_policy=task.tool_policy,
            preferred_memory_provider=preferred_memory_provider,
            preferred_memory_provider_label=memory_provider_label(preferred_memory_provider),
            preferred_executor=preferred_executor,
            preferred_executor_label=executor_label(preferred_executor),
            runtime_profile_summary=build_runtime_profile_summary(
                preferred_memory_provider=preferred_memory_provider,
                preferred_executor=preferred_executor,
            ),
        )

    async def build_task_draft(self, task_id: int) -> MissionDraftView:
        row = await self.database.get_task_blueprint(task_id)
        if row is None:
            raise KeyError(f"Unknown task blueprint {task_id}")
        task = _serialize_task(row)
        return await self._build_draft_for_task(task)

    async def _deliver_notifications(self, event_type: str, event: dict[str, Any]) -> None:
        await self._migrate_legacy_secret_refs()
        routes = await self.database.list_notification_routes()
        event_conversation_target = await self._resolve_event_conversation_target(event)
        event_session_key = await self._resolve_event_session_key(event)
        for route in routes:
            if not bool(route.get("enabled")):
                continue
            events = route.get("events", [])
            if not isinstance(events, list) or not any(
                _matches_event(str(pattern), event_type) for pattern in events
            ):
                continue
            route_conversation_target = _normalize_conversation_target(
                route.get("conversation_target")
            )
            route_match = (
                _conversation_target_route_match(
                    route_conversation_target,
                    event_conversation_target,
                )
                if route_conversation_target is not None
                else None
            )
            if route_conversation_target is not None and route_match is None:
                continue
            route_id = int(route["id"])
            route_scope: dict[str, Any] = {
                "route_id": route_id,
                "route_name": str(route.get("name") or f"Route {route_id}"),
                "route_kind": str(route.get("kind") or "webhook"),
                "route_target": str(route.get("target") or ""),
                "route_match": route_match,
            }
            event_payload = dict(event)
            if event_conversation_target is not None:
                event_payload["conversationTarget"] = event_conversation_target
            if route_conversation_target is not None:
                event_payload["routeConversationTarget"] = route_conversation_target
            if route_match is not None:
                event_payload["routeMatch"] = route_match
            delivery_id = await self.database.create_outbound_delivery(
                route_id=route_id,
                route_name=route_scope["route_name"],
                route_kind=route_scope["route_kind"],
                route_target=route_scope["route_target"],
                event_type=event_type,
                session_key=event_session_key,
                conversation_target=event_conversation_target or route_conversation_target,
                route_scope=route_scope,
                event_payload=event_payload,
                message_summary=_summarize_outbound_event(event_type, event_payload),
                test_delivery=bool(event.get("test")),
                delivery_state="pending",
                attempt_count=0,
            )
            delivery_row = await self.database.get_outbound_delivery(delivery_id)
            assert delivery_row is not None
            await self._deliver_saved_outbound_delivery_row(delivery_row, route)

    async def _resolve_event_conversation_target(
        self, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        explicit = _normalize_conversation_target(event.get("conversationTarget"))
        if explicit is not None:
            return explicit
        mission_id = event.get("missionId")
        if isinstance(mission_id, int):
            mission = await self.database.get_mission(mission_id)
            target = _normalize_conversation_target(
                mission.get("conversation_target") if mission is not None else None
            )
            if target is not None:
                return target
        task_id = event.get("taskId")
        if isinstance(task_id, int):
            task = await self.database.get_task_blueprint(task_id)
            target = _normalize_conversation_target(
                task.get("conversation_target") if task is not None else None
            )
            if target is not None:
                return target
        return None

    def _task_inbox_notification_event_type(
        self,
        item: DashboardTaskInboxItemView,
        *,
        missions_by_id: dict[int, MissionView],
    ) -> str | None:
        if item.kind in {"approval_required", "approval_orphaned"}:
            return "ops/inbox/approval-required"
        if item.kind == "mission_offline":
            return "ops/inbox/lane-offline"
        if item.kind == "mission_failed":
            mission = missions_by_id.get(item.mission_id or -1)
            if mission is not None and mission.auto_recover:
                if mission.failure_count < mission.auto_recover_limit:
                    return None
            return "ops/inbox/mission-failed"
        if item.kind == "mission_blocked":
            return "ops/inbox/mission-blocked"
        if item.kind == "checkpoint_ready":
            return "ops/inbox/checkpoint-ready"
        if item.kind == "continuity_fragile":
            return "ops/inbox/continuity-fragile"
        if item.kind == "reflex_armed":
            return "ops/inbox/reflex-armed"
        if item.kind == "task_due":
            return "ops/inbox/task-due"
        if item.kind == "task_attention":
            return "ops/inbox/task-attention"
        if item.kind == "playbook_attention":
            return "ops/inbox/playbook-failed"
        return None

    async def _publish_derived_task_inbox_notifications(
        self,
        *,
        task_blueprints: list[TaskBlueprintView] | None = None,
        missions: list[MissionView] | None = None,
        instances: list[InstanceView] | None = None,
        playbooks: list[PlaybookView] | None = None,
    ) -> None:
        current_tasks = (
            task_blueprints
            if task_blueprints is not None
            else await self.list_task_blueprint_views()
        )
        current_missions = missions if missions is not None else await self.missions.list_views()
        current_instances = instances if instances is not None else await self.manager.list_views()
        current_playbooks = (
            playbooks
            if playbooks is not None
            else [PlaybookView.model_validate(row) for row in await self.database.list_playbooks()]
        )
        task_views = _build_task_views(
            instances=current_instances,
            missions=current_missions,
            projects=[],
            task_blueprints=current_tasks,
            skill_pins=[],
            integrations=[],
        )
        inbox_items = _build_task_inbox_items(
            instances=current_instances,
            missions=current_missions,
            tasks=task_views,
            playbooks=current_playbooks,
            projects=[],
            integrations=await self.list_integration_views(),
        )
        missions_by_id = {mission.id: mission for mission in current_missions}
        active_signatures: dict[str, str] = {}
        for item in inbox_items:
            event_type = self._task_inbox_notification_event_type(
                item,
                missions_by_id=missions_by_id,
            )
            if event_type is None:
                continue
            signature = json.dumps(
                {
                    "eventType": event_type,
                    "summary": item.summary,
                    "recommendedAction": item.recommended_action,
                    "freshnessMinutes": item.freshness_minutes,
                },
                sort_keys=True,
            )
            active_signatures[item.id] = signature
            if self._notified_inbox_items.get(item.id) == signature:
                continue
            await self._publish_ops_event(
                event_type,
                {
                    "itemId": item.id,
                    "kind": item.kind,
                    "source": item.source,
                    "urgency": item.urgency,
                    "title": item.title,
                    "summary": item.summary,
                    "recommendedAction": item.recommended_action,
                    "jumpLabel": item.jump_label,
                    "laneLabel": item.lane_label,
                    "projectLabel": item.project_label,
                    "missionId": item.mission_id,
                    "taskId": item.task_id,
                    "instanceId": item.instance_id,
                    "requestId": item.request_id,
                    "freshnessMinutes": item.freshness_minutes,
                },
            )
            self._notified_inbox_items[item.id] = signature

        stale_ids = set(self._notified_inbox_items) - set(active_signatures)
        for item_id in stale_ids:
            self._notified_inbox_items.pop(item_id, None)

    def _get_json_provider_url(
        self,
        target: str,
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> object | None:
        headers: dict[str, str] = {}
        if secret_header_name and secret_token:
            headers[str(secret_header_name)] = str(secret_token)
        request = Request(
            target,
            headers=headers,
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Provider returned HTTP {response.status}")
                response_body = response.read().strip()
                if not response_body:
                    return {"status": response.status}
                try:
                    return json.loads(response_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return {"status": response.status}
        except HTTPError as exc:
            raise RuntimeError(_http_error_message("Provider returned HTTP", exc)) from exc
        except URLError as exc:
            raise RuntimeError(f"Provider request failed: {exc.reason}") from exc

    def _request_json_provider_url(
        self,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> object | None:
        headers: dict[str, str] = {}
        body: bytes | None = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if secret_header_name and secret_token:
            headers[str(secret_header_name)] = str(secret_token)
        request = Request(
            target,
            data=body,
            headers=headers,
            method=str(method or "GET").upper(),
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Provider returned HTTP {response.status}")
                response_body = response.read().strip()
                if not response_body:
                    return {"status": response.status}
                try:
                    return json.loads(response_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return {"status": response.status}
        except HTTPError as exc:
            raise RuntimeError(_http_error_message("Provider returned HTTP", exc)) from exc
        except URLError as exc:
            raise RuntimeError(f"Provider request failed: {exc.reason}") from exc

    def _post_json_webhook(
        self,
        target: str,
        payload: dict[str, Any],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object | None:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if secret_header_name and secret_token:
            headers[str(secret_header_name)] = str(secret_token)
        request = Request(
            target,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Webhook returned {response.status}")
                response_body = response.read().strip()
                if not response_body:
                    return {"status": response.status}
                try:
                    return json.loads(response_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return {"status": response.status}
        except HTTPError as exc:
            raise RuntimeError(_http_error_message("Webhook returned", exc)) from exc
        except URLError as exc:
            raise RuntimeError(f"Webhook failed: {exc.reason}") from exc

    def _post_slack_form(
        self,
        target: str,
        payload: dict[str, Any],
        *,
        secret_token: str,
    ) -> dict[str, Any]:
        body = urlencode(payload).encode("utf-8")
        request = Request(
            target,
            data=body,
            headers={
                "Authorization": _slack_bearer_token(secret_token),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Slack API returned HTTP {response.status}")
                response_body = response.read().strip()
        except HTTPError as exc:
            raise RuntimeError(_http_error_message("Slack API returned HTTP", exc)) from exc
        except URLError as exc:
            raise RuntimeError(f"Slack API failed: {exc.reason}") from exc
        try:
            result = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Slack API returned a non-JSON response.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-object response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        return result

    def _download_slack_media_url(self, media_url: str) -> bytes:
        if self.canvas_state_dir is not None:
            local_path = resolve_canvas_http_path_to_local_path(
                media_url,
                state_dir=self.canvas_state_dir,
            )
            if local_path is not None and local_path.is_file():
                return local_path.read_bytes()
        request = Request(media_url, method="GET")
        try:
            with urlopen(request, timeout=30) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Media URL returned HTTP {response.status}")
                return response.read()
        except HTTPError as exc:
            raise RuntimeError(_http_error_message("Media URL returned HTTP", exc)) from exc
        except URLError as exc:
            raise RuntimeError(f"Media URL failed: {exc.reason}") from exc

    def _upload_slack_file_bytes(
        self,
        *,
        upload_url: str,
        file_bytes: bytes,
    ) -> None:
        request = Request(
            upload_url,
            data=file_bytes,
            headers={"Content-Type": "application/octet-stream"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Slack upload URL returned HTTP {response.status}")
        except HTTPError as exc:
            raise RuntimeError(
                _http_error_message("Slack upload URL returned HTTP", exc)
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"Slack upload URL failed: {exc.reason}") from exc

    def _upload_slack_media_files(
        self,
        *,
        route: dict[str, Any],
        media_urls: list[str],
        channel_id: str,
        initial_comment: str,
        thread_id: str | None,
        secret_token: str,
    ) -> list[str]:
        files: list[dict[str, str]] = []
        for index, media_url in enumerate(media_urls, start=1):
            filename = _slack_media_filename(media_url, index)
            file_bytes = self._download_slack_media_url(media_url)
            ticket = self._post_slack_form(
                _slack_api_endpoint(str(route.get("target") or ""), "files.getUploadURLExternal"),
                {
                    "filename": filename,
                    "length": str(len(file_bytes)),
                },
                secret_token=secret_token,
            )
            upload_url = str(ticket.get("upload_url") or "").strip()
            file_id = str(ticket.get("file_id") or "").strip()
            if not upload_url or not file_id:
                raise RuntimeError("Slack upload URL response is missing upload_url or file_id.")
            self._upload_slack_file_bytes(
                upload_url=upload_url,
                file_bytes=file_bytes,
            )
            files.append({"id": file_id, "title": filename})
        complete_payload: dict[str, Any] = {
            "files": json.dumps(files),
            "channel_id": channel_id,
        }
        if initial_comment:
            complete_payload["initial_comment"] = initial_comment
        if thread_id:
            complete_payload["thread_ts"] = thread_id
        self._post_slack_form(
            _slack_api_endpoint(str(route.get("target") or ""), "files.completeUploadExternal"),
            complete_payload,
            secret_token=secret_token,
        )
        return [file["id"] for file in files]

    def _post_slack_provider_event(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> dict[str, object]:
        conversation_target = _normalize_conversation_target(event.get("conversationTarget"))
        channel_id = _slack_channel_id(
            str(event.get("to") or (conversation_target or {}).get("peer_id") or "")
        )
        if channel_id is None:
            raise RuntimeError("Slack route is missing a channel target.")
        if event_type == "gateway/poll":
            text = _format_direct_channel_poll_message(
                question=str(event.get("question") or event.get("summary") or ""),
                options=[
                    str(option)
                    for option in event.get("options", [])
                    if str(option).strip()
                ],
                max_selections=_optional_int_payload_value(event, "maxSelections"),
                duration_seconds=_optional_int_payload_value(event, "durationSeconds"),
                duration_hours=_optional_int_payload_value(event, "durationHours"),
                silent=_optional_bool_payload_value(event, "silent"),
                is_anonymous=_optional_bool_payload_value(event, "isAnonymous"),
            )
        else:
            text = str(event.get("message") or "").strip()
        if not text:
            raise RuntimeError("Slack route is missing message text.")
        raw_media_urls = event.get("mediaUrls")
        media_urls = _normalize_direct_channel_media_urls(
            media_url=event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None,
            media_urls=(
                [str(media_url) for media_url in raw_media_urls]
                if isinstance(raw_media_urls, list)
                else None
            ),
        )
        thread_id = str(event.get("replyToId") or event.get("threadId") or "").strip()
        if media_urls and event_type == "gateway/send":
            media_ids = self._upload_slack_media_files(
                route=route,
                media_urls=media_urls,
                channel_id=channel_id,
                initial_comment=text,
                thread_id=thread_id or None,
                secret_token=_slack_bearer_token(secret_token),
            )
            return {
                "runtime": "native-provider-backed",
                "messageId": media_ids[0],
                "chatId": channel_id,
                "channelId": channel_id,
                "mediaIds": media_ids,
                "mediaUrls": media_urls,
            }
        payload: dict[str, Any] = {
            "channel": channel_id,
            "text": text,
        }
        if thread_id:
            payload["thread_ts"] = thread_id
        if media_urls:
            blocks: list[dict[str, Any]] = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text[:3000]},
                }
            ]
            blocks.extend(
                {
                    "type": "image",
                    "image_url": media_url,
                    "alt_text": f"OpenZues media {index}",
                }
                for index, media_url in enumerate(media_urls, start=1)
            )
            payload["blocks"] = blocks
        result = self._post_json_webhook(
            _slack_api_endpoint(str(route.get("target") or ""), "chat.postMessage"),
            payload,
            secret_header_name="Authorization",
            secret_token=_slack_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("Slack API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("error") or "unknown_error")
            raise RuntimeError(f"Slack API returned {error}.")
        message_id = _slack_message_id(result)
        if message_id is None:
            raise RuntimeError("Slack API response did not include a message timestamp.")
        delivered_channel = _slack_channel_from_result(result, channel_id)
        native_result: dict[str, object] = {
            "runtime": "native-provider-backed",
            "messageId": message_id,
            "chatId": delivered_channel,
            "channelId": delivered_channel,
        }
        if event_type == "gateway/poll":
            native_result["conversationId"] = delivered_channel
            native_result["pollId"] = message_id
        if media_urls:
            native_result["mediaUrls"] = media_urls
        return native_result

    def _post_telegram_provider_event(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> dict[str, object]:
        conversation_target = _normalize_conversation_target(event.get("conversationTarget"))
        parsed_target = _parse_telegram_delivery_target(
            str(event.get("to") or (conversation_target or {}).get("peer_id") or "")
        )
        chat_id = str(parsed_target.get("chatId") or "").strip() or None
        if chat_id is None:
            raise RuntimeError("Telegram route is missing a chat target.")
        token = _telegram_bot_token(secret_token)
        thread_id = str(event.get("threadId") or parsed_target.get("threadId") or "").strip()
        reply_to_id = str(event.get("replyToId") or "").strip()
        silent = _optional_bool_payload_value(event, "silent")
        force_document = _optional_bool_payload_value(event, "forceDocument") is True
        if event_type == "gateway/poll":
            question = str(event.get("question") or event.get("summary") or "").strip()
            options = [str(option).strip() for option in event.get("options", [])]
            options = [option for option in options if option]
            _validate_direct_channel_poll_shape(question, options)
            _validate_direct_channel_poll_option_count("telegram", options)
            _validate_direct_channel_poll_max_selections(
                options,
                _optional_int_payload_value(event, "maxSelections"),
            )
            duration_seconds = _optional_int_payload_value(event, "durationSeconds")
            duration_hours = _optional_int_payload_value(event, "durationHours")
            _validate_direct_channel_poll_duration_exclusivity(
                duration_seconds=duration_seconds,
                duration_hours=duration_hours,
            )
            _validate_telegram_poll_duration_options(
                duration_seconds=duration_seconds,
                duration_hours=duration_hours,
            )
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "question": question,
                "options": options,
            }
            if _optional_bool_payload_value(event, "isAnonymous") is not None:
                payload["is_anonymous"] = _optional_bool_payload_value(
                    event,
                    "isAnonymous",
                )
            if duration_seconds is not None:
                payload["open_period"] = duration_seconds
            if silent is not None:
                payload["disable_notification"] = silent
            if thread_id:
                payload["message_thread_id"] = thread_id
            result = self._post_json_webhook(
                _telegram_api_endpoint(str(route.get("target") or ""), token, "sendPoll"),
                payload,
            )
        else:
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            text = str(event.get("message") or "").strip()
            payload = {"chat_id": chat_id}
            if thread_id:
                payload["message_thread_id"] = thread_id
            if reply_to_id:
                payload["reply_to_message_id"] = reply_to_id
            if silent is not None:
                payload["disable_notification"] = silent
            if len(media_urls) > 1:
                media: list[dict[str, str]] = []
                for index, media_url in enumerate(media_urls[:10]):
                    item = {
                        "type": "document" if force_document else "photo",
                        "media": media_url,
                    }
                    if index == 0 and text:
                        item["caption"] = text[:1024]
                    media.append(item)
                payload["media"] = media
                result = self._post_json_webhook(
                    _telegram_api_endpoint(
                        str(route.get("target") or ""),
                        token,
                        "sendMediaGroup",
                    ),
                    payload,
                )
            elif media_urls:
                payload["document" if force_document else "photo"] = media_urls[0]
                if text:
                    payload["caption"] = text[:1024]
                result = self._post_json_webhook(
                    _telegram_api_endpoint(
                        str(route.get("target") or ""),
                        token,
                        "sendDocument" if force_document else "sendPhoto",
                    ),
                    payload,
                )
            else:
                payload["text"] = text
                result = self._post_json_webhook(
                    _telegram_api_endpoint(
                        str(route.get("target") or ""),
                        token,
                        "sendMessage",
                    ),
                    payload,
                )
        if not isinstance(result, dict):
            raise RuntimeError("Telegram API returned a non-JSON response.")
        if result.get("ok") is False:
            error = str(result.get("description") or result.get("error_code") or "unknown")
            raise RuntimeError(f"Telegram API returned {error}.")
        message_id = _telegram_message_id(result)
        if message_id is None:
            raise RuntimeError("Telegram API response did not include a message id.")
        delivered_chat = _telegram_chat_from_result(result, chat_id)
        native_result: dict[str, object] = {
            "runtime": "native-provider-backed",
            "messageId": message_id,
            "chatId": delivered_chat,
            "channelId": delivered_chat,
        }
        poll_id = _telegram_poll_id(result)
        if poll_id is not None:
            native_result["pollId"] = poll_id
            native_result["conversationId"] = delivered_chat
        if event_type == "gateway/send":
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            if media_urls:
                native_result["mediaUrls"] = media_urls
                media_ids = _telegram_media_ids(result)
                if media_ids:
                    native_result["mediaIds"] = media_ids
        return native_result

    def _post_discord_provider_event(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> dict[str, object]:
        del secret_token
        conversation_target = _normalize_conversation_target(event.get("conversationTarget"))
        fallback_channel = str(
            event.get("to") or (conversation_target or {}).get("peer_id") or ""
        ).strip()
        thread_id = str(event.get("threadId") or "").strip()
        reply_to_id = str(event.get("replyToId") or "").strip()
        silent = _optional_bool_payload_value(event, "silent")
        if event_type == "gateway/poll":
            question = str(event.get("question") or event.get("summary") or "").strip()
            options = [str(option).strip() for option in event.get("options", [])]
            options = [option for option in options if option]
            _validate_direct_channel_poll_shape(question, options)
            _validate_direct_channel_poll_option_count("discord", options)
            max_selections = _optional_int_payload_value(event, "maxSelections")
            _validate_direct_channel_poll_max_selections(options, max_selections)
            _validate_direct_channel_poll_duration_exclusivity(
                duration_seconds=_optional_int_payload_value(event, "durationSeconds"),
                duration_hours=_optional_int_payload_value(event, "durationHours"),
            )
            payload: dict[str, Any] = {
                "poll": {
                    "question": {
                        "text": question,
                    },
                    "answers": [
                        {"poll_media": {"text": option}}
                        for option in options
                    ],
                    "duration": _discord_poll_duration_hours(event),
                    "allow_multiselect": (max_selections or 1) > 1,
                }
            }
        else:
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            text = str(event.get("message") or "").strip()
            payload = {"content": text[:2000] if text else ""}
            if media_urls:
                payload["embeds"] = [
                    {"image": {"url": media_url}}
                    for media_url in media_urls[:10]
                ]
        if silent is True:
            payload["flags"] = int(payload.get("flags") or 0) | (1 << 12)
        if reply_to_id and event_type == "gateway/send":
            payload["message_reference"] = {
                "message_id": reply_to_id,
                "fail_if_not_exists": False,
            }
        if thread_id:
            payload["thread_id"] = thread_id
        result = self._post_json_webhook(
            _discord_webhook_url(str(route.get("target") or "")),
            payload,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Discord webhook returned a non-JSON response.")
        message_id = _discord_message_id(result)
        if message_id is None:
            raise RuntimeError("Discord webhook response did not include a message id.")
        delivered_channel = _discord_channel_id(result, fallback_channel)
        native_result: dict[str, object] = {
            "runtime": "native-provider-backed",
            "messageId": message_id,
            "chatId": delivered_channel,
            "channelId": delivered_channel,
        }
        if event_type == "gateway/poll":
            native_result["conversationId"] = delivered_channel
            native_result["pollId"] = message_id
        else:
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            if media_urls:
                native_result["mediaUrls"] = media_urls
        return native_result

    def _post_whatsapp_provider_event(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> dict[str, object]:
        conversation_target = _normalize_conversation_target(event.get("conversationTarget"))
        recipient_id = _whatsapp_recipient_id(
            str(event.get("to") or (conversation_target or {}).get("peer_id") or "")
        )
        if recipient_id is None:
            raise RuntimeError("WhatsApp route is missing a recipient target.")
        if event_type == "gateway/poll":
            question = str(event.get("question") or event.get("summary") or "").strip()
            options = [str(option).strip() for option in event.get("options", [])]
            options = [option for option in options if option]
            _validate_direct_channel_poll_shape(question, options)
            _validate_direct_channel_poll_option_count("whatsapp", options)
            _validate_direct_channel_poll_max_selections(
                options,
                _optional_int_payload_value(event, "maxSelections"),
            )
            _validate_direct_channel_poll_duration_exclusivity(
                duration_seconds=_optional_int_payload_value(event, "durationSeconds"),
                duration_hours=_optional_int_payload_value(event, "durationHours"),
            )
            options = options[:3]
            payload: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": question[:1024]},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {
                                    "id": f"option-{index}",
                                    "title": option[:20],
                                },
                            }
                            for index, option in enumerate(options, start=1)
                        ],
                    },
                },
            }
        else:
            reply_to_id = str(event.get("replyToId") or "").strip()
            force_document = _optional_bool_payload_value(event, "forceDocument") is True
            gif_playback = _optional_bool_payload_value(event, "gifPlayback") is True
            media_payload_key = (
                "document" if force_document else "video" if gif_playback else "image"
            )
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            text = str(event.get("message") or "").strip()
            if media_urls:
                if len(media_urls) > 1:
                    endpoint = _whatsapp_messages_endpoint(str(route.get("target") or ""))
                    bearer_token = _whatsapp_bearer_token(secret_token)
                    message_ids: list[str] = []
                    delivered_contact = recipient_id
                    for index, media_url in enumerate(media_urls):
                        media_payload: dict[str, Any] = {"link": media_url}
                        if index == 0 and text:
                            media_payload["caption"] = text[:1024]
                        message_payload: dict[str, Any] = {
                            "messaging_product": "whatsapp",
                            "to": recipient_id,
                            "type": media_payload_key,
                            media_payload_key: media_payload,
                        }
                        if index == 0:
                            _whatsapp_apply_reply_context(message_payload, reply_to_id)
                        result = self._post_json_webhook(
                            endpoint,
                            message_payload,
                            secret_header_name="Authorization",
                            secret_token=bearer_token,
                        )
                        if not isinstance(result, dict):
                            raise RuntimeError("WhatsApp API returned a non-JSON response.")
                        if result.get("error"):
                            error = result.get("error")
                            if isinstance(error, dict):
                                detail = str(
                                    error.get("message") or error.get("code") or "unknown"
                                )
                            else:
                                detail = str(error)
                            raise RuntimeError(f"WhatsApp API returned {detail}.")
                        message_id = _whatsapp_message_id(result)
                        if message_id is None:
                            raise RuntimeError(
                                "WhatsApp API response did not include a message id."
                            )
                        message_ids.append(message_id)
                        delivered_contact = _whatsapp_contact_id(result, delivered_contact)
                    return {
                        "runtime": "native-provider-backed",
                        "messageId": message_ids[-1],
                        "chatId": delivered_contact,
                        "channelId": delivered_contact,
                        "mediaIds": message_ids,
                        "mediaUrls": media_urls,
                    }
                media_payload = {
                    "link": media_urls[0],
                }
                if text:
                    media_payload["caption"] = text[:1024]
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": media_payload_key,
                    media_payload_key: media_payload,
                }
                _whatsapp_apply_reply_context(payload, reply_to_id)
            else:
                text_chunks = _whatsapp_text_chunks(text)
                if len(text_chunks) > 1:
                    endpoint = _whatsapp_messages_endpoint(str(route.get("target") or ""))
                    bearer_token = _whatsapp_bearer_token(secret_token)
                    message_id = ""
                    delivered_contact = recipient_id
                    for chunk in text_chunks:
                        message_payload = {
                            "messaging_product": "whatsapp",
                            "to": recipient_id,
                            "type": "text",
                            "text": {"body": chunk},
                        }
                        _whatsapp_apply_reply_context(message_payload, reply_to_id)
                        result = self._post_json_webhook(
                            endpoint,
                            message_payload,
                            secret_header_name="Authorization",
                            secret_token=bearer_token,
                        )
                        if not isinstance(result, dict):
                            raise RuntimeError("WhatsApp API returned a non-JSON response.")
                        if result.get("error"):
                            error = result.get("error")
                            if isinstance(error, dict):
                                detail = str(
                                    error.get("message") or error.get("code") or "unknown"
                                )
                            else:
                                detail = str(error)
                            raise RuntimeError(f"WhatsApp API returned {detail}.")
                        chunk_message_id = _whatsapp_message_id(result)
                        if chunk_message_id is None:
                            raise RuntimeError(
                                "WhatsApp API response did not include a message id."
                            )
                        message_id = chunk_message_id
                        delivered_contact = _whatsapp_contact_id(result, delivered_contact)
                    return {
                        "runtime": "native-provider-backed",
                        "messageId": message_id,
                        "chatId": delivered_contact,
                        "channelId": delivered_contact,
                    }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_id,
                    "type": "text",
                    "text": {"body": text},
                }
                _whatsapp_apply_reply_context(payload, reply_to_id)
        result = self._post_json_webhook(
            _whatsapp_messages_endpoint(str(route.get("target") or "")),
            payload,
            secret_header_name="Authorization",
            secret_token=_whatsapp_bearer_token(secret_token),
        )
        if not isinstance(result, dict):
            raise RuntimeError("WhatsApp API returned a non-JSON response.")
        if result.get("error"):
            error = result.get("error")
            if isinstance(error, dict):
                detail = str(error.get("message") or error.get("code") or "unknown")
            else:
                detail = str(error)
            raise RuntimeError(f"WhatsApp API returned {detail}.")
        message_id = _whatsapp_message_id(result)
        if message_id is None:
            raise RuntimeError("WhatsApp API response did not include a message id.")
        delivered_contact = _whatsapp_contact_id(result, recipient_id)
        native_result: dict[str, object] = {
            "runtime": "native-provider-backed",
            "messageId": message_id,
            "chatId": delivered_contact,
            "channelId": delivered_contact,
        }
        if event_type == "gateway/poll":
            native_result["conversationId"] = delivered_contact
            native_result["pollId"] = message_id
        else:
            raw_media_urls = event.get("mediaUrls")
            media_urls = _normalize_direct_channel_media_urls(
                media_url=(
                    event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None
                ),
                media_urls=(
                    [str(media_url) for media_url in raw_media_urls]
                    if isinstance(raw_media_urls, list)
                    else None
                ),
            )
            if media_urls:
                native_result["mediaUrls"] = media_urls
        return native_result

    def _post_zalo_provider_event(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> dict[str, object]:
        if event_type != "gateway/send":
            raise RuntimeError("Zalo native provider route does not support polls.")
        conversation_target = _normalize_conversation_target(event.get("conversationTarget"))
        chat_id = _zalo_chat_id(
            str(event.get("to") or (conversation_target or {}).get("peer_id") or "")
        )
        if chat_id is None:
            raise RuntimeError("Zalo route is missing a chat target.")
        token = _zalo_bot_token(secret_token)
        text = str(event.get("message") or "").strip()
        raw_media_urls = event.get("mediaUrls")
        media_urls = _normalize_direct_channel_media_urls(
            media_url=event.get("mediaUrl") if isinstance(event.get("mediaUrl"), str) else None,
            media_urls=(
                [str(media_url) for media_url in raw_media_urls]
                if isinstance(raw_media_urls, list)
                else None
            ),
        )
        if media_urls:
            endpoint = _zalo_api_endpoint(str(route.get("target") or ""), token, "sendPhoto")
            message_ids: list[str] = []
            delivered_chat = chat_id
            for index, media_url in enumerate(media_urls):
                payload: dict[str, Any] = {
                    "chat_id": chat_id,
                    "photo": media_url,
                }
                if index == 0 and text:
                    payload["caption"] = text[:2000]
                result = self._post_json_webhook(endpoint, payload)
                if not isinstance(result, dict):
                    raise RuntimeError("Zalo API returned a non-JSON response.")
                if result.get("ok") is False:
                    error = str(
                        result.get("description") or result.get("error_code") or "unknown"
                    )
                    raise RuntimeError(f"Zalo API returned {error}.")
                message_id = _zalo_message_id(result)
                if message_id is None:
                    raise RuntimeError("Zalo API response did not include a message id.")
                message_ids.append(message_id)
                delivered_chat = _zalo_chat_from_result(result, delivered_chat)
            return {
                "runtime": "native-provider-backed",
                "messageId": message_ids[-1],
                "chatId": delivered_chat,
                "channelId": delivered_chat,
                "mediaIds": message_ids,
                "mediaUrls": media_urls,
            }
        endpoint = _zalo_api_endpoint(str(route.get("target") or ""), token, "sendMessage")
        message_id = ""
        delivered_chat = chat_id
        for chunk in _zalo_text_chunks(text):
            result = self._post_json_webhook(
                endpoint,
                {
                    "chat_id": chat_id,
                    "text": chunk,
                },
            )
            if not isinstance(result, dict):
                raise RuntimeError("Zalo API returned a non-JSON response.")
            if result.get("ok") is False:
                error = str(result.get("description") or result.get("error_code") or "unknown")
                raise RuntimeError(f"Zalo API returned {error}.")
            chunk_message_id = _zalo_message_id(result)
            if chunk_message_id is None:
                raise RuntimeError("Zalo API response did not include a message id.")
            message_id = chunk_message_id
            delivered_chat = _zalo_chat_from_result(result, delivered_chat)
        return {
            "runtime": "native-provider-backed",
            "messageId": message_id,
            "chatId": delivered_chat,
            "channelId": delivered_chat,
        }

    def _post_webhook(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> object | None:
        return self._post_json_webhook(
            str(route["target"]),
            {"eventType": event_type, "payload": event},
            secret_header_name=(
                str(route.get("secret_header_name"))
                if route.get("secret_header_name")
                else None
            ),
            secret_token=secret_token,
        )

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
