from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import typer
import uvicorn

from openzues.database import Database
from openzues.schemas import OnboardingBootstrapCreate, SetupWizardSessionUpdate
from openzues.services.access import AccessService
from openzues.services.codex_desktop import CodexDesktopService
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.hub import BroadcastHub
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.onboarding import OnboardingService
from openzues.services.ops_mesh import OpsMeshService
from openzues.services.playbooks import PlaybookService
from openzues.services.setup import SetupService
from openzues.services.vault import VaultService
from openzues.settings import Settings, settings

app = typer.Typer(help="OpenZues local control plane")
gateway_app = typer.Typer(help="Inspect and stamp the saved gateway bootstrap profile.")
setup_app = typer.Typer(
    help="Inspect, reuse, or reset the saved setup posture.",
    invoke_without_command=True,
)
setup_wizard_app = typer.Typer(
    help="Inspect or adjust the saved setup wizard session.",
    invoke_without_command=True,
)
app.add_typer(gateway_app, name="gateway")
app.add_typer(setup_app, name="setup")
setup_app.add_typer(setup_wizard_app, name="wizard")


def _runtime_settings() -> Settings:
    return Settings()


@dataclass(slots=True)
class CliServices:
    settings: Settings
    database: Database
    manager: RuntimeManager
    access: AccessService
    onboarding: OnboardingService
    gateway_bootstrap: GatewayBootstrapService
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
    vault = VaultService(database, app_settings)
    launch_routing = LaunchRoutingService(database, manager)
    mission_service = MissionService(database, manager, hub)
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

    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    vault.initialize()
    await database.initialize()
    await access.initialize()
    await manager.load(auto_connect=False)
    return CliServices(
        settings=app_settings,
        database=database,
        manager=manager,
        access=access,
        onboarding=onboarding,
        gateway_bootstrap=gateway_bootstrap,
        setup=setup,
    )


def _run(coro):
    return asyncio.run(coro)


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


@setup_app.callback()
def setup_show(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Emit the full setup posture as JSON."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    services = _run(_build_services(_runtime_settings()))
    payload = _run(services.setup.inspect()).model_dump(mode="json")
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
    services = _run(_build_services(_runtime_settings()))
    payload = _run(services.setup.get_wizard_session()).model_dump(mode="json")
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
    services = _run(_build_services(_runtime_settings()))
    payload = SetupWizardSessionUpdate(mode=mode, flow=flow)  # type: ignore[arg-type]
    result = _run(services.setup.save_wizard_session(payload)).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


@setup_app.command("launch")
def setup_launch(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit the saved launch handoff as JSON.",
    ),
) -> None:
    services = _run(_build_services(_runtime_settings()))
    payload = _run(services.setup.get_launch_handoff()).model_dump(mode="json")
    _emit_payload(payload, json_output=json_output)


@gateway_app.command("show")
def gateway_show(
    json_output: bool = typer.Option(False, "--json", help="Emit the full profile as JSON."),
) -> None:
    services = _run(_build_services(_runtime_settings()))
    payload = _run(services.gateway_bootstrap.get_view()).model_dump(mode="json")
    _emit_payload(payload, json_output=json_output)


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
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    services = _run(_build_services(_runtime_settings()))
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
    )
    result = _run(services.onboarding.bootstrap(payload)).model_dump(mode="json")
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
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    services = _run(_build_services(_runtime_settings()))
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
    )
    result = _run(services.onboarding.bootstrap(payload)).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


@setup_app.command("reset")
def setup_reset(
    scope: str = typer.Option(
        "config+creds+sessions",
        help="Reset scope: config, config+creds+sessions, or full.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit the full result as JSON."),
) -> None:
    services = _run(_build_services(_runtime_settings()))
    result = _run(services.setup.reset(scope=scope)).model_dump(mode="json")
    _emit_payload(result, json_output=json_output)


if __name__ == "__main__":
    app()
