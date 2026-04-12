from __future__ import annotations

from pathlib import Path

from openzues.database import Database
from openzues.schemas import (
    GatewayBootstrapResourceView,
    GatewayBootstrapStatus,
    GatewayBootstrapUpdate,
    GatewayBootstrapView,
    GatewayRouteBindingMode,
    InstanceView,
    OperatorView,
    ProjectView,
    SetupFlow,
    SetupMode,
    TaskBlueprintView,
    TeamView,
)
from openzues.services.access import AccessService
from openzues.services.hermes_runtime_profile import (
    executor_label,
    load_saved_runtime_preferences,
    memory_provider_label,
)
from openzues.services.hermes_toolsets import build_hermes_tool_policy, infer_hermes_toolsets
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager


def _normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    return str(Path(value).expanduser().resolve(strict=False))


def _resource_from_instance(instance: InstanceView | None) -> GatewayBootstrapResourceView | None:
    if instance is None:
        return None
    detail = str(instance.transport)
    if instance.cwd:
        detail = f"{detail} · {instance.cwd}"
    if instance.connected:
        detail = f"{detail} · connected"
    elif instance.error:
        detail = f"{detail} · {instance.error}"
    return GatewayBootstrapResourceView(
        id=instance.id,
        label=instance.name,
        detail=detail,
        connected=instance.connected,
    )


def _resource_from_project(project: ProjectView | None) -> GatewayBootstrapResourceView | None:
    if project is None:
        return None
    detail = project.path
    if project.branch:
        detail = f"{detail} · {project.branch}"
    return GatewayBootstrapResourceView(id=project.id, label=project.label, detail=detail)


def _resource_from_team(team: TeamView | None) -> GatewayBootstrapResourceView | None:
    if team is None:
        return None
    detail = f"{team.member_count} operator{'s' if team.member_count != 1 else ''}"
    return GatewayBootstrapResourceView(id=team.id, label=team.name, detail=detail)


def _resource_from_operator(operator: OperatorView | None) -> GatewayBootstrapResourceView | None:
    if operator is None:
        return None
    detail = str(operator.role)
    if operator.team_name:
        detail = f"{detail} · {operator.team_name}"
    if operator.has_api_key:
        detail = f"{detail} · remote key ready"
    else:
        detail = f"{detail} · local-only"
    return GatewayBootstrapResourceView(id=operator.id, label=operator.name, detail=detail)


def _resource_from_task(task: TaskBlueprintView | None) -> GatewayBootstrapResourceView | None:
    if task is None:
        return None
    detail = (
        f"every {task.cadence_minutes} min" if task.cadence_minutes is not None else "manual launch"
    )
    if not task.enabled:
        detail = f"{detail} · disabled"
    return GatewayBootstrapResourceView(id=task.id, label=task.name, detail=detail)


