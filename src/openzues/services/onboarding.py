from __future__ import annotations

import re
from pathlib import Path

from openzues.database import Database
from openzues.schemas import (
    IntegrationCreate,
    OnboardingBootstrapCreate,
    OnboardingBootstrapResourceView,
    OnboardingBootstrapResultView,
    OperatorCreate,
    SkillPinCreate,
    TaskBlueprintCreate,
    TeamCreate,
    VaultSecretCreate,
)
from openzues.services.access import AccessService
from openzues.services.device_bootstrap_profile import (
    default_device_bootstrap_profile,
    normalize_device_bootstrap_profile,
)
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import (
    MEMPALACE_MEMORY_TASK_NAME,
    MEMPALACE_MEMORY_TASK_SUMMARY,
    build_mempalace_maintenance_objective,
    is_mempalace_automation_task,
    is_mempalace_integration,
    mempalace_bootstrap_defaults,
    mempalace_maintenance_cadence_minutes,
)
from openzues.services.ops_mesh import OpsMeshService
from openzues.services.setup import SetupService


def _normalize_path(value: str) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "team"


def _resource(
    *,
    kind: str,
    identifier: int,
    label: str,
    created: bool,
    detail: str | None = None,
) -> OnboardingBootstrapResourceView:
    return OnboardingBootstrapResourceView(
        kind=kind,
        id=identifier,
        label=label,
        created=created,
        detail=detail,
    )


