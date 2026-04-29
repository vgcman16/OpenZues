from __future__ import annotations

import asyncio
import codecs
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import typer
import uvicorn

from openzues.app import build_brief, build_launchpad, build_radar
from openzues.database import Database
from openzues.schemas import (
    BrowserPostureView,
    ConversationTargetView,
    DashboardView,
    GatewayBootstrapView,
    GatewayCapabilityView,
    HermesDoctorView,
    HermesRuntimeProfileUpdate,
    HermesUpdateView,
    MissionCreate,
    NotificationRouteCreate,
    OnboardingBootstrapCreate,
    ProjectView,
    SetupWizardSessionUpdate,
)
from openzues.services.access import AccessService
from openzues.services.browser_posture import build_browser_posture
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.control_chat import (
    ControlChatService,
    plan_attention_queue,
    plan_control_chat,
)
from openzues.services.control_plane import ControlPlaneLease
from openzues.services.cortex import build_cortex, build_doctrines
from openzues.services.device_bootstrap_profile import default_device_bootstrap_profile
from openzues.services.environment import EnvironmentService
from openzues.services.followups import operator_blocked_missions
from openzues.services.gateway_agents import GatewayAgentsService
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.gateway_capability import GatewayCapabilityService
from openzues.services.gateway_channels import GatewayChannelsService
from openzues.services.gateway_commands import GatewayCommandsService
from openzues.services.github import GitHubService
from openzues.services.hermes_platform import HermesPlatformService
from openzues.services.hermes_runtime_profile import load_saved_runtime_preferences
from openzues.services.hub import BroadcastHub
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.onboarding import OnboardingService
from openzues.services.ops_mesh import OpsMeshService
from openzues.services.playbooks import PlaybookService
from openzues.services.projects import ProjectService
from openzues.services.recall import RecallService
from openzues.services.remote_ops import RemoteOpsService
from openzues.services.runtime_updates import RuntimeUpdateService
from openzues.services.setup import SetupService
from openzues.services.swarm import SWARM_COLLABORATION_MODE
from openzues.services.vault import VaultService
from openzues.settings import Settings, settings

app = typer.Typer(help="OpenZues local control plane")
_ATTENTION_QUEUE_IDLE_REPLY = (
    "The attention queue is clear right now. There is no bounded move to fire."
)
_DEFAULT_WATCH_TASK_NAME = "OpenClaw Total Parity Program"
_DEFAULT_BROWSER_SESSION = "openzues-browser"
_DEFAULT_BROWSER_WATCH_SESSION = "openzues-watch"
_BROWSER_RENDERED_SCREENSHOT_MIN_BYTES = 32_768
_BROWSER_BLANK_SCREENSHOT_MAX_BYTES = 8_192
_BROWSER_SNAPSHOT_CHAR_LIMIT = 24_000
_BROWSER_SNAPSHOT_LINE_LIMIT = 240
_WATCH_LEADER_PID_RE = re.compile(r"Leader PID:\s*(?P<pid>\d+)", re.IGNORECASE)


def _coerce_int(value: object) -> int:
    return int(cast("int | str", value or 0))


gateway_app = typer.Typer(help="Inspect and stamp the saved gateway bootstrap profile.")
browser_app = typer.Typer(help="Inspect and run the browser verification/runtime surface.")
hermes_app = typer.Typer(help="Inspect and tune Hermes runtime posture.")
routes_app = typer.Typer(help="Inspect and test notification routes.")
agents_app = typer.Typer(help="Inspect configured agent inventory.")
channels_app = typer.Typer(help="Inspect notification route channels.")
hermes_profile_app = typer.Typer(
    help="Inspect or update the saved Hermes runtime profile.",
    invoke_without_command=True,
)
update_app = typer.Typer(help="Inspect self-update posture and restart-safe repo state.")
setup_app = typer.Typer(
    help="Inspect, reuse, or reset the saved setup posture.",
    invoke_without_command=True,
)
setup_wizard_app = typer.Typer(
    help="Inspect or adjust the saved setup wizard session.",
    invoke_without_command=True,
)
app.add_typer(gateway_app, name="gateway")
app.add_typer(browser_app, name="browser")
app.add_typer(hermes_app, name="hermes")
app.add_typer(routes_app, name="routes")
app.add_typer(agents_app, name="agents")
app.add_typer(channels_app, name="channels")
hermes_app.add_typer(hermes_profile_app, name="profile")
app.add_typer(update_app, name="update")
app.add_typer(setup_app, name="setup")
setup_app.add_typer(setup_wizard_app, name="wizard")


def _runtime_settings() -> Settings:
    return Settings()


def _control_plane_base_url(app_settings: Settings) -> str:
    lease = ControlPlaneLease(app_settings.data_dir / "control-plane.lock")
    try:
        raw = lease.metadata_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raw = ""
    except OSError:
        raw = ""

    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            host_value = str(payload.get("host") or "").strip()
            port_value = payload.get("port")
            if isinstance(port_value, bool):
                port_number = 0
            elif isinstance(port_value, int):
                port_number = port_value
            elif isinstance(port_value, str):
                try:
                    port_number = int(port_value)
                except ValueError:
                    port_number = 0
            else:
                port_number = 0
            if (
                host_value
                and port_number > 0
                and _control_plane_metadata_endpoint_is_reachable(host_value, port_number)
            ):
                return _watch_base_url(url=None, host=host_value, port=port_number)

    return _watch_base_url(url=None, host=app_settings.host, port=app_settings.port)


