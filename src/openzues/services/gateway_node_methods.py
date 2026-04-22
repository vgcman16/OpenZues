from __future__ import annotations

import asyncio
import json
import re
import secrets
import time
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote, urlsplit, urlunsplit

from openzues.database import Database, utcnow
from openzues.schemas import (
    GatewayNodePendingActionAckView,
    GatewayNodePendingActionPullView,
    GatewayNodePendingWorkDrainView,
    GatewayNodePendingWorkEnqueueView,
    IntegrationView,
    NotificationRouteView,
)
from openzues.services.gateway_agent_files import GatewayAgentFilesService
from openzues.services.gateway_agents import GatewayAgentsService
from openzues.services.gateway_channels import GatewayChannelsService
from openzues.services.gateway_commands import GatewayCommandsService
from openzues.services.gateway_config import GatewayConfigService
from openzues.services.gateway_config_schema import GatewayConfigSchemaService
from openzues.services.gateway_cron import GatewayCronService, build_gateway_cron_task_blueprint
from openzues.services.gateway_health import GatewayHealthService
from openzues.services.gateway_identity import GatewayIdentityService
from openzues.services.gateway_last_heartbeat import GatewayLastHeartbeatService
from openzues.services.gateway_logs import GatewayLogsService, GatewayLogsUnavailableError
from openzues.services.gateway_method_policy import (
    ADMIN_GATEWAY_METHOD_SCOPE,
    TALK_SECRETS_GATEWAY_METHOD_SCOPE,
)
from openzues.services.gateway_models import GatewayModelsService
from openzues.services.gateway_node_command_policy import (
    is_node_command_allowed,
    normalize_declared_node_commands,
    resolve_node_command_allowlist,
)
from openzues.services.gateway_node_pairing import (
    GatewayNodePairingService,
    GatewayPairedNode,
)
from openzues.services.gateway_node_pending_work import (
    NodePendingWorkPriority,
    NodePendingWorkType,
)
from openzues.services.gateway_node_registry import GatewayNodeRegistry, KnownNode
from openzues.services.gateway_session_compaction import (
    GatewaySessionCompactionService,
    GatewaySessionCompactionUnavailableError,
)
from openzues.services.gateway_sessions import GatewaySessionsService
from openzues.services.gateway_skill_bins import GatewaySkillBinsService
from openzues.services.gateway_skill_catalog import GatewaySkillCatalogService
from openzues.services.gateway_skill_clawhub import (
    GatewaySkillClawHubService,
    GatewaySkillClawHubUnavailableError,
)
from openzues.services.gateway_skill_config import GatewaySkillConfigService
from openzues.services.gateway_skill_install import GatewaySkillInstallService
from openzues.services.gateway_skill_status import GatewaySkillStatusService
from openzues.services.gateway_system_presence import GatewaySystemPresenceService
from openzues.services.gateway_talk_config import GatewayTalkConfigService
from openzues.services.gateway_talk_mode import GatewayTalkModeService
from openzues.services.gateway_tools_catalog import GatewayToolsCatalogService
from openzues.services.gateway_tts import GatewayTtsService, normalize_tts_provider
from openzues.services.gateway_tts_runtime import (
    GatewayTtsRuntimeService,
    GatewayTtsRuntimeUnavailableError,
)
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.gateway_wake import GatewayWakeService
from openzues.services.gateway_wizard import GatewayWizardService
from openzues.services.hub import BroadcastHub
from openzues.services.session_keys import (
    classify_session_key_shape,
    parse_agent_session_key,
    parse_thread_session_suffix,
    resolve_agent_id_from_session_key,
    resolve_thread_session_keys,
    session_key_lookup_aliases,
)

_NODE_PENDING_WORK_TYPES = {"status.request", "location.request"}
_NODE_PENDING_WORK_PRIORITIES = {"default", "normal", "high"}
_CANVAS_CAPABILITY_PATH_PREFIX = "/__openclaw__/cap"
_CANVAS_CAPABILITY_TTL_MS = 10 * 60_000
_SESSION_LABEL_MAX_LENGTH = 512
_SESSION_PATCH_RESPONSE_USAGE_VALUES = {"full", "off", "on", "tokens"}
_SESSION_PATCH_SUBAGENT_ROLE_VALUES = {"leaf", "orchestrator"}
_SESSION_PATCH_SUBAGENT_CONTROL_SCOPE_VALUES = {"children", "none"}
_SESSION_PATCH_SEND_POLICY_VALUES = {"allow", "deny"}
_SESSION_PATCH_GROUP_ACTIVATION_VALUES = {"always", "mention"}
_INPUT_PROVENANCE_KIND_VALUES = {"external_user", "inter_session", "internal_system"}
_DEFAULT_SESSION_DELETE_ARCHIVE_RETENTION_MS = 30 * 24 * 60 * 60 * 1000
_KNOWN_GATEWAY_CHAT_CHANNEL_ORDER = ("discord", "slack", "telegram", "whatsapp")
_KNOWN_GATEWAY_CHAT_CHANNEL_IDS = set(_KNOWN_GATEWAY_CHAT_CHANNEL_ORDER)
_YYYY_MM_DD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UTC_OFFSET_RE = re.compile(r"^UTC[+-]\d{1,2}(?::[0-5]\d)?$")
_NODE_ONLY_METHODS = {
    "node.canvas.capability.refresh",
    "node.event",
    "node.invoke.result",
    "node.pending.pull",
    "node.pending.ack",
    "node.pending.drain",
}


@dataclass(frozen=True, slots=True)
class GatewayNodeMethodError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class GatewayNodeMethodRequester:
    node_id: str | None = None
    caller_scopes: tuple[str, ...] | None = None
    client_id: str | None = None


@dataclass(frozen=True, slots=True)
class GatewayTrackedChatRun:
    run_id: str
    session_key: str
    started_at_ms: int


@dataclass(frozen=True, slots=True)
class GatewayNodeWakeAttempt:
    attempted: bool = False
    available: bool = False
    connected: bool = False
    path: str | None = None
    duration_ms: int = 0


def _coerce_wake_attempt(value: object) -> GatewayNodeWakeAttempt:
    if isinstance(value, GatewayNodeWakeAttempt):
        return value
    if isinstance(value, bool):
        return GatewayNodeWakeAttempt(
            attempted=value,
            available=value,
            connected=False,
            path="legacy-bool" if value else None,
        )

    def _raw_field(name: str) -> object | None:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    attempted_value = _raw_field("attempted")
    available_value = _raw_field("available")
    connected_value = _raw_field("connected")
    path_value = _raw_field("path")
    duration_value = _raw_field("durationMs")
    if duration_value is None:
        duration_value = _raw_field("duration_ms")

    attempted = attempted_value if isinstance(attempted_value, bool) else None
    available = available_value if isinstance(available_value, bool) else None
    connected = connected_value if isinstance(connected_value, bool) else None
    duration_ms = (
        max(0, int(duration_value))
        if isinstance(duration_value, int | float) and not isinstance(duration_value, bool)
        else 0
    )
    path = path_value.strip() if isinstance(path_value, str) and path_value.strip() else None

    resolved_attempted = (
        attempted
        if attempted is not None
        else bool((available if available is not None else False) or (connected if connected else False))
    )
    resolved_available = (
        available
        if available is not None
        else bool(resolved_attempted or (connected if connected else False))
    )
    return GatewayNodeWakeAttempt(
        attempted=resolved_attempted,
        available=resolved_available,
        connected=bool(connected),
        path=path,
        duration_ms=duration_ms,
    )


def _wake_attempt_available(attempt: GatewayNodeWakeAttempt) -> bool:
    return attempt.available


def _wake_attempt_details(attempt: GatewayNodeWakeAttempt | None) -> dict[str, object] | None:
    if attempt is None or (
        not attempt.attempted
        and not attempt.available
        and not attempt.connected
        and attempt.path is None
        and attempt.duration_ms == 0
    ):
        return None
    payload: dict[str, object] = {
        "attempted": attempt.attempted,
        "available": attempt.available,
        "connected": attempt.connected,
        "durationMs": attempt.duration_ms,
    }
    if attempt.path is not None:
        payload["path"] = attempt.path
    return payload


def _wake_attempt_with_connection(
    attempt: GatewayNodeWakeAttempt | None,
    *,
    connected: bool,
) -> GatewayNodeWakeAttempt | None:
    if attempt is None or attempt.connected == connected:
        return attempt
    path = attempt.path
    if connected and path in {None, "legacy-bool", "not-connected"}:
        path = "connected"
    if not connected and path == "already-connected":
        path = "not-connected"
    return replace(attempt, connected=connected, path=path)


