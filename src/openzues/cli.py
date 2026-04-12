from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import typer
import uvicorn

from openzues.app import build_brief, build_launchpad, build_radar
from openzues.database import Database
from openzues.schemas import (
    HermesRuntimeProfileUpdate,
    MissionCreate,
    OnboardingBootstrapCreate,
    ProjectView,
    SetupWizardSessionUpdate,
)
from openzues.services.access import AccessService
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.control_chat import (
    ControlChatService,
    plan_attention_queue,
    plan_control_chat,
)
from openzues.services.cortex import build_cortex, build_doctrines
from openzues.services.environment import EnvironmentService
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.gateway_capability import GatewayCapabilityService
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
from openzues.services.vault import VaultService
from openzues.settings import Settings, settings

app = typer.Typer(help="OpenZues local control plane")
_ATTENTION_QUEUE_IDLE_REPLY = (
    "The attention queue is clear right now. There is no bounded move to fire."
)
gateway_app = typer.Typer(help="Inspect and stamp the saved gateway bootstrap profile.")
hermes_app = typer.Typer(help="Inspect and tune Hermes runtime posture.")
routes_app = typer.Typer(help="Inspect and test notification routes.")
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
app.add_typer(hermes_app, name="hermes")
app.add_typer(routes_app, name="routes")
hermes_app.add_typer(hermes_profile_app, name="profile")
app.add_typer(update_app, name="update")
app.add_typer(setup_app, name="setup")
setup_app.add_typer(setup_wizard_app, name="wizard")


def _runtime_settings() -> Settings:
    return Settings()


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
    control_chat = ControlChatService(
        database,
        mission_service,
        manager,
        hub,
    )
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
    diagnostics = payload.get("diagnostics")
    if isinstance(diagnostics, dict):
        typer.echo("diagnostics: " + str(diagnostics.get("summary") or ""))


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
                if detail:
                    typer.echo(f"[{level}] {title}: {detail}")
                else:
                    typer.echo(f"[{level}] {title}")

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
    if plan_only:
        plan = plan_control_chat(prompt, dashboard)
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
    result = await services.control_chat.submit(prompt, dashboard)
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


def _find_launchpad_opportunity(dashboard: SimpleNamespace, opportunity_id: str):
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


def _available_launchpad_ids(dashboard: SimpleNamespace) -> list[str]:
    return [opportunity.id for opportunity in dashboard.launchpad.opportunities]


def _build_status_payload(dashboard: SimpleNamespace) -> dict[str, object]:
    active_count = sum(1 for mission in dashboard.missions if mission.status == "active")
    blocked_count = sum(1 for mission in dashboard.missions if mission.status == "blocked")
    paused_count = sum(1 for mission in dashboard.missions if mission.status == "paused")
    failed_count = sum(1 for mission in dashboard.missions if mission.status == "failed")
    connected_count = sum(1 for instance in dashboard.instances if instance.connected)
    status_plan = plan_control_chat("status", dashboard)
    queue_plan = plan_attention_queue(dashboard)
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
        "gateway_capability": dashboard.gateway_capability.model_dump(mode="json"),
        "radar": dashboard.radar.model_dump(mode="json"),
        "launchpad": dashboard.launchpad.model_dump(mode="json"),
        "queue_plan": _attention_queue_plan_payload(queue_plan),
    }


async def _build_operator_dashboard(services: CliServices) -> SimpleNamespace:
    project_rows = await services.database.list_projects()
    projects = [
        ProjectView.model_validate(services.project_service.inspect(row)) for row in project_rows
    ]
    instances = await services.manager.list_views()
    missions = await services.mission_service.list_views()
    doctrines = build_doctrines(missions, projects)
    gateway_capability = await services.gateway_capability.get_view()
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
    return SimpleNamespace(
        brief=build_brief(instances, missions, projects),
        instances=instances,
        missions=missions,
        projects=projects,
        launchpad=launchpad,
        radar=build_radar(
            instances,
            missions,
            projects,
            gateway_capability=gateway_capability,
        ),
        gateway_capability=gateway_capability,
    )


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
) -> OnboardingBootstrapCreate:
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
        task_name=task_name,
        task_summary=task_summary,
        objective_template=objective_template,
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


@app.command()
def serve(
    host: str = typer.Option(settings.host, help="Host to bind."),
    port: int = typer.Option(settings.port, help="Port to bind."),
    reload: bool = typer.Option(False, help="Enable hot reload."),
) -> None:
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
        dashboard = await _build_operator_dashboard(services)
        return _build_status_payload(dashboard)

    payload = _run(_run_with_services(_action))
    _emit_status(payload, json_output=json_output)


@app.command("launch")
def launch_command(
    opportunity_id: str = typer.Argument(
        ...,
        help="Launchpad opportunity id from `openzues status --json` or the human status summary.",
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
        reason = str(opportunity.why_now or opportunity.summary or "").strip()
        if not reason:
            reason = "it is the strongest ready launchpad move right now."
        elif reason[-1] not in ".!?":
            reason = f"{reason}."

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
        plan = plan_attention_queue(dashboard)
        if plan_only:
            if plan is None:
                return {
                    "mode": "plan",
                    "executed": False,
                    "action_kind": "idle",
                    "status": "observed",
                    "reply": _ATTENTION_QUEUE_IDLE_REPLY,
                    "signal_id": None,
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
                "reply": _ATTENTION_QUEUE_IDLE_REPLY,
                "signal_id": None,
                "mission_id": None,
                "opportunity_id": None,
                "target_label": None,
            }

        latest_before = await services.database.get_latest_attention_queue_action(
            plan.signal_fingerprint
        )
        executed = await services.control_chat.tick_attention_queue(dashboard)
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

    payload = _run(_run_with_services(_action))
    _emit_attention_queue_action(payload, json_output=json_output)


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the Hermes parity doctor view as JSON.",
    ),
) -> None:
    payload = _run(
        _run_with_services(lambda services: services.hermes_platform.get_doctor_view())
    ).model_dump(mode="json")
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
    payload = _run(
        _run_with_services(lambda services: services.hermes_platform.get_update_view())
    ).model_dump(mode="json")
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
    _emit_payload(payload, json_output=json_output)


@gateway_app.command("doctor")
def gateway_doctor(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the gateway capability summary as JSON.",
    ),
) -> None:
    payload = _run(
        _run_with_services(lambda services: services.gateway_capability.get_view())
    ).model_dump(mode="json")
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
