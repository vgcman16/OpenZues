from __future__ import annotations

import json
import re
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, cast
from urllib.parse import quote, urlsplit, urlunsplit

from openzues.database import Database, utcnow
from openzues.schemas import (
    GatewayNodePendingActionAckView,
    GatewayNodePendingActionPullView,
    GatewayNodePendingWorkDrainView,
    GatewayNodePendingWorkEnqueueView,
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
from openzues.services.gateway_method_policy import TALK_SECRETS_GATEWAY_METHOD_SCOPE
from openzues.services.gateway_models import GatewayModelsService
from openzues.services.gateway_node_command_policy import (
    is_node_command_allowed,
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
from openzues.services.gateway_sessions import GatewaySessionsService
from openzues.services.gateway_skill_bins import GatewaySkillBinsService
from openzues.services.gateway_skill_catalog import GatewaySkillCatalogService
from openzues.services.gateway_skill_status import GatewaySkillStatusService
from openzues.services.gateway_system_presence import GatewaySystemPresenceService
from openzues.services.gateway_talk_config import GatewayTalkConfigService
from openzues.services.gateway_tools_catalog import GatewayToolsCatalogService
from openzues.services.gateway_tts import GatewayTtsService
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.hub import BroadcastHub
from openzues.services.session_keys import resolve_thread_session_keys, session_key_lookup_aliases

_NODE_PENDING_WORK_TYPES = {"status.request", "location.request"}
_NODE_PENDING_WORK_PRIORITIES = {"normal", "high"}
_CANVAS_CAPABILITY_PATH_PREFIX = "/__openclaw__/cap"
_CANVAS_CAPABILITY_TTL_MS = 10 * 60_000
_SESSION_LABEL_MAX_LENGTH = 512
_SESSION_PATCH_RESPONSE_USAGE_VALUES = {"full", "off", "on", "tokens"}
_SESSION_PATCH_SUBAGENT_ROLE_VALUES = {"leaf", "orchestrator"}
_SESSION_PATCH_SUBAGENT_CONTROL_SCOPE_VALUES = {"children", "none"}
_SESSION_PATCH_SEND_POLICY_VALUES = {"allow", "deny"}
_SESSION_PATCH_GROUP_ACTIVATION_VALUES = {"always", "mention"}
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

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class GatewayNodeMethodRequester:
    node_id: str | None = None
    caller_scopes: tuple[str, ...] | None = None


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
        commands_service: GatewayCommandsService | None = None,
        config_service: GatewayConfigService | None = None,
        config_schema_service: GatewayConfigSchemaService | None = None,
        cron_service: GatewayCronService | None = None,
        create_task_blueprint: Callable[..., Awaitable[object]] | None = None,
        run_task_blueprint_now: Callable[..., Awaitable[object]] | None = None,
        delete_task_blueprint: Callable[[int], Awaitable[None]] | None = None,
        health_service: GatewayHealthService | None = None,
        gateway_identity_service: GatewayIdentityService | None = None,
        last_heartbeat_service: GatewayLastHeartbeatService | None = None,
        models_service: GatewayModelsService | None = None,
        sessions_service: GatewaySessionsService | None = None,
        system_presence_service: GatewaySystemPresenceService | None = None,
        talk_config_service: GatewayTalkConfigService | None = None,
        tts_service: GatewayTtsService | None = None,
        tools_catalog_service: GatewayToolsCatalogService | None = None,
        skill_bins_service: GatewaySkillBinsService | None = None,
        skill_catalog_service: GatewaySkillCatalogService | None = None,
        skill_status_service: GatewaySkillStatusService | None = None,
        chat_send_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        chat_abort_service: Callable[..., Awaitable[dict[str, object]]] | None = None,
        status_service: Callable[[], Awaitable[dict[str, object]]] | None = None,
        voicewake_service: GatewayVoiceWakeService | None = None,
        sync: Callable[[], Awaitable[None]] | None = None,
        wake_node: Callable[[str], Awaitable[bool]] | None = None,
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
        self._models_service = models_service or GatewayModelsService()
        self._sessions_service = sessions_service
        if self._sessions_service is None and self._database is not None:
            self._sessions_service = GatewaySessionsService(self._database)
        self._system_presence_service = system_presence_service
        if self._system_presence_service is None and self._gateway_identity_service is not None:
            self._system_presence_service = GatewaySystemPresenceService(
                registry,
                gateway_identity_service=self._gateway_identity_service,
            )
        self._talk_config_service = talk_config_service or GatewayTalkConfigService()
        self._tts_service = tts_service or GatewayTtsService()
        self._tools_catalog_service = tools_catalog_service or GatewayToolsCatalogService()
        self._skill_bins_service = skill_bins_service or GatewaySkillBinsService()
        self._skill_catalog_service = skill_catalog_service or GatewaySkillCatalogService()
        self._skill_status_service = skill_status_service or GatewaySkillStatusService()
        self._chat_send_service = chat_send_service
        self._chat_abort_service = chat_abort_service
        self._gateway_chat_run_ids_by_session_key: dict[str, str] = {}
        self._status_service = status_service
        self._voicewake_service = voicewake_service
        self._sync = sync
        self._wake_node = wake_node

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
            node_payloads: dict[str, dict[str, Any]] = {
                node.node_id: _known_node_payload(node)
                for node in self.registry.list_known_nodes()
            }
            if self._pairing_service is not None:
                for paired_node in await self._pairing_service.list_paired_nodes():
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

        if resolved_method == "models.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return await self._models_service.build_catalog()

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
            _validate_exact_keys(resolved_method, payload, allowed_keys=("mode", "text"))
            _require_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"next-heartbeat", "now"},
            )
            _require_non_empty_string(payload.get("text"), label="text")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="wake is unavailable until control-plane wake queue is wired",
                status_code=503,
            )

        if resolved_method == "sessions.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("includeGlobal", "includeUnknown", "limit"),
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
            return await self._sessions_service.build_snapshot(
                include_global=bool(include_global),
                include_unknown=bool(include_unknown),
                limit=limit,
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
            session_id = _optional_non_empty_string(payload.get("sessionId"), label="sessionId")
            label = _optional_non_empty_string(payload.get("label"), label="label")
            agent_id = _optional_non_empty_string(payload.get("agentId"), label="agentId")
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
                session_id=session_id,
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
            _optional_non_empty_string(payload.get("key"), label="key")
            _optional_date_string(payload.get("startDate"), label="startDate")
            _optional_date_string(payload.get("endDate"), label="endDate")
            _optional_enum_value(
                payload.get("mode"),
                label="mode",
                allowed_values={"gateway", "specific", "utc"},
            )
            _optional_utc_offset_string(payload.get("utcOffset"), label="utcOffset")
            _optional_bounded_int(
                payload.get("limit"),
                label="limit",
                minimum=1,
                maximum=1000,
            )
            _optional_bool(payload.get("includeContextWeight"), label="includeContextWeight")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="sessions.usage is unavailable until session usage analytics are wired",
                status_code=503,
            )

        if resolved_method == "sessions.usage.timeseries":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.usage.timeseries is unavailable until session usage analytics "
                    "are wired"
                ),
                status_code=503,
            )

        if resolved_method == "sessions.usage.logs":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "limit"),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            _optional_bounded_int(payload.get("limit"), label="limit", minimum=1, maximum=1000)
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.usage.logs is unavailable until session usage analytics are wired"
                ),
                status_code=503,
            )

        if resolved_method == "talk.mode":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("enabled", "phase"))
            _require_bool(payload.get("enabled"), label="enabled")
            _optional_non_empty_string(payload.get("phase"), label="phase")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="Talk mode broadcast is not wired in OpenZues yet",
                status_code=503,
            )

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
            _require_non_empty_string(payload.get("text"), label="text")
            _optional_non_empty_string(payload.get("provider"), label="provider")
            _optional_non_empty_string(payload.get("voiceId"), label="voiceId")
            _optional_non_empty_string(payload.get("modelId"), label="modelId")
            _optional_non_empty_string(payload.get("outputFormat"), label="outputFormat")
            _optional_number(payload.get("speed"), label="speed")
            _optional_number(payload.get("rateWpm"), label="rateWpm")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="Talk synthesis runtime not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "tts.enable":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="TTS runtime not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "tts.disable":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="TTS runtime not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "tts.setProvider":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("provider",))
            _require_non_empty_string(payload.get("provider"), label="provider")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="TTS runtime not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "tts.convert":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("channel", "modelId", "provider", "text", "voiceId"),
            )
            _require_non_empty_string(payload.get("text"), label="text")
            _optional_non_empty_string(payload.get("provider"), label="provider")
            _optional_non_empty_string(payload.get("modelId"), label="modelId")
            _optional_non_empty_string(payload.get("voiceId"), label="voiceId")
            _optional_non_empty_string(payload.get("channel"), label="channel")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="TTS conversion runtime not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "config.get":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._config_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="config.get is unavailable until gateway config is wired",
                    status_code=503,
                )
            return self._config_service.build_snapshot()

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

        if resolved_method == "channels.status":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._channels_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="channels.status is unavailable until channel inventory is wired",
                    status_code=503,
                )
            return await self._channels_service.build_snapshot()

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
            _require_non_empty_string(payload.get("sessionKey"), label="sessionKey")
            agent_id = _optional_non_empty_string(payload.get("agentId"), label="agentId")
            if agent_id is not None and agent_id != "openzues":
                raise ValueError(f'unknown agent id "{agent_id}"')
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="Effective tool inventory is not wired in OpenZues yet",
                status_code=503,
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
                    "timeoutMs",
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
            message = _require_string(payload.get("message"), label="message")
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            deliver = _optional_bool(payload.get("deliver"), label="deliver")
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
            send_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=deliver,
                timeout_ms=timeout_ms,
            )
            self._remember_gateway_chat_run(session_key, send_result)
            return send_result

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
            message = _require_string(payload.get("message"), label="message")
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            attachments = payload.get("attachments")
            if attachments is not None:
                if not isinstance(attachments, list):
                    raise ValueError("attachments must be an array")
                if attachments:
                    raise ValueError("sessions.send attachments are not supported in OpenZues yet")
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
            send_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=None,
                timeout_ms=timeout_ms,
            )
            self._remember_gateway_chat_run(session_key, send_result)
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
            message = _require_string(payload.get("message"), label="message")
            thinking = (
                _require_string(payload.get("thinking"), label="thinking")
                if "thinking" in payload and payload.get("thinking") is not None
                else None
            )
            attachments = payload.get("attachments")
            if attachments is not None:
                if not isinstance(attachments, list):
                    raise ValueError("attachments must be an array")
                if attachments:
                    raise ValueError("sessions.steer attachments are not supported in OpenZues yet")
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
            if self._chat_send_service is None or self._chat_abort_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "sessions.steer is unavailable until control chat interruption is wired"
                    ),
                    status_code=503,
                )
            if self._tracked_gateway_chat_run_id(session_key) is not None:
                await self._abort_gateway_chat_run(session_key=session_key, run_id=None)
            steer_result = await self._chat_send_service(
                session_key=session_key,
                message=message,
                idempotency_key=idempotency_key,
                thinking=thinking,
                deliver=None,
                timeout_ms=timeout_ms,
            )
            self._remember_gateway_chat_run(session_key, steer_result)
            await self._publish_sessions_changed_event(
                session_key=session_key,
                reason="steer",
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
                        "sessions.reset is unavailable until control chat session reset "
                        "is wired"
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
            next_metadata: dict[str, Any] = {}
            if isinstance(existing_metadata_row, dict):
                metadata_value = existing_metadata_row.get("metadata")
                if isinstance(metadata_value, dict):
                    next_metadata = dict(metadata_value)
            await self._database.delete_control_chat_messages(session_key=canonical_key)
            await self._database.upsert_gateway_session_metadata(
                session_key=canonical_key,
                metadata=next_metadata,
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

            resolved_delete_transcript = (
                True if delete_transcript is None else delete_transcript
            )
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
            if message_count and resolved_delete_transcript:
                await self._database.delete_control_chat_messages(session_key=canonical_key)
            if metadata_row is not None:
                await self._database.delete_gateway_session_metadata(canonical_key)
            self._forget_gateway_chat_run(canonical_key)
            await self._publish_sessions_changed_event(
                session_key=canonical_key,
                reason="delete",
                now_ms=now_ms,
            )
            return {"ok": True, "key": canonical_key, "deleted": True, "archived": []}

        if resolved_method == "sessions.compact":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "maxLines"),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            _optional_bounded_int(
                payload.get("maxLines"),
                label="maxLines",
                minimum=1,
                maximum=1_000_000,
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="sessions.compact is unavailable until control chat compaction is wired",
                status_code=503,
            )

        if resolved_method == "sessions.compaction.restore":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            _require_non_empty_string(payload.get("checkpointId"), label="checkpointId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.compaction.restore is unavailable until control chat compaction "
                    "restore is wired"
                ),
                status_code=503,
            )

        if resolved_method == "sessions.compaction.list":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.compaction.list is unavailable until control chat compaction "
                    "checkpoints are wired"
                ),
                status_code=503,
            )

        if resolved_method == "sessions.compaction.get":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            _require_non_empty_string(payload.get("checkpointId"), label="checkpointId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.compaction.get is unavailable until control chat compaction "
                    "checkpoints are wired"
                ),
                status_code=503,
            )

        if resolved_method == "sessions.compaction.branch":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key", "checkpointId"),
            )
            _require_non_empty_string(payload.get("key"), label="key")
            _require_non_empty_string(payload.get("checkpointId"), label="checkpointId")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message=(
                    "sessions.compaction.branch is unavailable until control chat compaction "
                    "branching is wired"
                ),
                status_code=503,
            )

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
            return {"subscribed": False, "key": _canonical_session_key(session_key)}

        if resolved_method == "sessions.messages.unsubscribe":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("key",),
            )
            session_key = _require_non_empty_string(payload.get("key"), label="key")
            return {"subscribed": False, "key": _canonical_session_key(session_key)}

        if resolved_method == "sessions.subscribe":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return {"subscribed": False}

        if resolved_method == "sessions.unsubscribe":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            return {"subscribed": False}

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
            metadata = (
                dict(raw_metadata)
                if isinstance(raw_metadata, dict)
                else {}
            )
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
                self._remember_gateway_chat_run(canonical_key, send_result)
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
            run_id = _optional_non_empty_string(payload.get("runId"), label="runId")
            return await self._abort_gateway_chat_run(
                session_key=session_key,
                run_id=run_id,
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
            return await self._agents_service.get_identity(
                agent_id=_optional_non_empty_string(payload.get("agentId"), label="agentId"),
                session_key=_optional_non_empty_string(
                    payload.get("sessionKey"),
                    label="sessionKey",
                ),
            )

        if resolved_method == "agents.files.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=("agentId",))
            if self._agent_files_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message=(
                        "agents.files.list is unavailable until workspace file inventory "
                        "is wired"
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

        if resolved_method == "last-heartbeat":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            if self._last_heartbeat_service is None:
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="last-heartbeat is unavailable until gateway events are wired",
                    status_code=503,
                )
            return await self._last_heartbeat_service.build_snapshot()

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
                _require_non_empty_string(payload.get("slug"), label="slug")
                _optional_non_empty_string(payload.get("version"), label="version")
                _optional_bool(payload.get("force"), label="force")
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="ClawHub skill install is not wired in OpenZues yet",
                    status_code=503,
                )
            _require_non_empty_string(payload.get("name"), label="name")
            _require_non_empty_string(payload.get("installId"), label="installId")
            _optional_bool(
                payload.get("dangerouslyForceUnsafeInstall"),
                label="dangerouslyForceUnsafeInstall",
            )
            _optional_bounded_int(
                payload.get("timeoutMs"),
                label="timeoutMs",
                minimum=1,
                maximum=2_592_000_000,
            )
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="Gateway-host skill installers are not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "skills.update":
            _validate_exact_keys(
                resolved_method,
                payload,
                allowed_keys=("all", "apiKey", "enabled", "env", "skillKey", "slug", "source"),
            )
            source = _optional_non_empty_string(payload.get("source"), label="source")
            if source == "clawhub" or "slug" in payload or "all" in payload:
                if "slug" in payload:
                    _optional_non_empty_string(payload.get("slug"), label="slug")
                if "all" in payload:
                    _optional_bool(payload.get("all"), label="all")
                raise GatewayNodeMethodError(
                    code="UNAVAILABLE",
                    message="ClawHub skill update is not wired in OpenZues yet",
                    status_code=503,
                )
            _require_non_empty_string(payload.get("skillKey"), label="skillKey")
            if "enabled" in payload:
                _optional_bool(payload.get("enabled"), label="enabled")
            if "apiKey" in payload:
                _optional_non_empty_string(payload.get("apiKey"), label="apiKey")
            if "env" in payload:
                _require_string_mapping(payload.get("env"), label="env")
            raise GatewayNodeMethodError(
                code="UNAVAILABLE",
                message="Skill config patching is not wired in OpenZues yet",
                status_code=503,
            )

        if resolved_method == "node.pair.list":
            _validate_exact_keys(resolved_method, payload, allowed_keys=())
            pending_requests = (
                [] if self._pairing_service is None else await self._pairing_service.list_pending()
            )
            paired_payloads: dict[str, dict[str, Any]] = {}
            if self._pairing_service is not None:
                for paired in await self._pairing_service.list_paired():
                    paired_payloads[str(paired["nodeId"])] = dict(paired)
            for node in self.registry.list_known_nodes():
                if not node.paired:
                    continue
                node_payload = _paired_node_payload(node)
                existing = paired_payloads.get(node.node_id)
                paired_payloads[node.node_id] = (
                    node_payload
                    if existing is None
                    else _merge_paired_node_payload(existing, node_payload)
                )
            paired_nodes = sorted(
                paired_payloads.values(),
                key=_paired_node_sort_key,
            )
            return {
                "pending": pending_requests,
                "paired": paired_nodes,
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
            request_result = await self._pairing_service.request(
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
                caps=_optional_string_list(payload.get("caps"), label="caps"),
                commands=_optional_string_list(payload.get("commands"), label="commands"),
                remote_ip=_optional_non_empty_string(payload.get("remoteIp"), label="remoteIp"),
                silent=_optional_bool(payload.get("silent"), label="silent"),
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
                raise ValueError(
                    f"missing scope: {missing_scope}"
                )
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
                    merged_paired_node = await self._pairing_service.get_paired_node(
                        wanted_node_id
                    )
                    if merged_paired_node is not None:
                        payload_node = _merge_known_node_payload(
                            _known_paired_node_payload(merged_paired_node),
                            payload_node,
                        )
                return {"ts": timestamp_ms, **payload_node}
            if self._pairing_service is not None:
                stored_paired_node = await self._pairing_service.get_paired_node(
                    wanted_node_id
                )
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
            if self.registry.get(target_node_id) is None and self._wake_node is not None:
                await self._wake_node(target_node_id)
                refreshed_node = self.registry.describe_known_node(target_node_id)
                if refreshed_node is not None:
                    target_node = refreshed_node
            allowlist = resolve_node_command_allowlist(
                platform=target_node.platform,
                device_family=target_node.device_family,
            )
            allowed, reason = is_node_command_allowed(
                command=command,
                declared_commands=target_node.commands,
                allowlist=allowlist,
            )
            if not allowed:
                raise ValueError(
                    _build_node_command_rejection_hint(reason, command, target_node)
                )

            result = await self.registry.invoke(
                node_id=target_node_id,
                command=command,
                params=payload.get("params"),
                timeout_ms=timeout_ms,
                idempotency_key=idempotency_key,
            )
            if not result.ok:
                raise GatewayNodeMethodError(
                    code=str((result.error or {}).get("code") or "UNAVAILABLE"),
                    message=str((result.error or {}).get("message") or "node invoke failed"),
                    status_code=503,
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
                allowed_keys=("nodeId", "type", "priority", "expiresInMs", "wake"),
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

            queued = self.registry.enqueue_pending_work(
                node_id=target_node_id,
                work_type=cast(NodePendingWorkType, work_type),
                priority=cast(NodePendingWorkPriority | None, priority),
                expires_in_ms=expires_in_ms,
            )
            wake_triggered = False
            if (
                wake is not False
                and not queued.deduped
                and self.registry.get(target_node_id) is None
                and self._wake_node is not None
            ):
                wake_triggered = await self._wake_node(target_node_id)
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

        raise ValueError(f"unsupported method: {resolved_method}")

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
        if not node_id or self.registry.get(node_id) is None:
            raise ValueError(f"{method} requires a connected device identity")
        return node_id

    def _remember_gateway_chat_run(self, session_key: str, payload: dict[str, object]) -> None:
        run_id = payload.get("runId")
        if not isinstance(run_id, str):
            return
        trimmed_run_id = run_id.strip()
        if not trimmed_run_id:
            return
        for alias in _session_key_aliases(session_key):
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

    def _forget_gateway_chat_run(self, session_key: str) -> None:
        for alias in _session_key_aliases(session_key):
            self._gateway_chat_run_ids_by_session_key.pop(alias, None)


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
        raise ValueError(
            f"{label} must match UTC+H, UTC-H, UTC+HH, UTC-HH, UTC+H:MM, or UTC-HH:MM"
        )
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


def _build_node_command_rejection_hint(
    reason: str | None,
    command: str,
    node: KnownNode,
) -> str:
    platform = node.platform or "unknown"
    if reason == "command not declared by node":
        return (
            f'node command not allowed: the node (platform: {platform}) '
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
        "caps": observed.get("caps") or persisted.get("caps") or [],
        "commands": observed.get("commands") or persisted.get("commands") or [],
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


def _paired_node_payload(node: KnownNode) -> dict[str, Any]:
    return {
        "nodeId": node.node_id,
        "displayName": node.display_name,
        "platform": node.platform,
        "version": node.version,
        "coreVersion": node.core_version,
        "uiVersion": node.ui_version,
        "remoteIp": node.remote_ip,
        "permissions": node.permissions,
        "createdAtMs": None,
        "approvedAtMs": node.approved_at_ms,
        "lastConnectedAtMs": node.connected_at_ms,
    }


def _merge_paired_node_payload(
    persisted: dict[str, Any],
    observed: dict[str, Any],
) -> dict[str, Any]:
    return {
        "nodeId": persisted["nodeId"],
        "displayName": persisted.get("displayName") or observed.get("displayName"),
        "platform": persisted.get("platform") or observed.get("platform"),
        "version": persisted.get("version") or observed.get("version"),
        "coreVersion": persisted.get("coreVersion") or observed.get("coreVersion"),
        "uiVersion": persisted.get("uiVersion") or observed.get("uiVersion"),
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