class GatewayNodeMethodService:
    def __init__(
        self,
        registry: GatewayNodeRegistry,
        *,
        database: Database | None = None,
        hub: BroadcastHub | None = None,
        agents_service: GatewayAgentsService | None = None,
        agent_files_service: GatewayAgentFilesService | None = None,
        pairing_service: GatewayNodePairingService | None = None,
        channels_service: GatewayChannelsService | None = None,
        list_integration_views: Callable[[], Awaitable[list[IntegrationView]]] | None = None,
        list_notification_route_views: (
            Callable[[], Awaitable[list[NotificationRouteView]]] | None
        ) = None,
        commands_service: GatewayCommandsService | None = None,
        config_service: GatewayConfigService | None = None,
        config_schema_service: GatewayConfigSchemaService | None = None,
        cron_service: GatewayCronService | None = None,
        create_task_blueprint: Callable[..., Awaitable[object]] | None = None,
        run_task_blueprint_now: Callable[..., Awaitable[object]] | None = None,
        dispatch_cron_system_event_task: Callable[..., Awaitable[str]] | None = None,
        delete_task_blueprint: Callable[[int], Awaitable[None]] | None = None,
        health_service: GatewayHealthService | None = None,
        gateway_identity_service: GatewayIdentityService | None = None,
        last_heartbeat_service: GatewayLastHeartbeatService | None = None,
        logs_service: GatewayLogsService | None = None,
        models_service: GatewayModelsService | None = None,
        sessions_service: GatewaySessionsService | None = None,
        session_compaction_service: GatewaySessionCompactionService | None = None,
        system_presence_service: GatewaySystemPresenceService | None = None,
        talk_config_service: GatewayTalkConfigService | None = None,
        talk_mode_service: GatewayTalkModeService | None = None,
        tts_service: GatewayTtsService | None = None,
        tts_runtime_service: GatewayTtsRuntimeService | None = None,
        tools_catalog_service: GatewayToolsCatalogService | None = None,
        skill_bins_service: GatewaySkillBinsService | None = None,
        skill_catalog_service: GatewaySkillCatalogService | None = None,
        skill_clawhub_service: GatewaySkillClawHubService | None = None,
        skill_config_service: GatewaySkillConfigService | None = None,
        skill_install_service: GatewaySkillInstallService | None = None,
        skill_status_service: GatewaySkillStatusService | None = None,
        send_channel_message_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        send_channel_poll_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        chat_send_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        chat_abort_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        status_service: Callable[[], Awaitable[dict[str, object]]] | None = None,
        runtime_update_tick: Callable[[], Awaitable[bool]] | None = None,
        runtime_update_view: Callable[[], Awaitable[dict[str, object]]] | None = None,
        wizard_service: GatewayWizardService | None = None,
        voicewake_service: GatewayVoiceWakeService | None = None,
        wake_service: GatewayWakeService | None = None,
        set_heartbeats_enabled: Callable[[bool], Awaitable[bool]] | None = None,
        sync: Callable[[], Awaitable[None]] | None = None,
        wake_node: Callable[[str], Awaitable[object]] | None = None,
        probe_secret: Callable[[int], Awaitable[str | None]] | None = None,
    ) -> None:
        self.registry = registry
        self._database = database
        self._hub = hub
        self._agents_service: GatewayAgentsService = agents_service or GatewayAgentsService(
            database=self._database
        )
        self._agent_files_service = agent_files_service
        if self._agent_files_service is None:
            self._agent_files_service = GatewayAgentFilesService(database=self._database)
        self._pairing_service = pairing_service
        self._channels_service = channels_service
        self._list_integration_views = list_integration_views
        self._list_notification_route_views = list_notification_route_views
        self._commands_service = commands_service or GatewayCommandsService()
        self._config_service = config_service
        self._config_schema_service = config_schema_service or GatewayConfigSchemaService()
        self._create_task_blueprint = create_task_blueprint
        self._cron_service = cron_service
        if self._cron_service is None and self._database is not None:
            self._cron_service = GatewayCronService(
                self._database,
                create_task_blueprint=self._create_task_blueprint,
                run_task_blueprint_now=run_task_blueprint_now,
                dispatch_system_event_task=dispatch_cron_system_event_task,
                delete_task_blueprint=delete_task_blueprint,
            )
        self._health_service = health_service or GatewayHealthService()
        self._gateway_identity_service = gateway_identity_service
        self._last_heartbeat_service = last_heartbeat_service
        if self._last_heartbeat_service is None and self._database is not None:
            self._last_heartbeat_service = GatewayLastHeartbeatService(
                self._database,
                registry=registry,
            )
        self._logs_service = logs_service or GatewayLogsService()
        self._models_service = models_service or GatewayModelsService()
        self._sessions_service = sessions_service
        if self._sessions_service is None and self._database is not None:
            self._sessions_service = GatewaySessionsService(self._database)
        self._session_compaction_service = session_compaction_service
        if self._session_compaction_service is None and self._database is not None:
            self._session_compaction_service = GatewaySessionCompactionService(self._database)
        self._system_presence_service = system_presence_service
        if self._system_presence_service is None and self._gateway_identity_service is not None:
            self._system_presence_service = GatewaySystemPresenceService(
                registry,
                gateway_identity_service=self._gateway_identity_service,
            )
        self._talk_config_service = talk_config_service or GatewayTalkConfigService()
        self._talk_mode_service = talk_mode_service or GatewayTalkModeService()
        self._tts_service = tts_service or GatewayTtsService()
        self._tts_runtime_service = tts_runtime_service
        self._tools_catalog_service = tools_catalog_service or GatewayToolsCatalogService()
        self._skill_bins_service = skill_bins_service or GatewaySkillBinsService()
        self._skill_catalog_service = skill_catalog_service or GatewaySkillCatalogService()
        self._skill_clawhub_service = skill_clawhub_service or GatewaySkillClawHubService()
        self._skill_config_service = skill_config_service or GatewaySkillConfigService()
        self._skill_install_service = skill_install_service or GatewaySkillInstallService()
        self._skill_status_service = skill_status_service or GatewaySkillStatusService(
            skill_config_service=self._skill_config_service
        )
        self._send_channel_message_service = send_channel_message_service
        self._send_channel_poll_service = send_channel_poll_service
        self._chat_send_service = chat_send_service
        self._chat_abort_service = chat_abort_service
        self._gateway_chat_run_ids_by_session_key: dict[str, str] = {}
        self._gateway_tracked_chat_runs_by_id: dict[str, GatewayTrackedChatRun] = {}
        self._sleep = sleep or asyncio.sleep
        self._status_service = status_service
        self._runtime_update_tick = runtime_update_tick
        self._runtime_update_view = runtime_update_view
        self._wizard_service = wizard_service
        self._voicewake_service = voicewake_service
        self._wake_service = wake_service
        self._set_heartbeats_enabled = set_heartbeats_enabled
        self._sync = sync
        self._wake_node = wake_node
        self._probe_secret = probe_secret

    async def _wait_for_node_connection(
        self,
        node_id: str,
        *,
        timeout_ms: int = 1_000,
    ) -> bool:
        deadline = time.monotonic() + (max(timeout_ms, 0) / 1000)
        while True:
            if self.registry.get(node_id) is not None:
                return True
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                return self.registry.get(node_id) is not None
            await self._sleep(min(0.05, remaining_seconds))

    async def _request_node_pairing(
        self,
        *,
        node_id: str,
        display_name: str | None,
        platform: str | None,
        version: str | None,
        core_version: str | None,
        ui_version: str | None,
        device_family: str | None,
        model_identifier: str | None,
        caps: list[str] | None,
        commands: list[str] | None,
        remote_ip: str | None,
        silent: bool | None,
        now_ms: int | None,
    ) -> dict[str, object]:
        if self._pairing_service is None:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="node pairing storage unavailable",
                status_code=503,
            )
        request_result = await self._pairing_service.request(
            node_id=node_id,
            display_name=display_name,
            platform=platform,
            version=version,
            core_version=core_version,
            ui_version=ui_version,
            device_family=device_family,
            model_identifier=model_identifier,
            caps=caps,
            commands=commands,
            remote_ip=remote_ip,
            silent=silent,
            now_ms=_timestamp_ms(now_ms),
        )
        if (
            request_result.get("status") == "pending"
            and request_result.get("created") is True
            and isinstance(request_result.get("request"), dict)
        ):
            await self._publish_gateway_event(
                "node.pair.requested",
                cast(dict[str, Any], request_result["request"]),
            )
        return request_result

    async def _stage_scope_upgrade_request(
        self,
        node: KnownNode,
        *,
        paired_node: GatewayPairedNode,
        now_ms: int | None,
    ) -> dict[str, object] | None:
        if self._pairing_service is None or not node.connected:
            return None
        allowlist = resolve_node_command_allowlist(
            platform=node.platform or paired_node.platform,
            device_family=node.device_family or paired_node.device_family,
        )
        live_commands = list(
            normalize_declared_node_commands(
                node.commands,
                allowlist=allowlist,
            )
        )
        approved_commands = set(
            normalize_declared_node_commands(
                paired_node.commands,
                allowlist=allowlist,
            )
        )
        if not live_commands or not any(command not in approved_commands for command in live_commands):
            return None
        return await self._request_node_pairing(
            node_id=node.node_id,
            display_name=node.display_name or paired_node.display_name,
            platform=node.platform or paired_node.platform,
            version=node.version or paired_node.version,
            core_version=node.core_version or paired_node.core_version,
            ui_version=node.ui_version or paired_node.ui_version,
            device_family=node.device_family or paired_node.device_family,
            model_identifier=node.model_identifier or paired_node.model_identifier,
            caps=list(node.caps) if node.caps else list(paired_node.caps),
            commands=live_commands,
            remote_ip=node.remote_ip or paired_node.remote_ip,
            silent=True,
            now_ms=now_ms,
        )

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        requester: GatewayNodeMethodRequester | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        if self._sync is not None:
            await self._sync()

        resolved_method = method.strip()
        payload = _validate_object_params(resolved_method, params)
        resolved_requester = requester or GatewayNodeMethodRequester()

        if resolved_method in _NODE_ONLY_METHODS:
            node_id = self._require_connected_node_identity(
                resolved_method,
                resolved_requester,
            )
        else:
            node_id = None

        if resolved_method == "node.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            timestamp_ms = _timestamp_ms(now_ms)
            known_nodes = self.registry.list_known_nodes()
            known_nodes_by_id = {node.node_id: node for node in known_nodes}
            node_payloads: dict[str, dict[str, Any]] = {
                node_id: _known_node_payload(node)
                for node_id, node in known_nodes_by_id.items()
            }
            if self._pairing_service is not None:
                for paired_node in await self._pairing_service.list_paired_nodes():
                    existing_node = known_nodes_by_id.get(paired_node.node_id)
                    if existing_node is not None:
                        await self._stage_scope_upgrade_request(
                            existing_node,
                            paired_node=paired_node,
                            now_ms=now_ms,
                        )
                    paired_payload = _known_paired_node_payload(paired_node)
                    existing = node_payloads.get(paired_node.node_id)
                    node_payloads[paired_node.node_id] = (
                        paired_payload
                        if existing is None
                        else _merge_known_node_payload(paired_payload, existing)
                    )
            return {
                "ts": timestamp_ms,
                "nodes": sorted(node_payloads.values(), key=_known_node_sort_key_from_payload),
            }

        if resolved_method == "voicewake.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._voicewake_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="voice wake config unavailable",
                    status_code=503,
                )
            config = self._voicewake_service.load()
            return {"triggers": list(config.triggers)}

        if resolved_method == "talk.config":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("includeSecrets",))
            include_secrets = bool(
                _optional_bool(payload.get("includeSecrets"), label="includeSecrets")
            )
            if (
                include_secrets
                and resolved_requester.caller_scopes is not None
                and TALK_SECRETS_GATEWAY_METHOD_SCOPE not in resolved_requester.caller_scopes
            ):
                raise ValueError(f"missing scope: {TALK_SECRETS_GATEWAY_METHOD_SCOPE}")
            return self._talk_config_service.build_snapshot(include_secrets=include_secrets)

        if resolved_method == "tts.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._tts_service.build_status()

        if resolved_method == "tts.providers":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._tts_service.build_provider_catalog()

        if resolved_method == "commands.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "includeArgs", "provider", "scope"),
            )
            scope = _optional_enum_value(
                payload.get("scope"),
                label="scope",
                allowed_values={"both", "native", "text"},
            )
            return self._commands_service.build_catalog(
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId"),
                include_args=bool(
                    _optional_bool(payload.get("includeArgs"), label="includeArgs")
                    if "includeArgs" in payload
                    else True
                ),
                provider=_optional_non_empty_string(payload.get("provider"), label="provider"),
                scope=cast(Literal["both", "native", "text"], scope or "both"),
            )

        if resolved_method == "status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._status_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="status is unavailable until operator status is wired",
                    status_code=503,
                )
            return await self._status_service()

        if resolved_method == "usage.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return _build_usage_status_payload(
                model_catalog=await self._models_service.build_catalog(),
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "usage.cost":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("startDate", "endDate", "days", "mode", "utcOffset"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="usage.cost is unavailable until mission usage analytics are wired",
                    status_code=503,
                )
            usage_start_date = _optional_date_string(payload.get("startDate"), label="startDate")
            usage_end_date = _optional_date_string(payload.get("endDate"), label="endDate")
            usage_days = _optional_min_int(
                payload.get("days"),
                label="days",
                minimum=1,
            )
            usage_mode = _optional_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"gateway", "specific", "utc"},
            )
            usage_utc_offset = _optional_utc_offset_string(
                payload.get("utcOffset"),
                label="utcOffset",
            )
            return await _build_usage_cost_payload(
                self._database,
                start_date=usage_start_date,
                end_date=usage_end_date,
                days=usage_days,
                mode=cast(Literal["gateway", "specific", "utc"] | None, usage_mode),
                utc_offset=usage_utc_offset,
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "update.run":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "sessionKey",
                    "deliveryContext",
                    "note",
                    "restartDelayMs",
                    "timeoutMs",
                ),
            )
            _validate_optional_restart_request_fields(
                resolved_method,
                payload,
                include_timeout_ms=True,
            )
            if self._runtime_update_tick is None or self._runtime_update_view is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "update.run is unavailable until runtime self-update execution is wired"
                    ),
                    status_code=503,
                )
            await self._runtime_update_tick()
            return await self._runtime_update_view()

        if resolved_method == "wizard.start":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("mode", "workspace"),
            )
            if self._wizard_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="wizard.start is unavailable until setup wizard session is wired",
                    status_code=503,
                )
            mode = _optional_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"local", "remote"},
            )
            workspace = _optional_non_empty_string(payload.get("workspace"), label="workspace")
            return await self._wizard_service.start(
                mode=cast(Literal["local", "remote"] | None, mode),
                workspace=workspace,
            )

        if resolved_method == "wizard.next":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionId", "answer"),
            )
            if self._wizard_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="wizard.next is unavailable until setup wizard session is wired",
                    status_code=503,
                )
            session_id = _require_non_empty_string(payload.get("sessionId"), label="sessionId")
            answer_payload = payload.get("answer")
            answer: dict[str, object] | None = None
            if answer_payload is not None:
                if not isinstance(answer_payload, dict):
                    raise ValueError("invalid wizard.next params: answer must be an object")
                _validate_exact_keys(
                    "wizard.next.answer",
                    answer_payload,
                    allowed_keys=("stepId", "value"),
                )
                answer = {
                    "stepId": _require_non_empty_string(
                        answer_payload.get("stepId"),
                        label="stepId",
                    ),
                    "value": answer_payload.get("value"),
                }
            return await self._wizard_service.next(
                session_id=session_id,
                answer=answer,
            )

        if resolved_method == "wizard.cancel":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionId",),
            )
            if self._wizard_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="wizard.cancel is unavailable until setup wizard session is wired",
                    status_code=503,
                )
            session_id = _require_non_empty_string(payload.get("sessionId"), label="sessionId")
            return await self._wizard_service.cancel(session_id=session_id)

        if resolved_method == "wizard.status":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionId",),
            )
            if self._wizard_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="wizard.status is unavailable until setup wizard session is wired",
                    status_code=503,
                )
            session_id = _require_non_empty_string(payload.get("sessionId"), label="sessionId")
            return await self._wizard_service.status(session_id=session_id)

        if resolved_method == "logs.tail":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("cursor", "limit", "maxBytes"),
            )
            cursor = _optional_min_int(
                payload.get("cursor"),
                label="cursor",
                minimum=0,
            )
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=5_000,
            )
            max_bytes = _optional_bounded_int(
                payload.get("maxBytes"),
                label="maxBytes",
                minimum=1,
                maximum=1_000_000,
            )
            try:
                return await self._logs_service.read_tail(
                    cursor=cursor,
                    limit=limit,
                    max_bytes=max_bytes,
                )
            except GatewayLogsUnavailableError as exc:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=str(exc),
                    status_code=503,
                ) from exc

        if resolved_method == "models.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return await self._models_service.build_catalog()

        if resolved_method == "models.authStatus":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("refresh",))
            _optional_bool(payload.get("refresh"), label="refresh")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "models.authStatus is unavailable until model auth health runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "cron.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "includeDisabled",
                    "limit",
                    "offset",
                    "query",
                    "enabled",
                    "sortBy",
                    "sortDir",
                ),
            )
            if self._cron_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.list is unavailable until scheduled task inventory is wired",
                    status_code=503,
                )
            include_disabled = (
                _optional_bool(payload.get("includeDisabled"), label="includeDisabled")
                if "includeDisabled" in payload
                else False
            )
            enabled = _optional_enum_value(
                payload.get("enabled"),
                label="enabled",
                allowed_values={"all", "enabled", "disabled"},
            )
            if enabled is None:
                enabled = "all" if include_disabled else "enabled"
            sort_by = _optional_enum_value(
                payload.get("sortBy"),
                label="sortBy",
                allowed_values={"nextRunAtMs", "updatedAtMs", "name"},
            )
            sort_dir = _optional_enum_value(
                payload.get("sortDir"),
                label="sortDir",
                allowed_values={"asc", "desc"},
            )
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=200,
            )
            offset = _optional_bounded_int(
                payload.get("offset"),
                label="offset",
                minimum=0,
                maximum=1_000_000,
            )
            query = _optional_non_empty_string(payload.get("query"), label="query")
            return await self._cron_service.list_page(
                enabled=cast(Literal["all", "enabled", "disabled"], enabled),
                query=query,
                limit=limit,
                offset=offset,
                sort_by=cast(
                    Literal["nextRunAtMs", "updatedAtMs", "name"],
                    sort_by or "nextRunAtMs",
                ),
                sort_dir=cast(Literal["asc", "desc"], sort_dir or "asc"),
            )

        if resolved_method == "cron.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._cron_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.status is unavailable until scheduled task status is wired",
                    status_code=503,
                )
            return await self._cron_service.status()

        if resolved_method == "cron.add":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
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
                ),
            )
            if self._cron_service is None or not self._cron_service.can_add_jobs:
                if self._create_task_blueprint is not None:
                    build_gateway_cron_task_blueprint(dict(payload))
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.add is unavailable until scheduled task creation is wired",
                    status_code=503,
                )
            return await self._cron_service.add(dict(payload))

        if resolved_method == "cron.update":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "jobId", "patch"),
            )
            if self._cron_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.update is unavailable until scheduled task patching is wired",
                    status_code=503,
                )
            job_id = _optional_non_empty_string(payload.get("id"), label="id")
            if job_id is None:
                job_id = _optional_non_empty_string(payload.get("jobId"), label="jobId")
            if job_id is None:
                raise ValueError("invalid cron.update params: missing id")
            patch = payload.get("patch")
            if not isinstance(patch, dict):
                raise ValueError("invalid cron.update params: patch must be an object")
            return await self._cron_service.update(job_id, dict(patch))

        if resolved_method == "cron.run":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "jobId", "mode"),
            )
            if self._cron_service is None or not self._cron_service.can_run_jobs:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.run is unavailable until scheduled task launch is wired",
                    status_code=503,
                )
            job_id = _optional_non_empty_string(payload.get("id"), label="id")
            if job_id is None:
                job_id = _optional_non_empty_string(payload.get("jobId"), label="jobId")
            if job_id is None:
                raise ValueError("invalid cron.run params: missing id")
            mode = _optional_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"due", "force"},
            )
            return await self._cron_service.run(
                job_id=job_id,
                mode=cast(Literal["due", "force"], mode or "force"),
            )

        if resolved_method == "cron.remove":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "jobId"),
            )
            if self._cron_service is None or not self._cron_service.can_remove_jobs:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.remove is unavailable until scheduled task deletion is wired",
                    status_code=503,
                )
            job_id = _optional_non_empty_string(payload.get("id"), label="id")
            if job_id is None:
                job_id = _optional_non_empty_string(payload.get("jobId"), label="jobId")
            if job_id is None:
                raise ValueError("invalid cron.remove params: missing id")
            return await self._cron_service.remove(job_id)

        if resolved_method == "cron.runs":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "scope",
                    "id",
                    "jobId",
                    "limit",
                    "offset",
                    "statuses",
                    "status",
                    "deliveryStatuses",
                    "deliveryStatus",
                    "query",
                    "sortDir",
                ),
            )
            if self._cron_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="cron.runs is unavailable until scheduled task history is wired",
                    status_code=503,
                )
            job_id = _optional_non_empty_string(payload.get("id"), label="id")
            if job_id is None:
                job_id = _optional_non_empty_string(payload.get("jobId"), label="jobId")
            scope = _optional_enum_value(
                payload.get("scope"),
                label="scope",
                allowed_values={"job", "all"},
            )
            resolved_scope = cast(Literal["job", "all"], scope or ("job" if job_id else "all"))
            if resolved_scope == "job" and job_id is None:
                raise ValueError("invalid cron.runs params: missing id")
            status = _optional_enum_value(
                payload.get("status"),
                label="status",
                allowed_values={"all", "ok", "error", "skipped"},
            )
            statuses = _optional_enum_values(
                payload.get("statuses"),
                label="statuses",
                allowed_values={"ok", "error", "skipped"},
            )
            delivery_status = _optional_enum_value(
                payload.get("deliveryStatus"),
                label="deliveryStatus",
                allowed_values={"delivered", "not-delivered", "unknown", "not-requested"},
            )
            delivery_statuses = _optional_enum_values(
                payload.get("deliveryStatuses"),
                label="deliveryStatuses",
                allowed_values={"delivered", "not-delivered", "unknown", "not-requested"},
            )
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=200,
            )
            offset = _optional_bounded_int(
                payload.get("offset"),
                label="offset",
                minimum=0,
                maximum=1_000_000,
            )
            query = _optional_non_empty_string(payload.get("query"), label="query")
            sort_dir = _optional_enum_value(
                payload.get("sortDir"),
                label="sortDir",
                allowed_values={"asc", "desc"},
            )
            return await self._cron_service.runs_page(
                scope=resolved_scope,
                job_id=job_id,
                limit=limit,
                offset=offset,
                statuses=cast(
                    tuple[Literal["ok", "error", "skipped"], ...] | None,
                    statuses,
                ),
                status=cast(Literal["all", "ok", "error", "skipped"] | None, status),
                delivery_statuses=cast(
                    tuple[Literal["delivered", "not-delivered", "unknown", "not-requested"], ...]
                    | None,
                    delivery_statuses,
                ),
                delivery_status=cast(
                    Literal["delivered", "not-delivered", "unknown", "not-requested"] | None,
                    delivery_status,
                ),
                query=query,
                sort_dir=cast(Literal["asc", "desc"], sort_dir or "desc"),
            )

        if resolved_method == "wake":
            mode = _require_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"next-heartbeat", "now"},
            )
            text = _require_non_empty_string(payload.get("text"), label="text")
            reason = _optional_normalized_string(payload.get("reason"), label="reason")
            session_key = _optional_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            agent_id = _optional_normalized_string(payload.get("agentId"), label="agentId")
            if session_key is not None:
                parsed_agent_session = parse_agent_session_key(session_key)
                if agent_id is None and parsed_agent_session is not None:
                    agent_id = parsed_agent_session.agent_id
                resolved_agent_id = resolve_agent_id_from_session_key(session_key)
                if agent_id is not None and agent_id != resolved_agent_id:
                    raise ValueError(f'unknown agent id "{agent_id}"')
            elif agent_id is not None:
                if self._sessions_service is None:
                    raise GatewayNodeMethodError(
                        code="UNAVAILABLE",
                        message=(
                            "wake session targeting is unavailable until session inventory is wired"
                        ),
                        status_code=503,
                    )
                resolved_target = await self._sessions_service.resolve_key(
                    key=None,
                    session_id=None,
                    label=None,
                    agent_id=agent_id,
                    spawned_by=None,
                    include_global=True,
                    include_unknown=False,
                )
                session_key = _require_non_empty_string(
                    resolved_target.get("key"),
                    label="sessionKey",
                )
            if self._wake_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="wake is unavailable until control-plane wake queue is wired",
                    status_code=503,
                )
            return await self._wake_service.wake(
                mode=cast(Literal["next-heartbeat", "now"], mode),
                text=text,
                reason=reason,
                agent_id=agent_id,
                session_key=session_key,
            )

        if resolved_method == "connect":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="connect is only valid as the first request",
                status_code=400,
            )

        if resolved_method == "web.login.start":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("force", "timeoutMs", "verbose", "accountId"),
            )
            _optional_bool(payload.get("force"), label="force")
            _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            _optional_bool(payload.get("verbose"), label="verbose")
            if "accountId" in payload and payload.get("accountId") is not None:
                _require_string(payload.get("accountId"), label="accountId")
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="web login provider is not available",
                status_code=400,
            )

        if resolved_method == "web.login.wait":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("timeoutMs", "accountId"),
            )
            _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            if "accountId" in payload and payload.get("accountId") is not None:
                _require_string(payload.get("accountId"), label="accountId")
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="web login provider is not available",
                status_code=400,
            )

        if resolved_method == "push.test":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("nodeId", "title", "body", "environment"),
            )
            node_id = _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            if "title" in payload and payload.get("title") is not None:
                _require_string(payload.get("title"), label="title")
            if "body" in payload and payload.get("body") is not None:
                _require_string(payload.get("body"), label="body")
            _optional_enum_value(
                payload.get("environment"),
                label="environment",
                allowed_values={"sandbox", "production"},
            )
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=f"node {node_id} has no APNs registration (connect iOS node first)",
                status_code=400,
            )

        if resolved_method == "sessions.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "includeGlobal",
                    "includeUnknown",
                    "limit",
                    "activeMinutes",
                    "label",
                    "spawnedBy",
                    "agentId",
                    "search",
                    "includeDerivedTitles",
                    "includeLastMessage",
                ),
            )
            if self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.list is unavailable until session inventory is wired",
                    status_code=503,
                )
            include_global = (
                _optional_bool(payload.get("includeGlobal"), label="includeGlobal")
                if "includeGlobal" in payload
                else True
            )
            include_unknown = (
                _optional_bool(payload.get("includeUnknown"), label="includeUnknown")
                if "includeUnknown" in payload
                else False
            )
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1000,
            )
            active_minutes = _optional_min_int(
                payload.get("activeMinutes"),
                label="activeMinutes",
                minimum=1,
            )
            label = _optional_non_empty_string(payload.get("label"), label="label")
            spawned_by = _optional_non_empty_string(payload.get("spawnedBy"), label="spawnedBy")
            agent_id = _optional_normalized_string(payload.get("agentId"), label="agentId")
            search = _optional_non_empty_string(payload.get("search"), label="search")
            include_derived_titles = (
                _optional_bool(payload.get("includeDerivedTitles"), label="includeDerivedTitles")
                if "includeDerivedTitles" in payload
                else False
            )
            include_last_message = (
                _optional_bool(payload.get("includeLastMessage"), label="includeLastMessage")
                if "includeLastMessage" in payload
                else False
            )
            return await self._sessions_service.build_snapshot(
                include_global=bool(include_global),
                include_unknown=bool(include_unknown),
                limit=limit,
                active_minutes=active_minutes,
                label=label,
                spawned_by=spawned_by,
                agent_id=agent_id,
                search=search,
                include_derived_titles=bool(include_derived_titles),
                include_last_message=bool(include_last_message),
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "sessions.resolve":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "sessionId",
                    "label",
                    "agentId",
                    "spawnedBy",
                    "includeGlobal",
                    "includeUnknown",
                ),
            )
            if self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.resolve is unavailable until session inventory is wired",
                    status_code=503,
                )
            key = _optional_non_empty_string(payload.get("key"), label="key")
            resolved_session_id = _optional_non_empty_string(
                payload.get("sessionId"),
                label="sessionId",
            )
            label = _optional_non_empty_string(payload.get("label"), label="label")
            agent_id = _optional_normalized_string(payload.get("agentId"), label="agentId")
            spawned_by = _optional_non_empty_string(payload.get("spawnedBy"), label="spawnedBy")
            include_global = (
                _optional_bool(payload.get("includeGlobal"), label="includeGlobal")
                if "includeGlobal" in payload
                else True
            )
            include_unknown = (
                _optional_bool(payload.get("includeUnknown"), label="includeUnknown")
                if "includeUnknown" in payload
                else False
            )
            return await self._sessions_service.resolve_key(
                key=key,
                session_id=resolved_session_id,
                label=label,
                agent_id=agent_id,
                spawned_by=spawned_by,
                include_global=bool(include_global),
                include_unknown=bool(include_unknown),
            )

        if resolved_method == "sessions.get":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "sessionKey", "limit"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.get is unavailable until control chat persistence is wired",
                    status_code=503,
                )
            session_key = _require_session_lookup_key(payload)
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1000,
            )
            return await _build_sessions_get_payload(
                self._database,
                session_key=session_key,
                limit=limit,
            )

        if resolved_method == "sessions.usage":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "startDate",
                    "endDate",
                    "mode",
                    "utcOffset",
                    "limit",
                    "includeContextWeight",
                ),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.usage is unavailable until session usage analytics are wired",
                    status_code=503,
                )
            usage_session_key = _optional_non_empty_string(payload.get("key"), label="key")
            usage_start_date = _optional_date_string(payload.get("startDate"), label="startDate")
            usage_end_date = _optional_date_string(payload.get("endDate"), label="endDate")
            usage_mode = _optional_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"gateway", "specific", "utc"},
            )
            usage_utc_offset = _optional_utc_offset_string(
                payload.get("utcOffset"),
                label="utcOffset",
            )
            usage_limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1000,
            )
            usage_include_context_weight = _optional_bool(
                payload.get("includeContextWeight"),
                label="includeContextWeight",
            )
            return await _build_sessions_usage_payload(
                self._database,
                sessions_service=self._sessions_service,
                session_key=usage_session_key,
                start_date=usage_start_date,
                end_date=usage_end_date,
                mode=cast(Literal["gateway", "specific", "utc"] | None, usage_mode),
                utc_offset=usage_utc_offset,
                limit=usage_limit,
                include_context_weight=bool(usage_include_context_weight),
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "sessions.usage.timeseries":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.usage.timeseries is unavailable until session usage analytics "
                        "are wired"
                    ),
                    status_code=503,
                )
            return await _build_sessions_usage_timeseries_payload(
                self._database,
                sessions_service=self._sessions_service,
                session_key=_require_non_empty_string(payload.get("key"), label="key"),
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "sessions.usage.logs":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "limit"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.usage.logs is unavailable until session usage analytics are wired"
                    ),
                    status_code=503,
                )
            return await _build_sessions_usage_logs_payload(
                self._database,
                sessions_service=self._sessions_service,
                session_key=_require_non_empty_string(payload.get("key"), label="key"),
                limit=_optional_bounded_int(
                    payload.get("limit"),
                    label="limit",
                    minimum=1,
                    maximum=1000,
                ),
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "talk.mode":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("enabled", "phase"))
            talk_mode = self._talk_mode_service.set_mode(
                _require_bool(payload.get("enabled"), label="enabled"),
                phase=_optional_non_empty_string(payload.get("phase"), label="phase"),
                now_ms=_timestamp_ms(now_ms),
            )
            mode_payload = talk_mode.to_payload()
            for known_node in self.registry.list_known_nodes():
                if known_node.connected:
                    self.registry.send_event(known_node.node_id, "talk.mode", mode_payload)
            await self._publish_gateway_event("talk.mode", mode_payload)
            return mode_payload

        if resolved_method == "talk.speak":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "modelId",
                    "outputFormat",
                    "provider",
                    "rateWpm",
                    "speed",
                    "text",
                    "voiceId",
                ),
            )
            text = _require_non_empty_string(payload.get("text"), label="text")
            provider = _optional_non_empty_string(payload.get("provider"), label="provider")
            voice_id = _optional_non_empty_string(payload.get("voiceId"), label="voiceId")
            model_id = _optional_non_empty_string(payload.get("modelId"), label="modelId")
            output_format = _optional_non_empty_string(
                payload.get("outputFormat"),
                label="outputFormat",
            )
            speed = _optional_number(payload.get("speed"), label="speed")
            rate_wpm = _optional_number(payload.get("rateWpm"), label="rateWpm")
            if self._tts_runtime_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="Talk synthesis runtime not wired in OpenZues yet",
                    status_code=503,
                )
            try:
                return await self._tts_runtime_service.speak(
                    text=text,
                    provider=provider,
                    model_id=model_id,
                    voice_id=voice_id,
                    output_format=output_format,
                    speed=speed,
                    rate_wpm=rate_wpm,
                )
            except ValueError as exc:
                raise GatewayNodeMethodError(
                    code="INVALID_REQUEST",
                    message=str(exc).strip() or "invalid talk.speak params",
                    status_code=400,
                ) from exc
            except GatewayTtsRuntimeUnavailableError as exc:
                message = str(exc).strip() or "Talk synthesis runtime not wired in OpenZues yet"
                if message.startswith("TTS conversion"):
                    message = "Talk synthesis runtime not wired in OpenZues yet"
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=message,
                    status_code=503,
                ) from exc

        if resolved_method == "tts.enable":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._tts_service.set_enabled(True, now_ms=_timestamp_ms(now_ms))

        if resolved_method == "tts.disable":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._tts_service.set_enabled(False, now_ms=_timestamp_ms(now_ms))

        if resolved_method == "tts.setProvider":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("provider",))
            provider = normalize_tts_provider(payload.get("provider"))
            known_providers = {
                str(candidate).strip()
                for candidate in self._tts_service.build_provider_catalog().get("providers", [])
                if str(candidate).strip()
            }
            if provider is None or provider not in known_providers:
                raise GatewayNodeMethodError(
                    code="INVALID_REQUEST",
                    message="Invalid provider. Use a registered TTS provider id.",
                )
            return self._tts_service.set_provider(
                provider,
                now_ms=_timestamp_ms(now_ms),
            )

        if resolved_method == "tts.convert":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("channel", "modelId", "provider", "text", "voiceId"),
            )
            _require_non_empty_string(payload.get("text"), label="text")
            provider = _optional_normalized_string(payload.get("provider"), label="provider")
            model_id = _optional_normalized_string(payload.get("modelId"), label="modelId")
            voice_id = _optional_normalized_string(payload.get("voiceId"), label="voiceId")
            channel = _optional_normalized_string(payload.get("channel"), label="channel")
            if self._tts_runtime_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="TTS conversion runtime not wired in OpenZues yet",
                    status_code=503,
                )
            try:
                return await self._tts_runtime_service.convert(
                    text=_require_non_empty_string(payload.get("text"), label="text"),
                    channel=channel,
                    provider=provider,
                    model_id=model_id,
                    voice_id=voice_id,
                )
            except GatewayTtsRuntimeUnavailableError as exc:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=str(exc),
                    status_code=503,
                ) from exc

        if resolved_method == "config.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._config_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="config.get is unavailable until gateway config is wired",
                    status_code=503,
                )
            return self._config_service.build_snapshot()

        if resolved_method == "config.set":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("raw", "baseHash"),
            )
            _require_non_empty_string(payload.get("raw"), label="raw")
            _optional_non_empty_string(payload.get("baseHash"), label="baseHash")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "config.set is unavailable until writable gateway config ownership is wired"
                ),
                status_code=503,
            )

        if resolved_method == "config.patch":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "raw",
                    "baseHash",
                    "sessionKey",
                    "deliveryContext",
                    "note",
                    "restartDelayMs",
                ),
            )
            _require_non_empty_string(payload.get("raw"), label="raw")
            _optional_non_empty_string(payload.get("baseHash"), label="baseHash")
            _validate_optional_restart_request_fields(
                resolved_method,
                payload,
                include_timeout_ms=False,
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "config.patch is unavailable until writable gateway config patching is wired"
                ),
                status_code=503,
            )

        if resolved_method == "config.apply":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "raw",
                    "baseHash",
                    "sessionKey",
                    "deliveryContext",
                    "note",
                    "restartDelayMs",
                ),
            )
            _require_non_empty_string(payload.get("raw"), label="raw")
            _optional_non_empty_string(payload.get("baseHash"), label="baseHash")
            _validate_optional_restart_request_fields(
                resolved_method,
                payload,
                include_timeout_ms=False,
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "config.apply is unavailable until writable gateway config apply runtime "
                    "is wired"
                ),
                status_code=503,
            )

        if resolved_method == "config.openFile":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._config_service is not None and self._config_service.can_open_file():
                return self._config_service.open_file()
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "config.openFile is unavailable until operator config file ownership is wired"
                ),
                status_code=503,
            )

        if resolved_method == "config.schema":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._config_schema_service.build_schema()

        if resolved_method == "config.schema.lookup":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("path",))
            path = _require_string(payload.get("path"), label="path")
            lookup = self._config_schema_service.lookup(path)
            if lookup is None:
                raise ValueError("config schema path not found")
            return lookup

        if resolved_method == "secrets.reload":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return await self._reload_secrets()

        if resolved_method == "secrets.resolve":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("commandName", "targetIds"),
            )
            command_name = _require_string(payload.get("commandName"), label="commandName").strip()
            if not command_name:
                raise ValueError("invalid secrets.resolve params: commandName")
            _ = [
                entry.strip()
                for entry in _require_string_list(payload.get("targetIds"), label="targetIds")
                if entry.strip()
            ]
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "secrets.resolve is unavailable until command-target secret resolution is wired"
                ),
                status_code=503,
            )

        if resolved_method == "channels.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._channels_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="channels.status is unavailable until channel inventory is wired",
                    status_code=503,
                )
            return await self._channels_service.build_snapshot()

        if resolved_method == "channels.logout":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("channel", "accountId"),
            )
            raw_channel = payload.get("channel")
            if not isinstance(raw_channel, str) or not raw_channel.strip():
                raise GatewayNodeMethodError(
                    code="INVALID_REQUEST",
                    message="invalid channels.logout params: channel must be a non-empty string",
                    status_code=400,
                )
            channel = raw_channel.strip()
            normalized_channel = _normalize_gateway_chat_channel_id(channel)
            if normalized_channel is None:
                raise GatewayNodeMethodError(
                    code="INVALID_REQUEST",
                    message="invalid channels.logout channel",
                    status_code=400,
                )
            if "accountId" in payload and payload.get("accountId") is not None:
                _require_string(payload.get("accountId"), label="accountId")
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=f"channel {normalized_channel} does not support logout",
                status_code=400,
            )

        if resolved_method == "tools.catalog":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "includePlugins"),
            )
            return self._tools_catalog_service.build_catalog(
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId"),
                include_plugins=bool(
                    _optional_bool(payload.get("includePlugins"), label="includePlugins")
                    if "includePlugins" in payload
                    else True
                ),
            )

        if resolved_method == "tools.effective":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "sessionKey"),
            )
            session_key = _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            agent_id = _optional_non_empty_string(payload.get("agentId"), label="agentId")
            resolved_agent_id = resolve_agent_id_from_session_key(session_key)
            if agent_id is not None and agent_id != resolved_agent_id:
                raise ValueError(f'unknown agent id "{agent_id}"')
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "tools.effective is unavailable until control-plane persistence is wired"
                    ),
                    status_code=503,
                )
            return self._tools_catalog_service.build_effective(
                agent_id=agent_id or resolved_agent_id,
                toolsets=await self._resolve_effective_toolsets(session_key),
            )

        if resolved_method == "message.action":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "channel",
                    "action",
                    "params",
                    "accountId",
                    "requesterSenderId",
                    "senderIsOwner",
                    "sessionKey",
                    "sessionId",
                    "agentId",
                    "toolContext",
                    "idempotencyKey",
                ),
            )
            resolved_channel = await self._resolve_gateway_outbound_channel(
                payload.get("channel"),
                reject_webchat_as_internal_only=True,
            )
            action = _require_non_empty_string(payload.get("action"), label="action")
            _require_unknown_mapping(payload.get("params"), label="params")
            if "accountId" in payload and payload.get("accountId") is not None:
                _require_string(payload.get("accountId"), label="accountId")
            if "requesterSenderId" in payload and payload.get("requesterSenderId") is not None:
                _require_string(
                    payload.get("requesterSenderId"),
                    label="requesterSenderId",
                )
            if "senderIsOwner" in payload and payload.get("senderIsOwner") is not None:
                _require_bool(payload.get("senderIsOwner"), label="senderIsOwner")
            if "sessionKey" in payload and payload.get("sessionKey") is not None:
                _require_string(payload.get("sessionKey"), label="sessionKey")
            if "sessionId" in payload and payload.get("sessionId") is not None:
                _require_string(payload.get("sessionId"), label="sessionId")
            if "agentId" in payload and payload.get("agentId") is not None:
                _require_string(payload.get("agentId"), label="agentId")
            if "toolContext" in payload and payload.get("toolContext") is not None:
                _validate_message_action_tool_context(payload.get("toolContext"))
            _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message=f"Channel {resolved_channel} does not support action {action}.",
                status_code=400,
            )

        if resolved_method == "send":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "to",
                    "message",
                    "mediaUrl",
                    "mediaUrls",
                    "gifPlayback",
                    "channel",
                    "accountId",
                    "agentId",
                    "threadId",
                    "sessionKey",
                    "idempotencyKey",
                ),
            )
            to = _require_string(payload.get("to"), label="to")
            trimmed_to = to.strip()
            message = (
                _require_string(payload.get("message"), label="message")
                if "message" in payload and payload.get("message") is not None
                else ""
            )
            media_url = (
                _require_string(payload.get("mediaUrl"), label="mediaUrl")
                if "mediaUrl" in payload and payload.get("mediaUrl") is not None
                else ""
            )
            media_urls = (
                [
                    entry.strip()
                    for entry in _require_string_array(payload.get("mediaUrls"), label="mediaUrls")
                    if entry.strip()
                ]
                if "mediaUrls" in payload and payload.get("mediaUrls") is not None
                else []
            )
            normalized_media_urls = _normalize_gateway_send_media_urls(
                media_url=media_url,
                media_urls=media_urls,
            )
            if not message.strip() and not normalized_media_urls:
                raise ValueError("invalid send params: text or media is required")
            gif_playback = (
                _optional_bool(payload.get("gifPlayback"), label="gifPlayback")
                if "gifPlayback" in payload
                else None
            )
            resolved_channel = await self._resolve_gateway_outbound_channel(
                payload.get("channel"),
                reject_webchat_as_internal_only=True,
            )
            _validate_gateway_outbound_target(resolved_channel, to)
            account_id = _optional_normalized_string(payload.get("accountId"), label="accountId")
            agent_id = _optional_normalized_string(payload.get("agentId"), label="agentId")
            explicit_thread_id = _optional_normalized_string(
                payload.get("threadId"),
                label="threadId",
            )
            source_session_key = _optional_normalized_string(
                payload.get("sessionKey"),
                label="sessionKey",
            )
            idempotency_key = _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            if self._send_channel_message_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="send is unavailable until channel-target outbound delivery is wired",
                    status_code=503,
                )
            effective_thread_id = explicit_thread_id
            if effective_thread_id is None and source_session_key is not None:
                effective_thread_id = parse_thread_session_suffix(source_session_key).thread_id
            send_payload: dict[str, object | None] = {
                "channel": resolved_channel,
                "to": trimmed_to,
                "message": message,
                "account_id": account_id,
                "agent_id": agent_id,
                "thread_id": effective_thread_id,
                "session_key": source_session_key,
                "idempotency_key": idempotency_key,
            }
            if normalized_media_urls:
                send_payload["media_urls"] = normalized_media_urls
                if gif_playback is not None:
                    send_payload["gif_playback"] = gif_playback
            return await self._send_channel_message_service(**send_payload)

        if resolved_method == "poll":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "to",
                    "question",
                    "options",
                    "maxSelections",
                    "durationSeconds",
                    "durationHours",
                    "silent",
                    "isAnonymous",
                    "channel",
                    "accountId",
                    "threadId",
                    "idempotencyKey",
                ),
            )
            to = _require_string(payload.get("to"), label="to")
            trimmed_to = to.strip()
            question = _require_non_empty_string(payload.get("question"), label="question")
            raw_options = payload.get("options")
            if not isinstance(raw_options, list):
                raise ValueError("options must be an array")
            if len(raw_options) < 2 or len(raw_options) > 12:
                raise ValueError("options must contain between 2 and 12 items")
            options = [
                _require_non_empty_string(entry, label="options[]") for entry in raw_options
            ]
            max_selections = _optional_bounded_int(
                payload.get("maxSelections"),
                label="maxSelections",
                minimum=1,
                maximum=12,
            )
            duration_seconds = _optional_bounded_int(
                payload.get("durationSeconds"),
                label="durationSeconds",
                minimum=1,
                maximum=604_800,
            )
            duration_hours = _optional_min_int(
                payload.get("durationHours"),
                label="durationHours",
                minimum=1,
            )
            silent = _optional_bool(payload.get("silent"), label="silent")
            is_anonymous = _optional_bool(payload.get("isAnonymous"), label="isAnonymous")
            resolved_channel = await self._resolve_gateway_outbound_channel(
                payload.get("channel"),
                reject_webchat_as_internal_only=True,
                rejected_webchat_message="unsupported poll channel: webchat",
            )
            _validate_gateway_outbound_target(resolved_channel, to)
            account_id = _optional_normalized_string(payload.get("accountId"), label="accountId")
            thread_id = _optional_normalized_string(payload.get("threadId"), label="threadId")
            idempotency_key = _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            if self._send_channel_poll_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="poll is unavailable until channel-target poll delivery is wired",
                    status_code=503,
                )
            return await self._send_channel_poll_service(
                channel=resolved_channel,
                to=trimmed_to,
                question=question,
                options=options,
                max_selections=max_selections,
                duration_seconds=duration_seconds,
                duration_hours=duration_hours,
                silent=silent,
                is_anonymous=is_anonymous,
                account_id=account_id,
                thread_id=thread_id,
                idempotency_key=idempotency_key,
            )

        if resolved_method == "chat.history":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionKey", "limit", "maxChars"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="chat.history is unavailable until control chat persistence is wired",
                    status_code=503,
                )
            session_key = _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1000,
            )
            max_chars = _optional_bounded_int(
                payload.get("maxChars"),
                label="maxChars",
                minimum=1,
                maximum=500_000,
            )
            return await _build_chat_history_payload(
                self._database,
                session_key=session_key,
                limit=limit,
                max_chars=max_chars,
            )

        if resolved_method == "chat.send":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "sessionKey",
                    "message",
                    "thinking",
                    "deliver",
                    "originatingChannel",
                    "originatingTo",
                    "originatingAccountId",
                    "originatingThreadId",
                    "attachments",
                    "timeoutMs",
                    "systemInputProvenance",
                    "systemProvenanceReceipt",
                    "idempotencyKey",
                ),
            )
            if self._chat_send_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="chat.send is unavailable until control chat runtime is wired",
                    status_code=503,
                )
            session_key = _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            message = _sanitize_gateway_chat_send_message_input(
                _require_string(payload.get("message"), label="message")
            )
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            deliver = _optional_bool(payload.get("deliver"), label="deliver")
            explicit_origin = _normalize_gateway_chat_send_explicit_origin(
                originating_channel=payload.get("originatingChannel"),
                originating_to=payload.get("originatingTo"),
                originating_account_id=payload.get("originatingAccountId"),
                originating_thread_id=payload.get("originatingThreadId"),
            )
            raw_system_input_provenance = payload.get("systemInputProvenance")
            raw_system_provenance_receipt = payload.get("systemProvenanceReceipt")
            if raw_system_provenance_receipt is not None:
                _require_string(
                    raw_system_provenance_receipt,
                    label="systemProvenanceReceipt",
                )
            has_raw_system_input_provenance = _has_truthy_gateway_system_input_provenance(
                raw_system_input_provenance
            )
            has_raw_system_provenance_receipt = isinstance(
                raw_system_provenance_receipt,
                str,
            ) and bool(raw_system_provenance_receipt)
            if (
                (
                    has_raw_system_input_provenance
                    or has_raw_system_provenance_receipt
                    or explicit_origin is not None
                )
                and resolved_requester.caller_scopes is not None
                and ADMIN_GATEWAY_METHOD_SCOPE not in resolved_requester.caller_scopes
            ):
                raise ValueError(
                    "system provenance fields require admin scope"
                    if has_raw_system_input_provenance or has_raw_system_provenance_receipt
                    else "originating route fields require admin scope"
                )
            system_input_provenance = _normalize_gateway_optional_input_provenance(
                raw_system_input_provenance
            )
            system_provenance_receipt = _sanitize_gateway_optional_chat_system_receipt(
                payload.get("systemProvenanceReceipt"),
            )
            attachments = payload.get("attachments")
            has_effective_attachments = False
            if attachments is not None:
                if not isinstance(attachments, list):
                    raise ValueError("attachments must be an array")
                has_effective_attachments = _has_effective_agent_attachments(attachments)
            if not message.strip() and not has_effective_attachments:
                raise ValueError("message or attachment required")
            timeout_ms = _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            idempotency_key = _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            if _is_gateway_chat_stop_command_text(message):
                return await self._abort_gateway_chat_run(
                    session_key=session_key,
                    run_id=None,
                )
            if explicit_origin is not None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "chat.send originating route fields are unavailable until control chat "
                        "route provenance is wired"
                    ),
                    status_code=503,
                )
            if system_input_provenance is not None or system_provenance_receipt is not None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "chat.send system provenance fields are unavailable until control chat "
                        "provenance injection is wired"
                    ),
                    status_code=503,
                )
            if has_effective_attachments:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "chat.send attachments are unavailable until control chat "
                        "attachment runtime is wired"
                    ),
                    status_code=503,
                )
            timestamp_ms = _timestamp_ms(now_ms)
            send_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=deliver,
                timeout_ms=timeout_ms,
            )
            self._remember_gateway_chat_run(
                session_key,
                send_result,
                started_at_ms=timestamp_ms,
            )
            return send_result

        if resolved_method == "chat.inject":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionKey", "message", "label"),
            )
            if self._database is None or self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="chat.inject is unavailable until control chat persistence is wired",
                    status_code=503,
                )
            session_key = _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            message = _require_string(payload.get("message"), label="message")
            label = (
                _require_string(payload.get("label"), label="label")
                if "label" in payload and payload.get("label") is not None
                else None
            )
            timestamp_ms = _timestamp_ms(now_ms)
            session_payload = await self._sessions_service.build_session_payload_for_key(
                session_key=session_key,
                now_ms=timestamp_ms,
            )
            if session_payload is None:
                raise ValueError("session not found")
            canonical_session_key = str(session_payload["key"])
            message_id = await self._database.append_control_chat_message(
                role="assistant",
                content=message,
                target_label=label,
                session_key=canonical_session_key,
            )
            message_row = await self._database.get_control_chat_message(message_id)
            assert message_row is not None
            await self._publish_session_message_events(message_row=message_row, now_ms=timestamp_ms)
            return {"ok": True, "messageId": str(message_id)}

        if resolved_method == "sessions.send":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "message",
                    "thinking",
                    "attachments",
                    "timeoutMs",
                    "idempotencyKey",
                ),
            )
            if self._chat_send_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.send is unavailable until control chat runtime is wired",
                    status_code=503,
                )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            message = _sanitize_gateway_chat_send_message_input(
                _require_string(payload.get("message"), label="message")
            )
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            attachments = payload.get("attachments")
            has_effective_attachments = False
            if attachments is not None:
                if not isinstance(attachments, list):
                    raise ValueError("attachments must be an array")
                has_effective_attachments = _has_effective_agent_attachments(attachments)
            if not message.strip() and not has_effective_attachments:
                raise ValueError("message or attachment required")
            timeout_ms = _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            idempotency_key = _optional_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            ) or secrets.token_urlsafe(18)
            if _is_gateway_chat_stop_command_text(message):
                stop_result = await self._abort_gateway_chat_run(
                    session_key=session_key,
                    run_id=None,
                )
                await self._publish_sessions_changed_event(
                    session_key=session_key,
                    reason="send",
                    now_ms=now_ms,
                )
                return stop_result
            if has_effective_attachments:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.send attachments are unavailable until control chat "
                        "attachment runtime is wired"
                    ),
                    status_code=503,
                )
            pending_message_seq = (
                await self._database.count_control_chat_messages(session_key=session_key) + 1
                if self._database is not None
                else None
            )
            timestamp_ms = _timestamp_ms(now_ms)
            send_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=None,
                timeout_ms=timeout_ms,
            )
            if pending_message_seq is not None and _should_attach_pending_session_message_seq(
                send_result
            ):
                send_result = {
                    **send_result,
                    "messageSeq": pending_message_seq,
                }
            self._remember_gateway_chat_run(
                session_key,
                send_result,
                started_at_ms=timestamp_ms,
            )
            await self._publish_sessions_changed_event(
                session_key=session_key,
                reason="send",
                now_ms=now_ms,
            )
            return send_result

        if resolved_method == "sessions.steer":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "message",
                    "thinking",
                    "attachments",
                    "timeoutMs",
                    "idempotencyKey",
                ),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            message = _sanitize_gateway_chat_send_message_input(
                _require_string(payload.get("message"), label="message")
            )
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            attachments = payload.get("attachments")
            has_effective_attachments = False
            if attachments is not None:
                if not isinstance(attachments, list):
                    raise ValueError("attachments must be an array")
                has_effective_attachments = _has_effective_agent_attachments(attachments)
            if not message.strip() and not has_effective_attachments:
                raise ValueError("message or attachment required")
            timeout_ms = _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            idempotency_key = _optional_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            ) or secrets.token_urlsafe(18)
            timestamp_ms = _timestamp_ms(now_ms)
            if self._chat_send_service is None or self._chat_abort_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.steer is unavailable until control chat interruption is wired"
                    ),
                    status_code=503,
                )
            interrupted_active_run = False
            if self._tracked_gateway_chat_run_id(session_key) is not None:
                await self._abort_gateway_chat_run(session_key=session_key, run_id=None)
                interrupted_active_run = True
            steer_event_reason = "steer" if interrupted_active_run else "send"
            if _is_gateway_chat_stop_command_text(message):
                stop_result = await self._abort_gateway_chat_run(
                    session_key=session_key,
                    run_id=None,
                )
                if interrupted_active_run and stop_result.get("ok") is True:
                    stop_result = {
                        **stop_result,
                        "interruptedActiveRun": True,
                    }
                await self._publish_sessions_changed_event(
                    session_key=session_key,
                    reason=steer_event_reason,
                    now_ms=now_ms,
                )
                return stop_result
            if has_effective_attachments:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.steer attachments are unavailable until control chat "
                        "attachment runtime is wired"
                    ),
                    status_code=503,
                )
            pending_message_seq = (
                await self._database.count_control_chat_messages(session_key=session_key) + 1
                if self._database is not None
                else None
            )
            steer_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=None,
                timeout_ms=timeout_ms,
            )
            if pending_message_seq is not None and _should_attach_pending_session_message_seq(
                steer_result
            ):
                steer_result = {
                    **steer_result,
                    "messageSeq": pending_message_seq,
                }
            if interrupted_active_run and isinstance(steer_result, dict):
                steer_result = {
                    **steer_result,
                    "interruptedActiveRun": True,
                }
            self._remember_gateway_chat_run(
                session_key,
                steer_result,
                started_at_ms=timestamp_ms,
            )
            await self._publish_sessions_changed_event(
                session_key=session_key,
                reason=steer_event_reason,
                now_ms=now_ms,
            )
            return steer_result

        if resolved_method == "sessions.abort":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "runId"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            run_id = _optional_non_empty_string(payload.get("runId"), label="runId")
            abort_payload = await self._abort_gateway_chat_run(
                session_key=session_key,
                run_id=run_id,
            )
            run_ids = abort_payload.get("runIds")
            aborted_run_id = (
                run_ids[0]
                if isinstance(run_ids, list) and run_ids and isinstance(run_ids[0], str)
                else None
            )
            if abort_payload.get("aborted"):
                await self._publish_sessions_changed_event(
                    session_key=session_key,
                    reason="abort",
                    now_ms=now_ms,
                )
            return {
                "ok": True,
                "abortedRunId": aborted_run_id,
                "status": "aborted" if abort_payload.get("aborted") else "no-active-run",
            }

        if resolved_method == "sessions.reset":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "reason"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            _optional_enum_value(
                payload.get("reason"),
                label="reason",
                allowed_values={"new", "reset"},
            )
            if self._database is None or self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.reset is unavailable until control chat session reset is wired"
                    ),
                    status_code=503,
                )
            canonical_key = _canonical_session_key(session_key)
            reset_reason = "new" if payload.get("reason") == "new" else "reset"
            existing_entry = await self._sessions_service.build_session_payload_for_key(
                session_key=canonical_key,
                now_ms=_timestamp_ms(now_ms),
            )
            if existing_entry is None:
                raise ValueError(f"session not found: {session_key}")
            existing_metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            restored_metadata: dict[str, Any] = {}
            if isinstance(existing_metadata_row, dict):
                metadata_value = existing_metadata_row.get("metadata")
                if isinstance(metadata_value, dict):
                    restored_metadata = dict(metadata_value)
            await self._database.delete_control_chat_messages(session_key=canonical_key)
            await self._database.upsert_gateway_session_metadata(
                session_key=canonical_key,
                metadata=restored_metadata,
            )
            self._forget_gateway_chat_run(canonical_key)
            entry = await self._sessions_service.build_session_payload_for_key(
                session_key=canonical_key,
                now_ms=_timestamp_ms(now_ms),
            )
            assert entry is not None
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason=reset_reason,
                now_ms=now_ms,
            )
            return {"ok": True, "key": canonical_key, "entry": entry}

        if resolved_method == "sessions.delete":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "deleteTranscript", "emitLifecycleHooks"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            delete_transcript = _optional_bool(
                payload.get("deleteTranscript"),
                label="deleteTranscript",
            )
            _optional_bool(payload.get("emitLifecycleHooks"), label="emitLifecycleHooks")
            if self._database is None or self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.delete is unavailable until control chat session deletion "
                        "is wired"
                    ),
                    status_code=503,
                )
            canonical_key = _canonical_session_key(session_key)
            main_session_key = await self._sessions_service.main_session_key()
            if canonical_key in set(_session_key_aliases(main_session_key)):
                raise ValueError(f"Cannot delete the main session ({main_session_key}).")

            resolved_delete_transcript = True if delete_transcript is None else delete_transcript
            metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            message_count = await self._database.count_control_chat_messages(
                session_key=canonical_key
            )
            mission = await self._database.get_latest_mission_by_session_key(
                canonical_key,
                require_thread=False,
            )
            if mission is not None:
                return {"ok": True, "key": canonical_key, "deleted": False, "archived": []}
            if not resolved_delete_transcript and message_count:
                return {"ok": True, "key": canonical_key, "deleted": False, "archived": []}

            deleted = metadata_row is not None or message_count > 0
            if not deleted:
                return {"ok": True, "key": canonical_key, "deleted": False, "archived": []}
            archived: list[str] = []
            if message_count and resolved_delete_transcript:
                archived = await _archive_control_chat_transcript(
                    self._database,
                    session_key=canonical_key,
                    reason="deleted",
                    now_ms=_timestamp_ms(now_ms),
                )
                await self._database.delete_control_chat_messages(session_key=canonical_key)
            if metadata_row is not None:
                await self._database.delete_gateway_session_metadata(canonical_key)
            self._forget_gateway_chat_run(canonical_key)
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="delete",
                now_ms=now_ms,
            )
            return {"ok": True, "key": canonical_key, "deleted": True, "archived": archived}

        if resolved_method == "sessions.compact":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "maxLines"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            max_lines = _optional_bounded_int(
                payload.get("maxLines"),
                label="maxLines",
                minimum=1,
                maximum=1_000_000,
            )
            if self._session_compaction_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compact is unavailable until control chat compaction is wired"
                    ),
                    status_code=503,
                )
            try:
                compacted = await self._session_compaction_service.compact(
                    session_key=session_key,
                    max_lines=max_lines,
                    now_ms=_timestamp_ms(now_ms),
                )
            except GatewaySessionCompactionUnavailableError as exc:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=str(exc),
                    status_code=503,
                ) from exc
            if compacted.get("compacted") is True:
                await self._publish_sessions_changed_event(
                    session_key=session_key,
                    reason="compact",
                    now_ms=now_ms,
                    compacted=True,
                )
            return compacted

        if resolved_method == "sessions.compaction.restore":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            checkpoint_id = _require_non_empty_string(
                payload.get("checkpointId"),
                label="checkpointId",
            )
            if (
                self._database is None
                or self._sessions_service is None
                or self._session_compaction_service is None
            ):
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.restore is unavailable until control chat compaction "
                        "restore is wired"
                    ),
                    status_code=503,
                )
            canonical_key = _canonical_session_key(session_key)
            if self._tracked_gateway_chat_run_id(canonical_key) is not None:
                await self._abort_gateway_chat_run(session_key=canonical_key, run_id=None)
            existing_metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            next_metadata: dict[str, Any] = {}
            if isinstance(existing_metadata_row, dict):
                metadata_value = existing_metadata_row.get("metadata")
                if isinstance(metadata_value, dict):
                    next_metadata = dict(metadata_value)
            try:
                restored = await self._session_compaction_service.restore(
                    session_key=canonical_key,
                    checkpoint_id=checkpoint_id,
                )
            except GatewaySessionCompactionUnavailableError as exc:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=str(exc),
                    status_code=503,
                ) from exc
            await self._database.upsert_gateway_session_metadata(
                session_key=canonical_key,
                metadata=next_metadata,
            )
            self._forget_gateway_chat_run(canonical_key)
            entry = await self._sessions_service.build_session_payload_for_key(
                session_key=canonical_key,
                now_ms=_timestamp_ms(now_ms),
            )
            if entry is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.restore could not materialize the restored session"
                    ),
                    status_code=503,
                )
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="checkpoint-restore",
                now_ms=now_ms,
            )
            return {
                "ok": True,
                "key": canonical_key,
                "sessionId": entry["sessionId"],
                "checkpoint": restored["checkpoint"],
                "entry": entry,
            }

        if resolved_method == "sessions.compaction.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            if self._session_compaction_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.list is unavailable until control chat compaction "
                        "checkpoints are wired"
                    ),
                    status_code=503,
                )
            return await self._session_compaction_service.list_checkpoints(session_key=session_key)

        if resolved_method == "sessions.compaction.get":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            checkpoint_id = _require_non_empty_string(
                payload.get("checkpointId"),
                label="checkpointId",
            )
            if self._session_compaction_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.get is unavailable until control chat compaction "
                        "checkpoints are wired"
                    ),
                    status_code=503,
                )
            return await self._session_compaction_service.get_checkpoint(
                session_key=session_key,
                checkpoint_id=checkpoint_id,
            )

        if resolved_method == "sessions.compaction.branch":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            checkpoint_id = _require_non_empty_string(
                payload.get("checkpointId"),
                label="checkpointId",
            )
            if (
                self._database is None
                or self._sessions_service is None
                or self._session_compaction_service is None
            ):
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.branch is unavailable until control chat compaction "
                        "branching is wired"
                    ),
                    status_code=503,
                )
            canonical_key = _canonical_session_key(session_key)
            source_entry = await self._sessions_service.build_session_payload_for_key(
                session_key=canonical_key,
                now_ms=_timestamp_ms(now_ms),
            )
            if source_entry is None:
                raise ValueError(f"session not found: {session_key}")
            existing_metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            branch_metadata: dict[str, Any] = {}
            if isinstance(existing_metadata_row, dict):
                metadata_value = existing_metadata_row.get("metadata")
                if isinstance(metadata_value, dict):
                    branch_metadata = dict(metadata_value)
            label_source = _optional_non_empty_string(
                branch_metadata.get("label") or source_entry.get("label"),
                label="label",
            )
            branch_metadata["label"] = (
                f"{label_source} (checkpoint)" if label_source is not None else "Checkpoint branch"
            )
            branch_metadata["parentSessionKey"] = canonical_key
            model_override = _optional_non_empty_string(
                branch_metadata.get("model") or source_entry.get("model"),
                label="model",
            )
            if model_override is not None:
                branch_metadata["model"] = model_override

            parsed_session_key = parse_thread_session_suffix(canonical_key)
            base_session_key = (
                str(parsed_session_key.base_session_key or "").strip() or canonical_key
            )
            next_key = resolve_thread_session_keys(
                base_session_key=base_session_key,
                thread_id=f"checkpoint-{secrets.token_hex(6)}",
            ).session_key
            while (
                await self._sessions_service.build_session_payload_for_key(
                    session_key=next_key,
                    now_ms=_timestamp_ms(now_ms),
                )
                is not None
            ):
                next_key = resolve_thread_session_keys(
                    base_session_key=base_session_key,
                    thread_id=f"checkpoint-{secrets.token_hex(6)}",
                ).session_key
            try:
                branched = await self._session_compaction_service.branch(
                    session_key=canonical_key,
                    checkpoint_id=checkpoint_id,
                    target_session_key=next_key,
                )
            except GatewaySessionCompactionUnavailableError as exc:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=str(exc),
                    status_code=503,
                ) from exc
            await self._database.upsert_gateway_session_metadata(
                session_key=next_key,
                metadata=branch_metadata,
            )
            entry = await self._sessions_service.build_session_payload_for_key(
                session_key=next_key,
                now_ms=_timestamp_ms(now_ms),
            )
            if entry is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.compaction.branch could not materialize the checkpoint branch"
                    ),
                    status_code=503,
                )
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="checkpoint-branch",
                now_ms=now_ms,
            )
            await self._publish_sessions_changed_event(
                session_key=next_key,
                reason="checkpoint-branch",
                now_ms=now_ms,
            )
            return {
                "ok": True,
                "sourceKey": canonical_key,
                "key": next_key,
                "sessionId": entry["sessionId"],
                "checkpoint": branched["checkpoint"],
                "entry": entry,
            }

        if resolved_method == "sessions.preview":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("keys", "limit", "maxChars"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.preview is unavailable until transcript storage is wired",
                    status_code=503,
                )
            keys = _require_string_list(payload.get("keys"), label="keys")
            limit = _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1_000_000,
            )
            max_chars = _optional_bounded_int(
                payload.get("maxChars"),
                label="maxChars",
                minimum=20,
                maximum=1_000_000,
            )
            bounded_limit = max(1, min(limit or 12, 50))
            bounded_max_chars = max(20, min(max_chars or 240, 2000))
            current_session_key = (
                await self._sessions_service.current_session_key()
                if self._sessions_service is not None
                else None
            )
            current_session_aliases = set(_session_key_aliases(current_session_key or ""))
            previews: list[dict[str, Any]] = []
            for key in keys:
                canonical_key = _canonical_session_key(key)
                try:
                    rows = await self._database.list_control_chat_messages(
                        limit=bounded_limit,
                        session_key=canonical_key,
                    )
                    if rows:
                        previews.append(
                            {
                                "key": key,
                                "status": "ok",
                                "items": _project_session_preview_items(
                                    rows,
                                    max_items=bounded_limit,
                                    max_chars=bounded_max_chars,
                                ),
                            }
                        )
                        continue
                    mission = await self._database.get_latest_mission_by_session_key(
                        canonical_key,
                        require_thread=False,
                    )
                    previews.append(
                        {
                            "key": key,
                            "status": (
                                "empty"
                                if canonical_key in current_session_aliases or mission is not None
                                else "missing"
                            ),
                            "items": [],
                        }
                    )
                except Exception:
                    previews.append({"key": key, "status": "error", "items": []})
            return {"ts": _timestamp_ms(now_ms), "previews": previews}

        if resolved_method == "sessions.messages.subscribe":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            canonical_key = _canonical_session_key(session_key)
            if self._hub is None or not resolved_requester.client_id:
                return {"subscribed": False, "key": canonical_key}
            subscribed = self._hub.set_session_messages_subscription(
                client_id=resolved_requester.client_id,
                session_key=canonical_key,
                subscribed=True,
            )
            return {"subscribed": subscribed, "key": canonical_key}

        if resolved_method == "sessions.messages.unsubscribe":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            canonical_key = _canonical_session_key(session_key)
            if self._hub is None or not resolved_requester.client_id:
                return {"subscribed": False, "key": canonical_key}
            subscribed = self._hub.set_session_messages_subscription(
                client_id=resolved_requester.client_id,
                session_key=canonical_key,
                subscribed=False,
            )
            return {"subscribed": subscribed, "key": canonical_key}

        if resolved_method == "sessions.subscribe":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._hub is None or not resolved_requester.client_id:
                return {"subscribed": False}
            return {
                "subscribed": self._hub.set_sessions_subscription(
                    client_id=resolved_requester.client_id,
                    subscribed=True,
                )
            }

        if resolved_method == "sessions.unsubscribe":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._hub is None or not resolved_requester.client_id:
                return {"subscribed": False}
            return {
                "subscribed": self._hub.set_sessions_subscription(
                    client_id=resolved_requester.client_id,
                    subscribed=False,
                )
            }

        if resolved_method == "sessions.create":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "agentId",
                    "label",
                    "model",
                    "parentSessionKey",
                    "task",
                    "message",
                ),
            )
            _optional_non_empty_string(payload.get("key"), label="key")
            _optional_non_empty_string(payload.get("agentId"), label="agentId")
            if "label" in payload:
                _require_session_label(payload.get("label"), label="label")
            _optional_non_empty_string(payload.get("model"), label="model")
            _optional_non_empty_string(payload.get("parentSessionKey"), label="parentSessionKey")
            if "task" in payload:
                _require_string(payload.get("task"), label="task")
            if "message" in payload:
                _require_string(payload.get("message"), label="message")
            if self._database is None or self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.create is unavailable until session creation runtime is wired"
                    ),
                    status_code=503,
                )
            agent_id = _optional_non_empty_string(payload.get("agentId"), label="agentId")
            if agent_id is not None and agent_id != "main":
                raise ValueError(f'unknown agent id "{agent_id}"')
            timestamp_ms = _timestamp_ms(now_ms)
            parent_session_key = _optional_non_empty_string(
                payload.get("parentSessionKey"),
                label="parentSessionKey",
            )
            canonical_parent_session_key: str | None = None
            if parent_session_key is not None:
                parent_payload = await self._sessions_service.build_session_payload_for_key(
                    session_key=parent_session_key,
                    now_ms=timestamp_ms,
                )
                if parent_payload is None:
                    raise ValueError(f"unknown parent session: {parent_session_key}")
                canonical_parent_session_key = str(parent_payload["key"])

            requested_key = _optional_non_empty_string(payload.get("key"), label="key")
            if requested_key is not None:
                canonical_key = _canonical_session_key(requested_key)
            else:
                base_session_key = (
                    canonical_parent_session_key or await self._sessions_service.main_session_key()
                )
                generated_thread_id = f"gateway-create-{secrets.token_hex(6)}"
                canonical_key = resolve_thread_session_keys(
                    base_session_key=base_session_key,
                    thread_id=generated_thread_id,
                ).session_key

            initial_message = _resolve_optional_initial_session_message(
                task=payload.get("task"),
                message=payload.get("message"),
            )
            if initial_message is not None and self._chat_send_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.create initial send is unavailable until control chat runtime "
                        "is wired"
                    ),
                    status_code=503,
                )

            metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            raw_metadata = metadata_row.get("metadata") if metadata_row is not None else None
            metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
            label = _optional_non_empty_string(payload.get("label"), label="label")
            model = _optional_non_empty_string(payload.get("model"), label="model")
            if label is not None:
                metadata["label"] = label
            if model is not None:
                metadata["model"] = model
            if canonical_parent_session_key is not None:
                metadata["parentSessionKey"] = canonical_parent_session_key
            if metadata:
                await self._database.upsert_gateway_session_metadata(
                    session_key=canonical_key,
                    metadata=metadata,
                )

            entry = await self._sessions_service.build_session_payload_for_key(
                session_key=canonical_key,
                now_ms=timestamp_ms,
            )
            if entry is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.create could not materialize the created session",
                    status_code=503,
                )

            response: dict[str, Any] = {
                "ok": True,
                "key": canonical_key,
                "sessionId": entry["sessionId"],
                "entry": entry,
            }
            if initial_message is not None and self._chat_send_service is not None:
                send_result = await self._chat_send_service(
                    session_key=canonical_key,
                    message=initial_message,
                    idempotency_key=secrets.token_urlsafe(18),
                    thinking=None,
                    deliver=None,
                    timeout_ms=None,
                )
                self._remember_gateway_chat_run(
                    canonical_key,
                    send_result,
                    started_at_ms=timestamp_ms,
                )
                response["runStarted"] = bool(
                    isinstance(send_result.get("runId"), str)
                    and str(send_result.get("status") or "").strip().lower() == "ok"
                )
                response.update(send_result)

            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="create",
                now_ms=now_ms,
            )
            if initial_message is not None:
                await self._publish_sessions_changed_event(
                    session_key=canonical_key,
                    reason="send",
                    now_ms=now_ms,
                )
            return response

        if resolved_method == "sessions.patch":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "key",
                    "label",
                    "thinkingLevel",
                    "fastMode",
                    "verboseLevel",
                    "traceLevel",
                    "reasoningLevel",
                    "responseUsage",
                    "elevatedLevel",
                    "execHost",
                    "execSecurity",
                    "execAsk",
                    "execNode",
                    "model",
                    "spawnedBy",
                    "spawnedWorkspaceDir",
                    "spawnDepth",
                    "subagentRole",
                    "subagentControlScope",
                    "sendPolicy",
                    "groupActivation",
                ),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            if "label" in payload and payload.get("label") is not None:
                _require_session_label(payload.get("label"), label="label")
            _optional_non_empty_string(payload.get("thinkingLevel"), label="thinkingLevel")
            _optional_bool(payload.get("fastMode"), label="fastMode")
            _optional_non_empty_string(payload.get("verboseLevel"), label="verboseLevel")
            _optional_non_empty_string(payload.get("traceLevel"), label="traceLevel")
            _optional_non_empty_string(payload.get("reasoningLevel"), label="reasoningLevel")
            _optional_enum_value(
                payload.get("responseUsage"),
                label="responseUsage",
                allowed_values=_SESSION_PATCH_RESPONSE_USAGE_VALUES,
            )
            _optional_non_empty_string(payload.get("elevatedLevel"), label="elevatedLevel")
            _optional_non_empty_string(payload.get("execHost"), label="execHost")
            _optional_non_empty_string(payload.get("execSecurity"), label="execSecurity")
            _optional_non_empty_string(payload.get("execAsk"), label="execAsk")
            _optional_non_empty_string(payload.get("execNode"), label="execNode")
            _optional_non_empty_string(payload.get("model"), label="model")
            _optional_non_empty_string(payload.get("spawnedBy"), label="spawnedBy")
            _optional_non_empty_string(
                payload.get("spawnedWorkspaceDir"),
                label="spawnedWorkspaceDir",
            )
            _optional_min_int(payload.get("spawnDepth"), label="spawnDepth", minimum=0)
            _optional_enum_value(
                payload.get("subagentRole"),
                label="subagentRole",
                allowed_values=_SESSION_PATCH_SUBAGENT_ROLE_VALUES,
            )
            _optional_enum_value(
                payload.get("subagentControlScope"),
                label="subagentControlScope",
                allowed_values=_SESSION_PATCH_SUBAGENT_CONTROL_SCOPE_VALUES,
            )
            _optional_enum_value(
                payload.get("sendPolicy"),
                label="sendPolicy",
                allowed_values=_SESSION_PATCH_SEND_POLICY_VALUES,
            )
            _optional_enum_value(
                payload.get("groupActivation"),
                label="groupActivation",
                allowed_values=_SESSION_PATCH_GROUP_ACTIVATION_VALUES,
            )
            if self._database is None or self._sessions_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="sessions.patch is unavailable until session patch storage is wired",
                    status_code=503,
                )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            canonical_key = _canonical_session_key(session_key)
            current_session_key = await self._sessions_service.current_session_key()
            if canonical_key not in set(_session_key_aliases(current_session_key)):
                raise ValueError(f"session not found: {session_key}")
            existing_metadata_row = await self._database.get_gateway_session_metadata(canonical_key)
            existing_metadata: dict[str, Any] = {}
            if isinstance(existing_metadata_row, dict):
                metadata_value = existing_metadata_row.get("metadata")
                if isinstance(metadata_value, dict):
                    existing_metadata = dict(metadata_value)
            next_metadata = dict(existing_metadata)
            for field in (
                "label",
                "thinkingLevel",
                "fastMode",
                "verboseLevel",
                "traceLevel",
                "reasoningLevel",
                "responseUsage",
                "elevatedLevel",
                "execHost",
                "execSecurity",
                "execAsk",
                "execNode",
                "model",
                "spawnedBy",
                "spawnedWorkspaceDir",
                "spawnDepth",
                "subagentRole",
                "subagentControlScope",
                "sendPolicy",
                "groupActivation",
            ):
                if field not in payload:
                    continue
                value = payload.get(field)
                if value is None:
                    next_metadata.pop(field, None)
                else:
                    next_metadata[field] = value
            if next_metadata:
                await self._database.upsert_gateway_session_metadata(
                    session_key=canonical_key,
                    metadata=next_metadata,
                )
            else:
                await self._database.delete_gateway_session_metadata(canonical_key)
            entry = await self._sessions_service.build_current_session_payload(
                now_ms=_timestamp_ms(now_ms)
            )
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="patch",
                now_ms=now_ms,
            )
            return {
                "ok": True,
                "path": str(self._database.path),
                "key": canonical_key,
                "entry": entry,
                "resolved": {
                    "modelProvider": entry.get("modelProvider"),
                    "model": entry.get("model"),
                },
            }

        if resolved_method == "chat.abort":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("sessionKey", "runId"),
            )
            session_key = _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            run_id = None
            if "runId" in payload and payload.get("runId") is not None:
                run_id = _require_string(payload.get("runId"), label="runId")
                if run_id == "":
                    run_id = None
            return await self._abort_gateway_chat_run(
                session_key=session_key,
                run_id=run_id,
            )

        if resolved_method == "agent":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "message",
                    "agentId",
                    "provider",
                    "model",
                    "to",
                    "replyTo",
                    "sessionId",
                    "sessionKey",
                    "thinking",
                    "deliver",
                    "attachments",
                    "channel",
                    "replyChannel",
                    "accountId",
                    "replyAccountId",
                    "threadId",
                    "groupId",
                    "groupChannel",
                    "groupSpace",
                    "timeout",
                    "bestEffortDeliver",
                    "lane",
                    "extraSystemPrompt",
                    "bootstrapContextMode",
                    "bootstrapContextRunKind",
                    "internalEvents",
                    "inputProvenance",
                    "idempotencyKey",
                    "label",
                ),
            )
            _require_non_empty_string(payload.get("message"), label="message")
            agent_id = _optional_normalized_string(payload.get("agentId"), label="agentId")
            if agent_id is not None and agent_id != "main":
                raise ValueError(f'unknown agent id "{agent_id}"')
            requested_provider = _optional_normalized_string(
                payload.get("provider"),
                label="provider",
            )
            requested_model = _optional_normalized_string(
                payload.get("model"),
                label="model",
            )
            requested_to = _optional_normalized_string(
                payload.get("to"),
                label="to",
            )
            requested_reply_to = _optional_normalized_string(
                payload.get("replyTo"),
                label="replyTo",
            )
            requested_channel = _optional_normalized_string(
                payload.get("channel"),
                label="channel",
            )
            requested_reply_channel = _optional_normalized_string(
                payload.get("replyChannel"),
                label="replyChannel",
            )
            for channel_hint in (requested_channel, requested_reply_channel):
                _validate_agent_channel_hint(channel_hint)
            if requested_channel is not None and requested_channel.lower() == "last":
                requested_channel = None
            if requested_reply_channel is not None and requested_reply_channel.lower() == "last":
                requested_reply_channel = None
            requested_account_id = _optional_normalized_string(
                payload.get("accountId"),
                label="accountId",
            )
            requested_reply_account_id = _optional_normalized_string(
                payload.get("replyAccountId"),
                label="replyAccountId",
            )
            requested_thread_id = _optional_normalized_string(
                payload.get("threadId"),
                label="threadId",
            )
            requested_group_id = _optional_normalized_string(
                payload.get("groupId"),
                label="groupId",
            )
            requested_group_channel = _optional_normalized_string(
                payload.get("groupChannel"),
                label="groupChannel",
            )
            requested_group_space = _optional_normalized_string(
                payload.get("groupSpace"),
                label="groupSpace",
            )
            requested_lane = _optional_normalized_string(
                payload.get("lane"),
                label="lane",
            )
            requested_extra_system_prompt = _optional_normalized_string(
                payload.get("extraSystemPrompt"),
                label="extraSystemPrompt",
            )
            requested_deliver = _optional_bool(payload.get("deliver"), label="deliver")
            attachments = payload.get("attachments")
            if attachments is not None and not isinstance(attachments, list):
                raise ValueError("attachments must be an array")
            has_effective_attachments = _has_effective_agent_attachments(attachments)
            _optional_min_int(payload.get("timeout"), label="timeout", minimum=0)
            requested_best_effort_deliver = _optional_bool(
                payload.get("bestEffortDeliver"),
                label="bestEffortDeliver",
            )
            _optional_enum_value(
                payload.get("bootstrapContextMode"),
                label="bootstrapContextMode",
                allowed_values={"full", "lightweight"},
            )
            _optional_enum_value(
                payload.get("bootstrapContextRunKind"),
                label="bootstrapContextRunKind",
                allowed_values={"default", "heartbeat", "cron"},
            )
            if "internalEvents" in payload and payload.get("internalEvents") is not None:
                _validate_agent_internal_events(
                    payload.get("internalEvents"),
                    label="internalEvents",
                )
            if "inputProvenance" in payload and payload.get("inputProvenance") is not None:
                _validate_agent_input_provenance(
                    payload.get("inputProvenance"),
                    label="inputProvenance",
                )
            message = _require_non_empty_string(payload.get("message"), label="message")
            requested_session_key = _optional_normalized_string(
                payload.get("sessionKey"),
                label="sessionKey",
            )
            requested_session_id = _optional_normalized_string(
                payload.get("sessionId"),
                label="sessionId",
            )
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            timeout_ms = _optional_min_int(payload.get("timeout"), label="timeout", minimum=0)
            idempotency_key = _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            requested_label = _optional_session_label(payload.get("label"), label="label")
            if (
                requested_session_key is not None
                and classify_session_key_shape(requested_session_key) == "malformed_agent"
            ):
                raise ValueError(
                    f'invalid agent params: malformed session key "{requested_session_key}"'
                )
            if requested_session_key is not None and agent_id is not None:
                session_agent_id = resolve_agent_id_from_session_key(requested_session_key)
                if session_agent_id != agent_id:
                    raise ValueError(
                        f'invalid agent params: agent "{agent_id}" does not match session key '
                        f'agent "{session_agent_id}"'
                    )
            if (
                self._database is None
                or self._sessions_service is None
                or self._chat_send_service is None
            ):
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="agent is unavailable until gateway agent runtime bridge is wired",
                    status_code=503,
                )
            if (
                any(
                    value is not None
                    for value in (
                        requested_provider,
                        requested_model,
                        requested_to,
                        requested_reply_to,
                        requested_channel,
                        requested_reply_channel,
                        requested_account_id,
                        requested_reply_account_id,
                        requested_thread_id,
                        requested_group_id,
                        requested_group_channel,
                        requested_group_space,
                        requested_lane,
                        requested_extra_system_prompt,
                        payload.get("bootstrapContextMode"),
                        payload.get("bootstrapContextRunKind"),
                        payload.get("inputProvenance"),
                    )
                )
                or bool(payload.get("internalEvents"))
                or (
                    requested_deliver is True
                    or requested_best_effort_deliver is True
                    or has_effective_attachments
                )
            ):
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "agent only supports bounded control-chat session launches in "
                        "OpenZues today"
                    ),
                    status_code=503,
                )
            timestamp_ms = _timestamp_ms(now_ms)
            if requested_session_key is None and requested_session_id is None:
                target_session_key = await self._sessions_service.main_session_key()
            else:
                resolved_session = await self._sessions_service.resolve_key(
                    key=requested_session_key,
                    session_id=requested_session_id,
                    label=None,
                    agent_id=agent_id,
                    spawned_by=None,
                    include_global=True,
                    include_unknown=False,
                )
                target_session_key = _canonical_session_key(
                    _require_non_empty_string(
                        resolved_session.get("key"),
                        label="key",
                    )
                )
            if requested_label is not None:
                existing_metadata_row = await self._database.get_gateway_session_metadata(
                    target_session_key
                )
                next_session_metadata: dict[str, Any] = {}
                if isinstance(existing_metadata_row, dict):
                    existing_metadata_value = existing_metadata_row.get("metadata")
                    if isinstance(existing_metadata_value, dict):
                        next_session_metadata.update(existing_metadata_value)
                next_session_metadata["label"] = requested_label
                await self._database.upsert_gateway_session_metadata(
                    session_key=target_session_key,
                    metadata=next_session_metadata,
                )
            send_result = await self._chat_send_service(
                session_key=target_session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=requested_deliver,
                timeout_ms=timeout_ms,
            )
            self._remember_gateway_chat_run(
                target_session_key,
                send_result,
                started_at_ms=timestamp_ms,
            )
            await self._publish_sessions_changed_event(
                session_key=target_session_key,
                reason="send",
                now_ms=timestamp_ms,
            )
            return {
                "runId": _string_or_none(send_result.get("runId")) or idempotency_key,
                "status": "accepted",
                "acceptedAt": timestamp_ms,
            }

        if resolved_method == "agent.wait":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("runId", "timeoutMs"),
            )
            run_id = _require_non_empty_string(payload.get("runId"), label="runId")
            timeout_ms = _optional_min_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
            )
            return await self._wait_for_gateway_chat_run(
                run_id=run_id,
                timeout_ms=timeout_ms or 30_000,
            )

        if resolved_method == "agents.create":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("name", "workspace", "model", "emoji", "avatar"),
            )
            _require_non_empty_string(payload.get("name"), label="name")
            _require_non_empty_string(payload.get("workspace"), label="workspace")
            _optional_non_empty_string(payload.get("model"), label="model")
            if "emoji" in payload and payload.get("emoji") is not None:
                _require_string(payload.get("emoji"), label="emoji")
            if "avatar" in payload and payload.get("avatar") is not None:
                _require_string(payload.get("avatar"), label="avatar")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "agents.create is unavailable until multi-agent registry mutation is wired"
                ),
                status_code=503,
            )

        if resolved_method == "agents.update":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "name", "workspace", "model", "emoji", "avatar"),
            )
            _require_non_empty_string(payload.get("agentId"), label="agentId")
            _optional_non_empty_string(payload.get("name"), label="name")
            _optional_non_empty_string(payload.get("workspace"), label="workspace")
            _optional_non_empty_string(payload.get("model"), label="model")
            if "emoji" in payload and payload.get("emoji") is not None:
                _require_string(payload.get("emoji"), label="emoji")
            if "avatar" in payload and payload.get("avatar") is not None:
                _require_string(payload.get("avatar"), label="avatar")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "agents.update is unavailable until multi-agent registry mutation is wired"
                ),
                status_code=503,
            )

        if resolved_method == "agents.delete":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "deleteFiles"),
            )
            _require_non_empty_string(payload.get("agentId"), label="agentId")
            _optional_bool(payload.get("deleteFiles"), label="deleteFiles")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "agents.delete is unavailable until multi-agent registry mutation is wired"
                ),
                status_code=503,
            )

        if resolved_method == "doctor.memory.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "doctor.memory.status is unavailable until gateway memory doctor runtime "
                    "is wired"
                ),
                status_code=503,
            )

        if resolved_method in {
            "doctor.memory.dreamDiary",
            "doctor.memory.backfillDreamDiary",
            "doctor.memory.resetDreamDiary",
            "doctor.memory.resetGroundedShortTerm",
            "doctor.memory.repairDreamingArtifacts",
            "doctor.memory.dedupeDreamDiary",
        }:
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    f"{resolved_method} is unavailable until gateway dreaming runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "agents.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return await self._agents_service.list_agents()

        if resolved_method == "agent.identity.get":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "sessionKey"),
            )
            requested_agent_id = _optional_normalized_string(
                payload.get("agentId"),
                label="agentId",
            )
            requested_session_key = _optional_normalized_string(
                payload.get("sessionKey"),
                label="sessionKey",
            )
            if (
                requested_session_key is not None
                and classify_session_key_shape(requested_session_key) == "malformed_agent"
            ):
                raise ValueError(
                    "invalid agent.identity.get params: malformed session key "
                    f'"{requested_session_key}"'
                )
            if requested_session_key is not None and requested_agent_id is not None:
                session_agent_id = resolve_agent_id_from_session_key(requested_session_key)
                if session_agent_id != requested_agent_id:
                    raise ValueError(
                        f'invalid agent.identity.get params: agent "{requested_agent_id}" does '
                        f'not match session key agent "{session_agent_id}"'
                    )
            return await self._agents_service.get_identity(
                agent_id=requested_agent_id,
                session_key=requested_session_key,
            )

        if resolved_method == "agents.files.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("agentId",))
            if self._agent_files_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "agents.files.list is unavailable until workspace file inventory is wired"
                    ),
                    status_code=503,
                )
            agent_id = _require_non_empty_string(payload.get("agentId"), label="agentId")
            return await self._agent_files_service.list_files(agent_id=agent_id)

        if resolved_method == "agents.files.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("agentId", "name"))
            if self._agent_files_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="agents.files.get is unavailable until workspace file reads are wired",
                    status_code=503,
                )
            agent_id = _require_non_empty_string(payload.get("agentId"), label="agentId")
            name = _require_non_empty_string(payload.get("name"), label="name")
            return await self._agent_files_service.get_file(agent_id=agent_id, name=name)

        if resolved_method == "agents.files.set":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "name", "content"),
            )
            if self._agent_files_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="agents.files.set is unavailable until workspace file writes are wired",
                    status_code=503,
                )
            agent_id = _require_non_empty_string(payload.get("agentId"), label="agentId")
            name = _require_non_empty_string(payload.get("name"), label="name")
            content = _require_string(payload.get("content"), label="content")
            return await self._agent_files_service.set_file(
                agent_id=agent_id,
                name=name,
                content=content,
            )

        if resolved_method == "health":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return self._health_service.build_snapshot()

        if resolved_method == "gateway.identity.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._gateway_identity_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="gateway identity unavailable",
                    status_code=503,
                )
            identity = self._gateway_identity_service.load()
            return {"id": identity.id, "publicKey": identity.public_key}

        if resolved_method == "system-presence":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._system_presence_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="system presence unavailable",
                    status_code=503,
                )
            return self._system_presence_service.build_snapshot(now_ms=_timestamp_ms(now_ms))

        if resolved_method == "system-event":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "text",
                    "deviceId",
                    "instanceId",
                    "host",
                    "ip",
                    "mode",
                    "version",
                    "platform",
                    "deviceFamily",
                    "modelIdentifier",
                    "lastInputSeconds",
                    "reason",
                    "roles",
                    "scopes",
                    "tags",
                ),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="system-event is unavailable until gateway event logging is wired",
                    status_code=503,
                )
            event_payload: dict[str, Any] = {
                "text": _require_non_empty_string(payload.get("text"), label="text"),
            }
            for key in (
                "deviceId",
                "instanceId",
                "host",
                "ip",
                "mode",
                "version",
                "platform",
                "deviceFamily",
                "modelIdentifier",
                "reason",
            ):
                value = _optional_non_empty_string(payload.get(key), label=key)
                if value is not None:
                    event_payload[key] = value
            last_input_seconds = _optional_bounded_int(
                payload.get("lastInputSeconds"),
                label="lastInputSeconds",
                minimum=0,
                maximum=86_400_000,
            )
            if last_input_seconds is not None:
                event_payload["lastInputSeconds"] = last_input_seconds
            for key in ("roles", "scopes", "tags"):
                values = _optional_string_list(payload.get(key), label=key)
                if values:
                    event_payload[key] = values
            await self._database.append_event(
                instance_id=None,
                thread_id=None,
                method="system-event",
                payload=event_payload,
            )
            if self._system_presence_service is not None:
                presence_snapshot = self._system_presence_service.build_snapshot(
                    now_ms=_timestamp_ms(now_ms)
                )
                await self._publish_gateway_event(
                    "presence",
                    {"presence": list(presence_snapshot.get("entries") or [])},
                )
            return {"ok": True}

        if resolved_method == "last-heartbeat":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._last_heartbeat_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="last-heartbeat is unavailable until gateway events are wired",
                    status_code=503,
                )
            return await self._last_heartbeat_service.build_snapshot()

        if resolved_method == "set-heartbeats":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("enabled",))
            enabled_value = _require_bool(payload.get("enabled"), label="enabled")
            if self._set_heartbeats_enabled is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "set-heartbeats is unavailable until gateway heartbeat toggle runtime "
                        "is wired"
                    ),
                    status_code=503,
                )
            return {"ok": True, "enabled": await self._set_heartbeats_enabled(enabled_value)}

        if resolved_method == "voicewake.set":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("triggers",))
            if self._voicewake_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="voice wake config unavailable",
                    status_code=503,
                )
            config = self._voicewake_service.set_triggers(
                _require_string_array(payload.get("triggers"), label="triggers"),
                now_ms=_timestamp_ms(now_ms),
            )
            trigger_payload = {"triggers": list(config.triggers)}
            for known_node in self.registry.list_known_nodes():
                if known_node.connected:
                    self.registry.send_event(
                        known_node.node_id,
                        "voicewake.changed",
                        trigger_payload,
                    )
            await self._publish_gateway_event("voicewake.changed", trigger_payload)
            return trigger_payload

        if resolved_method == "skills.bins":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return {"bins": self._skill_bins_service.list_bins()}

        if resolved_method == "skills.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("agentId",))
            return self._skill_status_service.build_report(
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId")
            )

        if resolved_method == "skills.search":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("agentId", "limit", "query"),
            )
            return self._skill_catalog_service.search(
                query=_optional_non_empty_string(payload.get("query"), label="query"),
                limit=_optional_bounded_int(
                    payload.get("limit"),
                    label="limit",
                    minimum=1,
                    maximum=100,
                ),
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId"),
            )

        if resolved_method == "skills.detail":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("agentId", "slug"))
            return self._skill_catalog_service.detail(
                slug=_require_non_empty_string(payload.get("slug"), label="slug"),
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId"),
            )

        if resolved_method == "skills.install":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "dangerouslyForceUnsafeInstall",
                    "force",
                    "installId",
                    "name",
                    "slug",
                    "source",
                    "timeoutMs",
                    "version",
                ),
            )
            source = _optional_non_empty_string(payload.get("source"), label="source")
            if source == "clawhub":
                slug = _require_non_empty_string(payload.get("slug"), label="slug")
                version = _optional_non_empty_string(payload.get("version"), label="version")
                force = bool(_optional_bool(payload.get("force"), label="force"))
                try:
                    return await self._skill_clawhub_service.install(
                        slug=slug,
                        version=version,
                        force=force,
                    )
                except GatewaySkillClawHubUnavailableError as exc:
                    raise GatewayNodeMethodError(
                        code="UNAVAILABLE",
                        message=str(exc),
                        status_code=503,
                    ) from exc
                except RuntimeError as exc:
                    raise GatewayNodeMethodError(
                        code="INSTALL_FAILED",
                        message=str(exc),
                        status_code=500,
                    ) from exc
            _require_non_empty_string(payload.get("name"), label="name")
            _require_non_empty_string(payload.get("installId"), label="installId")
            dangerously_force_unsafe_install = _optional_bool(
                payload.get("dangerouslyForceUnsafeInstall"),
                label="dangerouslyForceUnsafeInstall",
            )
            timeout_ms = _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=1,
                maximum=2_592_000_000,
            )
            try:
                return await self._skill_install_service.install(
                    name=_require_non_empty_string(payload.get("name"), label="name"),
                    install_id=_require_non_empty_string(
                        payload.get("installId"),
                        label="installId",
                    ),
                    dangerously_force_unsafe_install=bool(dangerously_force_unsafe_install),
                    timeout_ms=timeout_ms,
                )
            except RuntimeError as exc:
                raise GatewayNodeMethodError(
                    code="INSTALL_FAILED",
                    message=str(exc),
                    status_code=500,
                ) from exc

        if resolved_method == "skills.update":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "all",
                    "apiKey",
                    "enabled",
                    "env",
                    "force",
                    "skillKey",
                    "slug",
                    "source",
                    "version",
                ),
            )
            source = _optional_non_empty_string(payload.get("source"), label="source")
            if source == "clawhub" or "slug" in payload or "all" in payload:
                clawhub_slug = (
                    _optional_non_empty_string(payload.get("slug"), label="slug")
                    if "slug" in payload
                    else None
                )
                all_installed = (
                    bool(_optional_bool(payload.get("all"), label="all"))
                    if "all" in payload
                    else False
                )
                version = (
                    _optional_non_empty_string(payload.get("version"), label="version")
                    if "version" in payload
                    else None
                )
                force = (
                    bool(_optional_bool(payload.get("force"), label="force"))
                    if "force" in payload
                    else False
                )
                try:
                    return await self._skill_clawhub_service.update(
                        slug=clawhub_slug,
                        all_installed=all_installed,
                        version=version,
                        force=force,
                    )
                except GatewaySkillClawHubUnavailableError as exc:
                    raise GatewayNodeMethodError(
                        code="UNAVAILABLE",
                        message=str(exc),
                        status_code=503,
                    ) from exc
                except RuntimeError as exc:
                    raise GatewayNodeMethodError(
                        code="UPDATE_FAILED",
                        message=str(exc),
                        status_code=500,
                    ) from exc
            skill_key = _require_non_empty_string(payload.get("skillKey"), label="skillKey")
            enabled_flag = (
                _optional_bool(payload.get("enabled"), label="enabled")
                if "enabled" in payload
                else None
            )
            api_key_value = (
                _require_string(payload.get("apiKey"), label="apiKey")
                if "apiKey" in payload
                else None
            )
            env_mapping = (
                _require_string_mapping(payload.get("env"), label="env")
                if "env" in payload
                else None
            )
            updated_config = self._skill_config_service.update_entry(
                skill_key=skill_key,
                enabled=enabled_flag,
                api_key=api_key_value,
                env=env_mapping,
            )
            return {"ok": True, "skillKey": skill_key, "config": updated_config}

        if resolved_method == "node.pair.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            pending_requests = []
            paired_payloads: dict[str, dict[str, object]] = {}
            if self._pairing_service is not None:
                stored_paired_nodes = await self._pairing_service.list_paired_nodes()
                known_nodes_by_id = {
                    node.node_id: node for node in self.registry.list_known_nodes()
                }
                for stored_paired_node in stored_paired_nodes:
                    existing_node = known_nodes_by_id.get(stored_paired_node.node_id)
                    if existing_node is not None:
                        await self._stage_scope_upgrade_request(
                            existing_node,
                            paired_node=stored_paired_node,
                            now_ms=now_ms,
                        )
                    stored_payload = _stored_paired_node_payload(stored_paired_node)
                    paired_payloads[stored_paired_node.node_id] = (
                        stored_payload
                        if existing_node is None
                        else _merge_paired_node_payload(
                            stored_payload,
                            _paired_node_payload(existing_node),
                        )
                    )
                pending_requests = await self._pairing_service.list_pending()
            return {
                "pending": pending_requests,
                "paired": sorted(paired_payloads.values(), key=_paired_node_sort_key),
            }

        if resolved_method == "node.pair.request":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "nodeId",
                    "displayName",
                    "platform",
                    "version",
                    "coreVersion",
                    "uiVersion",
                    "deviceFamily",
                    "modelIdentifier",
                    "caps",
                    "commands",
                    "remoteIp",
                    "silent",
                ),
            )
            if self._pairing_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node pairing storage unavailable",
                    status_code=503,
                )
            request_result = await self._request_node_pairing(
                node_id=_require_non_empty_string(payload.get("nodeId"), label="nodeId"),
                display_name=_optional_non_empty_string(
                    payload.get("displayName"),
                    label="displayName",
                ),
                platform=_optional_non_empty_string(payload.get("platform"), label="platform"),
                version=_optional_non_empty_string(payload.get("version"), label="version"),
                core_version=_optional_non_empty_string(
                    payload.get("coreVersion"),
                    label="coreVersion",
                ),
                ui_version=_optional_non_empty_string(
                    payload.get("uiVersion"),
                    label="uiVersion",
                ),
                device_family=_optional_non_empty_string(
                    payload.get("deviceFamily"),
                    label="deviceFamily",
                ),
                model_identifier=_optional_non_empty_string(
                    payload.get("modelIdentifier"),
                    label="modelIdentifier",
                ),
                caps=(
                    _optional_string_list(payload.get("caps"), label="caps")
                    if "caps" in payload
                    else None
                ),
                commands=(
                    _optional_string_list(payload.get("commands"), label="commands")
                    if "commands" in payload
                    else None
                ),
                remote_ip=_optional_non_empty_string(payload.get("remoteIp"), label="remoteIp"),
                silent=_optional_bool(payload.get("silent"), label="silent"),
                now_ms=now_ms,
            )
            return request_result

        if resolved_method == "node.pair.reject":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("requestId",))
            if self._pairing_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node pairing storage unavailable",
                    status_code=503,
                )
            rejected = await self._pairing_service.reject(
                _require_non_empty_string(payload.get("requestId"), label="requestId")
            )
            if rejected is None:
                raise ValueError("unknown requestId")
            await self._publish_gateway_event(
                "node.pair.resolved",
                {
                    "requestId": rejected["requestId"],
                    "nodeId": rejected["nodeId"],
                    "decision": "rejected",
                    "ts": _timestamp_ms(now_ms),
                },
            )
            return rejected

        if resolved_method == "node.pair.approve":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("requestId",))
            if self._pairing_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node pairing storage unavailable",
                    status_code=503,
                )
            request_id = _require_non_empty_string(payload.get("requestId"), label="requestId")
            approved = await self._pairing_service.approve(
                request_id,
                caller_scopes=resolved_requester.caller_scopes,
                now_ms=_timestamp_ms(now_ms),
            )
            if approved is None:
                raise ValueError("unknown requestId")
            if approved.get("status") == "forbidden":
                missing_scope = _require_non_empty_string(
                    approved.get("missingScope"),
                    label="missingScope",
                )
                raise ValueError(f"missing scope: {missing_scope}")
            approved_node = approved.get("node")
            if isinstance(approved_node, dict):
                await self._publish_gateway_event(
                    "node.pair.resolved",
                    {
                        "requestId": request_id,
                        "nodeId": _require_non_empty_string(
                            approved_node.get("nodeId"),
                            label="nodeId",
                        ),
                        "decision": "approved",
                        "ts": _timestamp_ms(now_ms),
                    },
                )
            return approved

        if resolved_method == "node.pair.verify":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("nodeId", "token"))
            if self._pairing_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node pairing storage unavailable",
                    status_code=503,
                )
            return await self._pairing_service.verify(
                _require_non_empty_string(payload.get("nodeId"), label="nodeId"),
                _require_non_empty_string(payload.get("token"), label="token"),
            )

        if resolved_method == "node.rename":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("nodeId", "displayName"))
            if self._pairing_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node pairing storage unavailable",
                    status_code=503,
                )
            renamed = await self._pairing_service.rename(
                _require_non_empty_string(payload.get("nodeId"), label="nodeId"),
                _require_non_empty_string(payload.get("displayName"), label="displayName"),
            )
            if renamed is None:
                raise ValueError("unknown nodeId")
            return renamed

        if resolved_method == "node.describe":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("nodeId",))
            wanted_node_id = _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            described_node = self.registry.describe_known_node(wanted_node_id)
            timestamp_ms = _timestamp_ms(now_ms)
            if described_node is not None:
                payload_node = _known_node_payload(described_node)
                if self._pairing_service is not None:
                    merged_paired_node = await self._pairing_service.get_paired_node(wanted_node_id)
                    if merged_paired_node is not None:
                        await self._stage_scope_upgrade_request(
                            described_node,
                            paired_node=merged_paired_node,
                            now_ms=now_ms,
                        )
                        payload_node = _merge_known_node_payload(
                            _known_paired_node_payload(merged_paired_node),
                            payload_node,
                        )
                return {"ts": timestamp_ms, **payload_node}
            if self._pairing_service is not None:
                stored_paired_node = await self._pairing_service.get_paired_node(wanted_node_id)
                if stored_paired_node is not None:
                    return {
                        "ts": timestamp_ms,
                        **_known_paired_node_payload(stored_paired_node),
                    }
            raise ValueError("unknown nodeId")

        if resolved_method == "node.canvas.capability.refresh":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            assert node_id is not None
            target_session = self.registry.get(node_id)
            if target_session is None or not str(target_session.canvas_host_url or "").strip():
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="canvas host unavailable for this node session",
                    status_code=503,
                )
            canvas_capability = _mint_canvas_capability_token()
            canvas_capability_expires_at_ms = _timestamp_ms(now_ms) + _CANVAS_CAPABILITY_TTL_MS
            scoped_canvas_host_url = _build_canvas_scoped_host_url(
                target_session.canvas_host_url,
                canvas_capability,
            )
            if scoped_canvas_host_url is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="failed to mint scoped canvas host URL",
                    status_code=503,
                )
            target_session.canvas_capability = canvas_capability
            target_session.canvas_capability_expires_at_ms = canvas_capability_expires_at_ms
            return {
                "canvasCapability": canvas_capability,
                "canvasCapabilityExpiresAtMs": canvas_capability_expires_at_ms,
                "canvasHostUrl": scoped_canvas_host_url,
            }

        if resolved_method == "node.event":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("event", "payload", "payloadJSON"),
            )
            if self._database is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="node.event is not wired to a server-node-events runtime yet",
                    status_code=503,
                )
            event_name = _require_non_empty_string(payload.get("event"), label="event")
            declared_payload = payload.get("payload")
            payload_json = payload.get("payloadJSON")
            if payload_json is not None and not isinstance(payload_json, str):
                raise ValueError("payloadJSON must be a string")
            resolved_payload_json = (
                payload_json
                if isinstance(payload_json, str)
                else json.dumps(declared_payload)
                if "payload" in payload
                else None
            )
            parsed_payload = declared_payload
            if parsed_payload is None and resolved_payload_json is not None:
                try:
                    parsed_payload = json.loads(resolved_payload_json)
                except json.JSONDecodeError:
                    parsed_payload = None
            event_record: dict[str, Any] = {
                "nodeId": node_id,
                "event": event_name,
                "payloadJSON": resolved_payload_json,
            }
            if "payload" in payload:
                event_record["payload"] = declared_payload
            await self._database.append_event(
                instance_id=None,
                thread_id=None,
                method="node.event",
                payload=event_record,
            )
            if self._hub is not None:
                await self._hub.publish(
                    {
                        "type": "node_event",
                        "nodeId": node_id,
                        "event": event_name,
                        "payload": parsed_payload,
                        "payloadJSON": resolved_payload_json,
                        "createdAt": utcnow(),
                    }
                )
            return {"ok": True}

        if resolved_method == "node.invoke":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("nodeId", "command", "params", "timeoutMs", "idempotencyKey"),
            )
            target_node_id = _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            command = _require_non_empty_string(payload.get("command"), label="command")
            idempotency_key = _require_non_empty_string(
                payload.get("idempotencyKey"),
                label="idempotencyKey",
            )
            timeout_ms = _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=0,
                maximum=2_592_000_000,
            )
            target_node = self.registry.describe_known_node(target_node_id)
            if target_node is None:
                raise ValueError("unknown nodeId")
            wake_attempt: GatewayNodeWakeAttempt | None = None
            if self.registry.get(target_node_id) is None and self._wake_node is not None:
                wake_attempt = _coerce_wake_attempt(await self._wake_node(target_node_id))
                if wake_attempt.available and self.registry.get(target_node_id) is None:
                    reconnected = await self._wait_for_node_connection(target_node_id)
                    wake_attempt = _wake_attempt_with_connection(
                        wake_attempt,
                        connected=reconnected,
                    )
                refreshed_node = self.registry.describe_known_node(target_node_id)
                if refreshed_node is not None:
                    target_node = refreshed_node
            if self.registry.get(target_node_id) is None:
                not_connected_details: dict[str, object] = {"code": "NOT_CONNECTED"}
                wake_details = _wake_attempt_details(wake_attempt)
                if wake_details is not None:
                    not_connected_details["wake"] = wake_details
                raise GatewayNodeMethodError(
                    code="NOT_CONNECTED",
                    message="node not connected",
                    status_code=503,
                    details=not_connected_details,
                )
            paired_node_record = (
                await self._pairing_service.get_paired_node(target_node_id)
                if self._pairing_service is not None
                else None
            )
            allowlist = resolve_node_command_allowlist(
                platform=(
                    target_node.platform
                    or (paired_node_record.platform if paired_node_record else None)
                ),
                device_family=(
                    target_node.device_family
                    or (paired_node_record.device_family if paired_node_record else None)
                ),
            )
            live_declared_commands = normalize_declared_node_commands(
                target_node.commands,
                allowlist=allowlist,
            )
            declared_commands = live_declared_commands
            scope_upgrade_request_id: str | None = None
            if paired_node_record is not None:
                scope_upgrade_request = await self._stage_scope_upgrade_request(
                    target_node,
                    paired_node=paired_node_record,
                    now_ms=now_ms,
                )
                scope_upgrade_request_id = _pairing_request_id_from_result(
                    scope_upgrade_request
                )
                approved_declared_commands = normalize_declared_node_commands(
                    paired_node_record.commands,
                    allowlist=allowlist,
                )
                visible_commands = _visible_paired_commands(
                    list(approved_declared_commands),
                    list(live_declared_commands),
                )
                declared_commands = tuple(visible_commands or ())
            allowed, reason = is_node_command_allowed(
                command=command,
                declared_commands=declared_commands,
                allowlist=allowlist,
            )
            if not allowed:
                trimmed_command = command.strip()
                if (
                    paired_node_record is not None
                    and scope_upgrade_request_id is not None
                    and trimmed_command in live_declared_commands
                    and trimmed_command not in declared_commands
                ):
                    raise GatewayNodeMethodError(
                        code="FAILED_PRECONDITION",
                        message=(
                            f"scope upgrade pending approval "
                            f"(requestId: {scope_upgrade_request_id})"
                        ),
                        status_code=409,
                    )
                raise ValueError(_build_node_command_rejection_hint(reason, command, target_node))

            result = await self.registry.invoke(
                node_id=target_node_id,
                command=command,
                params=payload.get("params"),
                timeout_ms=timeout_ms,
                idempotency_key=idempotency_key,
            )
            if not result.ok:
                error_payload = dict(result.error or {})
                error_code = str(error_payload.get("code") or "UNAVAILABLE")
                error_message = str(error_payload.get("message") or "node invoke failed")
                if error_code == "QUEUED_UNTIL_FOREGROUND":
                    raise GatewayNodeMethodError(
                        code="UNAVAILABLE",
                        message=error_message,
                        status_code=503,
                        details={
                            "code": "QUEUED_UNTIL_FOREGROUND",
                            "queuedActionId": result.queued_action_id,
                            "nodeId": target_node_id,
                            "command": command,
                            "nodeError": error_payload or None,
                        },
                        retryable=True,
                    )
                error_details: dict[str, object] | None = None
                if error_code == "NOT_CONNECTED":
                    error_details = {"code": "NOT_CONNECTED"}
                    wake_details = _wake_attempt_details(wake_attempt)
                    if wake_details is not None:
                        error_details["wake"] = wake_details
                raise GatewayNodeMethodError(
                    code=error_code,
                    message=error_message,
                    status_code=503,
                    details=error_details,
                )
            return {
                "ok": True,
                "nodeId": target_node_id,
                "command": command,
                "payload": result.payload,
                "payloadJSON": result.payload_json,
            }

        if resolved_method == "node.invoke.result":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "nodeId", "ok", "payload", "payloadJSON", "error"),
            )
            request_id = _require_non_empty_string(payload.get("id"), label="id")
            result_node_id = _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            if result_node_id != node_id:
                raise ValueError("nodeId does not match connected device identity")
            ok = _require_bool(payload.get("ok"), label="ok")
            payload_json = payload.get("payloadJSON")
            if payload_json is not None and not isinstance(payload_json, str):
                raise ValueError("payloadJSON must be a string")
            error = _optional_error_payload(payload.get("error"))
            handled = self.registry.handle_invoke_result(
                request_id=request_id,
                node_id=result_node_id,
                ok=ok,
                payload=payload.get("payload"),
                payload_json=payload_json,
                error=error,
            )
            if not handled:
                return {"ok": True, "ignored": True}
            return {"ok": True}

        if resolved_method == "node.pending.pull":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            assert node_id is not None
            pull_result = self.registry.pull_pending_actions_result(
                node_id,
                now_ms=now_ms,
            )
            return GatewayNodePendingActionPullView.model_validate(
                {"nodeId": pull_result.node_id, "actions": pull_result.actions}
            ).model_dump(mode="json", by_alias=True)

        if resolved_method == "node.pending.ack":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("ids",))
            ids = _require_string_list(payload.get("ids"), label="ids")
            assert node_id is not None
            ack_result = self.registry.ack_pending_actions_result(
                node_id,
                ids,
                now_ms=now_ms,
            )
            return GatewayNodePendingActionAckView.model_validate(
                {
                    "nodeId": ack_result.node_id,
                    "ackedIds": ack_result.acked_ids,
                    "remainingCount": ack_result.remaining_count,
                }
            ).model_dump(mode="json", by_alias=True)

        if resolved_method == "node.pending.drain":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("maxItems",))
            max_items = _optional_bounded_int(
                payload.get("maxItems"),
                label="maxItems",
                minimum=1,
                maximum=10,
            )
            assert node_id is not None
            drained_result = self.registry.drain_pending_work(
                node_id,
                max_items=max_items,
                include_default_status=True,
                now_ms=now_ms,
            )
            return GatewayNodePendingWorkDrainView.model_validate(
                {
                    "nodeId": node_id,
                    "revision": drained_result.revision,
                    "items": [
                        {
                            "id": item.id,
                            "type": item.type,
                            "priority": item.priority,
                            "createdAtMs": item.created_at_ms,
                            "expiresAtMs": item.expires_at_ms,
                            "payload": item.payload,
                        }
                        for item in drained_result.items
                    ],
                    "hasMore": drained_result.has_more,
                }
            ).model_dump(mode="json", by_alias=True)

        if resolved_method == "node.pending.enqueue":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("nodeId", "type", "priority", "expiresInMs", "payload", "wake"),
            )
            target_node_id = _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            work_type = _require_enum_value(
                payload.get("type"),
                label="type",
                allowed_values=_NODE_PENDING_WORK_TYPES,
            )
            priority = _optional_enum_value(
                payload.get("priority"),
                label="priority",
                allowed_values=_NODE_PENDING_WORK_PRIORITIES,
            )
            expires_in_ms = _optional_bounded_int(
                payload.get("expiresInMs"),
                label="expiresInMs",
                minimum=1_000,
                maximum=86_400_000,
            )
            wake = payload.get("wake")
            if wake is not None and not isinstance(wake, bool):
                raise ValueError("wake must be a boolean")
            pending_payload = None
            if "payload" in payload and payload["payload"] is not None:
                pending_payload = _require_unknown_mapping(payload["payload"], label="payload")

            queued = self.registry.enqueue_pending_work(
                node_id=target_node_id,
                work_type=cast(NodePendingWorkType, work_type),
                priority=cast(NodePendingWorkPriority | None, priority),
                expires_in_ms=expires_in_ms,
                payload=pending_payload,
            )
            wake_triggered = False
            if (
                wake is not False
                and not queued.deduped
                and self.registry.get(target_node_id) is None
                and self._wake_node is not None
            ):
                wake_attempt = _coerce_wake_attempt(await self._wake_node(target_node_id))
                wake_triggered = _wake_attempt_available(wake_attempt)
            return GatewayNodePendingWorkEnqueueView.model_validate(
                {
                    "nodeId": target_node_id,
                    "revision": queued.revision,
                    "queued": {
                        "id": queued.item.id,
                        "type": queued.item.type,
                        "priority": queued.item.priority,
                        "createdAtMs": queued.item.created_at_ms,
                        "expiresAtMs": queued.item.expires_at_ms,
                        "payload": queued.item.payload,
                    },
                    "wakeTriggered": wake_triggered,
                }
            ).model_dump(mode="json", by_alias=True)

        if resolved_method == "exec.approvals.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approvals.get is unavailable until exec approval policy config "
                    "runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approvals.set":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("file", "baseHash"),
            )
            _validate_exec_approvals_file_config(payload.get("file"), label="file")
            _optional_non_empty_string(payload.get("baseHash"), label="baseHash")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approvals.set is unavailable until exec approval policy config "
                    "runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approvals.node.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("nodeId",))
            _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approvals.node.get is unavailable until exec approval policy "
                    "config runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approvals.node.set":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("nodeId", "file", "baseHash"),
            )
            _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            _validate_exec_approvals_file_config(payload.get("file"), label="file")
            _optional_non_empty_string(payload.get("baseHash"), label="baseHash")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approvals.node.set is unavailable until exec approval policy "
                    "config runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approval.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("id",))
            _require_non_empty_string(payload.get("id"), label="id")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=("exec.approval.get is unavailable until exec approval runtime is wired"),
                status_code=503,
            )

        if resolved_method == "exec.approval.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=("exec.approval.list is unavailable until exec approval runtime is wired"),
                status_code=503,
            )

        if resolved_method == "exec.approval.request":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "id",
                    "command",
                    "commandArgv",
                    "systemRunPlan",
                    "env",
                    "cwd",
                    "nodeId",
                    "host",
                    "security",
                    "ask",
                    "agentId",
                    "resolvedPath",
                    "sessionKey",
                    "turnSourceChannel",
                    "turnSourceTo",
                    "turnSourceAccountId",
                    "turnSourceThreadId",
                    "timeoutMs",
                    "twoPhase",
                ),
            )
            if "id" in payload and payload.get("id") is not None:
                _require_non_empty_string(payload.get("id"), label="id")
            if "command" in payload and payload.get("command") is not None:
                _require_non_empty_string(payload.get("command"), label="command")
            if "commandArgv" in payload and payload.get("commandArgv") is not None:
                _require_string_array(payload.get("commandArgv"), label="commandArgv")
            if "systemRunPlan" in payload and payload.get("systemRunPlan") is not None:
                system_run_plan = payload.get("systemRunPlan")
                if not isinstance(system_run_plan, dict):
                    raise ValueError("systemRunPlan must be an object")
                _validate_exact_keys(
                    "systemRunPlan",
                    system_run_plan,
                    allowed_keys=(
                        "argv",
                        "cwd",
                        "commandText",
                        "commandPreview",
                        "agentId",
                        "sessionKey",
                        "mutableFileOperand",
                    ),
                )
                _require_string_array(system_run_plan.get("argv"), label="systemRunPlan.argv")
                if "cwd" not in system_run_plan:
                    raise ValueError("systemRunPlan.cwd is required")
                if system_run_plan.get("cwd") is not None:
                    _require_string(system_run_plan.get("cwd"), label="systemRunPlan.cwd")
                _require_string(
                    system_run_plan.get("commandText"),
                    label="systemRunPlan.commandText",
                )
                if (
                    "commandPreview" in system_run_plan
                    and system_run_plan.get("commandPreview") is not None
                ):
                    _require_string(
                        system_run_plan.get("commandPreview"),
                        label="systemRunPlan.commandPreview",
                    )
                for field in ("agentId", "sessionKey"):
                    if field not in system_run_plan:
                        raise ValueError(f"systemRunPlan.{field} is required")
                    if system_run_plan.get(field) is not None:
                        _require_string(
                            system_run_plan.get(field),
                            label=f"systemRunPlan.{field}",
                        )
                if "mutableFileOperand" in system_run_plan:
                    mutable_file_operand = system_run_plan.get("mutableFileOperand")
                    if mutable_file_operand is not None:
                        if not isinstance(mutable_file_operand, dict):
                            raise ValueError("systemRunPlan.mutableFileOperand must be an object")
                        _validate_exact_keys(
                            "systemRunPlan.mutableFileOperand",
                            mutable_file_operand,
                            allowed_keys=("argvIndex", "path", "sha256"),
                        )
                        argv_index = mutable_file_operand.get("argvIndex")
                        if (
                            isinstance(argv_index, bool)
                            or not isinstance(argv_index, int)
                            or argv_index < 0
                        ):
                            raise ValueError(
                                "systemRunPlan.mutableFileOperand.argvIndex must be an integer >= 0"
                            )
                        _require_string(
                            mutable_file_operand.get("path"),
                            label="systemRunPlan.mutableFileOperand.path",
                        )
                        _require_string(
                            mutable_file_operand.get("sha256"),
                            label="systemRunPlan.mutableFileOperand.sha256",
                        )
            if "env" in payload and payload.get("env") is not None:
                _require_string_mapping(payload.get("env"), label="env")
            if "nodeId" in payload and payload.get("nodeId") is not None:
                _require_non_empty_string(payload.get("nodeId"), label="nodeId")
            for field in (
                "cwd",
                "host",
                "security",
                "ask",
                "agentId",
                "resolvedPath",
                "sessionKey",
                "turnSourceChannel",
                "turnSourceTo",
                "turnSourceAccountId",
            ):
                if field in payload and payload.get(field) is not None:
                    _require_string(payload.get(field), label=field)
            if "turnSourceThreadId" in payload and payload.get("turnSourceThreadId") is not None:
                thread_id = payload.get("turnSourceThreadId")
                if isinstance(thread_id, bool) or not isinstance(thread_id, str | int | float):
                    raise ValueError("turnSourceThreadId must be a string or number")
            _optional_min_int(payload.get("timeoutMs"), label="timeoutMs", minimum=1)
            _optional_bool(payload.get("twoPhase"), label="twoPhase")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approval.request is unavailable until exec approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approval.waitDecision":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("id",))
            _require_non_empty_string(payload.get("id"), label="id")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approval.waitDecision is unavailable until exec approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "exec.approval.resolve":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "decision"),
            )
            _require_non_empty_string(payload.get("id"), label="id")
            _require_enum_value(
                payload.get("decision"),
                label="decision",
                allowed_values={"allow-once", "allow-always", "deny"},
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "exec.approval.resolve is unavailable until exec approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "plugin.approval.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "plugin.approval.list is unavailable until plugin approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "plugin.approval.request":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=(
                    "pluginId",
                    "title",
                    "description",
                    "severity",
                    "toolName",
                    "toolCallId",
                    "agentId",
                    "sessionKey",
                    "turnSourceChannel",
                    "turnSourceTo",
                    "turnSourceAccountId",
                    "turnSourceThreadId",
                    "timeoutMs",
                    "twoPhase",
                ),
            )
            if "pluginId" in payload and payload.get("pluginId") is not None:
                _require_non_empty_string(payload.get("pluginId"), label="pluginId")
            _require_non_empty_string(payload.get("title"), label="title")
            _require_non_empty_string(payload.get("description"), label="description")
            _optional_enum_value(
                payload.get("severity"),
                label="severity",
                allowed_values={"info", "warning", "critical"},
            )
            for field in (
                "toolName",
                "toolCallId",
                "agentId",
                "sessionKey",
                "turnSourceChannel",
                "turnSourceTo",
                "turnSourceAccountId",
            ):
                if field in payload and payload.get(field) is not None:
                    _require_string(payload.get(field), label=field)
            if "turnSourceThreadId" in payload and payload.get("turnSourceThreadId") is not None:
                thread_id = payload.get("turnSourceThreadId")
                if isinstance(thread_id, bool) or not isinstance(thread_id, str | int | float):
                    raise ValueError("turnSourceThreadId must be a string or number")
            _optional_min_int(payload.get("timeoutMs"), label="timeoutMs", minimum=1)
            _optional_bool(payload.get("twoPhase"), label="twoPhase")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "plugin.approval.request is unavailable until plugin approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "plugin.approval.waitDecision":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("id",))
            _require_non_empty_string(payload.get("id"), label="id")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "plugin.approval.waitDecision is unavailable until plugin approval runtime "
                    "is wired"
                ),
                status_code=503,
            )

        if resolved_method == "plugin.approval.resolve":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("id", "decision"),
            )
            _require_non_empty_string(payload.get("id"), label="id")
            _require_enum_value(
                payload.get("decision"),
                label="decision",
                allowed_values={"allow-once", "allow-always", "deny"},
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "plugin.approval.resolve is unavailable until plugin approval runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "device.pair.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "device.pair.list is unavailable until device auth pairing runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method in {
            "device.pair.approve",
            "device.pair.reject",
        }:
            _validate_exact_keys(resolved_method, payload, allowed_keys=("requestId",))
            _require_non_empty_string(payload.get("requestId"), label="requestId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    f"{resolved_method} is unavailable until device auth pairing runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "device.pair.remove":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("deviceId",))
            _require_non_empty_string(payload.get("deviceId"), label="deviceId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "device.pair.remove is unavailable until device auth pairing runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "device.token.rotate":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("deviceId", "role", "scopes"),
            )
            _require_non_empty_string(payload.get("deviceId"), label="deviceId")
            _require_non_empty_string(payload.get("role"), label="role")
            _optional_string_list(payload.get("scopes"), label="scopes")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "device.token.rotate is unavailable until device auth token runtime is wired"
                ),
                status_code=503,
            )

        if resolved_method == "device.token.revoke":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("deviceId", "role"),
            )
            _require_non_empty_string(payload.get("deviceId"), label="deviceId")
            _require_non_empty_string(payload.get("role"), label="role")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "device.token.revoke is unavailable until device auth token runtime is wired"
                ),
                status_code=503,
            )

        raise ValueError(f"unsupported method: {resolved_method}")

    async def _reload_secrets(self) -> dict[str, Any]:
        if (
            self._list_integration_views is None
            or self._list_notification_route_views is None
            or self._probe_secret is None
        ):
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "secrets.reload is unavailable until vault-backed secret inventory is wired"
                ),
                status_code=503,
            )

        warning_count = sum(
            1
            for integration in await self._list_integration_views()
            if integration.enabled
            and integration.vault_secret_id is not None
            and integration.auth_status == "degraded"
        )
        route_probe_cache: dict[int, str | None] = {}
        for route in await self._list_notification_route_views():
            if not route.enabled or route.vault_secret_id is None:
                continue
            secret_id = route.vault_secret_id
            if secret_id not in route_probe_cache:
                route_probe_cache[secret_id] = await self._probe_secret(secret_id)
            if route_probe_cache[secret_id]:
                warning_count += 1
        return {"ok": True, "warningCount": warning_count}

    async def _resolve_gateway_outbound_channel(
        self,
        value: object | None,
        *,
        reject_webchat_as_internal_only: bool = False,
        rejected_webchat_message: str | None = None,
    ) -> str:
        if value is not None:
            return _resolve_gateway_requested_channel(
                value,
                reject_webchat_as_internal_only=reject_webchat_as_internal_only,
                rejected_webchat_message=rejected_webchat_message,
            )
        configured_channels = await self._configured_gateway_outbound_channels()
        if len(configured_channels) == 1:
            return configured_channels[0]
        if not configured_channels:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="Channel is required (no configured channels detected).",
                status_code=400,
            )
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message=(
                "Channel is required when multiple channels are configured: "
                f"{', '.join(configured_channels)}"
            ),
            status_code=400,
        )

    async def _configured_gateway_outbound_channels(self) -> tuple[str, ...]:
        if self._list_notification_route_views is None:
            return ()

        configured: list[str] = []
        seen: set[str] = set()
        for route in await self._list_notification_route_views():
            if isinstance(route, dict):
                enabled = bool(route.get("enabled", True))
                conversation_target = route.get("conversation_target")
            else:
                enabled = bool(getattr(route, "enabled", True))
                conversation_target = getattr(route, "conversation_target", None)
            if not enabled or not conversation_target:
                continue

            if isinstance(conversation_target, dict):
                raw_channel = conversation_target.get("channel")
            else:
                raw_channel = getattr(conversation_target, "channel", None)
            if not isinstance(raw_channel, str):
                continue

            normalized_channel = _normalize_gateway_chat_channel_id(raw_channel)
            if normalized_channel is None or normalized_channel in seen:
                continue
            seen.add(normalized_channel)
            configured.append(normalized_channel)

        configured.sort(key=_gateway_chat_channel_sort_key)
        return tuple(configured)

    async def _resolve_effective_toolsets(self, session_key: str) -> list[str]:
        if self._database is None:
            return []

        metadata_row = await self._database.get_gateway_session_metadata(session_key)
        metadata = metadata_row.get("metadata") if metadata_row is not None else None
        metadata_toolsets = _toolsets_from_value(
            metadata.get("toolsets") if isinstance(metadata, dict) else None
        )
        if metadata_toolsets:
            return metadata_toolsets

        mission = await self._database.get_latest_mission_by_session_key(
            session_key,
            require_thread=False,
        )
        mission_toolsets = _toolsets_from_value(mission.get("toolsets") if mission else None)
        if mission_toolsets:
            return mission_toolsets

        gateway = await self._database.get_gateway_bootstrap()
        return _toolsets_from_value(gateway.get("toolsets") if gateway else None)

    async def _publish_gateway_event(self, event: str, payload: dict[str, Any]) -> None:
        if self._hub is None:
            return
        await self._hub.publish(
            {
                "type": "gateway_event",
                "event": event,
                "payload": payload,
                "createdAt": utcnow(),
            }
        )

    async def _publish_session_message_events(
        self,
        *,
        message_row: dict[str, Any],
        now_ms: int,
    ) -> None:
        if self._hub is None or self._sessions_service is None:
            return
        message_payload = await self._sessions_service.build_message_event_payload(
            message_row=message_row,
            now_ms=now_ms,
        )
        if message_payload is not None:
            await self._publish_gateway_event("session.message", message_payload)
        changed_payload = await self._sessions_service.build_message_changed_event_payload(
            message_row=message_row,
            now_ms=now_ms,
        )
        if changed_payload is not None:
            await self._publish_gateway_event("sessions.changed", changed_payload)

    async def _publish_sessions_changed_event(
        self,
        *,
        session_key: str,
        reason: str,
        now_ms: int | None,
        compacted: bool | None = None,
    ) -> None:
        if self._sessions_service is None:
            payload: dict[str, Any] = {
                "sessionKey": session_key,
                "reason": reason,
                "ts": _timestamp_ms(now_ms),
            }
            if compacted is not None:
                payload["compacted"] = compacted
            await self._publish_gateway_event("sessions.changed", payload)
            return

        payload = await self._sessions_service.build_changed_event_payload(
            session_key=session_key,
            reason=reason,
            now_ms=_timestamp_ms(now_ms),
            compacted=compacted,
        )
        await self._publish_gateway_event("sessions.changed", payload)

    def _require_connected_node_identity(
        self,
        method: str,
        requester: GatewayNodeMethodRequester,
    ) -> str:
        node_id = str(requester.node_id or "").strip()
        if node_id:
            if self.registry.get(node_id) is None:
                raise ValueError(f"{method} requires a connected device identity")
            return node_id
        client_id = str(requester.client_id or "").strip()
        if client_id and self.registry.get(client_id) is not None:
            return client_id
        raise ValueError(f"{method} requires a connected device identity")

    def _remember_gateway_chat_run(
        self,
        session_key: str,
        payload: dict[str, object],
        *,
        started_at_ms: int | None = None,
    ) -> None:
        run_id = payload.get("runId")
        if not isinstance(run_id, str):
            return
        trimmed_run_id = run_id.strip()
        if not trimmed_run_id:
            return
        canonical_session_key = _canonical_session_key(session_key)
        previous_run_id = self._tracked_gateway_chat_run_id(canonical_session_key)
        if previous_run_id is not None and previous_run_id != trimmed_run_id:
            self._gateway_tracked_chat_runs_by_id.pop(previous_run_id, None)
        self._gateway_tracked_chat_runs_by_id[trimmed_run_id] = GatewayTrackedChatRun(
            run_id=trimmed_run_id,
            session_key=canonical_session_key,
            started_at_ms=_timestamp_ms(started_at_ms),
        )
        for alias in _session_key_aliases(canonical_session_key):
            self._gateway_chat_run_ids_by_session_key[alias] = trimmed_run_id

    async def _abort_gateway_chat_run(
        self,
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        if self._chat_abort_service is None:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="chat.abort is unavailable until control chat cancellation is wired",
                status_code=503,
            )
        tracked_run_id = self._tracked_gateway_chat_run_id(session_key)
        if run_id is not None and tracked_run_id != run_id:
            return {"ok": True, "aborted": False, "runIds": []}
        interrupt_result = await self._chat_abort_service(
            session_key=session_key,
            run_id=run_id,
        )
        if interrupt_result.get("ok") is True:
            aborted_run_id = run_id or tracked_run_id
            self._forget_gateway_chat_run(session_key)
            return {
                "ok": True,
                "aborted": True,
                "runIds": [aborted_run_id] if aborted_run_id is not None else [],
            }
        if str(interrupt_result.get("reason") or "").strip().lower() == "no_active_turn":
            self._forget_gateway_chat_run(session_key)
            return {"ok": True, "aborted": False, "runIds": []}
        raise GatewayNodeMethodError(
            code="UNAVAILABLE",
            message="chat.abort failed to interrupt the active control chat run",
            status_code=503,
        )

    def _tracked_gateway_chat_run_id(self, session_key: str) -> str | None:
        for alias in _session_key_aliases(session_key):
            tracked_run_id = self._gateway_chat_run_ids_by_session_key.get(alias)
            if tracked_run_id is not None:
                return tracked_run_id
        return None

    async def _wait_for_gateway_chat_run(
        self,
        *,
        run_id: str,
        timeout_ms: int,
    ) -> dict[str, object]:
        if self._database is None:
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="agent.wait is unavailable until control chat run waiting is wired",
                status_code=503,
            )
        resolved_run_id = run_id.strip()
        deadline = time.monotonic() + (max(timeout_ms, 0) / 1000)
        slept = False
        while True:
            snapshot = await self._gateway_chat_terminal_snapshot(run_id=resolved_run_id)
            if snapshot is not None:
                return snapshot
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0 and (timeout_ms <= 0 or slept):
                return {"runId": resolved_run_id, "status": "timeout"}
            sleep_seconds = min(0.05, remaining_seconds) if remaining_seconds > 0 else 0.001
            await self._sleep(sleep_seconds)
            slept = True

    async def _gateway_chat_terminal_snapshot(self, *, run_id: str) -> dict[str, object] | None:
        if self._database is None:
            return None
        tracked_run = self._gateway_tracked_chat_runs_by_id.get(run_id)
        mission: dict[str, Any] | None = None
        if tracked_run is not None:
            mission = await self._database.get_latest_mission_by_session_key(
                tracked_run.session_key,
                require_thread=True,
            )
            if mission is None:
                mission = (
                    await self._database.get_latest_thread_child_mission_by_parent_session_key(
                        tracked_run.session_key,
                        require_thread=True,
                    )
                )
        if mission is None:
            mission = await self._database.get_latest_mission_by_run_id(
                run_id,
                require_session_key=True,
            )
            if mission is not None and tracked_run is None:
                mission_session_key = _string_or_none(mission.get("session_key"))
                if mission_session_key is not None:
                    tracked_run = GatewayTrackedChatRun(
                        run_id=run_id,
                        session_key=_canonical_session_key(mission_session_key),
                        started_at_ms=(
                            _iso8601_to_timestamp_ms(mission.get("created_at"))
                            or _timestamp_ms(None)
                        ),
                    )
                    self._gateway_tracked_chat_runs_by_id[run_id] = tracked_run
        if mission is None:
            return None
        status = str(mission.get("status") or "").strip().lower()
        if status not in {"completed", "failed"}:
            return None
        started_at_ms = (
            tracked_run.started_at_ms
            if tracked_run is not None
            else (
                _iso8601_to_timestamp_ms(mission.get("created_at"))
                or _iso8601_to_timestamp_ms(mission.get("updated_at"))
                or _timestamp_ms(None)
            )
        )
        ended_at_ms = (
            _iso8601_to_timestamp_ms(mission.get("updated_at"))
            or _iso8601_to_timestamp_ms(mission.get("created_at"))
            or started_at_ms
        )
        payload: dict[str, object] = {
            "runId": run_id,
            "status": "ok" if status == "completed" else "error",
            "startedAt": started_at_ms,
            "endedAt": max(started_at_ms, ended_at_ms),
        }
        error = _string_or_none(mission.get("last_error"))
        if status == "failed" and error is not None and error.strip():
            payload["error"] = error.strip()
        if tracked_run is not None:
            self._forget_gateway_chat_run(tracked_run.session_key)
        return payload

    def _forget_gateway_chat_run(self, session_key: str) -> None:
        canonical_session_key = _canonical_session_key(session_key)
        tracked_run_ids: set[str] = set()
        for alias in _session_key_aliases(canonical_session_key):
            tracked_run_id = self._gateway_chat_run_ids_by_session_key.pop(alias, None)
            if tracked_run_id is not None:
                tracked_run_ids.add(tracked_run_id)
        for tracked_run_id in tracked_run_ids:
            tracked_run = self._gateway_tracked_chat_runs_by_id.get(tracked_run_id)
            if tracked_run is not None and tracked_run.session_key == canonical_session_key:
                self._gateway_tracked_chat_runs_by_id.pop(tracked_run_id, None)


