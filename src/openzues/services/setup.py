from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    GatewayBootstrapResourceView,
    OnboardingBootstrapResourceView,
    SetupFlow,
    SetupFootprintView,
    SetupLaunchHandoffAction,
    SetupLaunchHandoffStatus,
    SetupLaunchHandoffView,
    SetupMode,
    SetupRecommendedAction,
    SetupResetResultView,
    SetupResetScope,
    SetupStatusView,
    SetupWizardProbeView,
    SetupWizardSessionUpdate,
    SetupWizardSessionView,
    TaskBlueprintView,
)
from openzues.services.access import AccessService
from openzues.services.device_bootstrap_profile import normalize_device_bootstrap_profile
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.manager import RuntimeManager
from openzues.services.ops_mesh import OpsMeshService


def _footprint_resource(
    resource: OnboardingBootstrapResourceView | dict[str, Any] | None,
) -> dict[str, Any] | None:
    if resource is None:
        return None
    if isinstance(resource, OnboardingBootstrapResourceView):
        return {
            "kind": resource.kind,
            "id": resource.id,
            "label": resource.label,
            "created": resource.created,
        }
    return {
        "kind": str(resource["kind"]),
        "id": int(resource["id"]),
        "label": str(resource["label"]),
        "created": bool(resource.get("created", False)),
    }