class GatewayBootstrapService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        access: AccessService,
        launch_routing: LaunchRoutingService | None = None,
    ) -> None:
        self.database = database
        self.manager = manager
        self.access = access
        self.launch_routing = launch_routing

    async def get_view(self, *, allow_backfill: bool = True) -> GatewayBootstrapView:
        row = await self.database.get_gateway_bootstrap()
        instances = {instance.id: instance for instance in await self.manager.list_views()}
        teams = {team.id: team for team in await self.access.list_team_views()}
        operators = {operator.id: operator for operator in await self.access.list_operator_views()}
        projects = {
            int(project["id"]): ProjectView.model_validate(
                {
                    **project,
                    "exists": Path(str(project["path"])).expanduser().exists(),
                    "is_git_repo": False,
                    "branch": None,
                    "git_status": None,
                    "recent_commits": [],
                    "pull_requests": [],
                    "last_scan_at": None,
                }
            )
            for project in await self.database.list_projects()
        }
        tasks = {
            task.id: task
            for task in [
                TaskBlueprintView.model_validate(raw)
                for raw in await self.database.list_task_blueprints()
            ]
        }

        if row is None:
            setup_footprint = await self.database.get_setup_footprint()
            if allow_backfill and setup_footprint is None:
                if await self._backfill_from_existing(
                    instances=instances,
                    projects=projects,
                    teams=teams,
                    operators=operators,
                    tasks=tasks,
                ):
                    return await self.get_view()
            return GatewayBootstrapView(
                status="unconfigured",
                headline="Gateway bootstrap is not configured",
                summary=(
                    "Run QuickStart once so OpenZues has a durable default lane, workspace, "
                    "remote operator, and launch policy."
                ),
                warnings=["No gateway bootstrap profile has been saved yet."],
                setup_mode="local",
                setup_flow="quickstart",
                route_binding_mode="saved_lane",
                instance=None,
                project=None,
                team=None,
                operator=None,
                task_blueprint=None,
                default_cwd=None,
                model="gpt-5.4",
                max_turns=4,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=[],
                tool_policy=build_hermes_tool_policy([], setup_mode="local"),
                launch_defaults_summary=(
                    "Verification on, built-in agents on, approvals paused, and auto-commit off."
                ),
                launch_route=None,
            )

        setup_mode: SetupMode = (
            "remote" if str(row.get("setup_mode") or "local") == "remote" else "local"
        )
        setup_flow_value = str(
            row.get("setup_flow") or ("advanced" if setup_mode == "remote" else "quickstart")
        )
        if setup_flow_value not in {"quickstart", "advanced"}:
            setup_flow_value = "advanced" if setup_mode == "remote" else "quickstart"
        setup_flow: SetupFlow = "advanced" if setup_flow_value == "advanced" else "quickstart"
        route_binding_mode = self._resolve_route_binding_mode(row, setup_mode=setup_mode)
        instance = (
            instances.get(int(row["preferred_instance_id"]))
            if row["preferred_instance_id"]
            else None
        )
        project = (
            projects.get(int(row["preferred_project_id"])) if row["preferred_project_id"] else None
        )
        team = teams.get(int(row["team_id"])) if row["team_id"] else None
        operator = operators.get(int(row["operator_id"])) if row["operator_id"] else None
        task = tasks.get(int(row["task_blueprint_id"])) if row["task_blueprint_id"] else None
        default_cwd = _normalize_path(row.get("default_cwd"))
        toolsets = infer_hermes_toolsets(
            str(getattr(task, "objective_template", "") or ""),
            explicit_toolsets=row.get("toolsets") or (task.toolsets if task is not None else []),
            project_label=project.label if project is not None else None,
            project_path=project.path if project is not None else default_cwd,
            setup_mode=setup_mode,
            use_builtin_agents=bool(row["use_builtin_agents"]),
            run_verification=bool(row["run_verification"]),
            cadence_minutes=task.cadence_minutes if task is not None else None,
        )
        tool_policy = build_hermes_tool_policy(toolsets, setup_mode=setup_mode)
        warnings: list[str] = []
        broken_references = False

        if row["preferred_instance_id"] and instance is None:
            warnings.append("The saved default lane no longer exists.")
            broken_references = True
        if row["preferred_project_id"] and project is None:
            warnings.append("The saved default workspace no longer exists.")
            broken_references = True
        if row["operator_id"] and operator is None:
            warnings.append("The saved default operator no longer exists.")
            broken_references = True
        if row["task_blueprint_id"] and task is None:
            warnings.append("The saved default recurring task no longer exists.")
            broken_references = True
        if instance is not None and not instance.connected:
            warnings.append("The default lane is saved, but it is not connected right now.")
        if operator is not None and not operator.has_api_key:
            warnings.append("The default remote operator does not have an active API key.")
        if setup_mode == "remote" and not instances:
            warnings.append(
                "Remote bootstrap is saved, but no Codex lane exists yet for the first launch."
            )

        if setup_mode == "remote":
            required_ready = [
                project is not None,
                operator is not None,
                task is not None,
            ]
            launch_ready = (
                all(required_ready)
                and operator is not None
                and operator.has_api_key
                and bool(instances)
            )
        else:
            required_ready = [
                instance is not None,
                project is not None,
                operator is not None,
                task is not None,
            ]
            launch_ready = (
                all(required_ready)
                and instance is not None
                and instance.connected
                and operator is not None
                and operator.has_api_key
            )
        status: GatewayBootstrapStatus
        if broken_references and any(required_ready):
            status = "degraded"
            headline = "Gateway bootstrap needs repair"
            summary = (
                "OpenZues has a saved gateway profile, but one or more default resources need "
                "attention before the control plane is fully launch-ready."
            )
        elif launch_ready:
            status = "ready"
            if setup_mode == "remote":
                headline = "Remote gateway bootstrap is launch-ready"
                summary = (
                    "Remote ingress, workspace defaults, and the recurring task are aligned. "
                    "OpenZues can bind the task onto an available lane at launch time."
                )
            else:
                headline = "Gateway bootstrap is launch-ready"
                summary = (
                    "The default lane, workspace, remote operator, and recurring task are aligned "
                    "behind one saved launch policy."
                )
        else:
            status = "staged"
            if setup_mode == "remote":
                headline = "Remote gateway bootstrap is staged"
                summary = (
                    "OpenZues has a saved remote-first launch profile, but it still needs a lane "
                    "or fresh remote access before the first run is fully armed."
                )
            else:
                headline = "Gateway bootstrap is staged"
                summary = (
                    "OpenZues has a saved launch profile, but the lane connection or remote access "
                    "still needs to be armed."
                )

        preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        launch_defaults_summary = self._summarize_launch_defaults(
            row,
            preferred_memory_provider=preferred_memory_provider,
            preferred_executor=preferred_executor,
        )
        launch_route = (
            await self.launch_routing.describe(task=task, persist=False)
            if self.launch_routing is not None
            else None
        )
        return GatewayBootstrapView(
            status=status,
            headline=headline,
            summary=summary,
            warnings=warnings,
            setup_mode=setup_mode,
            setup_flow=setup_flow,
            route_binding_mode=route_binding_mode,
            instance=_resource_from_instance(instance),
            project=_resource_from_project(project),
            team=_resource_from_team(team),
            operator=_resource_from_operator(operator),
            task_blueprint=_resource_from_task(task),
            default_cwd=default_cwd,
            model=str(row["model"]),
            max_turns=int(row["max_turns"]) if row["max_turns"] is not None else None,
            use_builtin_agents=bool(row["use_builtin_agents"]),
            run_verification=bool(row["run_verification"]),
            auto_commit=bool(row["auto_commit"]),
            pause_on_approval=bool(row["pause_on_approval"]),
            allow_auto_reflexes=bool(row["allow_auto_reflexes"]),
            auto_recover=bool(row["auto_recover"]),
            auto_recover_limit=int(row["auto_recover_limit"]),
            reflex_cooldown_seconds=int(row["reflex_cooldown_seconds"]),
            allow_failover=bool(row["allow_failover"]),
            toolsets=toolsets,
            tool_policy=tool_policy,
            launch_defaults_summary=launch_defaults_summary,
            launch_route=launch_route,
        )

    async def save(self, payload: GatewayBootstrapUpdate) -> GatewayBootstrapView:
        instance_id = await self._validate_instance(payload.preferred_instance_id)
        project = await self._validate_project(payload.preferred_project_id)
        team = await self._validate_team(payload.team_id)
        operator = await self._validate_operator(
            payload.operator_id,
            team_id=team["id"] if team else None,
        )
        task = await self._validate_task(payload.task_blueprint_id)
        setup_mode = payload.setup_mode
        setup_flow = payload.setup_flow
        if setup_mode == "remote":
            setup_flow = "advanced"
        route_binding_mode = payload.route_binding_mode or self._default_route_binding_mode(
            setup_mode
        )
        toolsets = infer_hermes_toolsets(
            str(task["objective_template"]) if task is not None else "",
            explicit_toolsets=payload.toolsets
            or (task.get("toolsets") if task is not None else []),
            project_label=str(project["label"]) if project is not None else None,
            project_path=(str(project["path"]) if project is not None else payload.default_cwd),
            setup_mode=setup_mode,
            use_builtin_agents=payload.use_builtin_agents,
            run_verification=payload.run_verification,
            cadence_minutes=(
                int(task["cadence_minutes"])
                if task is not None and task.get("cadence_minutes") is not None
                else None
            ),
        )

        default_cwd = _normalize_path(payload.default_cwd)
        if default_cwd is None and project is not None:
            default_cwd = _normalize_path(str(project["path"]))
        if default_cwd is None and instance_id is not None:
            instance = await self.manager.get(instance_id)
            default_cwd = _normalize_path(instance.cwd)

        await self.database.upsert_gateway_bootstrap(
            setup_mode=setup_mode,
            setup_flow=setup_flow,
            route_binding_mode=route_binding_mode,
            preferred_instance_id=instance_id,
            preferred_project_id=int(project["id"]) if project is not None else None,
            team_id=int(team["id"]) if team is not None else None,
            operator_id=int(operator["id"]) if operator is not None else None,
            task_blueprint_id=int(task["id"]) if task is not None else None,
            last_route_instance_id=None,
            last_route_resolved_at=None,
            default_cwd=default_cwd,
            model=payload.model,
            max_turns=payload.max_turns,
            use_builtin_agents=payload.use_builtin_agents,
            run_verification=payload.run_verification,
            auto_commit=payload.auto_commit,
            pause_on_approval=payload.pause_on_approval,
            allow_auto_reflexes=payload.allow_auto_reflexes,
            auto_recover=payload.auto_recover,
            auto_recover_limit=payload.auto_recover_limit,
            reflex_cooldown_seconds=payload.reflex_cooldown_seconds,
            allow_failover=payload.allow_failover,
            toolsets=toolsets,
        )
        return await self.get_view(allow_backfill=False)

    async def save_from_onboarding(
        self,
        *,
        setup_mode: SetupMode,
        setup_flow: SetupFlow,
        route_binding_mode: GatewayRouteBindingMode | None = None,
        instance_id: int | None,
        project_id: int,
        team_id: int,
        operator_id: int,
        task_blueprint_id: int,
        default_cwd: str | None,
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
        toolsets: list[str] | None = None,
    ) -> GatewayBootstrapView:
        return await self.save(
            GatewayBootstrapUpdate(
                setup_mode=setup_mode,
                setup_flow=setup_flow,
                route_binding_mode=route_binding_mode,
                preferred_instance_id=instance_id,
                preferred_project_id=project_id,
                team_id=team_id,
                operator_id=operator_id,
                task_blueprint_id=task_blueprint_id,
                default_cwd=default_cwd,
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
                toolsets=toolsets or [],
            )
        )

    async def _validate_instance(self, instance_id: int | None) -> int | None:
        if instance_id is None:
            return None
        await self.manager.get(instance_id)
        return instance_id

    async def _validate_project(self, project_id: int | None) -> dict | None:
        if project_id is None:
            return None
        project = await self.database.get_project(project_id)
        if project is None:
            raise ValueError(f"Unknown project {project_id}")
        return project

    async def _validate_team(self, team_id: int | None) -> dict | None:
        if team_id is None:
            return None
        team = await self.database.get_team(team_id)
        if team is None:
            raise ValueError(f"Unknown team {team_id}")
        return team

    async def _validate_operator(
        self,
        operator_id: int | None,
        *,
        team_id: int | None,
    ) -> dict | None:
        if operator_id is None:
            return None
        operator = await self.database.get_operator(operator_id)
        if operator is None:
            raise ValueError(f"Unknown operator {operator_id}")
        if team_id is not None and int(operator["team_id"]) != int(team_id):
            raise ValueError("The selected operator does not belong to the selected team.")
        return operator

    async def _validate_task(self, task_id: int | None) -> dict | None:
        if task_id is None:
            return None
        task = await self.database.get_task_blueprint(task_id)
        if task is None:
            raise ValueError(f"Unknown task blueprint {task_id}")
        return task

    async def _backfill_from_existing(
        self,
        *,
        instances: dict[int, InstanceView],
        projects: dict[int, ProjectView],
        teams: dict[int, TeamView],
        operators: dict[int, OperatorView],
        tasks: dict[int, TaskBlueprintView],
    ) -> bool:
        if not tasks or not operators:
            return False

        enabled_tasks = [task for task in tasks.values() if task.enabled]
        if len(enabled_tasks) != 1:
            return False
        task = enabled_tasks[0]
        if task.instance_id is not None:
            instance = instances.get(task.instance_id)
        else:
            if len(instances) != 1:
                return False
            instance = next(iter(instances.values()), None)
        project = (
            projects.get(task.project_id)
            if task.project_id is not None
            else next(iter(projects.values()), None)
        )
        ordered_operators = sorted(
            operators.values(),
            key=lambda operator: (
                operator.has_api_key is False,
                operator.role != "owner",
                operator.id,
            ),
        )
        operator = ordered_operators[0]
        team = teams.get(operator.team_id)
        if instance is None or project is None or team is None:
            return False

        await self.database.upsert_gateway_bootstrap(
            setup_mode="local",
            setup_flow="quickstart",
            route_binding_mode="saved_lane",
            preferred_instance_id=instance.id,
            preferred_project_id=project.id,
            team_id=team.id,
            operator_id=operator.id,
            task_blueprint_id=task.id,
            last_route_instance_id=None,
            last_route_resolved_at=None,
            default_cwd=_normalize_path(task.cwd) or project.path or instance.cwd,
            model=task.model,
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
        )
        return True

    def _default_route_binding_mode(self, setup_mode: SetupMode) -> GatewayRouteBindingMode:
        if self.launch_routing is not None:
            return self.launch_routing.default_gateway_route_binding_mode(setup_mode)
        return "workspace_affinity" if setup_mode == "remote" else "saved_lane"

    def _resolve_route_binding_mode(
        self,
        row: dict,
        *,
        setup_mode: SetupMode,
    ) -> GatewayRouteBindingMode:
        value = str(row.get("route_binding_mode") or "").strip().lower()
        if value == "workspace_affinity":
            return "workspace_affinity"
        if value == "saved_lane":
            return "saved_lane"
        return self._default_route_binding_mode(setup_mode)

    def _summarize_launch_defaults(
        self,
        row: dict,
        *,
        preferred_memory_provider: str | None = None,
        preferred_executor: str | None = None,
    ) -> str:
        clauses = [
            f"{str(row.get('setup_mode') or 'local')} mode",
            f"{str(row.get('setup_flow') or 'quickstart')} flow",
        ]
        if preferred_memory_provider:
            clauses.append(f"memory {memory_provider_label(preferred_memory_provider)}")
        if preferred_executor:
            clauses.append(f"executor {executor_label(preferred_executor)}")
        clauses.extend(
            [
                "verification on" if bool(row["run_verification"]) else "verification off",
                "built-in agents on" if bool(row["use_builtin_agents"]) else "built-in agents off",
                "auto-commit on" if bool(row["auto_commit"]) else "auto-commit off",
                "pause on approvals"
                if bool(row["pause_on_approval"])
                else "approval pause disabled",
            ]
        )
        if bool(row["auto_recover"]):
            clauses.append(f"auto-recover x{int(row['auto_recover_limit'])}")
        if bool(row["allow_failover"]):
            clauses.append("failover armed")
        max_turns = row.get("max_turns")
        if max_turns is not None:
            clauses.append(f"max {int(max_turns)} turns")
        toolsets = [
            str(toolset).strip() for toolset in row.get("toolsets", []) if str(toolset).strip()
        ]
        if toolsets:
            preview = ", ".join(toolsets[:4])
            if len(toolsets) > 4:
                preview += f", +{len(toolsets) - 4} more"
            clauses.append(f"Hermes toolsets {preview}")
        visible_clause_count = 9 if preferred_memory_provider or preferred_executor else 7
        return ", ".join(clauses[:visible_clause_count]) + "."