def _timestamp_ms(now_ms: int | None) -> int:
    return int(time.time() * 1000) if now_ms is None else int(now_ms)


def _session_key_aliases(session_key: str) -> tuple[str, ...]:
    aliases = session_key_lookup_aliases(session_key)
    if aliases:
        return aliases
    trimmed = session_key.strip()
    return (trimmed,) if trimmed else ()


def _canonical_session_key(session_key: str) -> str:
    aliases = _session_key_aliases(session_key)
    if aliases:
        return aliases[0]
    return session_key.strip()


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _bool_or_none(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _iso8601_to_timestamp_ms(value: object) -> int | None:
    text = _string_or_none(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(parsed.timestamp() * 1000)


def _mint_canvas_capability_token() -> str:
    return secrets.token_urlsafe(18)


async def _build_chat_history_payload(
    database: Database,
    *,
    session_key: str,
    limit: int | None,
    max_chars: int | None,
) -> dict[str, Any]:
    rows = await database.list_control_chat_messages(
        limit=limit or 200,
        session_key=session_key,
    )
    metadata_row = await database.get_gateway_session_metadata(session_key)
    metadata: dict[str, Any] = {}
    if isinstance(metadata_row, dict):
        metadata_value = metadata_row.get("metadata")
        if isinstance(metadata_value, dict):
            metadata = dict(metadata_value)
    return {
        "sessionKey": session_key,
        "sessionId": None,
        "messages": _project_control_chat_messages(rows, max_chars=max_chars),
        "thinkingLevel": _string_or_none(metadata.get("thinkingLevel")),
        "fastMode": _bool_or_none(metadata.get("fastMode")),
        "verboseLevel": _string_or_none(metadata.get("verboseLevel")),
        "traceLevel": _string_or_none(metadata.get("traceLevel")),
    }


async def _build_sessions_get_payload(
    database: Database,
    *,
    session_key: str,
    limit: int | None,
) -> dict[str, Any]:
    history = await _build_chat_history_payload(
        database,
        session_key=session_key,
        limit=limit,
        max_chars=None,
    )
    return {"messages": history["messages"]}


async def _build_sessions_usage_payload(
    database: Database,
    *,
    sessions_service: GatewaySessionsService | None,
    session_key: str | None,
    start_date: str | None,
    end_date: str | None,
    mode: Literal["gateway", "specific", "utc"] | None,
    utc_offset: str | None,
    limit: int | None,
    include_context_weight: bool,
    now_ms: int,
) -> dict[str, Any]:
    resolved_start_date, resolved_end_date = _resolve_sessions_usage_date_range(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        utc_offset=utc_offset,
        now_ms=now_ms,
    )
    bounded_limit = max(1, min(limit or 50, 1000))
    requested_session_key = (
        [_canonical_session_key(session_key)] if session_key is not None else None
    )
    session_payloads = await _usage_session_payloads_by_key(
        database,
        sessions_service=sessions_service,
        requested_session_keys=requested_session_key,
        limit=bounded_limit,
        now_ms=now_ms,
    )

    sessions: list[dict[str, Any]] = []
    totals = _empty_usage_totals()
    aggregate_messages = _empty_usage_message_counts()
    aggregate_tools = _empty_usage_tool_summary()
    by_model: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    by_provider: dict[str | None, dict[str, Any]] = {}

    for session_payload in session_payloads:
        usage_entry = await _build_single_session_usage_entry(
            database,
            session_payload=session_payload,
            include_context_weight=include_context_weight,
            now_ms=now_ms,
        )
        if usage_entry is None:
            continue
        sessions.append(usage_entry)
        usage_payload = usage_entry.get("usage")
        if isinstance(usage_payload, dict):
            _add_usage_totals(totals, usage_payload)
            message_counts = usage_payload.get("messageCounts")
            if isinstance(message_counts, dict):
                _add_usage_message_counts(aggregate_messages, message_counts)
            tool_usage = usage_payload.get("toolUsage")
            if isinstance(tool_usage, dict):
                _add_usage_tool_summary(aggregate_tools, tool_usage)
            _record_usage_model_aggregates(
                by_model,
                by_provider,
                provider=_string_or_none(usage_entry.get("modelProvider")),
                model=_string_or_none(usage_entry.get("model")),
                usage_payload=usage_payload,
            )

    return {
        "updatedAt": now_ms,
        "startDate": resolved_start_date,
        "endDate": resolved_end_date,
        "sessions": sessions,
        "totals": totals,
        "aggregates": {
            "messages": aggregate_messages,
            "tools": aggregate_tools,
            "byModel": list(by_model.values()),
            "byProvider": list(by_provider.values()),
            "byAgent": [],
            "byChannel": [],
            "daily": [],
        },
    }


def _build_usage_status_payload(
    *,
    model_catalog: dict[str, Any],
    now_ms: int,
) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in model_catalog.get("models", []):
        if not isinstance(entry, dict):
            continue
        provider = _string_or_none(entry.get("provider"))
        if provider is None:
            continue
        normalized_provider = provider.lower()
        if normalized_provider in seen:
            continue
        seen.add(normalized_provider)
        providers.append(
            {
                "provider": provider,
                "displayName": provider,
                "windows": [],
                "plan": None,
                "error": "Quota telemetry is not available in OpenZues yet.",
            }
        )
    providers.sort(key=lambda entry: str(entry.get("provider") or "").lower())
    return {"updatedAt": now_ms, "providers": providers}


async def _build_usage_cost_payload(
    database: Database,
    *,
    start_date: str | None,
    end_date: str | None,
    days: int | None,
    mode: Literal["gateway", "specific", "utc"] | None,
    utc_offset: str | None,
    now_ms: int,
) -> dict[str, Any]:
    resolved_start_date, resolved_end_date = _resolve_usage_cost_date_range(
        start_date=start_date,
        end_date=end_date,
        days=days,
        mode=mode,
        utc_offset=utc_offset,
        now_ms=now_ms,
    )
    start_day = datetime.strptime(resolved_start_date, "%Y-%m-%d").date()
    end_day = datetime.strptime(resolved_end_date, "%Y-%m-%d").date()
    tz = _sessions_usage_timezone(mode=mode, utc_offset=utc_offset)
    daily_map: dict[str, dict[str, Any]] = {}
    totals = _empty_usage_totals()

    for mission in await database.list_missions():
        usage_payload = _usage_totals_from_mission(mission)
        if usage_payload is None:
            continue
        total_tokens = int(usage_payload.get("totalTokens") or 0)
        total_cost = float(usage_payload.get("totalCost") or 0.0)
        if total_tokens <= 0 and total_cost <= 0:
            continue
        activity_at_ms = _mission_usage_timestamp_ms(mission)
        if activity_at_ms is None:
            continue
        activity_day = datetime.fromtimestamp(activity_at_ms / 1000, tz=UTC).astimezone(tz).date()
        if activity_day < start_day or activity_day > end_day:
            continue
        day_key = activity_day.isoformat()
        bucket = daily_map.get(day_key)
        if bucket is None:
            bucket = {"date": day_key, **_empty_usage_totals()}
            daily_map[day_key] = bucket
        _add_usage_totals(bucket, usage_payload)
        _add_usage_totals(totals, usage_payload)

    return {
        "updatedAt": now_ms,
        "days": (end_day - start_day).days + 1,
        "daily": [daily_map[key] for key in sorted(daily_map)],
        "totals": totals,
    }


async def _build_sessions_usage_timeseries_payload(
    database: Database,
    *,
    sessions_service: GatewaySessionsService | None,
    session_key: str,
    now_ms: int,
) -> dict[str, Any]:
    canonical_key = _canonical_session_key(session_key)
    session_payload = await _single_usage_session_payload(
        database,
        sessions_service=sessions_service,
        session_key=canonical_key,
        now_ms=now_ms,
    )
    missions = await _usage_missions_for_session(database, session_key=canonical_key)
    points: list[dict[str, Any]] = []
    cumulative_tokens = 0
    cumulative_cost = 0.0

    for mission in missions:
        usage_payload = _usage_totals_from_mission(mission)
        if usage_payload is None:
            continue
        total_tokens = int(usage_payload.get("totalTokens") or 0)
        total_cost = float(usage_payload.get("totalCost") or 0.0)
        if total_tokens <= 0 and total_cost <= 0:
            continue
        cumulative_tokens += total_tokens
        cumulative_cost += total_cost
        points.append(
            {
                "timestamp": (
                    _iso8601_to_timestamp_ms(mission.get("updated_at"))
                    or _iso8601_to_timestamp_ms(mission.get("created_at"))
                    or now_ms
                ),
                "input": int(usage_payload.get("input") or 0),
                "output": int(usage_payload.get("output") or 0),
                "cacheRead": int(usage_payload.get("cacheRead") or 0),
                "cacheWrite": int(usage_payload.get("cacheWrite") or 0),
                "totalTokens": total_tokens,
                "cost": total_cost,
                "cumulativeTokens": cumulative_tokens,
                "cumulativeCost": cumulative_cost,
            }
        )

    latest_mission = missions[-1] if missions else None
    return {
        "sessionId": _usage_session_id(
            session_payload=session_payload,
            mission=latest_mission,
        ),
        "points": points,
    }


async def _build_sessions_usage_logs_payload(
    database: Database,
    *,
    sessions_service: GatewaySessionsService | None,
    session_key: str,
    limit: int | None,
    now_ms: int,
) -> dict[str, Any]:
    canonical_key = _canonical_session_key(session_key)
    session_payload = await _single_usage_session_payload(
        database,
        sessions_service=sessions_service,
        session_key=canonical_key,
        now_ms=now_ms,
    )
    bounded_limit = max(1, min(limit or 200, 1000))
    rows = await database.list_control_chat_messages(
        limit=bounded_limit,
        session_key=canonical_key,
    )
    mission_ids = {
        mission_id
        for row in rows
        if (mission_id := _int_or_none(row.get("mission_id"))) is not None
    }
    mission_by_id = {
        mission_id: await database.get_mission(mission_id) for mission_id in sorted(mission_ids)
    }

    entries: list[dict[str, Any]] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        if role not in {"user", "assistant", "tool", "toolResult"}:
            continue
        entry: dict[str, Any] = {
            "timestamp": _iso8601_to_timestamp_ms(row.get("created_at")) or now_ms,
            "role": role,
            "content": str(row.get("content") or ""),
        }
        mission_id = _int_or_none(row.get("mission_id"))
        mission = mission_by_id.get(mission_id) if mission_id is not None else None
        usage_payload = _usage_totals_from_mission(mission)
        if usage_payload is not None:
            total_tokens = int(usage_payload.get("totalTokens") or 0)
            total_cost = float(usage_payload.get("totalCost") or 0.0)
            if total_tokens > 0:
                entry["tokens"] = total_tokens
            if total_cost > 0:
                entry["cost"] = total_cost
        entries.append(entry)

    latest_mission = next(
        (mission for mission in reversed(list(mission_by_id.values())) if mission is not None),
        None,
    )
    if latest_mission is None:
        latest_mission = await database.get_latest_mission_by_session_key(
            canonical_key,
            require_thread=False,
        )

    return {
        "sessionId": _usage_session_id(
            session_payload=session_payload,
            mission=latest_mission,
        ),
        "entries": entries,
    }


async def _single_usage_session_payload(
    database: Database,
    *,
    sessions_service: GatewaySessionsService | None,
    session_key: str,
    now_ms: int,
) -> dict[str, Any]:
    payloads = await _usage_session_payloads_by_key(
        database,
        sessions_service=sessions_service,
        requested_session_keys=[session_key],
        limit=1,
        now_ms=now_ms,
    )
    return payloads[0] if payloads else {"key": session_key}


async def _usage_session_payloads_by_key(
    database: Database,
    *,
    sessions_service: GatewaySessionsService | None,
    requested_session_keys: list[str] | None,
    limit: int,
    now_ms: int,
) -> list[dict[str, Any]]:
    ordered_keys: list[str] = []
    payload_by_key: dict[str, dict[str, Any]] = {}

    def remember(key: str, payload: dict[str, Any] | None = None) -> None:
        canonical_key = _canonical_session_key(key)
        if canonical_key in payload_by_key:
            if payload is not None:
                payload_by_key[canonical_key].update(payload)
            return
        if payload is None:
            payload = {"key": canonical_key}
        payload_by_key[canonical_key] = dict(payload)
        ordered_keys.append(canonical_key)

    if sessions_service is not None:
        if requested_session_keys is None:
            snapshot = await sessions_service.build_snapshot(
                include_global=True,
                include_unknown=True,
                limit=limit,
                active_minutes=None,
                label=None,
                spawned_by=None,
                agent_id=None,
                search=None,
                include_derived_titles=False,
                include_last_message=False,
                now_ms=now_ms,
            )
            for session_payload in snapshot.get("sessions", []):
                if not isinstance(session_payload, dict):
                    continue
                key = _string_or_none(session_payload.get("key"))
                if key is None:
                    continue
                remember(key, session_payload)
        else:
            for requested_key in requested_session_keys:
                session_payload = await sessions_service.build_session_payload_for_key(
                    session_key=requested_key,
                    now_ms=now_ms,
                )
                remember(requested_key, session_payload)

    if requested_session_keys is None:
        for key in await database.list_control_chat_session_keys():
            remember(key)
    else:
        for key in requested_session_keys:
            remember(key)

    return [payload_by_key[key] for key in ordered_keys[:limit]]


async def _usage_missions_for_session(
    database: Database,
    *,
    session_key: str,
) -> list[dict[str, Any]]:
    aliases = set(_session_key_aliases(session_key))
    missions = [
        mission
        for mission in await database.list_missions()
        if str(mission.get("session_key") or "").strip().lower() in aliases
    ]
    return sorted(
        missions,
        key=lambda mission: (
            _iso8601_to_timestamp_ms(mission.get("updated_at"))
            or _iso8601_to_timestamp_ms(mission.get("created_at"))
            or 0,
            int(mission.get("id") or 0),
        ),
    )


async def _build_single_session_usage_entry(
    database: Database,
    *,
    session_payload: dict[str, Any],
    include_context_weight: bool,
    now_ms: int,
) -> dict[str, Any] | None:
    session_key = _string_or_none(session_payload.get("key"))
    if session_key is None:
        return None
    canonical_key = _canonical_session_key(session_key)
    metadata_row = await database.get_gateway_session_metadata(canonical_key)
    metadata: dict[str, Any] = {}
    if isinstance(metadata_row, dict):
        metadata_value = metadata_row.get("metadata")
        if isinstance(metadata_value, dict):
            metadata = dict(metadata_value)
    mission = await database.get_latest_mission_by_session_key(
        canonical_key,
        require_thread=False,
    )
    message_count = await database.count_control_chat_messages(session_key=canonical_key)
    rows = (
        await database.list_control_chat_messages(
            limit=max(1, message_count),
            session_key=canonical_key,
        )
        if message_count
        else []
    )
    has_session_payload_data = any(key != "key" for key in session_payload)
    if mission is None and not rows and not metadata and not has_session_payload_data:
        return None

    updated_at = _usage_session_updated_at_ms(
        session_payload=session_payload,
        mission=mission,
        metadata_row=metadata_row,
        rows=rows,
        now_ms=now_ms,
    )
    resolved_model = _string_or_none(metadata.get("model")) or _string_or_none(
        session_payload.get("model")
    )
    message_counts = _usage_message_counts(rows)
    usage_payload = _usage_totals_from_mission(mission) or _empty_usage_totals()
    usage_payload["sessionId"] = _string_or_none(
        session_payload.get("sessionId")
    ) or _string_or_none(mission.get("thread_id") if mission is not None else None)
    usage_payload["lastActivity"] = updated_at
    usage_payload["messageCounts"] = message_counts
    usage_payload["toolUsage"] = _empty_usage_tool_summary()

    entry: dict[str, Any] = {
        "key": canonical_key,
        "label": _string_or_none(metadata.get("label"))
        or _string_or_none(session_payload.get("label")),
        "sessionId": _string_or_none(session_payload.get("sessionId"))
        or _string_or_none(mission.get("thread_id") if mission is not None else None),
        "updatedAt": updated_at,
        "modelProvider": (
            _string_or_none(session_payload.get("modelProvider"))
            or ("openai" if resolved_model is not None else None)
        ),
        "model": resolved_model,
        "usage": usage_payload,
    }
    if include_context_weight:
        entry["contextWeight"] = None
    return entry


def _resolve_sessions_usage_date_range(
    *,
    start_date: str | None,
    end_date: str | None,
    mode: Literal["gateway", "specific", "utc"] | None,
    utc_offset: str | None,
    now_ms: int,
) -> tuple[str, str]:
    tz = _sessions_usage_timezone(mode=mode, utc_offset=utc_offset)
    now = datetime.fromtimestamp(now_ms / 1000, tz=tz)
    resolved_end = (
        datetime.strptime(end_date, "%Y-%m-%d").date() if end_date is not None else now.date()
    )
    resolved_start = (
        datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date is not None
        else resolved_end - timedelta(days=29)
    )
    return (resolved_start.isoformat(), resolved_end.isoformat())


def _resolve_usage_cost_date_range(
    *,
    start_date: str | None,
    end_date: str | None,
    days: int | None,
    mode: Literal["gateway", "specific", "utc"] | None,
    utc_offset: str | None,
    now_ms: int,
) -> tuple[str, str]:
    if start_date is not None and end_date is not None:
        return _resolve_sessions_usage_date_range(
            start_date=start_date,
            end_date=end_date,
            mode=mode,
            utc_offset=utc_offset,
            now_ms=now_ms,
        )
    tz = _sessions_usage_timezone(mode=mode, utc_offset=utc_offset)
    now = datetime.fromtimestamp(now_ms / 1000, tz=tz)
    resolved_end = now.date()
    resolved_start = resolved_end - timedelta(days=max(1, days or 30) - 1)
    return (resolved_start.isoformat(), resolved_end.isoformat())


def _sessions_usage_timezone(
    *,
    mode: Literal["gateway", "specific", "utc"] | None,
    utc_offset: str | None,
) -> timezone:
    if mode == "gateway":
        local_tz = datetime.now().astimezone().tzinfo
        if isinstance(local_tz, timezone):
            return local_tz
        if local_tz is not None:
            current_offset = datetime.now().astimezone().utcoffset()
            if current_offset is not None:
                return timezone(current_offset)
        return UTC
    if mode == "specific":
        utc_offset_minutes = _utc_offset_minutes(utc_offset)
        if utc_offset_minutes is not None:
            return timezone(timedelta(minutes=utc_offset_minutes))
    return UTC


def _utc_offset_minutes(value: str | None) -> int | None:
    if value is None:
        return None
    match = _UTC_OFFSET_RE.match(value.strip())
    if match is None:
        return None
    sign = 1 if "+" in value else -1
    hours_part, _, minutes_part = value[3:].partition(":")
    hours = abs(int(hours_part))
    minutes = int(minutes_part or "0")
    return sign * (hours * 60 + minutes)


def _usage_session_updated_at_ms(
    *,
    session_payload: dict[str, Any],
    mission: dict[str, Any] | None,
    metadata_row: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    now_ms: int,
) -> int:
    candidates: list[int] = []
    session_payload_updated_at = _int_or_none(session_payload.get("updatedAt"))
    if session_payload_updated_at is not None:
        candidates.append(session_payload_updated_at)
    mission_updated_at = _iso8601_to_timestamp_ms(
        mission.get("updated_at") if mission is not None else None
    )
    if mission_updated_at is not None:
        candidates.append(mission_updated_at)
    metadata_updated_at = _iso8601_to_timestamp_ms(
        metadata_row.get("updated_at") if metadata_row is not None else None
    )
    if metadata_updated_at is not None:
        candidates.append(metadata_updated_at)
    if rows:
        latest_message_at = _iso8601_to_timestamp_ms(rows[-1].get("created_at"))
        if latest_message_at is not None:
            candidates.append(latest_message_at)
    return max(candidates) if candidates else now_ms


def _mission_usage_timestamp_ms(mission: dict[str, Any]) -> int | None:
    return _iso8601_to_timestamp_ms(mission.get("updated_at")) or _iso8601_to_timestamp_ms(
        mission.get("created_at")
    )


def _usage_totals_from_mission(mission: dict[str, Any] | None) -> dict[str, Any] | None:
    if mission is None:
        return None
    total_tokens = int(mission.get("total_tokens") or 0)
    output_tokens = int(mission.get("output_tokens") or 0)
    bounded_output_tokens = min(output_tokens, total_tokens)
    return {
        "input": max(total_tokens - bounded_output_tokens, 0),
        "output": bounded_output_tokens,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": total_tokens,
        "totalCost": 0.0,
        "inputCost": 0.0,
        "outputCost": 0.0,
        "cacheReadCost": 0.0,
        "cacheWriteCost": 0.0,
        "missingCostEntries": 1 if total_tokens or bounded_output_tokens else 0,
    }


def _usage_session_id(
    *,
    session_payload: dict[str, Any],
    mission: dict[str, Any] | None,
) -> str | None:
    return _string_or_none(session_payload.get("sessionId")) or _string_or_none(
        mission.get("thread_id") if mission is not None else None
    )


def _empty_usage_totals() -> dict[str, Any]:
    return {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 0,
        "totalCost": 0.0,
        "inputCost": 0.0,
        "outputCost": 0.0,
        "cacheReadCost": 0.0,
        "cacheWriteCost": 0.0,
        "missingCostEntries": 0,
    }


def _add_usage_totals(target: dict[str, Any], source: dict[str, Any]) -> None:
    for field in (
        "input",
        "output",
        "cacheRead",
        "cacheWrite",
        "totalTokens",
        "totalCost",
        "inputCost",
        "outputCost",
        "cacheReadCost",
        "cacheWriteCost",
        "missingCostEntries",
    ):
        target[field] = target.get(field, 0) + source.get(field, 0)


def _usage_message_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = _empty_usage_message_counts()
    for row in rows:
        role = str(row.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        counts["total"] += 1
        counts[role] += 1
    return counts


def _empty_usage_message_counts() -> dict[str, int]:
    return {
        "total": 0,
        "user": 0,
        "assistant": 0,
        "toolCalls": 0,
        "toolResults": 0,
        "errors": 0,
    }


def _add_usage_message_counts(target: dict[str, int], source: dict[str, Any]) -> None:
    for field in ("total", "user", "assistant", "toolCalls", "toolResults", "errors"):
        target[field] += int(source.get(field) or 0)


def _empty_usage_tool_summary() -> dict[str, Any]:
    return {"totalCalls": 0, "uniqueTools": 0, "tools": []}


def _add_usage_tool_summary(target: dict[str, Any], source: dict[str, Any]) -> None:
    target["totalCalls"] += int(source.get("totalCalls") or 0)
    existing_tools = {
        str(tool.get("name")): int(tool.get("count") or 0)
        for tool in target.get("tools", [])
        if isinstance(tool, dict) and tool.get("name")
    }
    for tool in source.get("tools", []):
        if not isinstance(tool, dict):
            continue
        name = _string_or_none(tool.get("name"))
        if name is None:
            continue
        existing_tools[name] = existing_tools.get(name, 0) + int(tool.get("count") or 0)
    target["tools"] = [
        {"name": name, "count": count}
        for name, count in sorted(existing_tools.items(), key=lambda item: item[0])
    ]
    target["uniqueTools"] = len(target["tools"])


def _record_usage_model_aggregates(
    by_model: dict[tuple[str | None, str | None], dict[str, Any]],
    by_provider: dict[str | None, dict[str, Any]],
    *,
    provider: str | None,
    model: str | None,
    usage_payload: dict[str, Any],
) -> None:
    totals_payload = _empty_usage_totals()
    _add_usage_totals(totals_payload, usage_payload)

    model_key = (provider, model)
    if model_key not in by_model:
        by_model[model_key] = {
            "provider": provider,
            "model": model,
            "count": 0,
            "totals": _empty_usage_totals(),
        }
    by_model_entry = by_model[model_key]
    by_model_entry["count"] += 1
    _add_usage_totals(by_model_entry["totals"], totals_payload)

    if provider not in by_provider:
        by_provider[provider] = {
            "provider": provider,
            "count": 0,
            "totals": _empty_usage_totals(),
        }
    by_provider_entry = by_provider[provider]
    by_provider_entry["count"] += 1
    _add_usage_totals(by_provider_entry["totals"], totals_payload)


def _project_control_chat_messages(
    rows: list[dict[str, Any]],
    *,
    max_chars: int | None,
) -> list[dict[str, Any]]:
    normalized: list[tuple[str, str]] = []
    for row in rows:
        role = str(row.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        normalized.append((role, str(row.get("content") or "")))

    if max_chars is None:
        return [_chat_history_message_payload(role, text) for role, text in normalized]

    bounded: list[dict[str, Any]] = []
    remaining = max_chars
    for role, text in reversed(normalized):
        if not text:
            bounded.append(_chat_history_message_payload(role, text))
            continue
        if len(text) <= remaining:
            bounded.append(_chat_history_message_payload(role, text))
            remaining -= len(text)
            continue
        if not bounded and remaining > 0:
            bounded.append(_chat_history_message_payload(role, text[-remaining:]))
        break
    bounded.reverse()
    return bounded


async def _archive_control_chat_transcript(
    database: Database,
    *,
    session_key: str,
    reason: str,
    now_ms: int,
) -> list[str]:
    message_count = await database.count_control_chat_messages(session_key=session_key)
    if message_count <= 0:
        return []
    rows = await database.list_control_chat_messages(
        limit=max(1, message_count),
        session_key=session_key,
    )
    if not rows:
        return []

    archive_dir = Path(database.path).resolve().parent / "gateway-session-archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.fromtimestamp(now_ms / 1000, tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = archive_dir / f"{_session_archive_slug(session_key)}-{reason}-{timestamp}.jsonl"
    with archive_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            record = {
                "id": row.get("id"),
                "sessionKey": session_key,
                "role": row.get("role"),
                "content": row.get("content"),
                "createdAt": row.get("created_at"),
                "missionId": row.get("mission_id"),
                "reason": reason,
            }
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    _cleanup_archived_control_chat_transcripts(
        archive_dir,
        reason=reason,
        older_than_ms=_DEFAULT_SESSION_DELETE_ARCHIVE_RETENTION_MS,
        now_ms=now_ms,
    )
    return [str(archive_path)]


def _session_archive_slug(session_key: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", session_key).strip("-").lower()
    return slug or "session"


def _cleanup_archived_control_chat_transcripts(
    archive_dir: Path,
    *,
    reason: str,
    older_than_ms: int,
    now_ms: int,
) -> None:
    if older_than_ms < 0:
        return
    for entry in archive_dir.iterdir():
        if not entry.is_file():
            continue
        archived_at_ms = _session_archive_timestamp_ms(entry.name, reason=reason)
        if archived_at_ms is None:
            continue
        if now_ms - archived_at_ms <= older_than_ms:
            continue
        try:
            entry.unlink()
        except OSError:
            continue


def _session_archive_timestamp_ms(filename: str, *, reason: str) -> int | None:
    pattern = rf"^.+-{re.escape(reason)}-(\d{{8}}T\d{{6}}Z)\.jsonl$"
    match = re.match(pattern, filename)
    if match is None:
        return None
    try:
        parsed = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return int(parsed.timestamp() * 1000)


def _chat_history_message_payload(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def _project_session_preview_items(
    rows: list[dict[str, Any]],
    *,
    max_items: int,
    max_chars: int,
) -> list[dict[str, str]]:
    bounded_items = max(1, min(max_items, 50))
    bounded_chars = max(20, min(max_chars, 2000))
    items: list[dict[str, str]] = []
    for row in rows[-bounded_items:]:
        raw_role = str(row.get("role") or "").strip().lower()
        role = raw_role if raw_role in {"user", "assistant", "tool", "system"} else "other"
        text = str(row.get("content") or "").strip()
        if not text:
            continue
        items.append({"role": role, "text": _truncate_preview_text(text, bounded_chars)})
    return items


def _truncate_preview_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3]}..."


def _require_session_lookup_key(params: dict[str, Any]) -> str:
    if "key" in params:
        return _require_non_empty_string(params.get("key"), label="key")
    if "sessionKey" in params:
        return _require_non_empty_string(params.get("sessionKey"), label="sessionKey")
    return _require_non_empty_string(None, label="key")


def _validate_optional_restart_request_fields(
    method: str,
    payload: dict[str, Any],
    *,
    include_timeout_ms: bool,
) -> None:
    if "sessionKey" in payload and payload.get("sessionKey") is not None:
        _require_string(payload.get("sessionKey"), label="sessionKey")
    _validate_optional_restart_delivery_context(
        payload.get("deliveryContext"),
        label=f"{method}.deliveryContext",
    )
    if "note" in payload and payload.get("note") is not None:
        _require_string(payload.get("note"), label="note")
    _optional_min_int(
        payload.get("restartDelayMs"),
        label="restartDelayMs",
        minimum=0,
    )
    if include_timeout_ms:
        _optional_min_int(
            payload.get("timeoutMs"),
            label="timeoutMs",
            minimum=1,
        )


def _validate_optional_restart_delivery_context(value: object, *, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError("deliveryContext must be an object")
    _validate_exact_keys(
        label,
        value,
        allowed_keys=("channel", "to", "accountId", "threadId"),
    )
    for field in ("channel", "to", "accountId"):
        if field in value and value.get(field) is not None:
            _require_string(value.get(field), label=field)
    if "threadId" in value and value.get("threadId") is not None:
        thread_id = value.get("threadId")
        if isinstance(thread_id, bool) or not isinstance(thread_id, str | int | float):
            raise ValueError("threadId must be a string or number")


def _resolve_optional_initial_session_message(
    *,
    task: object,
    message: object,
) -> str | None:
    if isinstance(task, str) and task.strip():
        return task
    if isinstance(message, str) and message.strip():
        return message
    return None


def _build_canvas_scoped_host_url(base_url: str | None, capability: str) -> str | None:
    normalized_base_url = str(base_url or "").strip()
    normalized_capability = capability.strip()
    if not normalized_base_url or not normalized_capability:
        return None
    try:
        split_url = urlsplit(normalized_base_url)
    except ValueError:
        return None
    if not split_url.scheme or not split_url.netloc:
        return None
    trimmed_path = split_url.path.rstrip("/")
    scoped_path = (
        f"{trimmed_path}{_CANVAS_CAPABILITY_PATH_PREFIX}/{quote(normalized_capability, safe='')}"
    )
    return urlunsplit((split_url.scheme, split_url.netloc, scoped_path, "", ""))


def _validate_object_params(method: str, params: dict[str, Any] | None) -> dict[str, Any]:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise ValueError(f"{method} params must be an object")
    return dict(params)


def _validate_exact_keys(
    method: str,
    params: dict[str, Any],
    *,
    allowed_keys: tuple[str, ...],
) -> None:
    unexpected = sorted(set(params) - set(allowed_keys))
    if unexpected:
        joined = ", ".join(unexpected)
        raise ValueError(f"{method} does not accept: {joined}")


def _require_non_empty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a non-empty string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{label} must be a non-empty string")
    return trimmed


def _require_session_label(value: object, *, label: str) -> str:
    resolved = _require_non_empty_string(value, label=label)
    if len(resolved) > _SESSION_LABEL_MAX_LENGTH:
        raise ValueError(f"{label} must be at most {_SESSION_LABEL_MAX_LENGTH} characters")
    return resolved


def _optional_session_label(value: object, *, label: str) -> str | None:
    normalized = _optional_normalized_string(value, label=label)
    if normalized is None:
        return None
    if len(normalized) > _SESSION_LABEL_MAX_LENGTH:
        raise ValueError(f"{label} must be at most {_SESSION_LABEL_MAX_LENGTH} characters")
    return normalized


def _require_string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _require_string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a non-empty string array")
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(f"{label} must be a non-empty string array")
        trimmed = entry.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    if not normalized:
        raise ValueError(f"{label} must be a non-empty string array")
    return normalized


def _require_string_array(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    normalized: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(f"{label} must be a string array")
        normalized.append(entry)
    return normalized


def _optional_string_list(value: object, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(f"{label} must be a string array")
        trimmed = entry.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return normalized


def _optional_bounded_int(
    value: object,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return value


def _optional_min_int(
    value: object,
    *,
    label: str,
    minimum: int,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def _optional_number(value: object, *, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{label} must be a number")
    return float(value)


def _require_enum_value(
    value: object,
    *,
    label: str,
    allowed_values: set[str],
) -> str:
    resolved = _optional_enum_value(
        value,
        label=label,
        allowed_values=allowed_values,
    )
    if resolved is None:
        raise ValueError(f"{label} is required")
    return resolved


def _optional_enum_value(
    value: object,
    *,
    label: str,
    allowed_values: set[str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed_values))}")
    trimmed = value.strip()
    if trimmed not in allowed_values:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed_values))}")
    return trimmed


def _optional_enum_values(
    value: object,
    *,
    label: str,
    allowed_values: set[str],
) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(f"{label} must contain only strings")
        trimmed = entry.strip()
        if trimmed not in allowed_values:
            raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed_values))}")
        if trimmed in seen:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return tuple(normalized)


def _require_bool(value: object, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _optional_bool(value: object, *, label: str) -> bool | None:
    if value is None:
        return None
    return _require_bool(value, label=label)


def _optional_non_empty_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_non_empty_string(value, label=label)


def _optional_normalized_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    trimmed = _require_string(value, label=label).strip()
    return trimmed or None


def _optional_date_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    resolved = _require_string(value, label=label)
    if not _YYYY_MM_DD_RE.match(resolved):
        raise ValueError(f"{label} must match YYYY-MM-DD")
    return resolved


def _optional_utc_offset_string(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    resolved = _require_string(value, label=label)
    if not _UTC_OFFSET_RE.match(resolved):
        raise ValueError(f"{label} must match UTC+H, UTC-H, UTC+HH, UTC-HH, UTC+H:MM, or UTC-HH:MM")
    return resolved


def _require_string_mapping(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    normalized: dict[str, str] = {}
    for key, entry in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{label} keys must be non-empty strings")
        if not isinstance(entry, str):
            raise ValueError(f"{label} values must be strings")
        normalized[key] = entry
    return normalized


def _validate_exec_approvals_file_config(value: object, *, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    _validate_exact_keys(
        label,
        value,
        allowed_keys=("version", "socket", "defaults", "agents"),
    )
    version = value.get("version")
    if version != 1:
        raise ValueError(f"{label}.version must be 1")
    socket_config = value.get("socket")
    if socket_config is not None:
        if not isinstance(socket_config, dict):
            raise ValueError(f"{label}.socket must be an object")
        _validate_exact_keys(
            f"{label}.socket",
            socket_config,
            allowed_keys=("path", "token"),
        )
        if "path" in socket_config and socket_config.get("path") is not None:
            _require_non_empty_string(socket_config.get("path"), label=f"{label}.socket.path")
        if "token" in socket_config and socket_config.get("token") is not None:
            _require_non_empty_string(
                socket_config.get("token"),
                label=f"{label}.socket.token",
            )
    defaults = value.get("defaults")
    if defaults is not None:
        _validate_exec_approvals_policy_config(
            defaults,
            label=f"{label}.defaults",
            allow_allowlist=False,
        )
    agents = value.get("agents")
    if agents is not None:
        if not isinstance(agents, dict):
            raise ValueError(f"{label}.agents must be an object")
        for agent_id, agent_config in agents.items():
            resolved_agent_id = _require_non_empty_string(agent_id, label=f"{label}.agents key")
            _validate_exec_approvals_policy_config(
                agent_config,
                label=f"{label}.agents.{resolved_agent_id}",
                allow_allowlist=True,
            )


def _validate_exec_approvals_policy_config(
    value: object,
    *,
    label: str,
    allow_allowlist: bool,
) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    allowed_keys: tuple[str, ...] = ("security", "ask", "askFallback", "autoAllowSkills")
    if allow_allowlist:
        allowed_keys = (*allowed_keys, "allowlist")
    _validate_exact_keys(label, value, allowed_keys=allowed_keys)
    for key in ("security", "ask", "askFallback"):
        if key in value and value.get(key) is not None:
            _require_non_empty_string(value.get(key), label=f"{label}.{key}")
    if "autoAllowSkills" in value:
        _optional_bool(value.get("autoAllowSkills"), label=f"{label}.autoAllowSkills")
    if allow_allowlist and "allowlist" in value and value.get("allowlist") is not None:
        allowlist = value.get("allowlist")
        if not isinstance(allowlist, list):
            raise ValueError(f"{label}.allowlist must be an array")
        for index, entry in enumerate(allowlist):
            _validate_exec_approvals_allowlist_entry(
                entry,
                label=f"{label}.allowlist[{index}]",
            )


def _validate_exec_approvals_allowlist_entry(value: object, *, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    _validate_exact_keys(
        label,
        value,
        allowed_keys=(
            "id",
            "pattern",
            "argPattern",
            "lastUsedAt",
            "lastUsedCommand",
            "lastResolvedPath",
        ),
    )
    _require_non_empty_string(value.get("pattern"), label=f"{label}.pattern")
    for key in ("id", "argPattern", "lastUsedCommand", "lastResolvedPath"):
        if key in value and value.get(key) is not None:
            _require_non_empty_string(value.get(key), label=f"{label}.{key}")
    if "lastUsedAt" in value:
        _optional_min_int(value.get("lastUsedAt"), label=f"{label}.lastUsedAt", minimum=0)


def _validate_agent_internal_events(value: object, *, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ValueError(f"{label}[{index}] must be an object")
        _validate_exact_keys(
            f"{label}[{index}]",
            entry,
            allowed_keys=(
                "type",
                "source",
                "childSessionKey",
                "childSessionId",
                "announceType",
                "taskLabel",
                "status",
                "statusLabel",
                "result",
                "mediaUrls",
                "statsLine",
                "replyInstruction",
            ),
        )
        for field in (
            "type",
            "source",
            "childSessionKey",
            "announceType",
            "taskLabel",
            "status",
            "statusLabel",
            "result",
            "replyInstruction",
        ):
            _require_string(entry.get(field), label=f"{label}[{index}].{field}")
        if "childSessionId" in entry and entry.get("childSessionId") is not None:
            _require_string(entry.get("childSessionId"), label=f"{label}[{index}].childSessionId")
        if "statsLine" in entry and entry.get("statsLine") is not None:
            _require_string(entry.get("statsLine"), label=f"{label}[{index}].statsLine")
        if "mediaUrls" in entry and entry.get("mediaUrls") is not None:
            _require_string_array(entry.get("mediaUrls"), label=f"{label}[{index}].mediaUrls")


def _validate_agent_input_provenance(value: object, *, label: str) -> None:
    input_provenance = _require_unknown_mapping(value, label=label)
    _validate_exact_keys(
        label,
        input_provenance,
        allowed_keys=(
            "kind",
            "originSessionId",
            "sourceSessionKey",
            "sourceChannel",
            "sourceTool",
        ),
    )
    _require_enum_value(
        input_provenance.get("kind"),
        label=f"{label}.kind",
        allowed_values=_INPUT_PROVENANCE_KIND_VALUES,
    )
    for field in ("originSessionId", "sourceSessionKey", "sourceChannel", "sourceTool"):
        if field in input_provenance and input_provenance.get(field) is not None:
            _require_string(input_provenance.get(field), label=f"{label}.{field}")


def _normalize_gateway_optional_input_provenance(
    value: object,
) -> dict[str, str | None] | None:
    if not isinstance(value, dict):
        return None
    raw_kind = value.get("kind")
    if not isinstance(raw_kind, str):
        return None
    kind = raw_kind.strip()
    if kind not in _INPUT_PROVENANCE_KIND_VALUES:
        return None
    normalized: dict[str, str | None] = {"kind": kind}
    for field in ("originSessionId", "sourceSessionKey", "sourceChannel", "sourceTool"):
        raw_field = value.get(field)
        if not isinstance(raw_field, str):
            continue
        trimmed = raw_field.strip()
        normalized[field] = trimmed or None
    return normalized


def _has_truthy_gateway_system_input_provenance(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return bool(value)
    return True


_GATEWAY_CHAT_ABORT_TRIGGER_VALUES = {
    "/stop",
    "stop",
    "esc",
    "abort",
    "wait",
    "exit",
    "interrupt",
    "detente",
    "deten",
    "det\u00e9n",
    "arrete",
    "arr\u00eate",
    "\u505c\u6b62",
    "\u3084\u3081\u3066",
    "\u6b62\u3081\u3066",
    "\u0930\u0941\u0915\u094b",
    "\u062a\u0648\u0642\u0641",
    "\u0441\u0442\u043e\u043f",
    "\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0441\u044c",
    "\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438",
    "\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c",
    "\u043f\u0440\u0435\u043a\u0440\u0430\u0442\u0438",
    "halt",
    "anhalten",
    "aufh\u00f6ren",
    "hoer auf",
    "stopp",
    "pare",
    "stop openclaw",
    "openclaw stop",
    "stop action",
    "stop current action",
    "stop run",
    "stop current run",
    "stop agent",
    "stop the agent",
    "stop don't do anything",
    "stop dont do anything",
    "stop do not do anything",
    "stop doing anything",
    "do not do that",
    "please stop",
    "stop please",
}
_GATEWAY_CHAT_ABORT_TRAILING_PUNCTUATION_RE = re.compile(
    r"""[.!?,\u2026\uFF0C\u3002;\uFF1B:\uFF1A'"`\u2019\u201D)\]}]+$"""
)


def _normalize_gateway_chat_stop_command_body(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed.startswith("/"):
        return trimmed
    newline_index = trimmed.find("\n")
    single_line = trimmed if newline_index == -1 else trimmed[:newline_index].strip()
    colon_match = re.match(r"^/([^\s:]+)\s*:(.*)$", single_line)
    if colon_match is None:
        return single_line
    command, rest = colon_match.groups()
    normalized_rest = rest.lstrip()
    if not normalized_rest:
        return f"/{command}"
    return f"/{command} {normalized_rest}"


def _normalize_gateway_chat_abort_trigger_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text).casefold()
    normalized = normalized.replace("\u2019", "'").replace("`", "'")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = _GATEWAY_CHAT_ABORT_TRAILING_PUNCTUATION_RE.sub("", normalized)
    return normalized.strip()


def _is_gateway_chat_stop_command_text(text: str) -> bool:
    normalized = _normalize_gateway_chat_stop_command_body(text).strip()
    if not normalized:
        return False
    normalized_lower = unicodedata.normalize("NFC", normalized).casefold()
    normalized_trigger = _normalize_gateway_chat_abort_trigger_text(normalized_lower)
    return normalized_lower == "/stop" or normalized_trigger in _GATEWAY_CHAT_ABORT_TRIGGER_VALUES


def _sanitize_gateway_chat_send_message_input(message: str) -> str:
    normalized = unicodedata.normalize("NFC", message)
    if "\x00" in normalized:
        raise ValueError("message must not contain null bytes")
    sanitized: list[str] = []
    for char in normalized:
        code = ord(char)
        if code in {9, 10, 13} or (code >= 32 and code != 127):
            sanitized.append(char)
    return "".join(sanitized)


def _should_attach_pending_session_message_seq(payload: object) -> bool:
    return isinstance(payload, dict) and payload.get("status") == "started"


def _sanitize_gateway_optional_chat_system_receipt(value: object) -> str | None:
    if value is None:
        return None
    sanitized = _sanitize_gateway_chat_send_message_input(
        _require_string(value, label="systemProvenanceReceipt")
    ).strip()
    return sanitized or None


def _normalize_gateway_chat_send_explicit_origin(
    *,
    originating_channel: object,
    originating_to: object,
    originating_account_id: object,
    originating_thread_id: object,
) -> dict[str, str] | None:
    normalized_channel = _optional_normalized_string(
        originating_channel,
        label="originatingChannel",
    )
    normalized_to = _optional_normalized_string(originating_to, label="originatingTo")
    normalized_account_id = _optional_normalized_string(
        originating_account_id,
        label="originatingAccountId",
    )
    normalized_thread_id = _optional_normalized_string(
        originating_thread_id,
        label="originatingThreadId",
    )
    if (
        normalized_channel is None
        and normalized_to is None
        and normalized_account_id is None
        and normalized_thread_id is None
    ):
        return None
    resolved_channel = (
        _normalize_gateway_chat_channel_id(normalized_channel)
        if normalized_channel is not None
        else None
    )
    if resolved_channel is None:
        raise ValueError("originatingChannel is required when using originating route fields")
    if normalized_to is None:
        raise ValueError("originatingTo is required when using originating route fields")
    explicit_origin = {
        "originatingChannel": resolved_channel,
        "originatingTo": normalized_to,
    }
    if normalized_account_id is not None:
        explicit_origin["originatingAccountId"] = normalized_account_id
    if normalized_thread_id is not None:
        explicit_origin["originatingThreadId"] = normalized_thread_id
    return explicit_origin


def _has_effective_agent_attachment_content(value: object) -> bool:
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return len(value) > 0
    return False


def _has_effective_agent_attachments(value: object) -> bool:
    if not isinstance(value, list):
        return False
    for entry in value:
        if not isinstance(entry, dict):
            continue
        if _has_effective_agent_attachment_content(entry.get("content")):
            return True
        source = entry.get("source")
        if not isinstance(source, dict):
            continue
        source_type = source.get("type")
        if not isinstance(source_type, str) or source_type != "base64":
            continue
        if _has_effective_agent_attachment_content(source.get("data")):
            return True
    return False


def _normalize_gateway_send_media_urls(
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


def _normalize_gateway_chat_channel_id(raw: str) -> str | None:
    normalized = raw.strip().lower()
    if not normalized:
        return None
    return normalized if normalized in _KNOWN_GATEWAY_CHAT_CHANNEL_IDS else None


def _validate_agent_channel_hint(value: str | None) -> None:
    if value is None:
        return
    normalized = value.strip().lower()
    if not normalized or normalized == "last":
        return
    if _normalize_gateway_chat_channel_id(normalized) is not None:
        return
    raise ValueError(f"invalid agent params: unknown channel: {normalized}")


def _gateway_chat_channel_sort_key(channel: str) -> tuple[int, str]:
    try:
        return (_KNOWN_GATEWAY_CHAT_CHANNEL_ORDER.index(channel), channel)
    except ValueError:
        return (len(_KNOWN_GATEWAY_CHAT_CHANNEL_ORDER), channel)


def _normalize_gateway_whatsapp_target(raw: str) -> str | None:
    trimmed = re.sub(r"^whatsapp:", "", raw.strip(), flags=re.IGNORECASE).strip()
    if not trimmed:
        return None
    lowered = trimmed.lower()
    if lowered.endswith("@g.us"):
        normalized_group = lowered.replace(" ", "")
        return normalized_group if re.fullmatch(r"\d+@g\.us", normalized_group) else None
    digits = re.sub(r"\D", "", trimmed)
    normalized_direct = f"+{digits}" if digits else ""
    return normalized_direct if re.fullmatch(r"\+\d{7,15}", normalized_direct) else None


def _normalize_gateway_telegram_target(raw: str) -> str | None:
    trimmed = re.sub(r"^telegram:", "", raw.strip(), flags=re.IGNORECASE).strip()
    if not trimmed:
        return None
    topic_match = re.fullmatch(r"(.*):topic:(\d+)", trimmed, flags=re.IGNORECASE)
    if topic_match is None:
        return trimmed
    chat_id = topic_match.group(1).strip()
    topic_id = topic_match.group(2)
    if not chat_id:
        return None
    return f"{chat_id}:topic:{topic_id}"


def _gateway_channel_label(channel: str) -> str:
    return {
        "discord": "Discord",
        "slack": "Slack",
        "telegram": "Telegram",
        "whatsapp": "WhatsApp",
    }.get(channel, channel.title())


def _validate_gateway_outbound_target(channel: str, target: str) -> None:
    if channel == "whatsapp":
        if _normalize_gateway_whatsapp_target(target) is None:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="WhatsApp target is required",
                status_code=400,
            )
        return
    if channel == "telegram":
        if _normalize_gateway_telegram_target(target) is None:
            raise GatewayNodeMethodError(
                code="INVALID_REQUEST",
                message="Telegram target is required",
                status_code=400,
            )
        return
    if not target.strip():
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message=f"{_gateway_channel_label(channel)} target is required",
            status_code=400,
        )


def _resolve_gateway_requested_channel(
    value: object,
    *,
    label: str = "channel",
    reject_webchat_as_internal_only: bool = False,
    rejected_webchat_message: str | None = None,
) -> str:
    channel = _require_non_empty_string(value, label=label)
    normalized = _normalize_gateway_chat_channel_id(channel)
    if normalized is not None:
        return normalized
    if reject_webchat_as_internal_only and channel.lower() == "webchat":
        raise GatewayNodeMethodError(
            code="INVALID_REQUEST",
            message=(
                rejected_webchat_message
                or "unsupported channel: webchat (internal-only). Use `chat.send` for "
                "WebChat UI messages or choose a deliverable channel."
            ),
            status_code=400,
        )
    raise GatewayNodeMethodError(
        code="INVALID_REQUEST",
        message=f"unsupported channel: {channel}",
        status_code=400,
    )


def _require_unknown_mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    normalized: dict[str, Any] = {}
    for key, entry in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{label} keys must be strings")
        normalized[key] = entry
    return normalized


def _validate_message_action_tool_context(value: object) -> None:
    tool_context = _require_unknown_mapping(value, label="toolContext")
    _validate_exact_keys(
        "message.action.toolContext",
        tool_context,
        allowed_keys=(
            "currentChannelId",
            "currentGraphChannelId",
            "currentChannelProvider",
            "currentThreadTs",
            "currentMessageId",
            "replyToMode",
            "hasRepliedRef",
            "skipCrossContextDecoration",
        ),
    )
    for label in (
        "currentChannelId",
        "currentGraphChannelId",
        "currentChannelProvider",
        "currentThreadTs",
    ):
        if label in tool_context and tool_context.get(label) is not None:
            _require_string(tool_context.get(label), label=f"toolContext.{label}")
    current_message_id = tool_context.get("currentMessageId")
    if current_message_id is not None and not isinstance(current_message_id, (str, int, float)):
        raise ValueError("toolContext.currentMessageId must be a string or number")
    if isinstance(current_message_id, bool):
        raise ValueError("toolContext.currentMessageId must be a string or number")
    if "replyToMode" in tool_context and tool_context.get("replyToMode") is not None:
        _optional_enum_value(
            tool_context.get("replyToMode"),
            label="toolContext.replyToMode",
            allowed_values={"off", "first", "all", "batched"},
        )
    has_replied_ref = tool_context.get("hasRepliedRef")
    if has_replied_ref is not None:
        resolved_has_replied_ref = _require_unknown_mapping(
            has_replied_ref,
            label="toolContext.hasRepliedRef",
        )
        _validate_exact_keys(
            "message.action.toolContext.hasRepliedRef",
            resolved_has_replied_ref,
            allowed_keys=("value",),
        )
        _require_bool(
            resolved_has_replied_ref.get("value"),
            label="toolContext.hasRepliedRef.value",
        )
    if (
        "skipCrossContextDecoration" in tool_context
        and tool_context.get("skipCrossContextDecoration") is not None
    ):
        _optional_bool(
            tool_context.get("skipCrossContextDecoration"),
            label="toolContext.skipCrossContextDecoration",
        )


def _optional_error_payload(
    value: object,
) -> dict[str, str | None] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("error must be an object")
    code = value.get("code")
    message = value.get("message")
    if code is not None and not isinstance(code, str):
        raise ValueError("error.code must be a string")
    if message is not None and not isinstance(message, str):
        raise ValueError("error.message must be a string")
    return {
        "code": code if isinstance(code, str) else None,
        "message": message if isinstance(message, str) else None,
    }


def _toolsets_from_value(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    toolsets: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        normalized = trimmed.lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        toolsets.append(trimmed)
    return toolsets


def _build_node_command_rejection_hint(
    reason: str | None,
    command: str,
    node: KnownNode,
) -> str:
    platform = node.platform or "unknown"
    if reason == "command not declared by node":
        return (
            f"node command not allowed: the node (platform: {platform}) "
            f'does not support "{command}"'
        )
    if reason == "command not allowlisted":
        return (
            f'node command not allowed: "{command}" is not in the allowlist for platform '
            f'"{platform}"'
        )
    if reason == "node did not declare commands":
        return "node command not allowed: the node did not declare any supported commands"
    if reason:
        return f"node command not allowed: {reason}"
    return "node command not allowed"


def _pairing_request_id_from_result(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    request = result.get("request")
    if not isinstance(request, dict):
        return None
    request_id = request.get("requestId")
    if not isinstance(request_id, str):
        return None
    trimmed_request_id = request_id.strip()
    return trimmed_request_id or None


def _known_node_payload(node: KnownNode) -> dict[str, Any]:
    return {
        "nodeId": node.node_id,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "clientId": node.client_id,
        "clientMode": node.client_mode,
        "remoteIp": node.remote_ip,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "pathEnv": node.path_env,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "permissions": node.permissions,
        "paired": node.paired,
        "connected": node.connected,
        "connectedAtMs": node.connected_at_ms,
        "approvedAtMs": node.approved_at_ms,
    }


def _known_paired_node_payload(node: GatewayPairedNode) -> dict[str, Any]:
    return {
        "nodeId": node.node_id,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "clientId": None,
        "clientMode": None,
        "remoteIp": node.remote_ip,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "pathEnv": None,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "permissions": node.permissions,
        "paired": True,
        "connected": False,
        "connectedAtMs": node.last_connected_at_ms,
        "approvedAtMs": node.approved_at_ms,
    }


def _merge_known_node_payload(
    persisted: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    observed_caps = observed.get("caps")
    observed_commands = observed.get("commands")
    visible_commands = _visible_paired_commands(
        persisted.get("commands"),
        observed_commands,
    )
    return {
        "nodeId": observed["nodeId"],
        "displayName": observed.get("displayName") or persisted.get("displayName"),
        "platform": observed.get("platform") or persisted.get("platform"),
        "version": observed.get("version") or persisted.get("version"),
        "coreVersion": observed.get("coreVersion") or persisted.get("coreVersion"),
        "uiVersion": observed.get("uiVersion") or persisted.get("uiVersion"),
        "clientId": observed.get("clientId"),
        "clientMode": observed.get("clientMode"),
        "remoteIp": observed.get("remoteIp") or persisted.get("remoteIp"),
        "deviceFamily": observed.get("deviceFamily") or persisted.get("deviceFamily"),
        "modelIdentifier": observed.get("modelIdentifier") or persisted.get("modelIdentifier"),
        "pathEnv": observed.get("pathEnv"),
        "caps": observed_caps if observed_caps is not None else persisted.get("caps") or [],
        "commands": visible_commands if visible_commands is not None else [],
        "permissions": (
            observed.get("permissions")
            if observed.get("permissions") is not None
            else persisted.get("permissions")
        ),
        "paired": bool(observed.get("paired") or persisted.get("paired")),
        "connected": bool(observed.get("connected")),
        "connectedAtMs": (
            observed.get("connectedAtMs")
            if observed.get("connectedAtMs") is not None
            else persisted.get("connectedAtMs")
        ),
        "approvedAtMs": (
            observed.get("approvedAtMs")
            if observed.get("approvedAtMs") is not None
            else persisted.get("approvedAtMs")
        ),
    }


def _known_node_sort_key_from_payload(payload: dict[str, Any]) -> tuple[int, str, str]:
    display_name = str(payload.get("displayName") or payload.get("nodeId") or "").strip().lower()
    return (0 if payload.get("connected") else 1, display_name, str(payload.get("nodeId") or ""))


def _visible_paired_commands(
    persisted_commands: object,
    observed_commands: object,
) -> list[str] | None:
    approved = (
        [command for command in persisted_commands if isinstance(command, str)]
        if isinstance(persisted_commands, list)
        else None
    )
    live = (
        [command for command in observed_commands if isinstance(command, str)]
        if isinstance(observed_commands, list)
        else None
    )
    if live is None:
        return approved
    if approved is None:
        return live
    approved_set = set(approved)
    return [command for command in live if command in approved_set]


def _paired_node_payload(node: KnownNode) -> dict[str, Any]:
    return {
        "nodeId": node.node_id,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": None,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.connected_at_ms,
    }


def _stored_paired_node_payload(node: GatewayPairedNode) -> dict[str, Any]:
    return {
        "nodeId": node.node_id,
        "token": node.token,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "deviceFamily": node.device_family,
        "modelIdentifier": node.model_identifier,
        "caps": list(node.caps),
        "commands": list(node.commands),
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": node.created_at_ms,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.last_connected_at_ms,
    }


def _merge_paired_node_payload(
    persisted: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "nodeId": persisted["nodeId"],
        "token": (
            persisted.get("token")
            if persisted.get("token") is not None
            else observed.get("token")
        ),
        "displayName": observed.get("displayName") or persisted.get("displayName"),
        "platform": observed.get("platform") or persisted.get("platform"),
        "version": observed.get("version") or persisted.get("version"),
        "coreVersion": observed.get("coreVersion") or persisted.get("coreVersion"),
        "uiVersion": observed.get("uiVersion") or persisted.get("uiVersion"),
        "deviceFamily": observed.get("deviceFamily") or persisted.get("deviceFamily"),
        "modelIdentifier": (
            observed.get("modelIdentifier") or persisted.get("modelIdentifier")
        ),
        "caps": (
            persisted.get("caps")
            if persisted.get("caps") is not None
            else observed.get("caps") or []
        ),
        "commands": (
            persisted.get("commands")
            if persisted.get("commands") is not None
            else observed.get("commands") or []
        ),
        "remoteIp": observed.get("remoteIp") or persisted.get("remoteIp"),
        "permissions": (
            persisted.get("permissions")
            if persisted.get("permissions") is not None
            else observed.get("permissions")
        ),
        "createdAtMs": persisted.get("createdAtMs"),
        "approvedAtMs": persisted.get("approvedAtMs")
        if persisted.get("approvedAtMs") is not None
        else observed.get("approvedAtMs"),
        "lastConnectedAtMs": (
            observed.get("lastConnectedAtMs")
            if observed.get("lastConnectedAtMs") is not None
            else persisted.get("lastConnectedAtMs")
        ),
    }


def _paired_node_sort_key(payload: dict[str, Any]) -> tuple[int, str]:
    approved_at_ms = payload.get("approvedAtMs")
    resolved_approved_at_ms = approved_at_ms if isinstance(approved_at_ms, int) else -1
    return (-resolved_approved_at_ms, str(payload.get("nodeId") or ""))