class OnboardingService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        access: AccessService,
        ops_mesh: OpsMeshService,
        gateway_bootstrap: GatewayBootstrapService,
        setup: SetupService,
    ) -> None:
        self.database = database
        self.manager = manager
        self.access = access
        self.ops_mesh = ops_mesh
        self.gateway_bootstrap = gateway_bootstrap
        self.setup = setup

    async def bootstrap(self, payload: OnboardingBootstrapCreate) -> OnboardingBootstrapResultView:
        payload = self._apply_integration_presets(payload)
        if payload.bootstrap_roles is None and payload.bootstrap_scopes is None:
            bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
        else:
            bootstrap_roles, bootstrap_scopes = normalize_device_bootstrap_profile(
                payload.bootstrap_roles,
                payload.bootstrap_scopes,
            )
        project_path = _normalize_path(payload.project_path)
        warnings: list[str] = []
        wizard_session_payload = {
            "mode": payload.setup_mode,
            "flow": payload.setup_flow,
            "use_mempalace": payload.use_mempalace,
            "instance_mode": payload.instance_mode,
            "instance_id": payload.instance_id,
            "instance_name": payload.instance_name,
            "project_path": project_path,
            "project_label": payload.project_label,
            "team_name": payload.team_name,
            "operator_name": payload.operator_name,
            "operator_email": payload.operator_email,
            "bootstrap_roles": bootstrap_roles,
            "bootstrap_scopes": bootstrap_scopes,
            "task_name": payload.task_name,
            "cadence_minutes": payload.cadence_minutes,
            "model": payload.model,
            "max_turns": payload.max_turns,
            "objective_template": payload.objective_template,
            "conversation_target": (
                payload.conversation_target.model_dump()
                if payload.conversation_target is not None
                else None
            ),
            "toolsets": payload.toolsets,
        }
        await self.setup.save_wizard_session(wizard_session_payload)

        instance = await self._resolve_bootstrap_instance(payload, cwd=project_path)
        project = await self._resolve_project(path=project_path, label=payload.project_label)
        team = await self._resolve_team(payload)
        operator, api_key, operator_warning = await self._resolve_operator(payload, team_id=team.id)
        if operator_warning:
            warnings.append(operator_warning)

        vault_secret = await self._resolve_vault_secret(payload)
        integration = await self._resolve_integration(
            payload,
            project_id=project.id,
            vault_secret_id=vault_secret.id if vault_secret is not None else None,
        )
        skill_pin = await self._resolve_skill_pin(payload, project_id=project.id)
        task_blueprint = await self._resolve_task_blueprint(
            payload,
            instance_id=instance.id if instance is not None else None,
            project_id=project.id,
            cwd=project_path,
        )
        memory_task_blueprint = await self._resolve_memory_task_blueprint(
            payload,
            instance_id=instance.id if instance is not None else None,
            project_id=project.id,
            project_label=project.label,
            cwd=project_path,
        )
        await self.gateway_bootstrap.save_from_onboarding(
            setup_mode=payload.setup_mode,
            setup_flow=payload.setup_flow,
            instance_id=instance.id if instance is not None else None,
            project_id=project.id,
            team_id=team.id,
            operator_id=operator.id,
            task_blueprint_id=task_blueprint.id,
            default_cwd=project_path,
            bootstrap_roles=bootstrap_roles,
            bootstrap_scopes=bootstrap_scopes,
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
            toolsets=payload.toolsets,
        )
        await self.setup.record_bootstrap_footprint(
            instance=instance,
            project=project,
            team=team,
            operator=operator,
            vault_secret=vault_secret,
            integration=integration,
            skill_pin=skill_pin,
            task_blueprint=task_blueprint,
            memory_task_blueprint=memory_task_blueprint,
        )
        wizard_session_payload.update(
            {
                "instance_mode": payload.instance_mode,
                "instance_id": instance.id if instance is not None else None,
                "instance_name": instance.label if instance is not None else payload.instance_name,
                "project_path": project_path,
                "project_label": project.label,
                "team_name": team.label,
                "operator_name": operator.label,
                "operator_email": payload.operator_email,
                "bootstrap_roles": bootstrap_roles,
                "bootstrap_scopes": bootstrap_scopes,
                "task_name": payload.task_name,
                "cadence_minutes": payload.cadence_minutes,
                "model": payload.model,
                "max_turns": payload.max_turns,
                "objective_template": payload.objective_template,
                "conversation_target": (
                    payload.conversation_target.model_dump()
                    if payload.conversation_target is not None
                    else None
                ),
                "toolsets": payload.toolsets,
            }
        )
        await self.setup.save_wizard_session(wizard_session_payload)

        if payload.setup_mode == "remote" and instance is None:
            warnings.append(
                "Remote mode staged the workspace spine without pinning a default lane."
            )
        elif instance is not None and "connected" not in (instance.detail or "").lower():
            warnings.append(
                "The bootstrap lane is saved, but the desktop bridge still needs a live "
                "connection check."
            )

        task_view = next(
            (
                task
                for task in await self.ops_mesh.list_task_blueprint_views()
                if task.id == task_blueprint.id
            ),
            None,
        )
        if task_view is None:
            raise ValueError("Bootstrap saved the task, but the launch draft could not be rebuilt.")
        mission_draft = None
        launch_route = None
        try:
            mission_draft = await self.ops_mesh.build_task_draft(task_view.id)
            mission_draft.name = f"Kick off {task_view.name}"
        except ValueError:
            warnings.append(
                "The recurring task is saved, but there is no lane available yet to generate "
                "a launch draft."
            )
        gateway_view = await self.gateway_bootstrap.get_view()
        launch_route = gateway_view.launch_route

        configured_parts = [
            "workspace",
            "operator access",
            "task loop",
        ]
        if instance is not None:
            configured_parts.insert(1, "lane")
        if vault_secret is not None:
            configured_parts.append("vault secret")
        if integration is not None:
            configured_parts.append("integration inventory")
        if skill_pin is not None:
            configured_parts.append("project skill pin")
        if memory_task_blueprint is not None:
            configured_parts.append("memory upkeep loop")

        headline = (
            "Remote setup spine is staged"
            if payload.setup_mode == "remote"
            else "QuickStart spine is staged"
        )
        if len(configured_parts) == 1:
            configured_summary = configured_parts[0]
        else:
            configured_summary = ", ".join(configured_parts[:-1]) + f", and {configured_parts[-1]}"
        if mission_draft is not None:
            summary = (
                f"Bootstrap saved the {configured_summary}. "
                "The first mission draft is ready in the composer."
            )
            next_entrypoint = "Load the launch draft, then run the first verified mission cycle."
        else:
            summary = (
                f"Bootstrap saved the {configured_summary}. "
                "Add or reconnect a lane before launching the first mission cycle."
            )
            next_entrypoint = (
                "Create or reconnect a lane, then launch the saved recurring task from the "
                "staged workspace."
            )

        return OnboardingBootstrapResultView(
            headline=headline,
            summary=summary,
            warnings=warnings,
            next_entrypoint=next_entrypoint,
            instance=instance,
            project=project,
            team=team,
            operator=operator,
            vault_secret=vault_secret,
            integration=integration,
            skill_pin=skill_pin,
            task_blueprint=task_blueprint,
            memory_task_blueprint=memory_task_blueprint,
            api_key=api_key,
            mission_draft=mission_draft,
            launch_route=launch_route,
        )

    def _apply_integration_presets(
        self, payload: OnboardingBootstrapCreate
    ) -> OnboardingBootstrapCreate:
        if not payload.use_mempalace:
            return payload
        defaults = mempalace_bootstrap_defaults()
        notes = str(payload.integration_notes or "").strip() or defaults["integration_notes"]
        auth_scheme = str(payload.integration_auth_scheme or "").strip().lower()
        if auth_scheme in {"", "token"}:
            auth_scheme = defaults["integration_auth_scheme"]
        return payload.model_copy(
            update={
                "integration_name": defaults["integration_name"],
                "integration_kind": defaults["integration_kind"],
                "integration_base_url": defaults["integration_base_url"],
                "integration_auth_scheme": auth_scheme,
                "integration_notes": notes,
            }
        )

    def _should_stage_mempalace_memory(self, payload: OnboardingBootstrapCreate) -> bool:
        if payload.use_mempalace:
            return True
        integration = {
            "name": payload.integration_name,
            "kind": payload.integration_kind,
            "base_url": payload.integration_base_url,
            "notes": payload.integration_notes,
        }
        return is_mempalace_integration(integration)

    async def _resolve_bootstrap_instance(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        cwd: str,
    ) -> OnboardingBootstrapResourceView | None:
        if payload.setup_mode == "remote":
            if payload.instance_mode != "existing":
                raise ValueError("Remote setup only supports reusing an existing saved lane.")
            if payload.instance_id is None:
                return None
        return await self._resolve_instance(payload, cwd=cwd)

    async def _resolve_instance(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        cwd: str,
    ) -> OnboardingBootstrapResourceView:
        existing_instances = await self.manager.list_views()
        if payload.instance_mode == "existing":
            instance_id = payload.instance_id
            if instance_id is None:
                raise ValueError("Select an existing lane before using existing mode.")
            runtime = await self.manager.get(instance_id)
            view = runtime.view()
            detail = "Reused existing lane."
            if view.connected:
                detail = "Reused existing connected lane."
            return _resource(
                kind="instance",
                identifier=view.id,
                label=view.name,
                created=False,
                detail=detail,
            )

        if payload.instance_mode == "create_desktop":
            runtime = await self.manager.create_instance(
                name=payload.instance_name,
                transport="desktop",
                command=None,
                args=None,
                websocket_url=None,
                cwd=cwd,
                auto_connect=False,
            )
            view = runtime.view()
            return _resource(
                kind="instance",
                identifier=view.id,
                label=view.name,
                created=True,
                detail="Created a desktop lane without connecting it yet.",
            )

        had_desktop_lane = any(instance.transport == "desktop" for instance in existing_instances)
        runtime = await self.manager.quick_connect_desktop(name=payload.instance_name, cwd=cwd)
        view = runtime.view()
        detail = (
            "Connected the desktop bridge."
            if view.connected
            else (view.error or "Created the desktop lane, but the bridge still needs attention.")
        )
        return _resource(
            kind="instance",
            identifier=view.id,
            label=view.name,
            created=not had_desktop_lane,
            detail=detail,
        )

    async def _resolve_project(
        self,
        *,
        path: str,
        label: str | None,
    ) -> OnboardingBootstrapResourceView:
        existing_projects = await self.database.list_projects()
        normalized_existing = {
            _normalize_path(str(project["path"])): project for project in existing_projects
        }
        existing = normalized_existing.get(path)
        if existing is not None:
            return _resource(
                kind="project",
                identifier=int(existing["id"]),
                label=str(existing["label"]),
                created=False,
                detail="Reused the existing workspace entry.",
            )

        resolved_label = label or Path(path).name
        project_id = await self.database.create_project(path=path, label=resolved_label)
        return _resource(
            kind="project",
            identifier=project_id,
            label=resolved_label,
            created=True,
            detail=path,
        )

    async def _resolve_team(
        self,
        payload: OnboardingBootstrapCreate,
    ) -> OnboardingBootstrapResourceView:
        teams = await self.access.list_team_views()
        requested_name = str(payload.team_name or "").strip()
        requested_slug = _slugify(payload.team_slug or requested_name) if requested_name else ""

        if requested_name:
            existing = next(
                (
                    team
                    for team in teams
                    if _normalize_text(team.name) == _normalize_text(requested_name)
                    or team.slug == requested_slug
                ),
                None,
            )
            if existing is not None:
                return _resource(
                    kind="team",
                    identifier=existing.id,
                    label=existing.name,
                    created=False,
                    detail="Reused the requested operator team.",
                )
            created = await self.access.create_team(
                TeamCreate(
                    name=requested_name,
                    slug=payload.team_slug or None,
                    description=payload.team_description,
                )
            )
            return _resource(
                kind="team",
                identifier=created.id,
                label=created.name,
                created=True,
                detail="Created a dedicated operator team for this workspace.",
            )

        if not teams:
            await self.access.initialize()
            teams = await self.access.list_team_views()
        default_team = teams[0]
        return _resource(
            kind="team",
            identifier=default_team.id,
            label=default_team.name,
            created=False,
            detail="Using the default local control team.",
        )

    async def _resolve_operator(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        team_id: int,
    ) -> tuple[OnboardingBootstrapResourceView, str | None, str | None]:
        operators = await self.access.list_operator_views()
        requested_email = _normalize_text(payload.operator_email)
        requested_name = _normalize_text(payload.operator_name)
        existing = next(
            (
                operator
                for operator in operators
                if operator.team_id == team_id
                and (
                    (requested_email and _normalize_text(operator.email) == requested_email)
                    or _normalize_text(operator.name) == requested_name
                )
            ),
            None,
        )
        if existing is not None:
            api_key: str | None = None
            warning: str | None = None
            operator_view = existing
            if payload.issue_api_key and not existing.has_api_key:
                issued = await self.access.issue_api_key(existing.id)
                operator_view = issued.operator
                api_key = issued.api_key
            elif payload.issue_api_key and existing.has_api_key:
                warning = (
                    f"Operator '{existing.name}' already has an API key, so the existing "
                    "credential was kept."
                )
            return (
                _resource(
                    kind="operator",
                    identifier=operator_view.id,
                    label=operator_view.name,
                    created=False,
                    detail="Reused the existing operator profile.",
                ),
                api_key,
                warning,
            )

        created = await self.access.create_operator(
            OperatorCreate(
                team_id=team_id,
                name=payload.operator_name,
                email=payload.operator_email,
                role=payload.operator_role,
                enabled=True,
                issue_api_key=payload.issue_api_key,
            )
        )
        detail = "Created an operator profile."
        if created.api_key:
            detail = "Created an operator profile and issued a remote API key."
        return (
            _resource(
                kind="operator",
                identifier=created.operator.id,
                label=created.operator.name,
                created=True,
                detail=detail,
            ),
            created.api_key,
            None,
        )

    async def _resolve_vault_secret(
        self,
        payload: OnboardingBootstrapCreate,
    ) -> OnboardingBootstrapResourceView | None:
        label = str(payload.vault_secret_label or "").strip()
        value = str(payload.vault_secret_value or "").strip()
        if not label and not value:
            return None
        if not label or not value:
            raise ValueError(
                "Provide both vault_secret_label and vault_secret_value, or leave both blank."
            )

        existing = next(
            (
                secret
                for secret in await self.ops_mesh.list_vault_secret_views()
                if _normalize_text(secret.label) == _normalize_text(label)
            ),
            None,
        )
        if existing is not None:
            return _resource(
                kind="vault_secret",
                identifier=existing.id,
                label=existing.label,
                created=False,
                detail="Reused the existing vault secret label.",
            )

        created = await self.ops_mesh.create_vault_secret(
            VaultSecretCreate(
                label=label,
                value=value,
                kind=payload.vault_secret_kind,
                notes=payload.vault_secret_notes,
            )
        )
        return _resource(
            kind="vault_secret",
            identifier=created.id,
            label=created.label,
            created=True,
            detail="Stored the credential in the vault.",
        )

    async def _resolve_integration(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        project_id: int,
        vault_secret_id: int | None,
    ) -> OnboardingBootstrapResourceView | None:
        name = str(payload.integration_name or "").strip()
        kind = str(payload.integration_kind or "").strip()
        base_url = str(payload.integration_base_url or "").strip() or None

        if not name and not kind and not base_url:
            return None
        if not name or not kind:
            raise ValueError(
                "Provide both integration_name and integration_kind, or leave both blank."
            )

        integrations = await self.ops_mesh.list_integration_views()
        existing = next(
            (
                integration
                for integration in integrations
                if integration.project_id == project_id
                and _normalize_text(integration.name) == _normalize_text(name)
                and _normalize_text(integration.kind) == _normalize_text(kind)
            ),
            None,
        )
        if existing is not None:
            await self.database.update_integration(
                existing.id,
                base_url=base_url,
                auth_scheme=payload.integration_auth_scheme,
                vault_secret_id=vault_secret_id,
                secret_label=payload.vault_secret_label,
                notes=payload.integration_notes,
                enabled=1,
            )
            return _resource(
                kind="integration",
                identifier=existing.id,
                label=existing.name,
                created=False,
                detail="Updated the existing integration attachment.",
            )

        created = await self.ops_mesh.create_integration(
            IntegrationCreate(
                name=name,
                kind=kind,
                project_id=project_id,
                base_url=base_url,
                auth_scheme=payload.integration_auth_scheme,
                vault_secret_id=vault_secret_id,
                secret_label=payload.vault_secret_label,
                secret_value=None,
                notes=payload.integration_notes,
                enabled=True,
            )
        )
        return _resource(
            kind="integration",
            identifier=created.id,
            label=created.name,
            created=True,
            detail="Registered the first tracked integration.",
        )

    async def _resolve_skill_pin(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        project_id: int,
    ) -> OnboardingBootstrapResourceView | None:
        name = str(payload.skill_name or "").strip()
        prompt_hint = str(payload.skill_prompt_hint or "").strip()
        source = str(payload.skill_source or "").strip() or None

        if not name and not prompt_hint and source is None:
            return None
        if not name or not prompt_hint:
            raise ValueError("Provide both skill_name and skill_prompt_hint, or leave both blank.")

        skill_pins = await self.ops_mesh.list_skill_pin_views()
        existing = next(
            (
                skill
                for skill in skill_pins
                if skill.project_id == project_id
                and _normalize_text(skill.name) == _normalize_text(name)
                and _normalize_text(skill.source) == _normalize_text(source)
            ),
            None,
        )
        if existing is not None:
            return _resource(
                kind="skill_pin",
                identifier=existing.id,
                label=existing.name,
                created=False,
                detail="Reused the existing project skill pin.",
            )

        created = await self.ops_mesh.create_skill_pin(
            SkillPinCreate(
                project_id=project_id,
                name=name,
                prompt_hint=prompt_hint,
                source=source,
                enabled=True,
            )
        )
        return _resource(
            kind="skill_pin",
            identifier=created.id,
            label=created.name,
            created=True,
            detail="Pinned a project-specific skill for future runs.",
        )

    async def _resolve_task_blueprint(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        instance_id: int | None,
        project_id: int,
        cwd: str,
    ) -> OnboardingBootstrapResourceView:
        existing_tasks = await self.database.list_task_blueprints()
        existing = next(
            (
                task
                for task in existing_tasks
                if int(task.get("project_id") or -1) == project_id
                and (int(task["instance_id"]) if task.get("instance_id") is not None else None)
                == instance_id
                and _normalize_text(str(task.get("name") or ""))
                == _normalize_text(payload.task_name)
            ),
            None,
        )

        task_payload = TaskBlueprintCreate(
            name=payload.task_name,
            summary=payload.task_summary,
            objective_template=payload.objective_template,
            conversation_target=payload.conversation_target,
            instance_id=instance_id,
            project_id=project_id,
            cadence_minutes=payload.cadence_minutes,
            run_until_complete=False,
            continuation_cooldown_minutes=10,
            completion_marker=payload.completion_marker,
            cwd=cwd,
            model=payload.model,
            reasoning_effort=None,
            collaboration_mode=None,
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
            toolsets=payload.toolsets,
            enabled=payload.enabled,
        )
        if existing is None:
            created = await self.ops_mesh.create_task_blueprint(task_payload)
            return _resource(
                kind="task_blueprint",
                identifier=created.id,
                label=created.name,
                created=True,
                detail=f"Scheduled every {payload.cadence_minutes} minutes.",
            )

        await self.database.update_task_blueprint(
            int(existing["id"]),
            name=payload.task_name,
            summary=payload.task_summary,
            project_id=project_id,
            instance_id=instance_id,
            cadence_minutes=payload.cadence_minutes,
            enabled=int(payload.enabled),
        )
        await self.database.update_task_blueprint_payload(
            int(existing["id"]),
            objective_template=payload.objective_template,
            conversation_target=(
                payload.conversation_target.model_dump()
                if payload.conversation_target is not None
                else None
            ),
            run_until_complete=False,
            continuation_cooldown_minutes=10,
            completion_marker=payload.completion_marker,
            cwd=cwd,
            model=payload.model,
            reasoning_effort=None,
            collaboration_mode=None,
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
            toolsets=payload.toolsets,
        )
        return _resource(
            kind="task_blueprint",
            identifier=int(existing["id"]),
            label=str(existing["name"]),
            created=False,
            detail=f"Updated the recurring task to run every {payload.cadence_minutes} minutes.",
        )

    async def _resolve_memory_task_blueprint(
        self,
        payload: OnboardingBootstrapCreate,
        *,
        instance_id: int | None,
        project_id: int,
        project_label: str,
        cwd: str,
    ) -> OnboardingBootstrapResourceView | None:
        if not self._should_stage_mempalace_memory(payload):
            return None

        cadence_minutes = mempalace_maintenance_cadence_minutes(payload.cadence_minutes)
        max_turns = min(payload.max_turns or 2, 2)
        objective_template = build_mempalace_maintenance_objective(
            project_label=project_label,
            project_path=cwd,
        )
        existing_tasks = await self.database.list_task_blueprints()
        existing = next(
            (
                task
                for task in existing_tasks
                if int(task.get("project_id") or -1) == project_id
                and is_mempalace_automation_task(task)
            ),
            None,
        )

        task_payload = TaskBlueprintCreate(
            name=MEMPALACE_MEMORY_TASK_NAME,
            summary=MEMPALACE_MEMORY_TASK_SUMMARY,
            objective_template=objective_template,
            instance_id=instance_id,
            project_id=project_id,
            cadence_minutes=cadence_minutes,
            run_until_complete=False,
            continuation_cooldown_minutes=10,
            completion_marker=None,
            cwd=cwd,
            model=payload.model,
            reasoning_effort=None,
            collaboration_mode=None,
            max_turns=max_turns,
            use_builtin_agents=False,
            run_verification=False,
            auto_commit=False,
            pause_on_approval=payload.pause_on_approval,
            allow_auto_reflexes=False,
            auto_recover=False,
            auto_recover_limit=0,
            reflex_cooldown_seconds=payload.reflex_cooldown_seconds,
            allow_failover=payload.allow_failover,
            toolsets=["safe", "memory", "session_search"],
            enabled=payload.enabled,
        )
        cadence_detail = (
            f"Scheduled every {cadence_minutes // 60}h to refresh durable memory."
            if cadence_minutes % 60 == 0
            else f"Scheduled every {cadence_minutes}m to refresh durable memory."
        )
        if existing is None:
            created = await self.ops_mesh.create_task_blueprint(task_payload)
            return _resource(
                kind="task_blueprint",
                identifier=created.id,
                label=created.name,
                created=True,
                detail=cadence_detail,
            )

        await self.database.update_task_blueprint(
            int(existing["id"]),
            name=MEMPALACE_MEMORY_TASK_NAME,
            summary=MEMPALACE_MEMORY_TASK_SUMMARY,
            project_id=project_id,
            instance_id=instance_id,
            cadence_minutes=cadence_minutes,
            enabled=int(payload.enabled),
        )
        await self.database.update_task_blueprint_payload(
            int(existing["id"]),
            objective_template=objective_template,
            run_until_complete=False,
            continuation_cooldown_minutes=10,
            completion_marker=None,
            cwd=cwd,
            model=payload.model,
            reasoning_effort=None,
            collaboration_mode=None,
            max_turns=max_turns,
            use_builtin_agents=False,
            run_verification=False,
            auto_commit=False,
            pause_on_approval=payload.pause_on_approval,
            allow_auto_reflexes=False,
            auto_recover=False,
            auto_recover_limit=0,
            reflex_cooldown_seconds=payload.reflex_cooldown_seconds,
            allow_failover=payload.allow_failover,
            toolsets=["safe", "memory", "session_search"],
        )
        return _resource(
            kind="task_blueprint",
            identifier=int(existing["id"]),
            label=MEMPALACE_MEMORY_TASK_NAME,
            created=False,
            detail=f"Updated the MemPalace upkeep loop. {cadence_detail}",
        )