def _normalize_path(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return str(Path(text).expanduser().resolve(strict=False))


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_LIGHTWEIGHT_SETUP_WIZARD_SELECTION_FIELDS = frozenset({"mode", "flow", "use_mempalace"})
_DEFAULT_SETUP_INSTANCE_MODE = "quick_connect_desktop"
_DEFAULT_SETUP_INSTANCE_NAME = "Local Codex Desktop"
_DEFAULT_SETUP_CADENCE_MINUTES = 180
_DEFAULT_SETUP_MODEL = "gpt-5.4"
_DEFAULT_SETUP_MAX_TURNS = 4


def _has_substantive_setup_wizard_state(payload: dict[str, Any]) -> bool:
    if _normalize_path(_text_or_none(payload.get("project_path"))) is not None:
        return True
    if _text_or_none(payload.get("project_label")) is not None:
        return True

    instance_id = payload.get("instance_id")
    if instance_id is not None:
        return True
    instance_mode = _text_or_none(payload.get("instance_mode"))
    if instance_mode is not None and instance_mode != _DEFAULT_SETUP_INSTANCE_MODE:
        if instance_mode != "existing":
            return True
        if _text_or_none(payload.get("instance_name")) not in {None, _DEFAULT_SETUP_INSTANCE_NAME}:
            return True
    instance_name = _text_or_none(payload.get("instance_name"))
    if instance_name is not None and instance_name != _DEFAULT_SETUP_INSTANCE_NAME:
        return True

    for field in ("team_name", "operator_name", "operator_email", "task_name"):
        if _text_or_none(payload.get(field)) is not None:
            return True

    bootstrap_roles = payload.get("bootstrap_roles")
    if isinstance(bootstrap_roles, list) and bootstrap_roles:
        return True
    bootstrap_scopes = payload.get("bootstrap_scopes")
    if isinstance(bootstrap_scopes, list) and bootstrap_scopes:
        return True

    cadence_minutes = payload.get("cadence_minutes")
    if cadence_minutes is not None and int(cadence_minutes) != _DEFAULT_SETUP_CADENCE_MINUTES:
        return True
    model = _text_or_none(payload.get("model"))
    if model is not None and model != _DEFAULT_SETUP_MODEL:
        return True
    max_turns = payload.get("max_turns")
    if max_turns is not None and int(max_turns) != _DEFAULT_SETUP_MAX_TURNS:
        return True

    if _text_or_none(payload.get("objective_template")) is not None:
        return True
    if payload.get("conversation_target") is not None:
        return True
    toolsets = payload.get("toolsets")
    if isinstance(toolsets, list) and toolsets:
        return True

    return False


def _filter_lightweight_setup_wizard_update(
    current: dict[str, Any],
    update_payload: dict[str, Any],
) -> dict[str, Any]:
    if not update_payload:
        return update_payload
    if set(update_payload).difference(_LIGHTWEIGHT_SETUP_WIZARD_SELECTION_FIELDS):
        return update_payload
    if _has_substantive_setup_wizard_state(current):
        return update_payload

    filtered: dict[str, Any] = {}
    if "use_mempalace" in update_payload:
        use_mempalace = bool(update_payload.get("use_mempalace"))
        if use_mempalace or bool(current.get("use_mempalace")):
            filtered["use_mempalace"] = use_mempalace
    return filtered


DEFAULT_SETUP_OBJECTIVE_TEMPLATE = (
    "Inspect the workspace, ship the next verified slice, run the relevant checks, "
    "and leave a concise operator handoff: completed, verified, next step, blockers."
)


class SetupService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        access: AccessService,
        gateway_bootstrap: GatewayBootstrapService,
        ops_mesh: OpsMeshService | None = None,
    ) -> None:
        self.database = database
        self.manager = manager
        self.access = access
        self.gateway_bootstrap = gateway_bootstrap
        self.ops_mesh = ops_mesh

    async def record_bootstrap_footprint(
        self,
        *,
        instance: OnboardingBootstrapResourceView | None,
        project: OnboardingBootstrapResourceView,
        team: OnboardingBootstrapResourceView,
        operator: OnboardingBootstrapResourceView,
        vault_secret: OnboardingBootstrapResourceView | None,
        integration: OnboardingBootstrapResourceView | None,
        skill_pin: OnboardingBootstrapResourceView | None,
        task_blueprint: OnboardingBootstrapResourceView,
        memory_task_blueprint: OnboardingBootstrapResourceView | None,
    ) -> None:
        await self.database.upsert_setup_footprint(
            {
                "instance": _footprint_resource(instance),
                "project": _footprint_resource(project),
                "team": _footprint_resource(team),
                "operator": _footprint_resource(operator),
                "vault_secret": _footprint_resource(vault_secret),
                "integration": _footprint_resource(integration),
                "skill_pin": _footprint_resource(skill_pin),
                "task_blueprint": _footprint_resource(task_blueprint),
                "memory_task_blueprint": _footprint_resource(memory_task_blueprint),
                "updated_at": utcnow(),
            }
        )

    async def get_wizard_session(self) -> SetupWizardSessionView:
        gateway = await self.gateway_bootstrap.get_view()
        instances = await self.manager.list_views()
        teams = await self.access.list_team_views()
        operators = await self.access.list_operator_views()
        stored = await self._load_wizard_session_payload()

        connected_count = sum(1 for instance in instances if instance.connected)
        local_probe = self._build_local_probe(
            connected_count=connected_count, instance_count=len(instances)
        )
        remote_probe = self._build_remote_probe(team_count=len(teams), operators=operators)
        recommended_mode = self._recommended_mode(
            gateway_mode=gateway.setup_mode,
            local_probe=local_probe,
            remote_probe=remote_probe,
        )
        recommended_flow: SetupFlow = "advanced" if recommended_mode == "remote" else "quickstart"
        mode = str(stored.get("mode") or gateway.setup_mode or recommended_mode)
        if mode not in {"local", "remote"}:
            mode = recommended_mode
        flow = str(stored.get("flow") or gateway.setup_flow or recommended_flow)
        if flow not in {"quickstart", "advanced"}:
            flow = recommended_flow
        if mode == "remote" and flow == "quickstart":
            flow = "advanced"

        warnings: list[str] = []
        if mode == "remote" and connected_count == 0:
            warnings.append(
                "Remote mode can stage workspace and operator access now, "
                "but the first launch still needs a saved lane."
            )
        if mode == "remote" and remote_probe.status != "ready":
            warnings.append("Remote mode is selected, but no active operator API key is armed yet.")

        if mode == "remote":
            status = "ready" if remote_probe.status == "ready" else "staged"
            headline = (
                "Remote setup posture is armed"
                if status == "ready"
                else "Remote setup posture is being staged"
            )
            summary = (
                "Remote-first setup keeps the recurring task and workspace "
                "spine ready while leaving lane binding flexible."
                if status == "ready"
                else "Stage remote ingress first, then bind or add a lane "
                "when you are ready to launch work."
            )
            instance_mode = "existing"
        else:
            status = "ready" if local_probe.status == "ready" else "staged"
            headline = (
                "Local setup posture is armed"
                if status == "ready"
                else "Local setup posture is being staged"
            )
            summary = (
                "QuickStart can reuse the local control plane and tighten "
                "the saved workspace spine."
                if status == "ready"
                else "Local mode is ready to create or quick-connect a lane, "
                "then save the first recurring task."
            )
            instance_mode = str(stored.get("instance_mode") or "quick_connect_desktop")
            if instance_mode not in {"quick_connect_desktop", "create_desktop", "existing"}:
                instance_mode = "quick_connect_desktop"

        updated_at = stored.get("updated_at")
        conversation_target = stored.get("conversation_target")
        if (
            conversation_target is None
            and gateway.launch_route is not None
            and gateway.launch_route.conversation_target is not None
        ):
            conversation_target = gateway.launch_route.conversation_target.model_dump()

        payload = {
            "status": status,
            "headline": headline,
            "summary": summary,
            "warnings": warnings,
            "mode": mode,
            "flow": flow,
            "use_mempalace": bool(stored.get("use_mempalace", False)),
            "recommended_mode": recommended_mode,
            "recommended_flow": recommended_flow,
            "instance_mode": instance_mode,
            "instance_id": stored.get("instance_id"),
            "instance_name": stored.get("instance_name") or "Local Codex Desktop",
            "project_path": stored.get("project_path"),
            "project_label": stored.get("project_label"),
            "team_name": stored.get("team_name"),
            "operator_name": stored.get("operator_name"),
            "operator_email": stored.get("operator_email"),
            "bootstrap_roles": None,
            "bootstrap_scopes": None,
            "task_name": stored.get("task_name"),
            "cadence_minutes": int(stored.get("cadence_minutes") or 180),
            "model": stored.get("model") or "gpt-5.4",
            "max_turns": stored.get("max_turns", 4),
            "objective_template": stored.get("objective_template")
            or DEFAULT_SETUP_OBJECTIVE_TEMPLATE,
            "conversation_target": conversation_target,
            "toolsets": stored.get("toolsets") or gateway.toolsets,
            "local_probe": local_probe,
            "remote_probe": remote_probe,
            "updated_at": updated_at,
        }
        payload["project_path"] = _normalize_path(payload["project_path"])
        bootstrap_roles, bootstrap_scopes = normalize_device_bootstrap_profile(
            stored.get("bootstrap_roles")
            if "bootstrap_roles" in stored
            else gateway.bootstrap_roles,
            stored.get("bootstrap_scopes")
            if "bootstrap_scopes" in stored
            else gateway.bootstrap_scopes,
        )
        payload["bootstrap_roles"] = bootstrap_roles
        payload["bootstrap_scopes"] = bootstrap_scopes
        return SetupWizardSessionView.model_validate(payload)

    async def save_wizard_session(
        self,
        payload: SetupWizardSessionUpdate | dict[str, Any],
    ) -> SetupWizardSessionView:
        current = await self._load_wizard_session_payload()
        if isinstance(payload, SetupWizardSessionUpdate):
            update_payload = {
                key: getattr(payload, key)
                for key in payload.model_fields_set
            }
        else:
            update_payload = dict(payload)
        update_payload = _filter_lightweight_setup_wizard_update(current, update_payload)
        if not update_payload:
            return await self.get_wizard_session()
        merged = {**current, **update_payload, "updated_at": utcnow()}
        mode = str(merged.get("mode") or "local")
        if mode not in {"local", "remote"}:
            mode = "local"
        merged["mode"] = mode
        flow = str(merged.get("flow") or ("advanced" if mode == "remote" else "quickstart"))
        if flow not in {"quickstart", "advanced"}:
            flow = "advanced" if mode == "remote" else "quickstart"
        previous_mode = _text_or_none(current.get("mode")) or "local"
        mode_changed_to_remote = mode == "remote" and previous_mode != "remote"
        if mode == "remote":
            flow = "advanced"
            merged["instance_mode"] = "existing"
            if mode_changed_to_remote and "instance_id" not in update_payload:
                merged["instance_id"] = None
            if mode_changed_to_remote and "instance_name" not in update_payload:
                merged["instance_name"] = _DEFAULT_SETUP_INSTANCE_NAME
        merged["flow"] = flow
        merged["project_path"] = _normalize_path(
            merged.get("project_path") if isinstance(merged.get("project_path"), str) else None
        )
        bootstrap_roles, bootstrap_scopes = normalize_device_bootstrap_profile(
            merged.get("bootstrap_roles"),
            merged.get("bootstrap_scopes"),
        )
        merged["bootstrap_roles"] = bootstrap_roles
        merged["bootstrap_scopes"] = bootstrap_scopes
        await self.database.upsert_setup_wizard_session(merged)
        return await self.get_wizard_session()

    async def load_wizard_session_payload(self) -> dict[str, Any]:
        return await self._load_wizard_session_payload()

    async def inspect(self) -> SetupStatusView:
        gateway = await self.gateway_bootstrap.get_view()
        footprint = await self._load_footprint()
        wizard_session = await self.get_wizard_session()
        warnings = list(gateway.warnings)

        recommended_action: SetupRecommendedAction
        available_actions: list[SetupRecommendedAction]
        if gateway.status == "ready":
            headline = "Setup posture is reusable"
            summary = (
                "The saved lane, workspace, remote operator, and recurring task are aligned. "
                "Keep the current defaults, rerun bootstrap to modify them, or reset with scope."
            )
            recommended_action = "keep"
            available_actions = ["keep", "modify", "reset"]
            next_entrypoint = (
                "Launch the saved recurring task or start the next mission from the default "
                "workspace."
            )
        elif gateway.status in {"staged", "degraded"}:
            headline = "Setup posture needs one more pass"
            summary = (
                "OpenZues has saved setup state, but the connection posture, remote access, or "
                "default references still need attention before the spine is fully reusable."
            )
            recommended_action = "modify"
            available_actions = ["keep", "modify", "reset"]
            if gateway.setup_mode == "remote":
                next_entrypoint = (
                    "Reissue remote access if needed, save or reconnect a "
                    "lane, then rerun bootstrap "
                    "with the remote posture you want to keep."
                )
            else:
                next_entrypoint = (
                    "Reconnect the default lane, reissue remote access if "
                    "needed, or rerun bootstrap "
                    "with corrected defaults."
                )
        elif footprint is not None:
            headline = "Setup can be re-entered"
            summary = (
                "The active gateway profile is clear, but the last bootstrap footprint is still "
                "known. You can rerun bootstrap to modify it or fully reset the managed resources."
            )
            recommended_action = "modify"
            available_actions = ["modify", "reset"]
            next_entrypoint = (
                "Run `openzues setup bootstrap ...` to restage the launch profile, or "
                "`openzues setup reset --scope full` to clear the last managed spine."
            )
        else:
            headline = "Setup has not been initialized"
            summary = (
                "No saved gateway profile or setup footprint exists yet. Bootstrap the first "
                "lane, workspace, remote operator, and recurring task."
            )
            recommended_action = "bootstrap"
            available_actions = ["bootstrap"]
            next_entrypoint = (
                "Run `openzues setup bootstrap ...` or use the QuickStart panel in the dashboard."
            )

        handoff_summary = self._build_handoff_summary(gateway)
        launch_handoff = await self.get_launch_handoff(gateway=gateway)
        return SetupStatusView(
            headline=headline,
            summary=summary,
            recommended_action=recommended_action,
            available_actions=available_actions,
            warnings=warnings,
            next_entrypoint=next_entrypoint,
            handoff_summary=handoff_summary,
            launch_handoff=launch_handoff,
            gateway_bootstrap=gateway,
            wizard_session=wizard_session,
            footprint=footprint,
        )

    async def get_launch_handoff(
        self,
        *,
        gateway=None,
    ) -> SetupLaunchHandoffView:
        active_gateway = gateway or await self.gateway_bootstrap.get_view()
        instances = {instance.id: instance for instance in await self.manager.list_views()}
        operators = {operator.id: operator for operator in await self.access.list_operator_views()}
        warnings = list(active_gateway.warnings)
        mission_draft = None
        draft_instance = None
        launch_route = active_gateway.launch_route
        task_blueprint: TaskBlueprintView | None = None

        if active_gateway.task_blueprint is not None:
            raw_task = await self.database.get_task_blueprint(active_gateway.task_blueprint.id)
            if raw_task is None:
                warnings.append("The saved recurring task no longer exists.")
            else:
                task_blueprint = TaskBlueprintView.model_validate(raw_task)

        if task_blueprint is not None and self.ops_mesh is not None:
            try:
                if self.ops_mesh.launch_routing is not None:
                    launch_route = await self.ops_mesh.launch_routing.describe(task=task_blueprint)
                mission_draft = await self.ops_mesh.build_task_draft(task_blueprint.id)
                if (
                    mission_draft.thread_id is None
                    and launch_route is not None
                    and launch_route.conversation_reuse is not None
                    and launch_route.conversation_reuse.reusable
                    and launch_route.conversation_reuse.thread_id is not None
                ):
                    mission_draft = mission_draft.model_copy(
                        update={"thread_id": launch_route.conversation_reuse.thread_id}
                    )
                draft_instance = instances.get(mission_draft.instance_id)
            except ValueError:
                warnings.append("No lane is available yet to materialize the saved launch draft.")

        instance_resource = active_gateway.instance
        if draft_instance is not None:
            detail = "Connected lane selected for the saved launch draft."
            if not draft_instance.connected:
                detail = "Saved launch draft is targeting a lane that still needs reconnection."
            instance_resource = GatewayBootstrapResourceView(
                id=draft_instance.id,
                label=draft_instance.name,
                detail=detail,
                connected=draft_instance.connected,
            )

        operator_view = (
            operators.get(active_gateway.operator.id)
            if active_gateway.operator is not None
            else None
        )
        operator_has_key = bool(operator_view and operator_view.has_api_key)
        connected_lane_count = sum(1 for instance in instances.values() if instance.connected)

        status: SetupLaunchHandoffStatus
        recommended_action: SetupLaunchHandoffAction
        action_label: str
        headline: str
        summary: str
        next_entrypoint: str

        if active_gateway.status == "unconfigured":
            status = "bootstrap"
            recommended_action = "bootstrap"
            action_label = "Run bootstrap"
            headline = "No saved launch handoff yet"
            summary = (
                "Bootstrap the workspace, operator access, and recurring task once so the next "
                "autonomous cycle can reload a durable launch draft."
            )
            next_entrypoint = (
                "Run `openzues setup bootstrap ...` or use the QuickStart panel in the dashboard."
            )
        elif active_gateway.task_blueprint is None:
            status = "repair" if active_gateway.status == "degraded" else "staged"
            recommended_action = "restage_setup"
            action_label = "Restage setup"
            headline = "Saved launch handoff needs one repair pass"
            summary = (
                "OpenZues still has part of the saved setup spine, but the recurring task "
                "reference is missing and needs to be restaged before launch can resume."
            )
            next_entrypoint = (
                "Rerun bootstrap to recreate or rebind the saved recurring task, then inspect "
                "setup again."
            )
        elif active_gateway.status == "ready" and mission_draft is not None:
            status = "ready"
            recommended_action = "load_draft"
            action_label = "Load launch draft"
            headline = "Saved launch handoff is ready"
            if active_gateway.setup_mode == "remote":
                summary = (
                    "The recurring task, remote operator, and workspace defaults are aligned. "
                    "OpenZues can hand the next mission cycle a concrete draft immediately."
                )
            else:
                summary = (
                    "The saved lane, remote operator, and recurring task are aligned behind one "
                    "reusable launch draft."
                )
            next_entrypoint = (
                "Load the saved launch draft, then run the next verified mission cycle."
            )
        else:
            status = "repair" if active_gateway.status == "degraded" else "staged"
            if active_gateway.setup_mode == "remote":
                if connected_lane_count == 0:
                    recommended_action = "connect_lane"
                    action_label = "Connect a lane"
                    headline = "Saved launch handoff is staged"
                    summary = (
                        "The remote-first setup spine is saved, but the next cycle still needs an "
                        "available lane before launch can be trusted."
                    )
                    next_entrypoint = (
                        "Connect or quick-connect a lane, then load the saved launch draft."
                        if mission_draft is not None
                        else "Connect or quick-connect a lane, then restage the saved task."
                    )
                elif not operator_has_key:
                    recommended_action = "repair_access"
                    action_label = "Repair remote access"
                    headline = "Saved launch handoff needs remote access repair"
                    summary = (
                        "The task spine is present, but the saved operator no longer has an active "
                        "API key for remote-first launches."
                    )
                    next_entrypoint = (
                        "Reissue the operator API key, then load the saved launch draft."
                        if mission_draft is not None
                        else "Reissue the operator API key, then recheck the saved launch posture."
                    )
                else:
                    recommended_action = "restage_setup"
                    action_label = "Restage setup"
                    headline = "Saved launch handoff needs one repair pass"
                    summary = (
                        "OpenZues still knows the remote-first task spine, but one or more saved "
                        "references need repair before the next cycle should trust it."
                    )
                    next_entrypoint = (
                        "Rerun bootstrap with the remote posture you want to keep, then reload the "
                        "saved launch draft."
                    )
            else:
                instance_connected = bool(instance_resource and instance_resource.connected)
                if not instance_connected:
                    recommended_action = "connect_lane"
                    action_label = "Reconnect lane"
                    headline = "Saved launch handoff is staged"
                    summary = (
                        "The recurring task draft is ready to reload, but the default local lane "
                        "still needs to reconnect before the next cycle can launch safely."
                    )
                    next_entrypoint = (
                        "Reconnect the saved lane, then load the saved launch draft."
                        if mission_draft is not None
                        else "Reconnect the saved lane, then restage the setup profile."
                    )
                elif not operator_has_key:
                    recommended_action = "repair_access"
                    action_label = "Repair remote access"
                    headline = "Saved launch handoff needs remote access repair"
                    summary = (
                        "The local launch spine is saved, but the default operator no longer has "
                        "an active API key for approvals or remote follow-through."
                    )
                    next_entrypoint = (
                        "Reissue the operator API key, then load the saved launch draft."
                        if mission_draft is not None
                        else "Reissue the operator API key, then inspect setup again."
                    )
                else:
                    recommended_action = "restage_setup"
                    action_label = "Restage setup"
                    headline = "Saved launch handoff needs one repair pass"
                    summary = (
                        "OpenZues still has the saved task spine, but the default references need "
                        "a repair pass before the next cycle should trust the launch defaults."
                    )
                    next_entrypoint = (
                        "Rerun bootstrap with corrected defaults, then reload "
                        "the saved launch draft."
                    )

        return SetupLaunchHandoffView(
            status=status,
            headline=headline,
            summary=summary,
            recommended_action=recommended_action,
            action_label=action_label,
            warnings=warnings,
            next_entrypoint=next_entrypoint,
            instance=instance_resource,
            project=active_gateway.project,
            operator=active_gateway.operator,
            task_blueprint=active_gateway.task_blueprint,
            mission_draft=mission_draft,
            launch_route=launch_route,
        )

    async def reset(self, scope: SetupResetScope) -> SetupResetResultView:
        footprint = await self._load_footprint()
        gateway_row = await self.database.get_gateway_bootstrap()
        cleared: list[str] = []
        preserved: list[str] = []
        warnings: list[str] = []

        if gateway_row is not None:
            await self.database.clear_gateway_bootstrap()
            cleared.append("gateway bootstrap profile")
        else:
            preserved.append("gateway bootstrap profile was already clear")

        instance_id = self._preferred_id("instance", footprint=footprint, gateway_row=gateway_row)
        operator_id = self._preferred_id("operator", footprint=footprint, gateway_row=gateway_row)

        if scope in {"config+creds+sessions", "full"}:
            wizard_session = await self.database.get_setup_wizard_session()
            if wizard_session is not None:
                await self.database.clear_setup_wizard_session()
                cleared.append("setup wizard session")
            if operator_id is not None:
                operator = await self.database.get_operator(operator_id)
                if operator is not None and operator.get("api_key_hash"):
                    await self.access.revoke_api_key(operator_id)
                    cleared.append("operator API key")
                else:
                    preserved.append("operator API key was already clear")

            if instance_id is not None:
                await self.database.clear_server_requests_for_instance(instance_id)
                cleared.append("instance approval/session requests")
                try:
                    await self.manager.disconnect_instance(instance_id)
                    cleared.append("live lane session")
                except KeyError:
                    preserved.append("live lane session was already absent")

        if scope == "full":
            if footprint is None:
                warnings.append(
                    "No setup footprint was recorded yet, so the full reset only cleared the "
                    "saved profile and any active credentials or sessions."
                )
            else:
                await self._reset_full(
                    footprint=footprint,
                    cleared=cleared,
                    preserved=preserved,
                    warnings=warnings,
                )
            await self.database.clear_setup_footprint()
            cleared.append("setup footprint")
        elif footprint is not None:
            preserved.append("setup footprint kept for future modify/reset guidance")

        setup = await self.inspect()
        return SetupResetResultView(
            headline="Setup reset completed",
            summary=(
                "The requested setup scope has been cleared. Inspect the new posture before "
                "restaging bootstrap defaults."
            ),
            scope=scope,
            warnings=warnings,
            cleared=cleared,
            preserved=preserved,
            setup=setup,
        )

    async def _load_footprint(self) -> SetupFootprintView | None:
        row = await self.database.get_setup_footprint()
        if row is None:
            return None
        payload = dict(row["footprint"])
        updated_at = payload.get("updated_at")
        if isinstance(updated_at, str):
            payload["updated_at"] = datetime.fromisoformat(updated_at)
        return SetupFootprintView.model_validate(payload)

    def _preferred_id(
        self,
        kind: str,
        *,
        footprint: SetupFootprintView | None,
        gateway_row: dict[str, Any] | None,
    ) -> int | None:
        gateway_key = {
            "instance": "preferred_instance_id",
            "project": "preferred_project_id",
            "team": "team_id",
            "operator": "operator_id",
            "task_blueprint": "task_blueprint_id",
        }.get(kind)
        if gateway_row is not None and gateway_key is not None and gateway_row.get(gateway_key):
            return int(gateway_row[gateway_key])
        if footprint is None:
            return None
        resource = getattr(footprint, kind, None)
        return resource.id if resource is not None else None

    def _build_handoff_summary(self, gateway) -> str:
        parts = [gateway.launch_defaults_summary]
        parts.append(f"mode: {gateway.setup_mode}")
        if gateway.project is not None:
            parts.append(f"workspace: {gateway.project.label}")
        if gateway.instance is not None:
            connection = "connected" if gateway.instance.connected else "not connected"
            parts.append(f"lane: {gateway.instance.label} ({connection})")
        if gateway.operator is not None:
            parts.append(f"operator: {gateway.operator.label}")
        if gateway.task_blueprint is not None:
            parts.append(f"task: {gateway.task_blueprint.label}")
        return "Saved setup handoff: " + "; ".join(parts)

    async def _load_wizard_session_payload(self) -> dict[str, Any]:
        row = await self.database.get_setup_wizard_session()
        if row is None:
            return {}
        payload = dict(row["session"])
        updated_at = payload.get("updated_at")
        if isinstance(updated_at, datetime):
            payload["updated_at"] = updated_at.isoformat()
        return payload

    def _build_local_probe(
        self, *, connected_count: int, instance_count: int
    ) -> SetupWizardProbeView:
        if connected_count > 0:
            lane_label = f"lane{'s' if connected_count != 1 else ''}"
            return SetupWizardProbeView(
                status="ready",
                headline="Local lane is live",
                summary=(f"{connected_count} connected {lane_label} can launch work immediately."),
            )
        if instance_count > 0:
            saved_lane_label = f"lane{'s' if instance_count != 1 else ''}"
            return SetupWizardProbeView(
                status="warn",
                headline="Local lane is saved but idle",
                summary=(
                    f"{instance_count} saved {saved_lane_label} still need connection attention."
                ),
            )
        return SetupWizardProbeView(
            status="missing",
            headline="No local lane is staged",
            summary="Local mode will need to create or quick-connect a Codex lane.",
        )

    def _build_remote_probe(
        self,
        *,
        team_count: int,
        operators: list[Any],
    ) -> SetupWizardProbeView:
        api_key_count = sum(1 for operator in operators if operator.has_api_key)
        if api_key_count > 0:
            key_label = f"key{'s' if api_key_count != 1 else ''}"
            return SetupWizardProbeView(
                status="ready",
                headline="Remote ingress is armed",
                summary=(f"{api_key_count} operator {key_label} can trigger work remotely."),
            )
        if operators or team_count:
            return SetupWizardProbeView(
                status="warn",
                headline="Remote ingress is partially staged",
                summary=(
                    "Teams or operators exist, but no active operator API key is available yet."
                ),
            )
        return SetupWizardProbeView(
            status="missing",
            headline="No remote ingress is staged",
            summary="Remote mode needs an operator and API key before it can dispatch work.",
        )

    def _recommended_mode(
        self,
        *,
        gateway_mode: str,
        local_probe: SetupWizardProbeView,
        remote_probe: SetupWizardProbeView,
    ) -> SetupMode:
        if gateway_mode in {"local", "remote"}:
            return gateway_mode  # type: ignore[return-value]
        if local_probe.status == "ready" and remote_probe.status != "ready":
            return "local"
        if remote_probe.status == "ready" and local_probe.status == "missing":
            return "remote"
        return "local"

    async def _reset_full(
        self,
        *,
        footprint: SetupFootprintView,
        cleared: list[str],
        preserved: list[str],
        warnings: list[str],
    ) -> None:
        for task in [footprint.task_blueprint, footprint.memory_task_blueprint]:
            if task is None or not task.created:
                continue
            existing = await self.database.get_task_blueprint(task.id)
            if existing is not None:
                await self.database.delete_task_blueprint(task.id)
                cleared.append(f"task blueprint '{task.label}'")

        integration = footprint.integration
        if integration is not None and integration.created:
            existing = await self.database.get_integration(integration.id)
            if existing is not None:
                await self.database.delete_integration(integration.id)
                cleared.append(f"integration '{integration.label}'")

        skill_pin = footprint.skill_pin
        if skill_pin is not None and skill_pin.created:
            skill_pins = await self.database.list_skill_pins()
            if any(int(item["id"]) == skill_pin.id for item in skill_pins):
                await self.database.delete_skill_pin(skill_pin.id)
                cleared.append(f"skill pin '{skill_pin.label}'")

        vault_secret = footprint.vault_secret
        if vault_secret is not None and vault_secret.created:
            integrations = await self.database.list_integrations()
            routes = await self.database.list_notification_routes()
            in_use = any(
                int(item.get("vault_secret_id") or 0) == vault_secret.id for item in integrations
            ) or any(int(item.get("vault_secret_id") or 0) == vault_secret.id for item in routes)
            if in_use:
                preserved.append(f"vault secret '{vault_secret.label}' is still referenced")
            else:
                existing = await self.database.get_vault_secret(vault_secret.id)
                if existing is not None:
                    await self.database.delete_vault_secret(vault_secret.id)
                    cleared.append(f"vault secret '{vault_secret.label}'")

        operator = footprint.operator
        if operator is not None and operator.created:
            remote_requests = await self.database.list_remote_requests()
            if any(int(item["operator_id"]) == operator.id for item in remote_requests):
                await self.database.update_operator(operator.id, enabled=False)
                preserved.append(
                    f"operator '{operator.label}' kept for request history and disabled"
                )
            else:
                existing = await self.database.get_operator(operator.id)
                if existing is not None:
                    await self.database.delete_operator(operator.id)
                    cleared.append(f"operator '{operator.label}'")

        team = footprint.team
        if team is not None and team.created:
            operators = await self.database.list_operators()
            remote_requests = await self.database.list_remote_requests()
            team_has_members = any(int(item["team_id"]) == team.id for item in operators)
            team_has_history = any(int(item["team_id"]) == team.id for item in remote_requests)
            if team_has_members or team_has_history:
                preserved.append(f"team '{team.label}' kept because it still has history")
            else:
                existing = await self.database.get_team(team.id)
                if existing is not None:
                    await self.database.delete_team(team.id)
                    cleared.append(f"team '{team.label}'")

        project = footprint.project
        if project is not None and project.created:
            tasks = await self.database.list_task_blueprints()
            integrations = await self.database.list_integrations()
            skill_pins = await self.database.list_skill_pins()
            missions = await self.database.list_missions()
            project_has_refs = (
                any(int(item.get("project_id") or 0) == project.id for item in tasks)
                or any(int(item.get("project_id") or 0) == project.id for item in integrations)
                or any(int(item.get("project_id") or 0) == project.id for item in skill_pins)
                or any(int(item.get("project_id") or 0) == project.id for item in missions)
            )
            if project_has_refs:
                preserved.append(
                    f"project '{project.label}' kept because historical runs reference it"
                )
            else:
                existing = await self.database.get_project(project.id)
                if existing is not None:
                    await self.database.delete_project(project.id)
                    cleared.append(f"project '{project.label}'")

        instance = footprint.instance
        if instance is not None and instance.created:
            playbooks = await self.database.list_playbooks()
            missions = await self.database.list_missions()
            instance_has_refs = any(
                int(item.get("instance_id") or 0) == instance.id for item in playbooks
            ) or any(int(item.get("instance_id") or 0) == instance.id for item in missions)
            if instance_has_refs:
                preserved.append(
                    f"lane '{instance.label}' kept because historical runs reference it"
                )
            else:
                try:
                    await self.manager.delete_instance(instance.id)
                    cleared.append(f"lane '{instance.label}'")
                except KeyError:
                    existing = await self.database.get_instance(instance.id)
                    if existing is not None:
                        await self.database.delete_instance(instance.id)
                        cleared.append(f"lane '{instance.label}'")
                    else:
                        warnings.append(
                            f"Lane '{instance.label}' was already absent during full reset."
                        )