def _control_plane_metadata_endpoint_is_reachable(
    host: str,
    port: int,
    *,
    timeout_seconds: float = 0.35,
) -> bool:
    normalized_host = _normalize_local_control_plane_host(host)
    if normalized_host is None:
        return True
    try:
        with socket.create_connection((normalized_host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def _normalize_local_control_plane_host(host: str) -> str | None:
    value = str(host or "").strip().lower()
    if not value:
        return None
    if value in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return "127.0.0.1"
    if value in {"::1", "[::1]", "::"}:
        return "::1"
    return None


def _try_live_api_model(
    base_url: str,
    path: str,
    model_type: Any,
    *,
    timeout_seconds: float,
) -> Any | None:
    try:
        payload = _watch_api_json(base_url, path, timeout_seconds=timeout_seconds)
    except RuntimeError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return model_type.model_validate(payload)
    except Exception:
        return None


async def _try_live_dashboard_view(app_settings: Settings) -> DashboardView | None:
    base_url = _control_plane_base_url(app_settings)
    result = await asyncio.to_thread(
        _try_live_api_model,
        base_url,
        "/api/dashboard",
        DashboardView,
        timeout_seconds=20.0,
    )
    return cast("DashboardView | None", result)


async def _try_live_status_payload(app_settings: Settings) -> dict[str, object] | None:
    base_url = _control_plane_base_url(app_settings)
    try:
        payload = await asyncio.to_thread(
            _watch_api_json,
            base_url,
            "/api/status",
            timeout_seconds=8.0,
        )
    except RuntimeError:
        return None
    return payload if isinstance(payload, dict) else None


async def _try_live_gateway_capability_view(
    app_settings: Settings,
) -> GatewayCapabilityView | None:
    base_url = _control_plane_base_url(app_settings)
    result = await asyncio.to_thread(
        _try_live_api_model,
        base_url,
        "/api/gateway/capability",
        GatewayCapabilityView,
        timeout_seconds=15.0,
    )
    return cast("GatewayCapabilityView | None", result)


async def _try_live_gateway_bootstrap_view(
    app_settings: Settings,
) -> GatewayBootstrapView | None:
    base_url = _control_plane_base_url(app_settings)
    result = await asyncio.to_thread(
        _try_live_api_model,
        base_url,
        "/api/gateway/bootstrap",
        GatewayBootstrapView,
        timeout_seconds=15.0,
    )
    return cast("GatewayBootstrapView | None", result)


async def _try_live_hermes_doctor_view(app_settings: Settings) -> HermesDoctorView | None:
    base_url = _control_plane_base_url(app_settings)
    result = await asyncio.to_thread(
        _try_live_api_model,
        base_url,
        "/api/hermes/doctor",
        HermesDoctorView,
        timeout_seconds=15.0,
    )
    return cast("HermesDoctorView | None", result)


async def _try_live_update_view(app_settings: Settings) -> HermesUpdateView | None:
    base_url = _control_plane_base_url(app_settings)
    result = await asyncio.to_thread(
        _try_live_api_model,
        base_url,
        "/api/update/status",
        HermesUpdateView,
        timeout_seconds=10.0,
    )
    return cast("HermesUpdateView | None", result)


@dataclass(slots=True)
class CliServices:
    settings: Settings
    database: Database
    manager: RuntimeManager
    control_chat: ControlChatService
    project_service: ProjectService
    mission_service: MissionService
    access: AccessService
    onboarding: OnboardingService
    gateway_capability: GatewayCapabilityService
    gateway_agents: GatewayAgentsService
    gateway_channels: GatewayChannelsService
    gateway_commands: GatewayCommandsService
    ops_mesh: OpsMeshService
    recall: RecallService
    hermes_platform: HermesPlatformService
    gateway_bootstrap: GatewayBootstrapService
    runtime_updates: RuntimeUpdateService
    setup: SetupService


async def _build_services(app_settings: Settings) -> CliServices:
    database = Database(app_settings.effective_db_path)
    hub = BroadcastHub()
    desktop_service = CodexDesktopService(
        approval_policy=app_settings.desktop_approval_policy,
        sandbox_mode=app_settings.desktop_sandbox_mode,
    )
    manager = RuntimeManager(database, hub, desktop_service=desktop_service)
    access = AccessService(database)
    environment = EnvironmentService(desktop_service=desktop_service)
    vault = VaultService(database, app_settings)
    launch_routing = LaunchRoutingService(database, manager)
    mission_service = MissionService(database, manager, hub)
    project_service = ProjectService(GitHubService())
    ops_mesh = OpsMeshService(
        database,
        manager,
        mission_service,
        hub,
        vault,
        playbooks=PlaybookService(),
        launch_routing=launch_routing,
    )
    gateway_bootstrap = GatewayBootstrapService(database, manager, access, launch_routing)
    gateway_agents = GatewayAgentsService(database=database)
    gateway_commands = GatewayCommandsService()
    setup = SetupService(database, manager, access, gateway_bootstrap, ops_mesh)
    onboarding = OnboardingService(
        database,
        manager,
        access,
        ops_mesh,
        gateway_bootstrap,
        setup,
    )
    remote_ops = RemoteOpsService(
        database,
        manager,
        mission_service,
        ops_mesh,
        hub,
    )
    gateway_capability = GatewayCapabilityService(
        database,
        manager,
        mission_service,
        access,
        remote_ops,
        ops_mesh,
        gateway_bootstrap,
        environment,
    )
    gateway_channels = GatewayChannelsService(
        list_notification_route_views=ops_mesh.list_notification_route_views,
    )
    control_chat = ControlChatService(
        database,
        mission_service,
        manager,
        hub,
    )
    ops_mesh.session_delivery_service = control_chat.append_session_assistant_message
    recall = RecallService(mission_service, database)
    runtime_updates = RuntimeUpdateService(
        database,
        enabled=app_settings.auto_self_update_enabled,
        poll_interval_seconds=app_settings.auto_self_update_poll_interval_seconds,
        restart_callback=lambda: asyncio.sleep(0),
    )
    hermes_platform = HermesPlatformService(
        database,
        manager,
        mission_service,
        project_service,
        gateway_bootstrap,
        app_settings,
        runtime_updates=runtime_updates,
        poll_interval_seconds=app_settings.hermes_learning_poll_interval_seconds,
    )

    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    vault.initialize()
    await database.initialize()
    await access.initialize()
    await manager.load(auto_connect=False)
    return CliServices(
        settings=app_settings,
        database=database,
        manager=manager,
        control_chat=control_chat,
        project_service=project_service,
        mission_service=mission_service,
        access=access,
        onboarding=onboarding,
        gateway_capability=gateway_capability,
        gateway_agents=gateway_agents,
        gateway_channels=gateway_channels,
        gateway_commands=gateway_commands,
        ops_mesh=ops_mesh,
        recall=recall,
        hermes_platform=hermes_platform,
        gateway_bootstrap=gateway_bootstrap,
        runtime_updates=runtime_updates,
        setup=setup,
    )


def _run(coro):
    return asyncio.run(coro)


async def _close_services(services: CliServices) -> None:
    await services.control_chat.close_attention_queue()
    await services.runtime_updates.close()
    await services.hermes_platform.close()
    await services.ops_mesh.close()
    await services.mission_service.close()
    await services.manager.close()


async def _run_with_services(action):
    services = await _build_services(_runtime_settings())
    try:
        return await action(services)
    finally:
        await _close_services(services)


def _emit_payload(payload: object, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if isinstance(payload, dict):
        headline = payload.get("headline")
        summary = payload.get("summary")
        if headline:
            typer.echo(str(headline))
        if summary:
            typer.echo(str(summary))
        warnings = payload.get("warnings")
        if isinstance(warnings, list):
            for warning in warnings:
                typer.echo(f"warning: {warning}")
        api_key = payload.get("api_key")
        if api_key:
            typer.echo(f"api_key: {api_key}")
        return
    typer.echo(str(payload))


def _emit_agents_inventory(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    agents = payload.get("agents")
    if not isinstance(agents, list):
        _emit_payload(payload, json_output=False)
        return

    default_id = str(payload.get("defaultId") or "").strip()
    main_key = str(payload.get("mainKey") or "").strip()
    scope = str(payload.get("scope") or "").strip()
    typer.echo("Agents:")
    summary_bits: list[str] = []
    if default_id:
        summary_bits.append(f"default: {default_id}")
    if main_key:
        summary_bits.append(f"main key: {main_key}")
    if scope:
        summary_bits.append(f"scope: {scope}")
    if summary_bits:
        typer.echo("  " + " | ".join(summary_bits))

    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "").strip()
        if not agent_id:
            continue
        label = str(agent.get("name") or "").strip()
        heading = f"- {agent_id}"
        if label and label != agent_id:
            heading += f" ({label})"
        if agent_id == default_id:
            heading += " [default]"
        typer.echo(heading)

        workspace = str(agent.get("workspace") or "").strip()
        if workspace:
            typer.echo("  workspace: " + workspace)

        identity = agent.get("identity")
        if isinstance(identity, dict):
            identity_name = str(identity.get("name") or "").strip()
            avatar_url = str(identity.get("avatarUrl") or identity.get("avatar") or "").strip()
            identity_bits = [bit for bit in (identity_name, avatar_url) if bit]
            if identity_bits:
                typer.echo("  identity: " + " | ".join(identity_bits))

        model = agent.get("model")
        if isinstance(model, dict):
            primary_model = str(model.get("primary") or "").strip()
            if primary_model:
                typer.echo("  model: " + primary_model)


def _emit_channel_inventory(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    channel_order = payload.get("channelOrder")
    if not isinstance(channel_order, list):
        _emit_payload(payload, json_output=False)
        return

    channel_labels = payload.get("channelLabels")
    channel_detail_labels = payload.get("channelDetailLabels")
    channel_accounts = payload.get("channelAccounts")
    channel_default_account_id = payload.get("channelDefaultAccountId")
    channels = payload.get("channels")
    if not isinstance(channel_labels, dict):
        channel_labels = {}
    if not isinstance(channel_detail_labels, dict):
        channel_detail_labels = {}
    if not isinstance(channel_accounts, dict):
        channel_accounts = {}
    if not isinstance(channel_default_account_id, dict):
        channel_default_account_id = {}
    if not isinstance(channels, dict):
        channels = {}

    typer.echo("Channels:")
    route_count = payload.get("routeCount")
    enabled_count = payload.get("enabledCount")
    conversation_target_count = payload.get("conversationTargetCount")
    summary_bits: list[str] = []
    if isinstance(route_count, int):
        summary_bits.append(f"routes: {route_count}")
    if isinstance(enabled_count, int):
        summary_bits.append(f"enabled: {enabled_count}")
    if isinstance(conversation_target_count, int):
        summary_bits.append(f"targets: {conversation_target_count}")
    if summary_bits:
        typer.echo("  " + " | ".join(summary_bits))

    for channel_id_value in channel_order:
        channel_id = str(channel_id_value or "").strip()
        if not channel_id:
            continue
        label = str(channel_labels.get(channel_id) or channel_id).strip() or channel_id
        detail_label = str(channel_detail_labels.get(channel_id) or label).strip() or label
        heading = f"- {detail_label}"
        if channel_id != detail_label:
            heading += f" ({channel_id})"
        typer.echo(heading)

        summary = channels.get(channel_id)
        if isinstance(summary, dict):
            stats: list[str] = []
            for key, label_name in (
                ("routeCount", "routes"),
                ("enabledRouteCount", "enabled"),
                ("conversationTargetCount", "targets"),
                ("accountCount", "accounts"),
            ):
                value = summary.get(key)
                if isinstance(value, int):
                    stats.append(f"{value} {label_name}")
            if stats:
                typer.echo("  " + ", ".join(stats))

        default_account_id = str(channel_default_account_id.get(channel_id) or "").strip()
        if default_account_id:
            typer.echo("  default account: " + default_account_id)

        accounts = channel_accounts.get(channel_id)
        if isinstance(accounts, list):
            for account in accounts[:3]:
                if not isinstance(account, dict):
                    continue
                account_id = str(account.get("accountId") or "").strip()
                if not account_id:
                    continue
                bits: list[str] = []
                for key, label_name in (
                    ("routeCount", "routes"),
                    ("enabledRouteCount", "enabled"),
                    ("conversationTargetCount", "targets"),
                ):
                    value = account.get(key)
                    if isinstance(value, int):
                        bits.append(f"{value} {label_name}")
                line = f"  - {account_id}"
                if bits:
                    line += ": " + ", ".join(bits)
                typer.echo(line)


def _emit_gateway_bootstrap(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    launch_defaults_summary = str(payload.get("launch_defaults_summary") or "").strip()
    if launch_defaults_summary:
        typer.echo("launch defaults: " + launch_defaults_summary)
    launch_route = payload.get("launch_route")
    if isinstance(launch_route, dict):
        summary = str(launch_route.get("summary") or "").strip()
        if summary:
            typer.echo("launch route: " + summary)
    runtime_inventory = payload.get("runtime_inventory")
    if isinstance(runtime_inventory, dict):
        typer.echo("runtime inventory: " + str(runtime_inventory.get("summary") or ""))
        browser_runtime = runtime_inventory.get("browser_runtime")
        if isinstance(browser_runtime, dict):
            typer.echo("browser runtime: " + str(browser_runtime.get("summary") or ""))
            browser_methods = browser_runtime.get("methods")
            if isinstance(browser_methods, list) and browser_methods:
                typer.echo(
                    "browser methods: "
                    + ", ".join(
                        str(method_name)
                        for method_name in browser_methods[:6]
                        if str(method_name).strip()
                    )
                )
            browser_services = browser_runtime.get("services")
            if isinstance(browser_services, list) and browser_services:
                typer.echo(
                    "browser services: "
                    + ", ".join(
                        str(service_name)
                        for service_name in browser_services[:6]
                        if str(service_name).strip()
                    )
                )
            recommended_action = str(browser_runtime.get("recommended_action") or "").strip()
            if recommended_action:
                typer.echo("browser action: " + recommended_action)
        method_catalog = runtime_inventory.get("method_catalog")
        if isinstance(method_catalog, dict):
            typer.echo("method catalog: " + str(method_catalog.get("summary") or ""))


def _emit_gateway_capability(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    connected_lane_health = payload.get("connected_lane_health")
    if isinstance(connected_lane_health, dict):
        typer.echo("lane health: " + str(connected_lane_health.get("summary") or ""))
    inventory = payload.get("inventory")
    if isinstance(inventory, dict):
        typer.echo("inventory: " + str(inventory.get("summary") or ""))
        typer.echo("memory: " + str(inventory.get("memory_summary") or ""))
        browser_runtime = inventory.get("browser_runtime")
        if isinstance(browser_runtime, dict):
            typer.echo("browser runtime: " + str(browser_runtime.get("summary") or ""))
            browser_methods = browser_runtime.get("methods")
            if isinstance(browser_methods, list) and browser_methods:
                typer.echo(
                    "browser methods: "
                    + ", ".join(
                        str(method_name)
                        for method_name in browser_methods[:6]
                        if str(method_name).strip()
                    )
                )
            browser_services = browser_runtime.get("services")
            if isinstance(browser_services, list) and browser_services:
                typer.echo(
                    "browser services: "
                    + ", ".join(
                        str(service_name)
                        for service_name in browser_services[:6]
                        if str(service_name).strip()
                    )
                )
            recommended_action = str(browser_runtime.get("recommended_action") or "").strip()
            if recommended_action:
                typer.echo("browser action: " + recommended_action)
        method_catalog = inventory.get("method_catalog")
        if isinstance(method_catalog, dict):
            typer.echo("method catalog: " + str(method_catalog.get("summary") or ""))
            method_tools = method_catalog.get("tools")
            if isinstance(method_tools, list) and method_tools:
                typer.echo(
                    "method tools: "
                    + ", ".join(str(tool) for tool in method_tools[:6] if str(tool).strip())
                )
            reserved_admin_methods = method_catalog.get("reserved_admin_methods")
            if isinstance(reserved_admin_methods, list) and reserved_admin_methods:
                typer.echo(
                    "reserved admin methods: "
                    + ", ".join(
                        str(tool) for tool in reserved_admin_methods[:6] if str(tool).strip()
                    )
                )
            method_scopes = method_catalog.get("scopes")
            if isinstance(method_scopes, list) and method_scopes:
                scope_labels: list[str] = []
                for scope_entry in method_scopes[:6]:
                    if not isinstance(scope_entry, dict):
                        continue
                    scope_name = str(scope_entry.get("scope") or "").strip()
                    method_count = scope_entry.get("method_count")
                    if not scope_name:
                        continue
                    if isinstance(method_count, int):
                        scope_labels.append(f"{scope_name} ({method_count})")
                    else:
                        scope_labels.append(scope_name)
                if scope_labels:
                    typer.echo("method scopes: " + ", ".join(scope_labels))
        memory_evidence = inventory.get("memory_evidence")
        if isinstance(memory_evidence, list):
            for evidence in memory_evidence[:3]:
                typer.echo("memory evidence: " + str(evidence))
        memory_proof_reference = inventory.get("memory_proof_reference")
        if isinstance(memory_proof_reference, dict):
            typer.echo("memory proof: " + str(memory_proof_reference.get("summary") or ""))
            continuity_path = str(memory_proof_reference.get("continuity_path") or "").strip()
            if continuity_path:
                typer.echo("memory proof continuity: " + continuity_path)
        memory_proof_continuity = inventory.get("memory_proof_continuity")
        if isinstance(memory_proof_continuity, dict):
            state = str(memory_proof_continuity.get("state") or "").strip()
            score = memory_proof_continuity.get("score")
            if state:
                suffix = f" ({score}/100)" if isinstance(score, int) else ""
                typer.echo(f"memory relay: {state}{suffix}")
            summary = str(memory_proof_continuity.get("summary") or "").strip()
            if summary:
                typer.echo("memory relay summary: " + summary)
            anchor = str(memory_proof_continuity.get("anchor") or "").strip()
            if anchor:
                typer.echo("memory relay anchor: " + anchor)
            next_handoff = str(memory_proof_continuity.get("next_handoff") or "").strip()
            if next_handoff:
                typer.echo("memory relay next: " + next_handoff)
        if inventory.get("memory_proof_launchable"):
            launch_label = str(inventory.get("memory_proof_launch_label") or "").strip()
            if launch_label:
                typer.echo("memory proof launch: " + launch_label)
    approval_posture = payload.get("approval_posture")
    if isinstance(approval_posture, dict):
        typer.echo("approvals: " + str(approval_posture.get("summary") or ""))
    launch_policy = payload.get("launch_policy")
    if isinstance(launch_policy, dict):
        typer.echo("launch policy: " + str(launch_policy.get("summary") or ""))
        launch_route = launch_policy.get("launch_route")
        if isinstance(launch_route, dict):
            conversation_target = launch_route.get("conversation_target")
            if isinstance(conversation_target, dict):
                summary = str(conversation_target.get("summary") or "").strip()
                if summary:
                    typer.echo("conversation target: " + summary)
            conversation_reuse = launch_route.get("conversation_reuse")
            if isinstance(conversation_reuse, dict):
                typer.echo("conversation reuse: " + str(conversation_reuse.get("summary") or ""))
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, dict):
        typer.echo("diagnostics: " + str(diagnostics.get("summary") or ""))


def _emit_browser_status(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    control_plane_url = str(payload.get("control_plane_url") or "").strip()
    if control_plane_url:
        typer.echo("control plane: " + control_plane_url)
    local_agent_browser = payload.get("local_agent_browser")
    if isinstance(local_agent_browser, dict):
        typer.echo("local browser: " + str(local_agent_browser.get("summary") or ""))
    saved_launch = payload.get("saved_launch")
    if isinstance(saved_launch, dict):
        typer.echo("saved launch: " + str(saved_launch.get("summary") or ""))
    saved_launch_browser_runtime = payload.get("saved_launch_browser_runtime")
    if isinstance(saved_launch_browser_runtime, dict):
        typer.echo(
            "saved browser runtime: "
            + str(saved_launch_browser_runtime.get("summary") or "")
        )
    live_gateway_browser_runtime = payload.get("live_gateway_browser_runtime")
    if isinstance(live_gateway_browser_runtime, dict):
        typer.echo(
            "live browser runtime: "
            + str(live_gateway_browser_runtime.get("summary") or "")
        )
    recommended_action = str(payload.get("recommended_action") or "").strip()
    if recommended_action:
        typer.echo("browser action: " + recommended_action)


def _emit_browser_verify(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    url = str(payload.get("url") or "").strip()
    session = str(payload.get("session") or "").strip()
    title = str(payload.get("title") or "").strip()
    snapshot_summary = str(payload.get("snapshot_summary") or "").strip()
    screenshot_path = str(payload.get("screenshot_path") or "").strip()
    if url:
        typer.echo("url: " + url)
    if session:
        typer.echo("session: " + session)
    if title:
        typer.echo("title: " + title)
    if snapshot_summary:
        typer.echo("snapshot: " + snapshot_summary)
    if screenshot_path:
        typer.echo("screenshot: " + screenshot_path)


def _emit_browser_stream(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    session = str(payload.get("session") or "").strip()
    if session:
        typer.echo("session: " + session)
    lines = payload.get("lines")
    if isinstance(lines, list):
        for line in lines:
            text = str(line).strip()
            if text:
                typer.echo(text)


def _emit_browser_doctor(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_browser_status(payload, json_output=False)
    verification = payload.get("verification")
    if not isinstance(verification, dict):
        return

    status = str(verification.get("status") or "").strip()
    summary = str(verification.get("summary") or "").strip()
    if status or summary:
        typer.echo(
            "browser verify: " + " / ".join(part for part in (status, summary) if part)
        )
    url = str(verification.get("url") or "").strip()
    if url:
        typer.echo("verify url: " + url)
    session = str(verification.get("session") or "").strip()
    if session:
        typer.echo("verify session: " + session)
    title = str(verification.get("title") or "").strip()
    if title:
        typer.echo("verify title: " + title)
    screenshot_path = str(verification.get("screenshot_path") or "").strip()
    if screenshot_path:
        typer.echo("verify screenshot: " + screenshot_path)


def _browser_verify_payload(
    *,
    verification: dict[str, object],
    resolved_url: str,
    session: str,
) -> dict[str, object]:
    ok = bool(verification.get("ok"))
    return {
        **verification,
        "ok": ok,
        "status": str(verification.get("status") or ("ready" if ok else "warn")).strip()
        or ("ready" if ok else "warn"),
        "headline": (
            "Browser verification passed"
            if ok
            else "Browser verification found issues"
        ),
        "summary": str(verification.get("summary") or "").strip(),
        "url": str(verification.get("url") or resolved_url).strip() or resolved_url,
        "session": session,
    }


def _browser_verify_error_payload(
    *,
    summary: str,
    resolved_url: str,
    session: str,
) -> dict[str, object]:
    return {
        "ok": False,
        "status": "warn",
        "headline": "Browser verification needs attention",
        "summary": summary,
        "url": resolved_url,
        "session": session,
    }


def _browser_command_status_payload() -> dict[str, object]:
    try:
        command = _browser_command()
    except RuntimeError as exc:
        return {
            "available": False,
            "command": None,
            "summary": str(exc),
        }
    return {
        "available": True,
        "command": command,
        "summary": f"agent-browser is available at {command}.",
    }


async def _build_browser_status_payload(services: CliServices) -> dict[str, object]:
    control_plane_url = _control_plane_base_url(services.settings)
    bootstrap_view = await _try_live_gateway_bootstrap_view(services.settings)
    if bootstrap_view is None:
        bootstrap_view = await services.gateway_bootstrap.get_view()
    capability_view = await _try_live_gateway_capability_view(services.settings)
    if capability_view is None:
        capability_view = await services.gateway_capability.get_view()
    return build_browser_posture(
        control_plane_url=control_plane_url,
        gateway_bootstrap=bootstrap_view,
        gateway_capability=capability_view,
    ).model_dump(mode="json")


def _browser_stream_payload(
    *,
    label: str,
    session: str,
    output: str,
) -> dict[str, object]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return {
        "ok": True,
        "status": "ready",
        "headline": f"Browser {label} captured",
        "summary": f"Captured {len(lines)} {label} line(s) from session {session}.",
        "session": session,
        "line_count": len(lines),
        "lines": lines,
    }


def _emit_memory_proof_mission(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    mission_label = payload.get("name") or "MemPalace Direct Proof"
    typer.echo(f"memory proof mission {payload.get('id')}: {mission_label}")
    instance_name = str(payload.get("instance_name") or "").strip()
    if instance_name:
        typer.echo(f"lane: {instance_name}")
    project_label = str(payload.get("project_label") or "").strip()
    if project_label:
        typer.echo(f"scope: {project_label}")
    status = str(payload.get("status") or "").strip()
    phase = str(payload.get("phase") or "").strip()
    if status or phase:
        typer.echo(f"status: {status or 'unknown'}" + (f" ({phase})" if phase else ""))
    thread_id = str(payload.get("thread_id") or "").strip()
    if thread_id:
        typer.echo(f"thread: {thread_id}")
    objective = str(payload.get("objective") or "").strip()
    if objective:
        typer.echo(objective.splitlines()[0])


def _emit_recall(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    items = payload.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        mission_id = item.get("mission_id")
        name = str(item.get("mission_name") or "Mission")
        prefix = f"[M{mission_id}] " if mission_id is not None else ""
        typer.echo(f"{prefix}{name}")
        project_label = str(item.get("project_label") or "").strip()
        detail_parts: list[str] = []
        if item.get("match_source"):
            detail_parts.append(str(item["match_source"]))
        if item.get("score") is not None:
            detail_parts.append(f"score {item['score']}")
        if project_label:
            detail_parts.append(project_label)
        freshness = item.get("freshness_minutes")
        if freshness is not None:
            detail_parts.append(f"{freshness}m ago")
        if detail_parts:
            typer.echo("  " + " | ".join(detail_parts))
        excerpt = str(item.get("excerpt") or "").strip()
        if excerpt:
            typer.echo("  " + excerpt)
        next_handoff = str(item.get("next_handoff") or "").strip()
        if next_handoff:
            typer.echo("  next: " + next_handoff)
        continuity_path = str(item.get("continuity_path") or "").strip()
        if continuity_path:
            typer.echo("  continuity: " + continuity_path)


def _emit_cortex(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    reviews = payload.get("reviews")
    if isinstance(reviews, list) and reviews:
        for review in reviews:
            if not isinstance(review, dict):
                continue
            level = str(review.get("level") or "info").upper()
            typer.echo(f"[{level}] {str(review.get('title') or 'Learning review')}")
            detail_parts: list[str] = []
            project_label = str(review.get("project_label") or "").strip()
            if project_label:
                detail_parts.append(project_label)
            evidence_count = review.get("evidence_count")
            if evidence_count:
                detail_parts.append(f"{evidence_count} evidence points")
            recommended_toolsets = review.get("recommended_toolsets")
            if isinstance(recommended_toolsets, list) and recommended_toolsets:
                detail_parts.append(", ".join(str(item) for item in recommended_toolsets[:4]))
            if detail_parts:
                typer.echo("  " + " | ".join(detail_parts))
            summary = str(review.get("summary") or "").strip()
            if summary:
                typer.echo("  " + summary)
            recommendation = str(review.get("recommendation") or "").strip()
            if recommendation:
                typer.echo("  next: " + recommendation)
        return

    doctrines = payload.get("doctrines")
    if isinstance(doctrines, list) and doctrines:
        doctrine = doctrines[0]
        if isinstance(doctrine, dict):
            typer.echo("[DOCTRINE] " + str(doctrine.get("project_label") or "Workspace"))
            typer.echo("  " + str(doctrine.get("summary") or ""))
        return

    typer.echo("No Hermes learning reviews yet.")


def _emit_hermes_doctor(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    profile = payload.get("profile")
    if isinstance(profile, dict):
        typer.echo("profile: " + str(profile.get("summary") or ""))
    promotion_loop = payload.get("promotion_loop")
    if isinstance(promotion_loop, dict):
        typer.echo("learning: " + str(promotion_loop.get("summary") or ""))
    for key in ("memory", "executors", "plugins", "delivery", "acp", "extras"):
        section = payload.get(key)
        if isinstance(section, dict):
            typer.echo(f"{key}: " + str(section.get("summary") or ""))
    updates = payload.get("updates")
    if isinstance(updates, dict):
        typer.echo("updates: " + str(updates.get("summary") or ""))
    warnings = payload.get("warnings")
    if isinstance(warnings, list):
        for warning in warnings:
            typer.echo("warning: " + str(warning))


def _emit_update_status(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    repo_root = str(payload.get("repo_root") or "").strip()
    if repo_root:
        typer.echo("repo: " + repo_root)
    current_revision = str(payload.get("current_revision") or "").strip()
    if current_revision:
        typer.echo("current revision: " + current_revision)
    pending_revision = str(payload.get("pending_revision") or "").strip()
    if pending_revision:
        typer.echo("pending revision: " + pending_revision)
    if payload.get("pending_restart"):
        typer.echo(
            "restart posture: "
            + ("safe now" if payload.get("safe_to_restart") else "waiting for a safe boundary")
        )


def _emit_continue_action(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    reply = str(payload.get("reply") or "").strip()
    if reply:
        typer.echo(reply)
    mode = str(payload.get("mode") or "").strip()
    if mode:
        typer.echo(f"mode: {mode}")
    action_kind = str(payload.get("action_kind") or "").strip()
    if action_kind:
        typer.echo(f"action: {action_kind}")
    target_label = str(payload.get("target_label") or "").strip()
    if target_label:
        typer.echo(f"target: {target_label}")
    opportunity_id = str(payload.get("opportunity_id") or "").strip()
    if opportunity_id:
        typer.echo(f"opportunity: {opportunity_id}")
    mission_id = payload.get("mission_id")
    if mission_id is not None:
        typer.echo(f"mission: {mission_id}")


def _emit_attention_queue_action(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    _emit_payload(payload, json_output=False)
    reply = str(payload.get("reply") or "").strip()
    if reply:
        typer.echo(reply)
    typer.echo(f"mode: {payload.get('mode') or 'unknown'}")
    typer.echo(f"executed: {bool(payload.get('executed'))}")
    typer.echo(f"action: {payload.get('action_kind') or 'idle'}")
    status = str(payload.get("status") or "").strip()
    if status:
        typer.echo(f"status: {status}")
    signal_id = str(payload.get("signal_id") or "").strip()
    if signal_id:
        typer.echo(f"signal: {signal_id}")
    target_label = str(payload.get("target_label") or "").strip()
    if target_label:
        typer.echo(f"target: {target_label}")
    opportunity_id = str(payload.get("opportunity_id") or "").strip()
    if opportunity_id:
        typer.echo(f"opportunity: {opportunity_id}")
    mission_id = payload.get("mission_id")
    if mission_id is not None:
        typer.echo(f"mission: {mission_id}")


def _emit_status(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    headline = str(payload.get("headline") or "").strip()
    if headline:
        typer.echo(headline)
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(summary)

    status_plan = payload.get("status_plan")
    if isinstance(status_plan, dict):
        reply = str(status_plan.get("reply") or "").strip()
        if reply:
            typer.echo("status: " + reply)

    mission_summary = payload.get("mission_summary")
    if isinstance(mission_summary, dict):
        typer.echo(
            "missions: "
            f"{mission_summary.get('active_count', 0)} active, "
            f"{mission_summary.get('blocked_count', 0)} blocked, "
            f"{mission_summary.get('paused_count', 0)} paused, "
            f"{mission_summary.get('failed_count', 0)} failed"
        )

    instance_summary = payload.get("instance_summary")
    if isinstance(instance_summary, dict):
        typer.echo(
            "lanes: "
            f"{instance_summary.get('connected_count', 0)} connected / "
            f"{instance_summary.get('total_count', 0)} total"
        )

    browser_posture = payload.get("browser_posture")
    if isinstance(browser_posture, dict):
        typer.echo("browser: " + str(browser_posture.get("summary") or ""))
        local_agent_browser = browser_posture.get("local_agent_browser")
        if isinstance(local_agent_browser, dict):
            typer.echo("browser tool: " + str(local_agent_browser.get("summary") or ""))
        recommended_action = str(browser_posture.get("recommended_action") or "").strip()
        if recommended_action:
            typer.echo("browser action: " + recommended_action)

    gateway_capability = payload.get("gateway_capability")
    if isinstance(gateway_capability, dict):
        typer.echo("gateway: " + str(gateway_capability.get("summary") or ""))
        connected_lane_health = gateway_capability.get("connected_lane_health")
        if isinstance(connected_lane_health, dict):
            typer.echo("lane health: " + str(connected_lane_health.get("summary") or ""))
        inventory = gateway_capability.get("inventory")
        if isinstance(inventory, dict):
            typer.echo("inventory: " + str(inventory.get("summary") or ""))
        approval_posture = gateway_capability.get("approval_posture")
        if isinstance(approval_posture, dict):
            typer.echo("approvals: " + str(approval_posture.get("summary") or ""))
        launch_policy = gateway_capability.get("launch_policy")
        if isinstance(launch_policy, dict):
            typer.echo("launch policy: " + str(launch_policy.get("summary") or ""))
            launch_route = launch_policy.get("launch_route")
            if isinstance(launch_route, dict):
                conversation_target = launch_route.get("conversation_target")
                if isinstance(conversation_target, dict):
                    summary = str(conversation_target.get("summary") or "").strip()
                    if summary:
                        typer.echo("conversation target: " + summary)
                conversation_reuse = launch_route.get("conversation_reuse")
                if isinstance(conversation_reuse, dict):
                    typer.echo(
                        "conversation reuse: "
                        + str(conversation_reuse.get("summary") or "")
                    )
        warnings = gateway_capability.get("warnings")
        if isinstance(warnings, list):
            for warning in warnings[:3]:
                typer.echo("warning: " + str(warning))

    radar = payload.get("radar")
    if isinstance(radar, dict):
        typer.echo("radar: " + str(radar.get("summary") or ""))
        signals = radar.get("signals")
        if isinstance(signals, list):
            for signal in signals[:3]:
                if not isinstance(signal, dict):
                    continue
                level = str(signal.get("level") or "info").upper()
                title = str(signal.get("title") or "Signal").strip()
                detail = str(signal.get("detail") or "").strip()
                signal_id = str(signal.get("id") or "").strip()
                label = f"{title} ({signal_id})" if signal_id else title
                if detail:
                    typer.echo(f"[{level}] {label}: {detail}")
                else:
                    typer.echo(f"[{level}] {label}")

    launchpad = payload.get("launchpad")
    if isinstance(launchpad, dict):
        typer.echo("launchpad: " + str(launchpad.get("summary") or ""))
        opportunities = launchpad.get("opportunities")
        if isinstance(opportunities, list):
            for opportunity in opportunities[:3]:
                if not isinstance(opportunity, dict):
                    continue
                title = str(opportunity.get("title") or "").strip()
                opportunity_id = str(opportunity.get("id") or "").strip()
                label = title or opportunity_id
                if not label:
                    continue
                if opportunity_id and title:
                    typer.echo(f"opportunity: {label} ({opportunity_id})")
                    continue
                typer.echo("opportunity: " + label)

    queue_plan = payload.get("queue_plan")
    if isinstance(queue_plan, dict):
        reply = str(queue_plan.get("reply") or "").strip()
        if reply:
            typer.echo("queue: " + reply)

    brief = payload.get("brief")
    if isinstance(brief, dict):
        next_actions = brief.get("next_actions")
        if isinstance(next_actions, list):
            for action in next_actions[:3]:
                typer.echo("next: " + str(action))


def _emit_route_test(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(summary)
    typer.echo(f"ok: {bool(payload.get('ok'))}")
    route_name = str(payload.get("route_name") or "").strip()
    if route_name:
        typer.echo(f"route: {route_name}")
    target = str(payload.get("target") or "").strip()
    if target:
        typer.echo(f"target: {target}")
    event_type = str(payload.get("event_type") or "").strip()
    if event_type:
        typer.echo(f"event: {event_type}")
    error = str(payload.get("error") or "").strip()
    if error:
        typer.echo(f"error: {error}")


def _emit_routes(payload: list[dict[str, object]], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return
    if not payload:
        typer.echo("No notification routes saved.")
        return
    for route in payload:
        route_id = route.get("id")
        name = str(route.get("name") or "").strip() or f"Route {route_id}"
        kind = str(route.get("kind") or "").strip() or "webhook"
        target = str(route.get("target") or "").strip()
        enabled = bool(route.get("enabled"))
        events = route.get("events")
        conversation_target = route.get("conversation_target")
        last_result = str(route.get("last_result") or "").strip()
        typer.echo(f"[{route_id}] {name} ({kind})")
        typer.echo(f"  enabled: {enabled}")
        if target:
            typer.echo(f"  target: {target}")
        if isinstance(events, list) and events:
            rendered_events = ", ".join(
                str(event) for event in events if str(event).strip()
            )
            typer.echo("  events: " + rendered_events)
        if isinstance(conversation_target, dict):
            summary = str(conversation_target.get("summary") or "").strip()
            if summary:
                typer.echo(f"  conversation target: {summary}")
        if last_result:
            typer.echo(f"  last result: {last_result}")


def _emit_outbound_deliveries(payload: list[dict[str, object]], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return
    if not payload:
        typer.echo("No outbound deliveries recorded.")
        return
    for delivery in payload:
        delivery_id = delivery.get("id")
        state = str(delivery.get("delivery_state") or "").strip() or "pending"
        event_type = str(delivery.get("event_type") or "").strip()
        route_name = str(delivery.get("route_name") or "").strip()
        route_kind = str(delivery.get("route_kind") or "").strip()
        route_target = str(delivery.get("route_target") or "").strip()
        summary = str(delivery.get("message_summary") or "").strip()
        session_key = str(delivery.get("session_key") or "").strip()
        conversation_target = delivery.get("conversation_target")
        typer.echo(f"[{delivery_id}] {state} {event_type}".strip())
        if route_name:
            route_label = route_name
            if route_kind:
                route_label += f" [{route_kind}]"
            typer.echo(f"  route: {route_label}")
        elif route_kind:
            typer.echo(f"  route: [{route_kind}]")
        if route_target:
            typer.echo(f"  target: {route_target}")
        if summary:
            typer.echo(f"  summary: {summary}")
        if session_key:
            typer.echo(f"  session: {session_key}")
        if isinstance(conversation_target, dict):
            target_summary = str(conversation_target.get("summary") or "").strip()
            if target_summary:
                typer.echo(f"  conversation target: {target_summary}")
        last_error = str(delivery.get("last_error") or "").strip()
        if last_error:
            typer.echo(f"  error: {last_error}")


def _emit_outbound_delivery_replay(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(summary)
    typer.echo(f"ok: {bool(payload.get('ok'))}")
    typer.echo(
        "counts: "
        + ", ".join(
            [
                f"attempted={_coerce_int(payload.get('attempted_count'))}",
                f"replayed={_coerce_int(payload.get('replayed_count'))}",
                f"failed={_coerce_int(payload.get('failed_count'))}",
                f"deferred={_coerce_int(payload.get('deferred_count'))}",
                f"maxed={_coerce_int(payload.get('skipped_max_retries_count'))}",
            ]
        )
    )
    deliveries = payload.get("deliveries")
    if not isinstance(deliveries, list):
        return
    for item in deliveries:
        if not isinstance(item, dict):
            continue
        status = "ok" if bool(item.get("ok")) else "error"
        route_name = str(item.get("route_name") or "").strip()
        route_target = str(item.get("target") or "").strip()
        event_type = str(item.get("event_type") or "").strip()
        route_kind = ""
        route = item.get("route")
        if isinstance(route, dict):
            route_kind = str(route.get("kind") or "").strip()
            if not route_target:
                route_target = str(route.get("target") or "").strip()
        headline = f"[{status}] {event_type} -> {route_name}".strip()
        if route_kind:
            headline += f" [{route_kind}]"
        typer.echo(headline)
        if route_target:
            typer.echo(f"  target: {route_target}")
        detail = str(item.get("summary") or "").strip()
        if detail:
            typer.echo(f"  summary: {detail}")
        error = str(item.get("error") or "").strip()
        if error:
            typer.echo(f"  error: {error}")


def _emit_direct_channel_delivery(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return
    typer.echo(f"ok: {bool(payload.get('ok'))}")
    delivery_id = payload.get("deliveryId") or payload.get("delivery_id")
    if delivery_id is not None:
        typer.echo(f"delivery: {delivery_id}")
    channel = str(payload.get("channel") or "").strip()
    if channel:
        typer.echo(f"channel: {channel}")
    session_key = str(payload.get("sessionKey") or payload.get("session_key") or "").strip()
    if session_key:
        typer.echo(f"session: {session_key}")
    run_id = str(payload.get("runId") or payload.get("run_id") or "").strip()
    if run_id:
        typer.echo(f"run: {run_id}")
    message_id = str(payload.get("messageId") or payload.get("message_id") or "").strip()
    if message_id:
        typer.echo(f"message: {message_id}")
    poll_id = str(payload.get("pollId") or payload.get("poll_id") or "").strip()
    if poll_id:
        typer.echo(f"poll: {poll_id}")


def _first_text_line(value: object, *, limit: int = 220) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if len(first_line) <= limit:
        return first_line
    return first_line[: max(0, limit - 3)].rstrip() + "..."


def _watch_base_url(*, url: str | None, host: str, port: int) -> str:
    if url:
        return str(url).rstrip("/")
    return f"http://{host}:{port}"


def _watch_decode_error_body(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        body = ""
    if not body:
        return exc.reason or "request failed"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return body


def _watch_api_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    timeout_seconds: float = 60.0,
    allow_timeout: bool = False,
) -> Any:
    body: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif method != "GET":
        body = b""
    request = Request(f"{base_url}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = _watch_decode_error_body(exc)
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc
    except TimeoutError as exc:
        if allow_timeout:
            return {"timed_out": True}
        raise RuntimeError(f"{method} {path} timed out against {base_url}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        if allow_timeout and isinstance(reason, TimeoutError):
            return {"timed_out": True}
        raise RuntimeError(f"Could not reach OpenZues at {base_url}: {reason}") from exc

    if not response_text.strip():
        return None
    return json.loads(response_text)


def _browser_command() -> str:
    command = shutil.which("agent-browser.cmd") or shutil.which("agent-browser")
    if command is None:
        raise RuntimeError(
            "agent-browser is not installed or not on PATH. Install it before using --browser."
        )
    return command


def _run_browser_command(
    args: list[str],
    *,
    session_name: str,
    timeout_seconds: float = 60.0,
    allow_failure: bool = False,
) -> str:
    command = _browser_command()
    invocation = [command, "--session", session_name, *args]
    process_args = invocation
    if os.name == "nt":
        if _browser_command_expects_output(args):
            return _run_windows_browser_command_direct(
                invocation,
                args=args,
                timeout_seconds=timeout_seconds,
                allow_failure=allow_failure,
            )
        return _run_windows_browser_command(
            invocation,
            args=args,
            timeout_seconds=timeout_seconds,
            allow_failure=allow_failure,
        )
    try:
        completed = subprocess.run(
            process_args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"agent-browser {' '.join(args)} timed out after {timeout_seconds:.0f}s."
        ) from exc
    output = (completed.stdout or "").strip()
    error_output = (completed.stderr or "").strip()
    if completed.returncode != 0 and not allow_failure:
        detail = error_output or output or "browser command failed"
        raise RuntimeError(f"agent-browser {' '.join(args)} failed: {detail}")
    return output or error_output


def _powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _browser_command_expects_output(args: list[str]) -> bool:
    if not args:
        return False
    if args[0] in {"get", "eval", "snapshot"}:
        return True
    if args[0] in {"errors", "console"} and "--clear" not in args[1:]:
        return True
    return False


def _decode_browser_capture_bytes(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig", errors="replace").strip()
    if (
        data.startswith(codecs.BOM_UTF16_LE)
        or data.startswith(codecs.BOM_UTF16_BE)
        or b"\x00" in data
    ):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return data.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
    return data.decode("utf-8", errors="replace").strip()


def _read_browser_capture_text(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return _decode_browser_capture_bytes(data)


def _run_windows_browser_command_direct(
    invocation: list[str],
    *,
    args: list[str],
    timeout_seconds: float,
    allow_failure: bool,
) -> str:
    try:
        completed = subprocess.run(
            invocation,
            capture_output=True,
            text=False,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"agent-browser {' '.join(args)} timed out after {timeout_seconds:.0f}s."
        ) from exc
    output = _decode_browser_capture_bytes(completed.stdout or b"")
    error_output = _decode_browser_capture_bytes(completed.stderr or b"")
    if completed.returncode != 0 and not allow_failure:
        detail = error_output or output or "browser command failed"
        raise RuntimeError(f"agent-browser {' '.join(args)} failed: {detail}")
    return output or error_output


def _run_windows_browser_command(
    invocation: list[str],
    *,
    args: list[str],
    timeout_seconds: float,
    allow_failure: bool,
) -> str:
    argument_list = ", ".join(_powershell_single_quote(item) for item in invocation[1:])
    stdout_capture = Path(tempfile.mkstemp(prefix="openzues-browser-out-", suffix=".log")[1])
    stderr_capture = Path(tempfile.mkstemp(prefix="openzues-browser-err-", suffix=".log")[1])
    process_script = [
        "$ErrorActionPreference = 'Stop'",
        "$startArgs = @{",
        f"  FilePath = {_powershell_single_quote(invocation[0])}",
        "  PassThru = $true",
        "  WindowStyle = 'Hidden'",
        f"  RedirectStandardOutput = {_powershell_single_quote(str(stdout_capture))}",
        f"  RedirectStandardError = {_powershell_single_quote(str(stderr_capture))}",
        "}",
    ]
    if argument_list:
        process_script.append(f"$startArgs.ArgumentList = @({argument_list})")
    process_script.extend(
        [
            "$process = Start-Process @startArgs",
            f"if (-not $process.WaitForExit({int(timeout_seconds * 1000)})) {{",
            "  try { $process.Kill() } catch {}",
            "  exit 124",
            "}",
            "exit $process.ExitCode",
        ]
    )
    ps_command = "\n".join(process_script)
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"agent-browser {' '.join(args)} timed out after {timeout_seconds:.0f}s."
        ) from exc
    try:
        wrapper_output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
        child_stdout = _read_browser_capture_text(stdout_capture)
        child_stderr = _read_browser_capture_text(stderr_capture)
        child_output = "\n".join(
            part for part in (child_stdout, child_stderr) if str(part).strip()
        ).strip()
        if completed.returncode == 124 and not allow_failure:
            raise RuntimeError(
                f"agent-browser {' '.join(args)} timed out after {timeout_seconds:.0f}s."
            )
        if completed.returncode != 0 and not allow_failure:
            detail = child_output or wrapper_output or "browser command failed"
            raise RuntimeError(f"agent-browser {' '.join(args)} failed: {detail}")
        return child_output or wrapper_output
    finally:
        for capture_path in (stdout_capture, stderr_capture):
            try:
                capture_path.unlink(missing_ok=True)
            except OSError:
                pass


def _try_browser_command(
    args: list[str],
    *,
    session_name: str,
    timeout_seconds: float = 10.0,
) -> str:
    try:
        return _run_browser_command(
            args,
            session_name=session_name,
            timeout_seconds=timeout_seconds,
            allow_failure=True,
        )
    except RuntimeError:
        return ""


def _strip_browser_value(value: str) -> str:
    text = value.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        return text[1:-1]
    return text


def _browser_url_value(value: str) -> str:
    text = _strip_browser_value(value)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return text
    return ""


def _browser_title_value(value: str) -> str:
    text = _strip_browser_value(value)
    if not text or "\x00" in text or "HRESULT" in text or "failed" in text.lower():
        return ""
    return text


def _browser_probe_status(value: str, *, allowed: set[str]) -> str:
    text = _strip_browser_value(value)
    return text if text in allowed else ""


def _browser_screenshot_path(output: str) -> str | None:
    marker = "Screenshot saved to "
    for line in output.splitlines():
        line = line.strip()
        if marker in line:
            return line.split(marker, 1)[1].strip()
    return None


def _browser_screenshot_signal(path_text: str | None) -> tuple[str | None, int | None]:
    if not path_text:
        return None, None
    try:
        size_bytes = Path(path_text).expanduser().stat().st_size
    except OSError:
        return None, None
    if size_bytes >= _BROWSER_RENDERED_SCREENSHOT_MIN_BYTES:
        return "rendered", size_bytes
    if size_bytes <= _BROWSER_BLANK_SCREENSHOT_MAX_BYTES:
        return "likely_blank", size_bytes
    return "unknown", size_bytes


def _watch_http_content_signal(browser_url: str, *, timeout_seconds: float = 20.0) -> bool:
    request = Request(browser_url, headers={"Accept": "text/html"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError):
        return False
    normalized = response_text.lower()
    return len(response_text.strip()) >= 200 and "<body" in normalized


def _summarize_browser_snapshot(output: str, *, limit: int = 8) -> str:
    truncated_output = output[:_BROWSER_SNAPSHOT_CHAR_LIMIT]
    lines: list[str] = []
    for raw_line in truncated_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) >= _BROWSER_SNAPSHOT_LINE_LIMIT:
            break
    if not lines:
        return "No interactive browser snapshot lines were returned."
    interesting = [
        line
        for line in lines
        if line.startswith("- ")
        or line.startswith("[")
        or 'heading "' in line
        or 'button "' in line
        or 'textbox "' in line
    ]
    sample = interesting[:limit] if interesting else lines[:limit]
    summary = " | ".join(sample)
    if len(output) > len(truncated_output) or len(lines) >= _BROWSER_SNAPSHOT_LINE_LIMIT:
        summary += " | [snapshot truncated]"
    return summary


def _watch_browser_verify(
    *,
    browser_url: str,
    session_name: str,
) -> dict[str, Any]:
    # Watch sessions are unique by default, so clearing prior error/console state is usually
    # redundant and has proven flaky on some Windows agent-browser installs.
    _run_browser_command(["open", browser_url], session_name=session_name, timeout_seconds=15.0)
    _run_browser_command(
        ["wait", "2000"],
        session_name=session_name,
        timeout_seconds=5.0,
        allow_failure=True,
    )

    page_url = _browser_url_value(
        _try_browser_command(["get", "url"], session_name=session_name, timeout_seconds=3.0)
    )
    title = _browser_title_value(
        _try_browser_command(["get", "title"], session_name=session_name, timeout_seconds=3.0)
    )
    has_content = _browser_probe_status(
        _try_browser_command(
            [
                "eval",
                (
                    "document.body && document.body.innerText.trim().length > 0 "
                    "? 'HAS_CONTENT' : 'BLANK'"
                ),
            ],
            session_name=session_name,
            timeout_seconds=3.0,
        ),
        allowed={"HAS_CONTENT", "BLANK"},
    )
    overlay_status = _browser_probe_status(
        _try_browser_command(
            [
                "eval",
                "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
                "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
            ],
            session_name=session_name,
            timeout_seconds=3.0,
        ),
        allowed={"OK", "ERROR_OVERLAY"},
    )
    screenshot_path: str | None = None
    screenshot_error: str | None = None
    try:
        screenshot_target = (
            Path(tempfile.gettempdir())
            / f"openzues-watch-{session_name}-{int(time.time() * 1000)}.png"
        )
        screenshot_output = _run_browser_command(
            ["--annotate", "screenshot", str(screenshot_target)],
            session_name=session_name,
            timeout_seconds=12.0,
        )
        screenshot_path = _browser_screenshot_path(screenshot_output) or str(screenshot_target)
    except RuntimeError as exc:
        screenshot_error = str(exc)
    screenshot_signal, screenshot_bytes = _browser_screenshot_signal(screenshot_path)
    http_content_visible = _watch_http_content_signal(browser_url)

    snapshot_summary = "Browser snapshot unavailable."
    snapshot_error: str | None = None
    try:
        snapshot_output = _run_browser_command(
            ["snapshot", "-i"],
            session_name=session_name,
            timeout_seconds=4.0,
            allow_failure=True,
        )
        if snapshot_output:
            snapshot_summary = _summarize_browser_snapshot(snapshot_output)
    except RuntimeError as exc:
        snapshot_error = str(exc)
    errors_output = _try_browser_command(
        ["errors"],
        session_name=session_name,
        timeout_seconds=3.0,
    )
    console_output = _try_browser_command(
        ["console"],
        session_name=session_name,
        timeout_seconds=3.0,
    )
    error_count = len([line for line in errors_output.splitlines() if line.strip()])
    console_count = len([line for line in console_output.splitlines() if line.strip()])
    content_source = "agent-browser"
    content_visible = has_content == "HAS_CONTENT"
    if has_content not in {"HAS_CONTENT", "BLANK"}:
        if screenshot_signal == "rendered":
            content_visible = True
            content_source = "screenshot"
        elif http_content_visible:
            content_visible = True
            content_source = "http"
        else:
            content_visible = False
            content_source = "unknown"
    elif has_content == "BLANK" and screenshot_signal == "rendered" and http_content_visible:
        content_visible = True
        content_source = "screenshot_override"
    overlay_ok = overlay_status == "OK"
    if not overlay_status and error_count == 0 and screenshot_signal == "rendered":
        overlay_ok = True
    ok = content_visible and overlay_ok and error_count == 0
    content_summary = "content visible" if content_visible else "page looks blank"
    if content_source == "screenshot":
        content_summary = "content visible (screenshot-backed fallback)"
    elif content_source == "http":
        content_summary = "content visible (HTTP fallback)"
    elif content_source == "screenshot_override":
        content_summary = "content visible (screenshot overrode a blank probe)"
    overlay_summary = "no overlay" if overlay_ok else "error overlay present"
    if not overlay_status and overlay_ok:
        overlay_summary = "no overlay (probe unavailable)"
    summary_parts = [
        f"url {page_url or browser_url}",
        content_summary,
        overlay_summary,
        f"{error_count} page error(s)",
        f"{console_count} console line(s)",
    ]
    if screenshot_signal == "rendered" and screenshot_bytes is not None:
        summary_parts.append(f"screenshot {screenshot_bytes} bytes")
    elif screenshot_signal == "likely_blank" and screenshot_bytes is not None:
        summary_parts.append(f"screenshot looks blank at {screenshot_bytes} bytes")
    return {
        "ok": ok,
        "status": "ready" if ok else "warn",
        "summary": ", ".join(summary_parts) + ".",
        "url": page_url or browser_url,
        "title": title or None,
        "has_content": content_visible,
        "content_source": content_source,
        "http_content_visible": http_content_visible,
        "overlay_status": overlay_status or "unknown",
        "error_count": error_count,
        "console_count": console_count,
        "screenshot_path": screenshot_path,
        "screenshot_signal": screenshot_signal,
        "screenshot_bytes": screenshot_bytes,
        "screenshot_error": screenshot_error,
        "snapshot_summary": snapshot_summary,
        "snapshot_error": snapshot_error,
        "errors_excerpt": _first_text_line(errors_output, limit=280) or None,
        "console_excerpt": _first_text_line(console_output, limit=280) or None,
    }


def _watch_browser_verify_guarded(
    *,
    browser_url: str,
    session_name: str,
    timeout_seconds: float = 45.0,
) -> dict[str, Any]:
    if os.name != "nt":
        return _watch_browser_verify(browser_url=browser_url, session_name=session_name)
    worker_code = "\n".join(
        [
            "import json",
            "from openzues.cli import _watch_browser_verify",
            (
                "payload = _watch_browser_verify("
                f"browser_url={json.dumps(browser_url)}, "
                f"session_name={json.dumps(session_name)})"
            ),
            "print(json.dumps(payload, separators=(',', ':')))",
        ]
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", worker_code],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"browser verification timed out after {timeout_seconds:.0f}s."
        ) from exc
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        detail = _first_text_line(stderr or stdout, limit=280) or "browser verification failed."
        raise RuntimeError(detail)
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("browser verification returned no payload.")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        detail = _first_text_line(stdout, limit=280) or "browser verification payload invalid."
        raise RuntimeError(detail) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("browser verification returned an unexpected payload.")
    return payload


def _watch_target_payload(
    dashboard: dict[str, Any],
    handoff: dict[str, Any],
    *,
    mission_id: int | None,
    task_name: str | None,
) -> dict[str, Any]:
    missions = [item for item in dashboard.get("missions", []) if isinstance(item, dict)]
    brief = dashboard.get("brief")
    task_blueprint = (
        handoff.get("task_blueprint") if isinstance(handoff.get("task_blueprint"), dict) else None
    )
    task_blueprint_id = (
        int(task_blueprint["id"])
        if isinstance(task_blueprint, dict) and task_blueprint.get("id") is not None
        else None
    )
    resolved_task_name = str(task_name or "").strip() or (
        str(task_blueprint.get("label") or "").strip() if isinstance(task_blueprint, dict) else ""
    )
    if not resolved_task_name:
        resolved_task_name = _DEFAULT_WATCH_TASK_NAME

    def _mission_sort_key(mission: dict[str, Any]) -> tuple[int, float, int]:
        status_priority = {
            "active": 0,
            "blocked": 1,
            "paused": 2,
            "failed": 3,
            "completed": 4,
        }.get(str(mission.get("status") or "").strip().lower(), 5)
        updated_text = str(mission.get("updated_at") or mission.get("created_at") or "").strip()
        updated_at = 0.0
        if updated_text:
            try:
                updated_at = datetime.fromisoformat(updated_text.replace("Z", "+00:00")).timestamp()
            except ValueError:
                updated_at = 0.0
        return (
            status_priority,
            -updated_at,
            -int(mission.get("id") or 0),
        )

    watched_mission: dict[str, Any] | None = None
    if mission_id is not None:
        watched_mission = next(
            (mission for mission in missions if int(mission.get("id") or 0) == mission_id),
            None,
        )
    if watched_mission is None and task_blueprint_id is not None:
        candidates = [
            mission
            for mission in missions
            if int(mission.get("task_blueprint_id") or 0) == task_blueprint_id
        ]
        if candidates:
            watched_mission = sorted(candidates, key=_mission_sort_key)[0]
    if watched_mission is None and resolved_task_name:
        candidates = [
            mission
            for mission in missions
            if str(mission.get("name") or "").strip() == resolved_task_name
        ]
        if candidates:
            watched_mission = sorted(candidates, key=_mission_sort_key)[0]
    if (
        watched_mission is None
        and isinstance(brief, dict)
        and brief.get("focus_mission_id") is not None
    ):
        focus_mission_id = int(brief["focus_mission_id"])
        watched_mission = next(
            (mission for mission in missions if int(mission.get("id") or 0) == focus_mission_id),
            None,
        )
    return {
        "task_name": resolved_task_name,
        "task_blueprint_id": task_blueprint_id,
        "mission": watched_mission,
    }


def _watch_is_runnable(status: object) -> bool:
    return str(status or "").strip().lower() in {"paused", "failed"}


def _watch_is_terminal(status: object) -> bool:
    return str(status or "").strip().lower() in {"completed", "failed"}


def _watch_auto_action_summary(action: dict[str, Any] | None) -> str:
    if not isinstance(action, dict):
        return ""
    return _first_text_line(action.get("summary"))


def _watch_observer_posture(dashboard: dict[str, Any]) -> dict[str, Any] | None:
    control_chat = dashboard.get("control_chat")
    attention_queue = dashboard.get("attention_queue")
    candidate_sections = [
        section
        for section in (control_chat, attention_queue)
        if isinstance(section, dict)
    ]
    observer_section = next(
        (
            section
            for section in candidate_sections
            if str(section.get("headline") or "").strip() == "Observer mode is active"
        ),
        None,
    )
    if observer_section is None:
        return None

    summary = str(observer_section.get("summary") or "").strip()
    if not summary:
        summary = next(
            (
                str(section.get("summary") or "").strip()
                for section in candidate_sections
                if str(section.get("summary") or "").strip()
            ),
            "",
        )
    leader_pid: int | None = None
    if summary:
        match = _WATCH_LEADER_PID_RE.search(summary)
        if match is not None:
            leader_pid = int(match.group("pid"))
    return {
        "active": True,
        "summary": summary or "Observer mode is active in this window.",
        "leader_pid": leader_pid,
    }


def _maybe_launch_watch_target(
    base_url: str,
    *,
    dashboard: dict[str, Any],
    handoff: dict[str, Any],
    mission_id: int | None,
    task_name: str | None,
) -> dict[str, Any] | None:
    target = _watch_target_payload(
        dashboard,
        handoff,
        mission_id=mission_id,
        task_name=task_name,
    )
    watched_mission = target.get("mission")
    if isinstance(watched_mission, dict) and watched_mission.get("id") is not None:
        watched_mission_id = int(watched_mission["id"])
        watched_mission_name = str(
            watched_mission.get("name") or f"mission {watched_mission_id}"
        ).strip()
        if _watch_is_runnable(watched_mission.get("status")):
            _watch_api_json(
                base_url,
                f"/api/missions/{watched_mission_id}/start",
                method="POST",
                timeout_seconds=5.0,
                allow_timeout=True,
            )
            return {
                "action": "resume_mission",
                "mission_id": watched_mission_id,
                "summary": (
                    f"Sent a resume request for mission #{watched_mission_id} "
                    f"({watched_mission_name}) and switched to live polling."
                ),
            }
        return {
            "action": "observe_existing_mission",
            "mission_id": watched_mission_id,
            "summary": f"Watching mission #{watched_mission_id} ({watched_mission_name}).",
        }

    recommended_action = str(handoff.get("recommended_action") or "").strip()
    instance = handoff.get("instance")
    if (
        recommended_action == "connect_lane"
        and isinstance(instance, dict)
        and instance.get("id") is not None
    ):
        instance_id = int(instance["id"])
        _watch_api_json(base_url, f"/api/instances/{instance_id}/connect", method="POST")
        return {
            "action": "connect_lane",
            "instance_id": instance_id,
            "summary": f"Reconnected lane #{instance_id} so the saved launch handoff can run.",
        }

    mission_draft = handoff.get("mission_draft")
    if isinstance(mission_draft, dict):
        created = _watch_api_json(base_url, "/api/missions", method="POST", payload=mission_draft)
        if isinstance(created, dict):
            created_id = int(created.get("id") or 0)
            created_name = str(created.get("name") or f"mission {created_id}").strip()
            if created_id and _watch_is_runnable(created.get("status")):
                _watch_api_json(
                    base_url,
                    f"/api/missions/{created_id}/start",
                    method="POST",
                    timeout_seconds=5.0,
                    allow_timeout=True,
                )
                return {
                    "action": "resume_mission",
                    "mission_id": created_id,
                    "summary": (
                        f"Sent a resume request for saved mission #{created_id} "
                        f"({created_name}) from the launch handoff and switched to live polling."
                    ),
                }
            return {
                "action": "create_mission",
                "mission_id": created_id if created_id else None,
                "summary": (
                    f"Launched mission #{created_id} ({created_name}) from the saved handoff."
                ),
            }

    next_entrypoint = _first_text_line(
        handoff.get("next_entrypoint")
        or handoff.get("summary")
        or "No launchable mission is saved yet."
    )
    return {
        "action": "observe_handoff",
        "summary": next_entrypoint,
    }


def _build_watch_payload(
    *,
    base_url: str,
    dashboard: dict[str, Any],
    handoff: dict[str, Any],
    mission_id: int | None,
    task_name: str | None,
    auto_action: dict[str, Any] | None,
    browser_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    target = _watch_target_payload(
        dashboard,
        handoff,
        mission_id=mission_id,
        task_name=task_name,
    )
    missions = [item for item in dashboard.get("missions", []) if isinstance(item, dict)]
    instances = [item for item in dashboard.get("instances", []) if isinstance(item, dict)]
    observer_posture = _watch_observer_posture(dashboard)
    return {
        "headline": str(dashboard.get("brief", {}).get("headline") or "").strip(),
        "summary": str(dashboard.get("brief", {}).get("summary") or "").strip(),
        "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "base_url": base_url,
        "watch_target": {
            "mission_id": mission_id,
            "task_name": target["task_name"],
            "task_blueprint_id": target["task_blueprint_id"],
        },
        "auto_action": auto_action,
        "browser_verification": browser_verification,
        "observer_posture": observer_posture,
        "setup_launch_handoff": handoff,
        "mission_summary": {
            "active_count": sum(str(item.get("status") or "") == "active" for item in missions),
            "blocked_count": sum(str(item.get("status") or "") == "blocked" for item in missions),
            "paused_count": sum(str(item.get("status") or "") == "paused" for item in missions),
            "failed_count": sum(str(item.get("status") or "") == "failed" for item in missions),
        },
        "instance_summary": {
            "connected_count": sum(bool(item.get("connected")) for item in instances),
            "total_count": len(instances),
        },
        "gateway_capability": dashboard.get("gateway_capability"),
        "watched_mission": target["mission"],
    }


def _watch_lines(payload: dict[str, object]) -> list[str]:
    lines: list[str] = []
    checked_at = str(payload.get("checked_at") or "").strip()
    base_url = str(payload.get("base_url") or "").strip()
    prefix = f"[{checked_at}] " if checked_at else ""
    lines.append(f"{prefix}OpenZues watch @ {base_url or 'live server'}")
    observer_posture = payload.get("observer_posture")
    observer_active = isinstance(observer_posture, dict) and bool(observer_posture.get("active"))

    headline = str(payload.get("headline") or "").strip()
    if headline:
        lines.append("brief: " + headline)
    summary = str(payload.get("summary") or "").strip()
    if summary:
        lines.append("summary: " + summary)
    if isinstance(observer_posture, dict) and observer_posture.get("active"):
        leader_pid = observer_posture.get("leader_pid")
        mode_line = "mode: observer"
        if isinstance(leader_pid, int):
            mode_line += f" / leader PID {leader_pid}"
        lines.append(mode_line)
        observer_summary = _first_text_line(observer_posture.get("summary"), limit=320)
        if observer_summary:
            lines.append("mode summary: " + observer_summary)
        lines.append(
            "mode note: Mission telemetry may be leader-owned while lane, gateway, and "
            "handoff posture below come from this observer window."
        )

    watch_target = payload.get("watch_target")
    if isinstance(watch_target, dict):
        task_name = str(watch_target.get("task_name") or "").strip()
        task_blueprint_id = watch_target.get("task_blueprint_id")
        target_parts: list[str] = []
        if task_name:
            target_parts.append(task_name)
        if task_blueprint_id is not None:
            target_parts.append(f"task #{task_blueprint_id}")
        mission_id = watch_target.get("mission_id")
        if mission_id is not None:
            target_parts.append(f"mission #{mission_id}")
        if target_parts:
            lines.append("target: " + " | ".join(target_parts))

    auto_action = payload.get("auto_action")
    if isinstance(auto_action, dict):
        auto_summary = _watch_auto_action_summary(auto_action)
        if auto_summary:
            lines.append("auto: " + auto_summary)

    browser_verification = payload.get("browser_verification")
    if isinstance(browser_verification, dict):
        browser_status = str(browser_verification.get("status") or "").strip()
        browser_summary = str(browser_verification.get("summary") or "").strip()
        if browser_status or browser_summary:
            lines.append(
                "browser: "
                + " / ".join(part for part in (browser_status, browser_summary) if part)
            )
        title = str(browser_verification.get("title") or "").strip()
        if title:
            lines.append("browser title: " + title)
        snapshot_summary = _first_text_line(browser_verification.get("snapshot_summary"), limit=320)
        if snapshot_summary:
            lines.append("browser snapshot: " + snapshot_summary)
        artifact_path = str(browser_verification.get("artifact_path") or "").strip()
        if artifact_path:
            lines.append("browser artifact: " + artifact_path)
        screenshot_path = str(browser_verification.get("screenshot_path") or "").strip()
        if screenshot_path:
            lines.append("browser screenshot: " + screenshot_path)
        screenshot_error = _first_text_line(browser_verification.get("screenshot_error"))
        if screenshot_error:
            lines.append("browser screenshot warning: " + screenshot_error)
        snapshot_error = _first_text_line(browser_verification.get("snapshot_error"))
        if snapshot_error:
            lines.append("browser snapshot warning: " + snapshot_error)
        errors_excerpt = _first_text_line(browser_verification.get("errors_excerpt"))
        if errors_excerpt:
            lines.append("browser errors: " + errors_excerpt)
        console_excerpt = _first_text_line(browser_verification.get("console_excerpt"))
        if console_excerpt:
            lines.append("browser console: " + console_excerpt)

    handoff = payload.get("setup_launch_handoff")
    if isinstance(handoff, dict):
        handoff_status = str(handoff.get("status") or "").strip()
        handoff_headline = str(handoff.get("headline") or "").strip()
        handoff_summary = _first_text_line(handoff.get("summary"))
        handoff_label = "observer handoff" if observer_active else "handoff"
        handoff_summary_label = (
            "observer handoff summary" if observer_active else "handoff summary"
        )
        next_label = "observer next" if observer_active else "next"
        if handoff_status or handoff_headline:
            lines.append(
                f"{handoff_label}: "
                + " / ".join(part for part in (handoff_status, handoff_headline) if part)
            )
        if handoff_summary:
            lines.append(f"{handoff_summary_label}: " + handoff_summary)
        next_entrypoint = _first_text_line(handoff.get("next_entrypoint"))
        if next_entrypoint:
            lines.append(f"{next_label}: " + next_entrypoint)

    instance_summary = payload.get("instance_summary")
    if isinstance(instance_summary, dict):
        lanes_label = "observer lanes" if observer_active else "lanes"
        lines.append(
            f"{lanes_label}: "
            f"{instance_summary.get('connected_count', 0)} connected / "
            f"{instance_summary.get('total_count', 0)} total"
        )

    mission_summary = payload.get("mission_summary")
    if isinstance(mission_summary, dict):
        lines.append(
            "missions: "
            f"{mission_summary.get('active_count', 0)} active, "
            f"{mission_summary.get('blocked_count', 0)} blocked, "
            f"{mission_summary.get('paused_count', 0)} paused, "
            f"{mission_summary.get('failed_count', 0)} failed"
        )

    gateway_capability = payload.get("gateway_capability")
    if isinstance(gateway_capability, dict):
        gateway_level = str(gateway_capability.get("level") or "").strip()
        gateway_headline = str(gateway_capability.get("headline") or "").strip()
        gateway_label = "observer gateway" if observer_active else "gateway"
        gateway_summary_label = (
            "observer gateway summary" if observer_active else "gateway summary"
        )
        if gateway_level or gateway_headline:
            lines.append(
                f"{gateway_label}: "
                + " / ".join(part for part in (gateway_level, gateway_headline) if part)
            )
        gateway_summary = _first_text_line(gateway_capability.get("summary"))
        if gateway_summary:
            lines.append(f"{gateway_summary_label}: " + gateway_summary)
        launch_policy = gateway_capability.get("launch_policy")
        if isinstance(launch_policy, dict):
            launch_route = launch_policy.get("launch_route")
            if isinstance(launch_route, dict):
                conversation_target = launch_route.get("conversation_target")
                if isinstance(conversation_target, dict):
                    target_summary = _first_text_line(conversation_target.get("summary"))
                    if target_summary:
                        target_label = (
                            "observer conversation target"
                            if observer_active
                            else "conversation target"
                        )
                        lines.append(f"{target_label}: " + target_summary)
                conversation_reuse = launch_route.get("conversation_reuse")
                if isinstance(conversation_reuse, dict):
                    reuse_summary = _first_text_line(conversation_reuse.get("summary"))
                    if reuse_summary:
                        reuse_label = (
                            "observer conversation reuse"
                            if observer_active
                            else "conversation reuse"
                        )
                        lines.append(f"{reuse_label}: " + reuse_summary)

    watched_mission = payload.get("watched_mission")
    if not isinstance(watched_mission, dict):
        lines.append("mission: No matching live mission yet.")
        return lines

    watched_mission_id = watched_mission.get("id")
    watched_name = str(watched_mission.get("name") or "Mission").strip()
    watched_status = str(watched_mission.get("status") or "").strip()
    watched_phase = str(watched_mission.get("phase") or "").strip()
    lines.append(
        "mission: "
        + f"#{watched_mission_id} {watched_name}"
        + (
            " [" + " / ".join(part for part in (watched_status, watched_phase) if part) + "]"
            if watched_status or watched_phase
            else ""
        )
    )

    live_telemetry = watched_mission.get("live_telemetry")
    if isinstance(live_telemetry, dict):
        live_summary = _first_text_line(live_telemetry.get("summary"))
        if live_summary:
            lines.append("live: " + live_summary)

    delegation_brief = watched_mission.get("delegation_brief")
    if isinstance(delegation_brief, dict):
        delegation_summary = _first_text_line(delegation_brief.get("summary"))
        if delegation_summary:
            lines.append("delegation: " + delegation_summary)

    toolsets = watched_mission.get("toolsets")
    if isinstance(toolsets, list) and toolsets:
        lines.append("toolsets: " + ", ".join(str(item) for item in toolsets[:8]))
    tool_evidence = watched_mission.get("tool_evidence")
    if isinstance(tool_evidence, dict):
        tool_evidence_summary = _first_text_line(tool_evidence.get("summary"))
        if tool_evidence_summary:
            lines.append("tool proof: " + tool_evidence_summary)

    current_command = _first_text_line(watched_mission.get("current_command"))
    if current_command:
        lines.append("command: " + current_command)

    commentary = _first_text_line(watched_mission.get("last_commentary"))
    if commentary:
        lines.append("commentary: " + commentary)

    checkpoint = _first_text_line(watched_mission.get("last_checkpoint"))
    if checkpoint:
        lines.append("checkpoint: " + checkpoint)

    last_error = _first_text_line(watched_mission.get("last_error"))
    if last_error:
        lines.append("error: " + last_error)
    return lines


def _watch_output(payload: dict[str, object], *, json_output: bool) -> str:
    if json_output:
        return json.dumps(payload, indent=2)
    return "\n".join(_watch_lines(payload))


def _emit_watch(payload: dict[str, object], *, json_output: bool) -> None:
    typer.echo(_watch_output(payload, json_output=json_output))


def _watch_log_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.name}.{index}")


def _rotate_watch_log(path: Path, *, max_bytes: int, backups: int) -> None:
    if max_bytes <= 0 or backups <= 0 or not path.exists():
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size < max_bytes:
        return
    oldest = _watch_log_path(path, backups)
    if oldest.exists():
        oldest.unlink()
    for index in range(backups - 1, 0, -1):
        source = _watch_log_path(path, index)
        destination = _watch_log_path(path, index + 1)
        if source.exists():
            source.replace(destination)
    path.replace(_watch_log_path(path, 1))


def _append_watch_log(
    path: Path,
    *,
    text: str,
    max_bytes: int,
    backups: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_watch_log(path, max_bytes=max_bytes, backups=backups)
    if path.exists():
        try:
            existing_bytes = path.read_bytes()
        except OSError:
            existing_bytes = b""
        if existing_bytes and not existing_bytes.startswith(codecs.BOM_UTF8):
            path.write_bytes(codecs.BOM_UTF8 + existing_bytes)
    needs_bom = not path.exists()
    if not needs_bom:
        try:
            needs_bom = path.stat().st_size == 0
        except OSError:
            needs_bom = True
    with path.open("ab") as handle:
        if needs_bom:
            handle.write(codecs.BOM_UTF8)
        handle.write(text.encode("utf-8"))
        handle.write(b"\n\n")


def _copy_watch_screenshot(
    browser_verification: dict[str, Any] | None,
    *,
    artifact_path: Path,
) -> dict[str, Any] | None:
    if not isinstance(browser_verification, dict):
        return browser_verification
    screenshot_text = str(browser_verification.get("screenshot_path") or "").strip()
    if not screenshot_text:
        return browser_verification
    source = Path(screenshot_text)
    if not source.exists():
        return browser_verification
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, artifact_path)
    updated = dict(browser_verification)
    updated["artifact_path"] = str(artifact_path)
    return updated


def _emit_executor_arm(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    headline = str(payload.get("headline") or "").strip()
    if headline:
        typer.echo(headline)
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(summary)
    executor_label = str(payload.get("executor_label") or "").strip()
    if executor_label:
        typer.echo(f"executor: {executor_label}")
    cwd = str(payload.get("cwd") or "").strip()
    if cwd:
        typer.echo(f"cwd: {cwd}")
    derived_from = str(payload.get("derived_from") or "").strip()
    if derived_from:
        typer.echo(f"derived from: {derived_from}")
    image = str(payload.get("image") or "").strip()
    if image:
        typer.echo(f"image: {image}")
    if payload.get("mount_workspace") is not None:
        typer.echo(f"mount workspace: {bool(payload.get('mount_workspace'))}")
    typer.echo(f"created: {bool(payload.get('created'))}")
    typer.echo(f"connected: {bool(payload.get('connected'))}")
    instance = payload.get("instance")
    if isinstance(instance, dict):
        lane_name = str(instance.get("name") or "").strip()
        if lane_name:
            typer.echo(f"lane: {lane_name}")
        lane_id = instance.get("id")
        if lane_id is not None:
            typer.echo(f"instance: {lane_id}")


def _emit_executor_preflight(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        _emit_payload(payload, json_output=True)
        return

    headline = str(payload.get("headline") or "").strip()
    if headline:
        typer.echo(headline)
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(summary)
    typer.echo(f"ok: {bool(payload.get('ok'))}")
    status = str(payload.get("status") or "").strip()
    if status:
        typer.echo(f"status: {status}")
    cwd = str(payload.get("cwd") or "").strip()
    if cwd:
        typer.echo(f"cwd: {cwd}")
    image = str(payload.get("image") or "").strip()
    if image:
        typer.echo(f"image: {image}")
    command_path = str(payload.get("command_path") or "").strip()
    if command_path:
        typer.echo(f"docker path: {command_path}")
    docker_version = str(payload.get("docker_version") or "").strip()
    if docker_version:
        typer.echo(f"docker version: {docker_version}")
    daemon_version = str(payload.get("daemon_version") or "").strip()
    if daemon_version:
        typer.echo(f"daemon version: {daemon_version}")
    if payload.get("image_present") is not None:
        typer.echo(f"image present: {bool(payload.get('image_present'))}")


async def _run_control_chat_prompt(
    services: CliServices,
    *,
    prompt: str,
    plan_only: bool,
) -> dict[str, object]:
    dashboard = await _build_operator_dashboard(services)
    typed_dashboard = cast(DashboardView, dashboard)
    if plan_only:
        plan = plan_control_chat(prompt, typed_dashboard)
        return {
            "mode": "plan",
            "executed": False,
            "action_kind": plan.action_kind,
            "reply": plan.reply,
            "mission_id": plan.mission_id,
            "opportunity_id": plan.opportunity_id,
            "target_label": plan.target_label,
            "mission_payload": (
                plan.mission_payload.model_dump(mode="json")
                if plan.mission_payload is not None
                else None
            ),
        }
    result = await services.control_chat.submit(prompt, typed_dashboard)
    return {
        "mode": "executed",
        "executed": result.executed,
        "action_kind": result.action_kind,
        "reply": result.assistant.content,
        "mission_id": result.assistant.mission_id,
        "opportunity_id": result.assistant.opportunity_id,
        "target_label": result.assistant.target_label,
        "assistant_message_id": result.assistant.id,
        "user_message_id": result.user.id,
    }


def _control_chat_plan_payload(plan) -> dict[str, object]:
    return {
        "action_kind": plan.action_kind,
        "reply": plan.reply,
        "mission_id": plan.mission_id,
        "opportunity_id": plan.opportunity_id,
        "target_label": plan.target_label,
        "mission_payload": (
            plan.mission_payload.model_dump(mode="json")
            if plan.mission_payload is not None
            else None
        ),
    }


def _attention_queue_plan_payload(plan) -> dict[str, object] | None:
    if plan is None:
        return None
    return {
        "action_kind": plan.action_kind,
        "status": plan.status,
        "reply": plan.reply,
        "signal_id": plan.signal_id,
        "mission_id": plan.mission_id,
        "opportunity_id": plan.opportunity_id,
        "target_label": plan.target_label,
        "mission_payload": (
            plan.mission_payload.model_dump(mode="json")
            if plan.mission_payload is not None
            else None
        ),
    }


def _find_launchpad_opportunity(
    dashboard: DashboardView | SimpleNamespace,
    opportunity_id: str,
):
    wanted = opportunity_id.strip()
    if not wanted:
        return None
    return next(
        (
            opportunity
            for opportunity in dashboard.launchpad.opportunities
            if opportunity.id == wanted
        ),
        None,
    )


def _available_launchpad_ids(dashboard: DashboardView | SimpleNamespace) -> list[str]:
    return [opportunity.id for opportunity in dashboard.launchpad.opportunities]


def _attention_queue_idle_reply(*, signal_id: str | None = None) -> str:
    wanted = str(signal_id or "").strip()
    if wanted:
        return (
            f"The selected attention-queue signal `{wanted}` does not have a bounded move "
            "right now."
        )
    return _ATTENTION_QUEUE_IDLE_REPLY


def _build_status_payload(
    dashboard: DashboardView | SimpleNamespace,
) -> dict[str, object]:
    active_count = sum(1 for mission in dashboard.missions if mission.status == "active")
    blocked_count = len(operator_blocked_missions(dashboard.missions))
    paused_count = sum(1 for mission in dashboard.missions if mission.status == "paused")
    failed_count = sum(1 for mission in dashboard.missions if mission.status == "failed")
    connected_count = sum(1 for instance in dashboard.instances if instance.connected)
    typed_dashboard = cast(DashboardView, dashboard)
    browser_posture = (
        typed_dashboard.browser_posture
        if isinstance(typed_dashboard.browser_posture, BrowserPostureView)
        else None
    )
    status_plan = plan_control_chat("status", typed_dashboard)
    queue_plan = plan_attention_queue(typed_dashboard)
    return {
        "headline": dashboard.brief.headline,
        "summary": dashboard.brief.summary,
        "brief": dashboard.brief.model_dump(mode="json"),
        "status_plan": _control_chat_plan_payload(status_plan),
        "mission_summary": {
            "active_count": active_count,
            "blocked_count": blocked_count,
            "paused_count": paused_count,
            "failed_count": failed_count,
        },
        "instance_summary": {
            "connected_count": connected_count,
            "total_count": len(dashboard.instances),
        },
        "browser_posture": (
            browser_posture.model_dump(mode="json") if browser_posture is not None else None
        ),
        "gateway_capability": dashboard.gateway_capability.model_dump(mode="json"),
        "radar": dashboard.radar.model_dump(mode="json"),
        "launchpad": dashboard.launchpad.model_dump(mode="json"),
        "queue_plan": _attention_queue_plan_payload(queue_plan),
    }


async def _build_operator_dashboard(services: CliServices) -> DashboardView | SimpleNamespace:
    live_dashboard = await _try_live_dashboard_view(services.settings)
    if live_dashboard is not None:
        return live_dashboard
    project_rows = await services.database.list_projects()
    projects = [
        ProjectView.model_validate(services.project_service.inspect(row)) for row in project_rows
    ]
    instances = await services.manager.list_views()
    missions = await services.mission_service.list_views()
    doctrines = build_doctrines(missions, projects)
    gateway_capability = await services.gateway_capability.get_view()
    gateway_bootstrap = await services.gateway_bootstrap.get_view()
    preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
        services.database
    )
    launchpad = build_launchpad(
        instances,
        missions,
        projects,
        doctrines=doctrines,
        gateway_capability=gateway_capability,
        preferred_memory_provider=preferred_memory_provider,
        preferred_executor=preferred_executor,
    )
    browser_posture = build_browser_posture(
        control_plane_url=_control_plane_base_url(services.settings),
        gateway_bootstrap=gateway_bootstrap,
        gateway_capability=gateway_capability,
    )
    return SimpleNamespace(
        brief=build_brief(
            instances,
            missions,
            projects,
            browser_posture=browser_posture,
        ),
        instances=instances,
        missions=missions,
        projects=projects,
        launchpad=launchpad,
        radar=build_radar(
            instances,
            missions,
            projects,
            browser_posture=browser_posture,
            gateway_capability=gateway_capability,
        ),
        browser_posture=browser_posture,
        gateway_capability=gateway_capability,
        gateway_bootstrap=gateway_bootstrap,
        ops_mesh=SimpleNamespace(skillbooks=[]),
    )


def _build_cli_conversation_target(
    *,
    conversation_channel: str | None,
    conversation_account_id: str | None,
    conversation_peer_kind: str | None,
    conversation_peer_id: str | None,
) -> ConversationTargetView | None:
    channel = str(conversation_channel or "").strip()
    account_id = str(conversation_account_id or "").strip() or None
    peer_kind = str(conversation_peer_kind or "").strip().lower() or None
    peer_id = str(conversation_peer_id or "").strip() or None
    if not channel and not account_id and not peer_kind and not peer_id:
        return None
    if not channel:
        raise ValueError(
            "Provide --conversation-channel when saving a conversation route target."
        )
    if bool(peer_kind) != bool(peer_id):
        raise ValueError(
            "Provide both --conversation-peer-kind and --conversation-peer-id together."
        )
    if peer_kind not in {None, "direct", "group", "channel"}:
        raise ValueError("--conversation-peer-kind must be one of: direct, group, channel.")
    resolved_peer_kind = cast(Literal["direct", "group", "channel"] | None, peer_kind)
    return ConversationTargetView(
        channel=channel,
        account_id=account_id,
        peer_kind=resolved_peer_kind,
        peer_id=peer_id,
    )


def _parse_cli_csv_list(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _build_bootstrap_payload(
    *,
    setup_mode: str,
    setup_flow: str,
    project_path: Path,
    operator_name: str,
    task_name: str,
    objective_template: str,
    instance_mode: str,
    instance_id: int | None,
    instance_name: str,
    project_label: str | None,
    team_name: str | None,
    operator_email: str | None,
    issue_api_key: bool,
    task_summary: str | None,
    cadence_minutes: int,
    model: str,
    max_turns: int | None,
    use_builtin_agents: bool,
    run_verification: bool,
    auto_commit: bool,
    pause_on_approval: bool,
    allow_auto_reflexes: bool,
    auto_recover: bool,
    auto_recover_limit: int,
    reflex_cooldown_seconds: int,
    allow_failover: bool,
    enabled: bool,
    use_mempalace: bool,
    conversation_channel: str | None = None,
    conversation_account_id: str | None = None,
    conversation_peer_kind: str | None = None,
    conversation_peer_id: str | None = None,
) -> OnboardingBootstrapCreate:
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    conversation_target = _build_cli_conversation_target(
        conversation_channel=conversation_channel,
        conversation_account_id=conversation_account_id,
        conversation_peer_kind=conversation_peer_kind,
        conversation_peer_id=conversation_peer_id,
    )
    return OnboardingBootstrapCreate(
        setup_mode=setup_mode,  # type: ignore[arg-type]
        setup_flow=setup_flow,  # type: ignore[arg-type]
        instance_mode=instance_mode,  # type: ignore[arg-type]
        instance_id=instance_id,
        instance_name=instance_name,
        project_path=str(project_path),
        project_label=project_label,
        operator_name=operator_name,
        operator_email=operator_email,
        team_name=team_name,
        issue_api_key=issue_api_key,
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
        task_name=task_name,
        task_summary=task_summary,
        objective_template=objective_template,
        conversation_target=conversation_target,
        cadence_minutes=cadence_minutes,
        model=model,
        max_turns=max_turns,
        use_builtin_agents=use_builtin_agents,
        run_verification=run_verification,
        auto_commit=auto_commit,
        pause_on_approval=pause_on_approval,
        allow_auto_reflexes=allow_auto_reflexes,
        auto_recover=auto_recover,
        auto_recover_limit=auto_recover_limit,
        reflex_cooldown_seconds=reflex_cooldown_seconds,
        allow_failover=allow_failover,
        enabled=enabled,
        use_mempalace=use_mempalace,
    )


def _apply_swarm_launch_override(
    payload: MissionCreate,
    *,
    swarm_enabled: bool,
) -> MissionCreate:
    if not swarm_enabled:
        return payload
    return payload.model_copy(
        update={
            "swarm_enabled": True,
            "collaboration_mode": SWARM_COLLABORATION_MODE,
        }
    )


@app.command()
def serve(
    host: str = typer.Option(settings.host, help="Host to bind."),
    port: int = typer.Option(settings.port, help="Port to bind."),
    reload: bool = typer.Option(False, help="Enable hot reload."),
) -> None:
    settings.host = host
    settings.port = port
    os.environ["OPENZUES_HOST"] = host
    os.environ["OPENZUES_PORT"] = str(port)
    uvicorn.run(
        "openzues.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


@app.command("recall")
def recall(
    query: str | None = typer.Argument(
        None,
        help="Optional search query. Omit it to browse recent durable recall.",
    ),
    project_id: int | None = typer.Option(
        None,
        help="Optional project filter.",
    ),
    limit: int = typer.Option(
        6,
        min=1,
        max=12,
        help="Maximum recall items to return.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the recall results as JSON.",
    ),
) -> None:
    payload = _run(
        _run_with_services(
            lambda services: services.recall.search(
                query=query,
                project_id=project_id,
                limit=limit,
            )
        )
    ).model_dump(mode="json")
    _emit_recall(payload, json_output=json_output)


@app.command("learn")
def learn(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the learning review payload as JSON.",
    ),
) -> None:
    async def _action(services: CliServices):
        project_rows = await services.database.list_projects()
        projects = [
            ProjectView.model_validate(services.project_service.inspect(row))
            for row in project_rows
        ]
        instances = await services.manager.list_views()
        missions = await services.mission_service.list_views()
        doctrines = build_doctrines(missions, projects)
        return build_cortex(instances, missions, projects, doctrines=doctrines)

    payload = _run(_run_with_services(_action)).model_dump(mode="json")
    _emit_cortex(payload, json_output=json_output)


@app.command("status")
def status_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the operator status summary as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        live_status = await _try_live_status_payload(services.settings)
        if live_status is not None:
            return live_status
        dashboard = await _build_operator_dashboard(services)
        return _build_status_payload(dashboard)

    payload = _run(_run_with_services(_action))
    _emit_status(payload, json_output=json_output)


@app.command("watch")
def watch_command(
    host: str = typer.Option(settings.host, help="Host for the live OpenZues server."),
    port: int = typer.Option(settings.port, help="Port for the live OpenZues server."),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Explicit base URL for the live OpenZues server.",
    ),
    mission_id: int | None = typer.Option(
        None,
        "--mission-id",
        help="Watch a specific mission id.",
    ),
    task_name: str | None = typer.Option(
        None,
        "--task-name",
        help=(
            "Mission or task label to watch. Defaults to the saved setup handoff task, then "
            "falls back to the OpenClaw parity program label."
        ),
    ),
    launch: bool = typer.Option(
        False,
        "--launch",
        help=(
            "If the watched mission is paused, failed, or only staged in the saved handoff, "
            "resume or launch it before watching."
        ),
    ),
    follow: bool = typer.Option(
        False,
        "--follow",
        help="Keep polling the live server until interrupted or the watch condition settles.",
    ),
    interval_seconds: float = typer.Option(
        5.0,
        "--interval",
        min=1.0,
        help="Polling interval in seconds while following.",
    ),
    cycles: int | None = typer.Option(
        None,
        "--cycles",
        min=1,
        help="Optional maximum number of watch cycles to print.",
    ),
    until_terminal: bool = typer.Option(
        False,
        "--until-terminal",
        help="Stop once the watched mission reaches a completed or failed terminal state.",
    ),
    browser: bool = typer.Option(
        False,
        "--browser",
        help="Also verify the live dashboard surface with agent-browser during watch cycles.",
    ),
    browser_url: str | None = typer.Option(
        None,
        "--browser-url",
        help="Explicit URL for browser verification. Defaults to the same live OpenZues URL.",
    ),
    browser_every: int = typer.Option(
        1,
        "--browser-every",
        min=1,
        help="Run browser verification every N watch cycles when --browser is enabled.",
    ),
    browser_session: str = typer.Option(
        _DEFAULT_BROWSER_WATCH_SESSION,
        "--browser-session",
        help="agent-browser session name to reuse across watch cycles.",
    ),
    browser_screenshot_copy: str | None = typer.Option(
        None,
        "--browser-screenshot-copy",
        help="Optional stable path that should always hold the latest browser screenshot artifact.",
    ),
    log_file: str | None = typer.Option(
        None,
        "--log-file",
        help="Optional rolling log file for watch output.",
    ),
    log_max_bytes: int = typer.Option(
        1_000_000,
        "--log-max-bytes",
        min=1,
        help="Rotate the watch log when it reaches this size.",
    ),
    log_backups: int = typer.Option(
        3,
        "--log-backups",
        min=1,
        help="Number of rotated watch log backups to keep.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the watch snapshot as JSON.",
    ),
) -> None:
    base_url = _watch_base_url(url=url, host=host, port=port)
    keep_watching = follow or until_terminal or (cycles is not None and cycles > 1)
    cycle_index = 0
    auto_action: dict[str, Any] | None = None
    poll_timeout = max(60.0, interval_seconds * 12.0)
    browser_target_url = browser_url or base_url
    resolved_browser_session = browser_session
    if resolved_browser_session == _DEFAULT_BROWSER_WATCH_SESSION:
        resolved_browser_session = f"{_DEFAULT_BROWSER_WATCH_SESSION}-{int(time.time())}"
    log_path = Path(log_file).expanduser() if log_file else None
    screenshot_artifact_path = (
        Path(browser_screenshot_copy).expanduser() if browser_screenshot_copy else None
    )

    try:
        while True:
            if launch and cycle_index == 0:
                initial_dashboard = _watch_api_json(
                    base_url,
                    "/api/dashboard",
                    timeout_seconds=poll_timeout,
                )
                initial_handoff = _watch_api_json(
                    base_url,
                    "/api/setup/launch",
                    timeout_seconds=poll_timeout,
                )
                if not isinstance(initial_dashboard, dict) or not isinstance(initial_handoff, dict):
                    raise RuntimeError(
                        "OpenZues watch did not receive the expected dashboard payload."
                    )
                auto_action = _maybe_launch_watch_target(
                    base_url,
                    dashboard=initial_dashboard,
                    handoff=initial_handoff,
                    mission_id=mission_id,
                    task_name=task_name,
                )

            try:
                dashboard = _watch_api_json(
                    base_url,
                    "/api/dashboard",
                    timeout_seconds=poll_timeout,
                )
                handoff = _watch_api_json(
                    base_url,
                    "/api/setup/launch",
                    timeout_seconds=poll_timeout,
                )
            except RuntimeError:
                if not keep_watching:
                    raise
                typer.echo(f"watch warning: {base_url} is slow to answer; retrying.")
                time.sleep(interval_seconds)
                auto_action = None
                continue
            if not isinstance(dashboard, dict) or not isinstance(handoff, dict):
                raise RuntimeError("OpenZues watch did not receive the expected live payload.")
            browser_verification: dict[str, Any] | None = None
            if browser and cycle_index % browser_every == 0:
                try:
                    browser_verification = _watch_browser_verify_guarded(
                        browser_url=browser_target_url,
                        session_name=resolved_browser_session,
                    )
                    if screenshot_artifact_path is not None:
                        browser_verification = _copy_watch_screenshot(
                            browser_verification,
                            artifact_path=screenshot_artifact_path,
                        )
                except RuntimeError as exc:
                    browser_verification = {
                        "ok": False,
                        "status": "warn",
                        "summary": str(exc),
                    }
            payload = _build_watch_payload(
                base_url=base_url,
                dashboard=dashboard,
                handoff=handoff,
                mission_id=mission_id,
                task_name=task_name,
                auto_action=auto_action,
                browser_verification=browser_verification,
            )
            rendered_output = _watch_output(payload, json_output=json_output)
            typer.echo(rendered_output)
            if log_path is not None:
                _append_watch_log(
                    log_path,
                    text=rendered_output,
                    max_bytes=log_max_bytes,
                    backups=log_backups,
                )

            cycle_index += 1
            watched_mission = payload.get("watched_mission")
            if not keep_watching:
                break
            if cycles is not None and cycle_index >= cycles:
                break
            if (
                until_terminal
                and isinstance(watched_mission, dict)
                and _watch_is_terminal(watched_mission.get("status"))
                and not bool(watched_mission.get("in_progress"))
            ):
                break
            if not json_output:
                typer.echo("")
            time.sleep(interval_seconds)
            auto_action = None
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt as exc:
        typer.echo("watch stopped")
        raise typer.Exit(code=130) from exc


@browser_app.command("status")
def browser_status(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser runtime/operator posture as JSON.",
    ),
) -> None:
    payload = _run(_run_with_services(_build_browser_status_payload))
    _emit_browser_status(payload, json_output=json_output)


@browser_app.command("doctor")
def browser_doctor(
    verify: bool = typer.Option(
        False,
        "--verify",
        help="Also run a bounded browser verification against the control-plane URL.",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Explicit URL for the optional verification run.",
    ),
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name for the optional verification run.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser doctor result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        payload = await _build_browser_status_payload(services)
        if not verify:
            return {**payload, "verification": None}

        resolved_url = url or _control_plane_base_url(services.settings)
        try:
            verification = _watch_browser_verify_guarded(
                browser_url=resolved_url,
                session_name=session,
            )
        except RuntimeError as exc:
            verification_payload = _browser_verify_error_payload(
                summary=str(exc),
                resolved_url=resolved_url,
                session=session,
            )
            return {
                **payload,
                "status": "warn",
                "headline": "Browser doctor found repair work",
                "summary": str(exc),
                "verification": verification_payload,
            }

        verification_payload = _browser_verify_payload(
            verification=verification,
            resolved_url=resolved_url,
            session=session,
        )
        if not bool(verification_payload.get("ok")):
            return {
                **payload,
                "status": "warn",
                "headline": "Browser doctor found repair work",
                "summary": str(verification_payload.get("summary") or payload.get("summary") or ""),
                "verification": verification_payload,
            }
        return {**payload, "verification": verification_payload}

    payload = _run(_run_with_services(_action))
    _emit_browser_doctor(payload, json_output=json_output)
    verification = payload.get("verification")
    if verify and isinstance(verification, dict) and not bool(verification.get("ok")):
        raise typer.Exit(code=1)


@browser_app.command("verify")
def browser_verify(
    url: str | None = typer.Option(
        None,
        "--url",
        help="Explicit URL to verify. Defaults to the current OpenZues control-plane URL.",
    ),
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name for the verification run.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser verification result as JSON.",
    ),
) -> None:
    resolved_url = url or _control_plane_base_url(_runtime_settings())
    try:
        verification = _watch_browser_verify_guarded(
            browser_url=resolved_url,
            session_name=session,
        )
    except RuntimeError as exc:
        payload = _browser_verify_error_payload(
            summary=str(exc),
            resolved_url=resolved_url,
            session=session,
        )
        _emit_browser_verify(payload, json_output=json_output)
        raise typer.Exit(code=1) from exc

    payload = _browser_verify_payload(
        verification=verification,
        resolved_url=resolved_url,
        session=session,
    )
    _emit_browser_verify(payload, json_output=json_output)
    if not bool(payload.get("ok")):
        raise typer.Exit(code=1)


@browser_app.command("open")
def browser_open(
    target: str = typer.Argument(..., help="URL to open in the agent-browser session."),
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name for the browser tab.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser open result as JSON.",
    ),
) -> None:
    try:
        _run_browser_command(
            ["open", target],
            session_name=session,
            timeout_seconds=15.0,
        )
    except RuntimeError as exc:
        payload = {
            "ok": False,
            "status": "warn",
            "headline": "Browser open failed",
            "summary": str(exc),
            "url": target,
            "session": session,
        }
        _emit_browser_verify(payload, json_output=json_output)
        raise typer.Exit(code=1) from exc

    payload = {
        "ok": True,
        "status": "ready",
        "headline": "Browser page opened",
        "summary": f"Opened {target} in agent-browser session {session}.",
        "url": target,
        "session": session,
    }
    _emit_browser_verify(payload, json_output=json_output)


@browser_app.command("snapshot")
def browser_snapshot(
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser snapshot result as JSON.",
    ),
) -> None:
    try:
        snapshot_output = _run_browser_command(
            ["snapshot", "-i"],
            session_name=session,
            timeout_seconds=6.0,
        )
    except RuntimeError as exc:
        payload = {
            "ok": False,
            "status": "warn",
            "headline": "Browser snapshot failed",
            "summary": str(exc),
            "session": session,
        }
        _emit_browser_verify(payload, json_output=json_output)
        raise typer.Exit(code=1) from exc

    snapshot_summary = _summarize_browser_snapshot(snapshot_output)
    payload = {
        "ok": True,
        "status": "ready",
        "headline": "Browser snapshot captured",
        "summary": snapshot_summary,
        "session": session,
        "snapshot_summary": snapshot_summary,
        "snapshot_output": snapshot_output,
    }
    _emit_browser_verify(payload, json_output=json_output)


@browser_app.command("console")
def browser_console(
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser console lines as JSON.",
    ),
) -> None:
    try:
        output = _run_browser_command(
            ["console"],
            session_name=session,
            timeout_seconds=5.0,
        )
    except RuntimeError as exc:
        payload = {
            "ok": False,
            "status": "warn",
            "headline": "Browser console read failed",
            "summary": str(exc),
            "session": session,
            "line_count": 0,
            "lines": [],
        }
        _emit_browser_stream(payload, json_output=json_output)
        raise typer.Exit(code=1) from exc

    payload = _browser_stream_payload(label="console", session=session, output=output)
    _emit_browser_stream(payload, json_output=json_output)


@browser_app.command("errors")
def browser_errors(
    session: str = typer.Option(
        _DEFAULT_BROWSER_SESSION,
        "--session",
        help="agent-browser session name to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the browser page errors as JSON.",
    ),
) -> None:
    try:
        output = _run_browser_command(
            ["errors"],
            session_name=session,
            timeout_seconds=5.0,
        )
    except RuntimeError as exc:
        payload = {
            "ok": False,
            "status": "warn",
            "headline": "Browser error read failed",
            "summary": str(exc),
            "session": session,
            "line_count": 0,
            "lines": [],
        }
        _emit_browser_stream(payload, json_output=json_output)
        raise typer.Exit(code=1) from exc

    payload = _browser_stream_payload(label="error", session=session, output=output)
    _emit_browser_stream(payload, json_output=json_output)


@agents_app.command("list")
def agents_list(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the configured agent inventory as JSON.",
    ),
) -> None:
    payload = _run(_run_with_services(lambda services: services.gateway_agents.list_agents()))
    _emit_agents_inventory(payload, json_output=json_output)


@channels_app.command("status")
def channels_status(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the notification route channel inventory as JSON.",
    ),
) -> None:
    payload = _run(
        _run_with_services(lambda services: services.gateway_channels.build_snapshot())
    )
    _emit_channel_inventory(payload, json_output=json_output)


@app.command("launch")
def launch_command(
    opportunity_id: str = typer.Argument(
        ...,
        help="Launchpad opportunity id from `openzues status --json` or the human status summary.",
    ),
    swarm_enabled: bool = typer.Option(
        False,
        "--swarm",
        help="Launch the selected draft through the native swarm constitution pipeline.",
    ),
    plan_only: bool = typer.Option(
        False,
        "--plan",
        help="Preview the targeted launchpad move without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the targeted launchpad result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        dashboard = await _build_operator_dashboard(services)
        opportunity = _find_launchpad_opportunity(dashboard, opportunity_id)
        if opportunity is None:
            available_ids = _available_launchpad_ids(dashboard)
            available_note = (
                f" Available ids: {', '.join(available_ids)}."
                if available_ids
                else " The launchpad is empty right now."
            )
            raise ValueError(
                f"Launchpad opportunity '{opportunity_id}' is not available right now."
                f"{available_note} Run `openzues status --json` to inspect the current launchpad."
            )

        mission_payload = MissionCreate.model_validate(opportunity.mission_draft.model_dump())
        mission_payload = _apply_swarm_launch_override(
            mission_payload,
            swarm_enabled=swarm_enabled,
        )
        reason = str(opportunity.why_now or opportunity.summary or "").strip()
        if not reason:
            reason = "it is the strongest ready launchpad move right now."
        elif reason[-1] not in ".!?":
            reason = f"{reason}."
        if swarm_enabled:
            reason = (
                f"{reason} The run will use the structured nine-role swarm constitution."
            )

        if plan_only:
            return {
                "mode": "plan",
                "executed": False,
                "action_kind": "launch_opportunity",
                "reply": (
                    f"I would launch `{opportunity.title}` from the launchpad because {reason}"
                ),
                "opportunity_id": opportunity.id,
                "target_label": opportunity.title,
                "mission_id": None,
                "summary": opportunity.summary,
                "why_now": opportunity.why_now,
                "action_label": opportunity.action_label,
                "swarm_enabled": mission_payload.swarm_enabled,
                "mission_payload": mission_payload.model_dump(mode="json"),
            }

        mission = await services.mission_service.create(mission_payload)
        return {
            "mode": "executed",
            "executed": True,
            "action_kind": "launch_opportunity",
            "reply": f"I launched `{opportunity.title}` from the launchpad because {reason}",
            "opportunity_id": opportunity.id,
            "target_label": mission.name,
            "mission_id": mission.id,
            "summary": opportunity.summary,
            "why_now": opportunity.why_now,
            "action_label": opportunity.action_label,
            "swarm_enabled": mission_payload.swarm_enabled,
        }

    try:
        payload = _run(_run_with_services(_action))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _emit_continue_action(payload, json_output=json_output)


@app.command("continue")
def continue_command(
    plan_only: bool = typer.Option(
        False,
        "--plan",
        help="Preview the next gateway-aware continue action without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the continue result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return await _run_control_chat_prompt(
            services,
            prompt="continue",
            plan_only=plan_only,
        )

    payload = _run(_run_with_services(_action))
    _emit_continue_action(payload, json_output=json_output)


@app.command("recover")
def recover_command(
    plan_only: bool = typer.Option(
        False,
        "--plan",
        help="Preview the next gateway-aware recovery action without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the recovery result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return await _run_control_chat_prompt(
            services,
            prompt="recover",
            plan_only=plan_only,
        )

    payload = _run(_run_with_services(_action))
    _emit_continue_action(payload, json_output=json_output)


@app.command("harden")
def harden_command(
    plan_only: bool = typer.Option(
        False,
        "--plan",
        help="Preview the next gateway-aware hardening action without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the hardening result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return await _run_control_chat_prompt(
            services,
            prompt="harden",
            plan_only=plan_only,
        )

    payload = _run(_run_with_services(_action))
    _emit_continue_action(payload, json_output=json_output)


@routes_app.command("test")
def routes_test_command(
    route_id: int = typer.Argument(..., help="Notification route ID."),
    event_type: str | None = typer.Option(
        None,
        "--event",
        help="Optional synthetic event type to use for the test delivery.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the test route result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.ops_mesh.test_notification_route(route_id, event_type=event_type)
        ).model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_route_test(payload, json_output=json_output)


@routes_app.command("create")
def routes_create_command(
    name: str = typer.Option(..., "--name", help="Notification route label."),
    kind: str = typer.Option(
        "webhook",
        "--kind",
        help="Route kind: webhook, slack, telegram, discord, or whatsapp.",
    ),
    target: str = typer.Option(
        ...,
        "--target",
        help="Webhook URL or provider API target/base endpoint.",
    ),
    events: str | None = typer.Option(
        None,
        "--events",
        help="Comma-separated events such as gateway/send,gateway/poll.",
    ),
    conversation_channel: str | None = typer.Option(
        None,
        "--conversation-channel",
        help="Conversation channel for route matching, e.g. slack or whatsapp.",
    ),
    conversation_account_id: str | None = typer.Option(
        None,
        "--conversation-account",
        help="Account, workspace, bot, or business identity for route matching.",
    ),
    conversation_peer_kind: str | None = typer.Option(
        None,
        "--conversation-peer-kind",
        help="Peer kind for the route target: direct, group, or channel.",
    ),
    conversation_peer_id: str | None = typer.Option(
        None,
        "--conversation-peer-id",
        help="Peer identifier such as channel:C123 or direct:+15551234567.",
    ),
    secret_header_name: str | None = typer.Option(
        None,
        "--secret-header",
        help="Secret header for generic webhook routes.",
    ),
    secret_token: str | None = typer.Option(
        None,
        "--secret-token",
        help="Inline route secret token; prefer --vault-secret-id for durable use.",
    ),
    vault_secret_id: int | None = typer.Option(
        None,
        "--vault-secret-id",
        help="Vault secret id to attach to this route.",
    ),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable the route."),
    json_output: bool = typer.Option(False, "--json", help="Emit the route as JSON."),
) -> None:
    route_kind = str(kind or "").strip().lower()
    if route_kind not in {"webhook", "slack", "telegram", "discord", "whatsapp"}:
        raise typer.BadParameter(
            "--kind must be one of: webhook, slack, telegram, discord, whatsapp."
        )
    route_events = _parse_cli_csv_list(events)
    if not route_events:
        route_events = (
            ["gateway/send", "gateway/poll"]
            if route_kind in {"slack", "telegram", "discord", "whatsapp"}
            else ["mission/completed", "mission/failed"]
        )
    payload = NotificationRouteCreate(
        name=name,
        kind=cast(
            Literal["webhook", "slack", "telegram", "discord", "whatsapp"],
            route_kind,
        ),
        target=target,
        events=route_events,
        conversation_target=_build_cli_conversation_target(
            conversation_channel=conversation_channel,
            conversation_account_id=conversation_account_id,
            conversation_peer_kind=conversation_peer_kind,
            conversation_peer_id=conversation_peer_id,
        ),
        enabled=enabled,
        secret_header_name=secret_header_name,
        secret_token=secret_token,
        vault_secret_id=vault_secret_id,
    )

    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.ops_mesh.create_notification_route(payload)
        ).model_dump(mode="json")

    result = _run(_run_with_services(_action))
    _emit_payload(result, json_output=json_output)


@routes_app.command("send")
def routes_send_command(
    channel: str = typer.Option(..., "--channel", help="Outbound provider channel."),
    to: str = typer.Option(..., "--to", help="Explicit provider target."),
    message: str = typer.Option("", "--message", "-m", help="Message text to send."),
    media_urls: Annotated[
        list[str] | None,
        typer.Option(
            "--media-url",
            help="Media URL to attach. Repeat for multiple media items.",
        ),
    ] = None,
    gif_playback: bool = typer.Option(
        False,
        "--gif-playback",
        help="Ask capable providers to send animated media as a GIF.",
    ),
    reply_to_id: str | None = typer.Option(
        None,
        "--reply-to",
        help="Provider message id to reply to.",
    ),
    silent: bool = typer.Option(
        False,
        "--silent",
        help="Send without notification when supported.",
    ),
    force_document: bool = typer.Option(
        False,
        "--force-document",
        help="Send media as a document when supported.",
    ),
    account_id: str | None = typer.Option(None, "--account", help="Provider account id."),
    agent_id: str | None = typer.Option(None, "--agent-id", help="Originating agent id."),
    thread_id: str | None = typer.Option(None, "--thread", help="Provider thread/topic id."),
    session_key: str | None = typer.Option(
        None,
        "--session-key",
        help="Originating OpenZues session key.",
    ),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Stable idempotency key for retry-safe delivery.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the send result as JSON."),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return await services.ops_mesh.send_direct_channel_message(
            channel=channel,
            to=to,
            message=message,
            media_urls=list(media_urls or []),
            gif_playback=True if gif_playback else None,
            reply_to_id=reply_to_id,
            silent=True if silent else None,
            force_document=True if force_document else None,
            account_id=account_id,
            agent_id=agent_id,
            thread_id=thread_id,
            session_key=session_key,
            idempotency_key=idempotency_key,
        )

    result = _run(_run_with_services(_action))
    _emit_direct_channel_delivery(result, json_output=json_output)


@routes_app.command("poll")
def routes_poll_command(
    channel: str = typer.Option(..., "--channel", help="Outbound provider channel."),
    to: str = typer.Option(..., "--to", help="Explicit provider target."),
    question: str = typer.Option(..., "--question", help="Poll question."),
    options: Annotated[
        list[str] | None,
        typer.Option(
            "--option",
            "-o",
            help="Poll option. Repeat for each choice.",
        ),
    ] = None,
    max_selections: int | None = typer.Option(
        None,
        "--max-selections",
        min=1,
        help="Maximum selectable poll options.",
    ),
    duration_seconds: int | None = typer.Option(
        None,
        "--duration-seconds",
        min=1,
        help="Poll duration in seconds.",
    ),
    duration_hours: int | None = typer.Option(
        None,
        "--duration-hours",
        min=1,
        help="Poll duration in hours.",
    ),
    silent: bool = typer.Option(
        False,
        "--silent",
        help="Send without notification when supported.",
    ),
    is_anonymous: bool | None = typer.Option(
        None,
        "--anonymous/--named",
        help="Request anonymous or named poll behavior when supported.",
    ),
    account_id: str | None = typer.Option(None, "--account", help="Provider account id."),
    thread_id: str | None = typer.Option(None, "--thread", help="Provider thread/topic id."),
    idempotency_key: str | None = typer.Option(
        None,
        "--idempotency-key",
        help="Stable idempotency key for retry-safe delivery.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the poll result as JSON."),
) -> None:
    poll_options = [str(option).strip() for option in options or [] if str(option).strip()]
    if len(poll_options) < 2:
        raise typer.BadParameter("provide at least two --option values")

    async def _action(services: CliServices) -> dict[str, object]:
        return await services.ops_mesh.send_direct_channel_poll(
            channel=channel,
            to=to,
            question=question,
            options=poll_options,
            max_selections=max_selections,
            duration_seconds=duration_seconds,
            duration_hours=duration_hours,
            silent=True if silent else None,
            is_anonymous=is_anonymous,
            account_id=account_id,
            thread_id=thread_id,
            idempotency_key=idempotency_key,
        )

    result = _run(_run_with_services(_action))
    _emit_direct_channel_delivery(result, json_output=json_output)


@routes_app.command("list")
def routes_list_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit saved notification routes as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> list[dict[str, object]]:
        return [
            route.model_dump(mode="json")
            for route in await services.ops_mesh.list_notification_route_views()
        ]

    payload = _run(_run_with_services(_action))
    _emit_routes(payload, json_output=json_output)


@routes_app.command("deliveries")
def routes_deliveries_command(
    limit: int = typer.Option(25, min=1, max=200, help="Maximum deliveries to return."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit saved outbound deliveries as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> list[dict[str, object]]:
        return [
            delivery.model_dump(mode="json")
            for delivery in await services.ops_mesh.list_outbound_delivery_views(limit=limit)
        ]

    payload = _run(_run_with_services(_action))
    _emit_outbound_deliveries(payload, json_output=json_output)


@routes_app.command("replay")
def routes_replay_command(
    limit: int = typer.Option(25, min=1, max=200, help="Maximum saved deliveries to inspect."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the replay summary as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.ops_mesh.replay_outbound_deliveries(limit=limit)
        ).model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_outbound_delivery_replay(payload, json_output=json_output)


@hermes_app.command("arm-shell")
def hermes_arm_shell(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Explicit workspace path for the shell-backed lane.",
    ),
    connect: bool = typer.Option(
        False,
        "--connect",
        help="Also try to connect the shell-backed lane immediately.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the shell-arm result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.hermes_platform.arm_workspace_shell(
                cwd=cwd,
                auto_connect=connect,
            )
        ).model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_executor_arm(payload, json_output=json_output)


@hermes_app.command("arm-docker")
def hermes_arm_docker(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Explicit workspace path for the Docker staging profile.",
    ),
    image: str | None = typer.Option(
        None,
        "--image",
        help="Docker image to pin for staged execution.",
    ),
    connect: bool = typer.Option(
        False,
        "--connect",
        help="Also try to connect the shell-backed control lane immediately.",
    ),
    mount_workspace: bool = typer.Option(
        False,
        "--mount-workspace",
        help="Opt into mounting the host workspace into the staged Docker profile.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the Docker-arm result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.hermes_platform.arm_docker_backend(
                cwd=cwd,
                image=image,
                auto_connect=connect,
                mount_workspace=mount_workspace,
            )
        ).model_dump(mode="json")

    try:
        payload = _run(_run_with_services(_action))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _emit_executor_arm(payload, json_output=json_output)


@hermes_app.command("preflight-docker")
def hermes_preflight_docker(
    cwd: str | None = typer.Option(
        None,
        "--cwd",
        help="Optional workspace path to validate for the staged Docker profile.",
    ),
    image: str | None = typer.Option(
        None,
        "--image",
        help="Optional Docker image override for the preflight check.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the Docker preflight result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        return (
            await services.hermes_platform.preflight_docker_backend(
                cwd=cwd,
                image=image,
            )
        ).model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_executor_preflight(payload, json_output=json_output)


@app.command("queue")
def queue_command(
    signal_id: str | None = typer.Option(
        None,
        "--signal-id",
        help="Target one radar signal id instead of the next automatic queue move.",
    ),
    plan_only: bool = typer.Option(
        False,
        "--plan",
        help="Preview the next autonomous attention-queue move without executing it.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the queue result as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        dashboard = await _build_operator_dashboard(services)
        typed_dashboard = cast(DashboardView, dashboard)
        plan = plan_attention_queue(typed_dashboard, target_signal_id=signal_id)
        if plan_only:
            if plan is None:
                return {
                    "mode": "plan",
                    "executed": False,
                    "action_kind": "idle",
                    "status": "observed",
                    "reply": _attention_queue_idle_reply(signal_id=signal_id),
                    "signal_id": signal_id,
                    "mission_id": None,
                    "opportunity_id": None,
                    "target_label": None,
                    "mission_payload": None,
                }
            return {
                "mode": "plan",
                "executed": False,
                "action_kind": plan.action_kind,
                "status": plan.status,
                "reply": plan.reply,
                "signal_id": plan.signal_id,
                "mission_id": plan.mission_id,
                "opportunity_id": plan.opportunity_id,
                "target_label": plan.target_label,
                "mission_payload": (
                    plan.mission_payload.model_dump(mode="json")
                    if plan.mission_payload is not None
                    else None
                ),
            }

        if plan is None:
            return {
                "mode": "executed",
                "executed": False,
                "action_kind": "idle",
                "status": "observed",
                "reply": _attention_queue_idle_reply(signal_id=signal_id),
                "signal_id": signal_id,
                "mission_id": None,
                "opportunity_id": None,
                "target_label": None,
            }

        latest_before = await services.database.get_latest_attention_queue_action(
            plan.signal_fingerprint
        )
        executed = await services.control_chat.tick_attention_queue(
            typed_dashboard,
            target_signal_id=signal_id,
        )
        latest_after = await services.database.get_latest_attention_queue_action(
            plan.signal_fingerprint
        )
        if executed and latest_after is not None:
            return {
                "mode": "executed",
                "executed": True,
                "action_kind": latest_after.get("action_kind") or plan.action_kind,
                "status": latest_after.get("status") or plan.status,
                "reply": latest_after.get("summary") or plan.reply,
                "signal_id": latest_after.get("signal_id") or plan.signal_id,
                "mission_id": latest_after.get("mission_id"),
                "opportunity_id": latest_after.get("opportunity_id"),
                "target_label": latest_after.get("target_label") or plan.target_label,
            }
        if latest_before is not None:
            target_label = str(latest_before.get("target_label") or plan.target_label or "").strip()
            target_note = f" `{target_label}`" if target_label else ""
            return {
                "mode": "executed",
                "executed": False,
                "action_kind": latest_before.get("action_kind") or plan.action_kind,
                "status": latest_before.get("status") or "observed",
                "reply": (
                    f"The attention queue already handled{target_note} for this signal, so I "
                    "left it alone."
                ),
                "signal_id": latest_before.get("signal_id") or plan.signal_id,
                "mission_id": latest_before.get("mission_id"),
                "opportunity_id": latest_before.get("opportunity_id"),
                "target_label": latest_before.get("target_label") or plan.target_label,
            }
        return {
            "mode": "executed",
            "executed": False,
            "action_kind": plan.action_kind,
            "status": "observed",
            "reply": "The attention queue did not find a safe move to execute right now.",
            "signal_id": plan.signal_id,
            "mission_id": plan.mission_id,
            "opportunity_id": plan.opportunity_id,
            "target_label": plan.target_label,
        }

    try:
        payload = _run(_run_with_services(_action))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _emit_attention_queue_action(payload, json_output=json_output)


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the Hermes parity doctor view as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        view = await _try_live_hermes_doctor_view(services.settings)
        if view is None:
            view = await services.hermes_platform.get_doctor_view()
        return view.model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_hermes_doctor(payload, json_output=json_output)


@hermes_profile_app.callback()
def hermes_profile_show(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the saved Hermes runtime profile as JSON.",
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    payload = _run(
        _run_with_services(lambda services: services.hermes_platform.get_runtime_profile())
    ).model_dump(mode="json")
    _emit_payload(payload, json_output=json_output)


@hermes_profile_app.command("set")
def hermes_profile_set(
    preferred_memory_provider: str | None = typer.Option(
        None,
        "--memory-provider",
        help="Saved Hermes memory provider key.",
    ),
    preferred_executor: str | None = typer.Option(
        None,
        "--executor",
        help="Saved Hermes executor profile key.",
    ),
    learning_autopromote_enabled: bool | None = typer.Option(
        None,
        "--auto-promote/--no-auto-promote",
        help="Enable or disable Hermes learning autopromote.",
    ),
    plugin_discovery_enabled: bool | None = typer.Option(
        None,
        "--plugin-discovery/--no-plugin-discovery",
        help="Enable or disable Hermes plugin discovery inventory.",
    ),
    channel_inventory_enabled: bool | None = typer.Option(
        None,
        "--channel-inventory/--no-channel-inventory",
        help="Enable or disable Hermes channel delivery inventory.",
    ),
    acp_inventory_enabled: bool | None = typer.Option(
        None,
        "--acp-inventory/--no-acp-inventory",
        help="Enable or disable Hermes ACP inventory.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the updated Hermes runtime profile as JSON.",
    ),
) -> None:
    update = HermesRuntimeProfileUpdate(
        preferred_memory_provider=preferred_memory_provider,
        preferred_executor=preferred_executor,
        learning_autopromote_enabled=learning_autopromote_enabled,
        plugin_discovery_enabled=plugin_discovery_enabled,
        channel_inventory_enabled=channel_inventory_enabled,
        acp_inventory_enabled=acp_inventory_enabled,
    )
    try:
        payload = _run(
            _run_with_services(
                lambda services: services.hermes_platform.update_runtime_profile(update)
            )
        ).model_dump(mode="json")
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _emit_payload(payload, json_output=json_output)


@update_app.command("status")
def update_status(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the runtime update status as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        view = await _try_live_update_view(services.settings)
        if view is None:
            view = await services.hermes_platform.get_update_view()
        return view.model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_update_status(payload, json_output=json_output)


@setup_app.callback()
def setup_show(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Emit the full setup posture as JSON."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    payload = _run(_run_with_services(lambda services: services.setup.inspect())).model_dump(
        mode="json"
    )
    _emit_payload(payload, json_output=json_output)


@setup_wizard_app.callback()
def setup_wizard_show(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the saved wizard session as JSON.",
    ),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    payload = _run(
        _run_with_services(lambda services: services.setup.get_wizard_session())
    ).model_dump(mode="json")
    _emit_payload(payload, json_output=json_output)


@setup_wizard_app.command("update")
def setup_wizard_update(
    mode: str | None = typer.Option(None, help="Setup mode: local or remote."),
    flow: str | None = typer.Option(None, help="Setup flow: quickstart or advanced."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the saved wizard session as JSON.",
    ),
) -> None:
    payload = SetupWizardSessionUpdate(mode=mode, flow=flow)  # type: ignore[arg-type]
    result = _run(
        _run_with_services(lambda services: services.setup.save_wizard_session(payload))
    ).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


@setup_app.command("launch")
def setup_launch(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the saved launch handoff as JSON.",
    ),
) -> None:
    payload = _run(
        _run_with_services(lambda services: services.setup.get_launch_handoff())
    ).model_dump(mode="json")
    _emit_payload(payload, json_output=json_output)


@gateway_app.command("show")
def gateway_show(
    json_output: bool = typer.Option(False, "--json", help="Emit the full profile as JSON."),
) -> None:
    payload = _run(
        _run_with_services(lambda services: services.gateway_bootstrap.get_view())
    ).model_dump(mode="json")
    _emit_gateway_bootstrap(payload, json_output=json_output)


@gateway_app.command("doctor")
def gateway_doctor(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the gateway capability summary as JSON.",
    ),
) -> None:
    async def _action(services: CliServices) -> dict[str, object]:
        view = await _try_live_gateway_capability_view(services.settings)
        if view is None:
            view = await services.gateway_capability.get_view()
        return view.model_dump(mode="json")

    payload = _run(_run_with_services(_action))
    _emit_gateway_capability(payload, json_output=json_output)


@gateway_app.command("memory-prove")
def gateway_memory_prove(
    instance_id: int | None = typer.Option(
        None,
        help="Optional lane id to target for the direct MemPalace proof.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the launched proof mission as JSON.",
    ),
) -> None:
    try:
        payload = _run(
            _run_with_services(
                lambda services: services.gateway_capability.launch_memory_proof(
                    instance_id=instance_id
                )
            )
        ).model_dump(mode="json")
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _emit_memory_proof_mission(payload, json_output=json_output)


@gateway_app.command("bootstrap")
def gateway_bootstrap(
    setup_mode: str = typer.Option("local", help="Setup mode: local or remote."),
    setup_flow: str = typer.Option("quickstart", help="Setup flow: quickstart or advanced."),
    project_path: Path = typer.Option(  # noqa: B008
        ...,
        exists=False,
        help="Workspace path to register.",
    ),
    operator_name: str = typer.Option(..., help="Default remote operator name."),
    task_name: str = typer.Option(..., help="Recurring task name."),
    objective_template: str = typer.Option(..., help="Recurring mission objective template."),
    instance_mode: str = typer.Option(
        "quick_connect_desktop",
        help="Bootstrap lane mode: quick_connect_desktop, create_desktop, or existing.",
    ),
    instance_id: int | None = typer.Option(None, help="Existing lane id when using existing mode."),
    instance_name: str = typer.Option("Local Codex Desktop", help="Lane label."),
    project_label: str | None = typer.Option(None, help="Workspace label override."),
    team_name: str | None = typer.Option(None, help="Operator team name."),
    operator_email: str | None = typer.Option(None, help="Operator email."),
    issue_api_key: bool = typer.Option(True, help="Issue a remote API key if needed."),
    task_summary: str | None = typer.Option(None, help="Recurring task summary."),
    cadence_minutes: int = typer.Option(180, min=1, help="Recurring task cadence in minutes."),
    model: str = typer.Option("gpt-5.4", help="Default mission model."),
    max_turns: int | None = typer.Option(4, min=1, help="Max turns per mission run."),
    use_builtin_agents: bool = typer.Option(True, help="Allow built-in agents."),
    run_verification: bool = typer.Option(True, help="Run verification by default."),
    auto_commit: bool = typer.Option(False, help="Auto-commit milestones by default."),
    pause_on_approval: bool = typer.Option(True, help="Pause when approvals are required."),
    allow_auto_reflexes: bool = typer.Option(True, help="Allow automated reflex nudges."),
    auto_recover: bool = typer.Option(True, help="Allow auto-recovery."),
    auto_recover_limit: int = typer.Option(2, min=0, help="Auto-recovery retry limit."),
    reflex_cooldown_seconds: int = typer.Option(
        900,
        min=60,
        help="Cooldown between reflex launches.",
    ),
    allow_failover: bool = typer.Option(True, help="Allow failover guidance."),
    enabled: bool = typer.Option(True, help="Enable the recurring task."),
    use_mempalace: bool = typer.Option(
        False,
        "--use-mempalace",
        help="Stage MemPalace as the tracked project memory integration.",
    ),
    conversation_channel: str | None = typer.Option(
        None,
        "--conversation-channel",
        help="Adapter-neutral route channel, for example slack or telegram.",
    ),
    conversation_account_id: str | None = typer.Option(
        None,
        "--conversation-account",
        help="Adapter-neutral account or bot identity.",
    ),
    conversation_peer_kind: str | None = typer.Option(
        None,
        "--conversation-peer-kind",
        help="Peer kind for the route target: direct, group, or channel.",
    ),
    conversation_peer_id: str | None = typer.Option(
        None,
        "--conversation-peer-id",
        help="Peer identifier for the route target.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    payload = _build_bootstrap_payload(
        setup_mode=setup_mode,
        setup_flow=setup_flow,
        project_path=project_path,
        operator_name=operator_name,
        task_name=task_name,
        objective_template=objective_template,
        instance_mode=instance_mode,
        instance_id=instance_id,
        instance_name=instance_name,
        project_label=project_label,
        team_name=team_name,
        operator_email=operator_email,
        issue_api_key=issue_api_key,
        task_summary=task_summary,
        cadence_minutes=cadence_minutes,
        model=model,
        max_turns=max_turns,
        use_builtin_agents=use_builtin_agents,
        run_verification=run_verification,
        auto_commit=auto_commit,
        pause_on_approval=pause_on_approval,
        allow_auto_reflexes=allow_auto_reflexes,
        auto_recover=auto_recover,
        auto_recover_limit=auto_recover_limit,
        reflex_cooldown_seconds=reflex_cooldown_seconds,
        allow_failover=allow_failover,
        enabled=enabled,
        use_mempalace=use_mempalace,
        conversation_channel=conversation_channel,
        conversation_account_id=conversation_account_id,
        conversation_peer_kind=conversation_peer_kind,
        conversation_peer_id=conversation_peer_id,
    )
    result = _run(
        _run_with_services(lambda services: services.onboarding.bootstrap(payload))
    ).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


@setup_app.command("bootstrap")
def setup_bootstrap(
    setup_mode: str = typer.Option("local", help="Setup mode: local or remote."),
    setup_flow: str = typer.Option("quickstart", help="Setup flow: quickstart or advanced."),
    project_path: Path = typer.Option(  # noqa: B008
        ...,
        exists=False,
        help="Workspace path to register.",
    ),
    operator_name: str = typer.Option(..., help="Default remote operator name."),
    task_name: str = typer.Option(..., help="Recurring task name."),
    objective_template: str = typer.Option(..., help="Recurring mission objective template."),
    instance_mode: str = typer.Option(
        "quick_connect_desktop",
        help="Bootstrap lane mode: quick_connect_desktop, create_desktop, or existing.",
    ),
    instance_id: int | None = typer.Option(None, help="Existing lane id when using existing mode."),
    instance_name: str = typer.Option("Local Codex Desktop", help="Lane label."),
    project_label: str | None = typer.Option(None, help="Workspace label override."),
    team_name: str | None = typer.Option(None, help="Operator team name."),
    operator_email: str | None = typer.Option(None, help="Operator email."),
    issue_api_key: bool = typer.Option(True, help="Issue a remote API key if needed."),
    task_summary: str | None = typer.Option(None, help="Recurring task summary."),
    cadence_minutes: int = typer.Option(180, min=1, help="Recurring task cadence in minutes."),
    model: str = typer.Option("gpt-5.4", help="Default mission model."),
    max_turns: int | None = typer.Option(4, min=1, help="Max turns per mission run."),
    use_builtin_agents: bool = typer.Option(True, help="Allow built-in agents."),
    run_verification: bool = typer.Option(True, help="Run verification by default."),
    auto_commit: bool = typer.Option(False, help="Auto-commit milestones by default."),
    pause_on_approval: bool = typer.Option(True, help="Pause when approvals are required."),
    allow_auto_reflexes: bool = typer.Option(True, help="Allow automated reflex nudges."),
    auto_recover: bool = typer.Option(True, help="Allow auto-recovery."),
    auto_recover_limit: int = typer.Option(2, min=0, help="Auto-recovery retry limit."),
    reflex_cooldown_seconds: int = typer.Option(
        900,
        min=60,
        help="Cooldown between reflex launches.",
    ),
    allow_failover: bool = typer.Option(True, help="Allow failover guidance."),
    enabled: bool = typer.Option(True, help="Enable the recurring task."),
    use_mempalace: bool = typer.Option(
        False,
        "--use-mempalace",
        help="Stage MemPalace as the tracked project memory integration.",
    ),
    conversation_channel: str | None = typer.Option(
        None,
        "--conversation-channel",
        help="Adapter-neutral route channel, for example slack or telegram.",
    ),
    conversation_account_id: str | None = typer.Option(
        None,
        "--conversation-account",
        help="Adapter-neutral account or bot identity.",
    ),
    conversation_peer_kind: str | None = typer.Option(
        None,
        "--conversation-peer-kind",
        help="Peer kind for the route target: direct, group, or channel.",
    ),
    conversation_peer_id: str | None = typer.Option(
        None,
        "--conversation-peer-id",
        help="Peer identifier for the route target.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    payload = _build_bootstrap_payload(
        setup_mode=setup_mode,
        setup_flow=setup_flow,
        project_path=project_path,
        operator_name=operator_name,
        task_name=task_name,
        objective_template=objective_template,
        instance_mode=instance_mode,
        instance_id=instance_id,
        instance_name=instance_name,
        project_label=project_label,
        team_name=team_name,
        operator_email=operator_email,
        issue_api_key=issue_api_key,
        task_summary=task_summary,
        cadence_minutes=cadence_minutes,
        model=model,
        max_turns=max_turns,
        use_builtin_agents=use_builtin_agents,
        run_verification=run_verification,
        auto_commit=auto_commit,
        pause_on_approval=pause_on_approval,
        allow_auto_reflexes=allow_auto_reflexes,
        auto_recover=auto_recover,
        auto_recover_limit=auto_recover_limit,
        reflex_cooldown_seconds=reflex_cooldown_seconds,
        allow_failover=allow_failover,
        enabled=enabled,
        use_mempalace=use_mempalace,
        conversation_channel=conversation_channel,
        conversation_account_id=conversation_account_id,
        conversation_peer_kind=conversation_peer_kind,
        conversation_peer_id=conversation_peer_id,
    )
    result = _run(
        _run_with_services(lambda services: services.onboarding.bootstrap(payload))
    ).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


@setup_app.command("reset")
def setup_reset(
    scope: str = typer.Option(
        "config+creds+sessions",
        help="Reset scope: config, config+creds+sessions, or full.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    result = _run(
        _run_with_services(lambda services: services.setup.reset(scope=scope))
    ).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


if __name__ == "__main__":
    app()
