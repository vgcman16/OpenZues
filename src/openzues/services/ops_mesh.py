from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openzues.database import Database, utcnow
from openzues.schemas import (
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
    NotificationRouteView,
    OperatorView,
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
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.playbooks import PlaybookService, summarize_playbook_result
from openzues.services.reflexes import build_reflex_deck
from openzues.services.scope_enforcer import build_scope_assessment
from openzues.services.skillbook import materialize_skillbook_pins
from openzues.services.vault import VaultService, mask_secret

logger = logging.getLogger(__name__)
DEFAULT_TASK_COMPLETION_MARKER = "TASK COMPLETE"


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
    if task.cadence_minutes is None or not task.enabled:
        return None
    last = _parse_timestamp(task.last_launched_at)
    if last is None:
        return utcnow()
    return (last + timedelta(minutes=task.cadence_minutes)).isoformat()


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


def _serialize_task(row: dict[str, Any]) -> TaskBlueprintView:
    return TaskBlueprintView.model_validate(row)


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
        project.id
        for project in projects
        if _path_matches_project(instance.cwd, project.path)
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
        * _capability_terms(name, kind, source),
        * _capability_terms_for_url(base_url),
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
                    capability_labels.add(
                        f"{match['kind'].replace('_', ' ')}: {match['name']}"
                    )
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
                source_kinds=sorted({
                    "integration",
                    *(match_type for lane in lane_views for match_type in lane.match_types),
                }),
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
        item.tracked and item.readiness in {"auth_gap", "lane_gap", "degraded"}
        for item in items
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
                    _skill_matches_pin(skill, pin)
                    for skill in lane_skill_rows.get(instance.id, [])
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
                    _skill_matches_pin(skill, pin)
                    for skill in lane_skill_rows.get(instance.id, [])
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
) -> str:
    sections = [task.objective_template]
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
    )


def _build_task_views(
    *,
    instances: list[InstanceView],
    missions: list[MissionView],
    projects: list[ProjectView],
    task_blueprints: list[TaskBlueprintView],
    skill_pins: list[SkillPinView],
    integrations: list[IntegrationView],
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
        scoped_skills = materialize_skillbook_pins(
            task.project_id or 0,
            task.objective_template,
            explicit_pins=skills_by_project.get(task.project_id or -1, []),
            project_label=project.label if project is not None else None,
            project_path=project.path if project is not None else None,
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
            add_item(
                item_id=f"mission:{mission.id}:handoff",
                kind="checkpoint_ready",
                source="Checkpoints",
                urgency="ready",
                lane_label=lane_label,
                project_label=mission.project_label,
                title=f"Handoff ready from {mission.name}",
                summary=_summarize_text(mission.last_checkpoint),
                recommended_action=_mission_action(
                    mission,
                    "Review the checkpoint and resume only when the next slice is clear.",
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
    access_posture: DashboardAccessPostureView | None = None,
    teams: list[TeamView] | None = None,
    operators: list[OperatorView] | None = None,
    remote_requests: list[RemoteRequestView] | None = None,
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
    )
    inbox_items = _build_task_inbox_items(
        instances=instances,
        missions=missions,
        tasks=tasks,
        playbooks=playbooks,
        projects=projects,
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
    playbooks: PlaybookService = field(default_factory=PlaybookService)
    poll_interval_seconds: float = 20.0
    snapshot_interval_seconds: float = 1800.0
    _task: asyncio.Task[None] | None = field(init=False, default=None)
    _stop_event: asyncio.Event = field(init=False, default_factory=asyncio.Event)
    _notified_inbox_items: dict[str, str] = field(init=False, default_factory=dict)

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

    async def list_task_blueprint_views(self) -> list[TaskBlueprintView]:
        return [_serialize_task(row) for row in await self.database.list_task_blueprints()]

    async def list_vault_secret_views(self) -> list[VaultSecretView]:
        return await self.vault.list_secret_views()

    async def create_vault_secret(self, payload: VaultSecretCreate) -> VaultSecretView:
        return await self.vault.create_secret(payload)

    async def delete_vault_secret(self, secret_id: int) -> None:
        await self.vault.delete_secret(secret_id)

    async def list_notification_route_views(self) -> list[NotificationRouteView]:
        await self._migrate_legacy_secret_refs()
        secrets_by_id = {
            secret.id: secret for secret in await self.vault.list_secret_views()
        }
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

    async def list_integration_views(self) -> list[IntegrationView]:
        await self._migrate_legacy_secret_refs()
        secrets_by_id = {
            secret.id: secret for secret in await self.vault.list_secret_views()
        }
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
                    if status == "completed" and _task_has_terminal_completion(task, summary):
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
        await self._deliver_notifications(event_type, event)
        await self._publish_derived_task_inbox_notifications()

    async def tick_once(self) -> None:
        tasks = await self.list_task_blueprint_views()
        missions = await self.missions.list_views()
        instances = await self.manager.list_views()
        playbooks = [
            PlaybookView.model_validate(row)
            for row in await self.database.list_playbooks()
        ]

        for task in tasks:
            if not task.enabled:
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

    async def build_task_draft(self, task_id: int) -> MissionDraftView:
        row = await self.database.get_task_blueprint(task_id)
        if row is None:
            raise KeyError(f"Unknown task blueprint {task_id}")
        task = _serialize_task(row)
        return await self._build_draft_for_task(task)

    async def _deliver_notifications(self, event_type: str, event: dict[str, Any]) -> None:
        await self._migrate_legacy_secret_refs()
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
                secret_id = route.get("vault_secret_id")
                secret_token = (
                    await self.vault.get_secret_value(int(secret_id))
                    if secret_id is not None
                    else (str(route.get("secret_token")) if route.get("secret_token") else None)
                )
                await asyncio.to_thread(self._post_webhook, route, event_type, event, secret_token)
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

    def _post_webhook(
        self,
        route: dict[str, Any],
        event_type: str,
        event: dict[str, Any],
        secret_token: str | None,
    ) -> None:
        body = json.dumps({"eventType": event_type, "payload": event}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        secret_header_name = route.get("secret_header_name")
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
