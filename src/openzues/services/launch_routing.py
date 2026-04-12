from __future__ import annotations

from pathlib import Path

from openzues.database import Database, utcnow
from openzues.schemas import (
    GatewayBootstrapResourceView,
    GatewayRouteBindingMode,
    InstanceView,
    LaunchRouteBindingMode,
    LaunchRouteMatch,
    LaunchRouteStatus,
    LaunchRouteView,
    TaskBlueprintView,
)
from openzues.services.hermes_runtime_profile import (
    build_executor_launch_assessment,
    executor_candidate_rank,
    executor_candidate_supported,
    load_saved_runtime_preferences,
)
from openzues.services.manager import RuntimeManager


def _normalize_path(value: str | None) -> str | None:
    if not value:
        return None
    return (
        str(Path(value).expanduser().resolve(strict=False)).replace("\\", "/").rstrip("/").lower()
    )


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


def _path_matches_any_project(
    candidate: str | None,
    project_paths: tuple[str, ...],
) -> bool:
    return any(_path_matches_project(candidate, project_path) for project_path in project_paths)


def _instance_resource(
    instance: InstanceView | None,
    *,
    detail: str | None = None,
) -> GatewayBootstrapResourceView | None:
    if instance is None:
        return None
    rendered_detail = detail
    if rendered_detail is None:
        rendered_detail = str(instance.transport)
        if instance.cwd:
            rendered_detail = f"{rendered_detail} · {instance.cwd}"
        if instance.connected:
            rendered_detail = f"{rendered_detail} · connected"
        elif instance.error:
            rendered_detail = f"{rendered_detail} · {instance.error}"
    return GatewayBootstrapResourceView(
        id=instance.id,
        label=instance.name,
        detail=rendered_detail,
        connected=instance.connected,
    )


class LaunchRoutingService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
    ) -> None:
        self.database = database
        self.manager = manager

    async def describe(
        self,
        *,
        task: TaskBlueprintView | None = None,
        persist: bool = True,
    ) -> LaunchRouteView:
        gateway = await self.database.get_gateway_bootstrap()
        _preferred_memory_provider, preferred_executor = await load_saved_runtime_preferences(
            self.database
        )
        instances = await self.manager.list_views()
        instances_by_id = {instance.id: instance for instance in instances}

        preferred_instance_id = (
            task.instance_id
            if task is not None and task.instance_id is not None
            else int(gateway["preferred_instance_id"])
            if gateway is not None and gateway.get("preferred_instance_id") is not None
            else None
        )
        preferred_instance = (
            instances_by_id.get(preferred_instance_id)
            if preferred_instance_id is not None
            else None
        )
        project_id = (
            task.project_id
            if task is not None and task.project_id is not None
            else int(gateway["preferred_project_id"])
            if gateway is not None and gateway.get("preferred_project_id") is not None
            else None
        )
        project_path = None
        if project_id is not None:
            project = await self.database.get_project(project_id)
            if project is not None:
                project_path = str(project["path"])
        target_cwd = (
            (task.cwd if task is not None else None)
            or project_path
            or (
                str(gateway.get("default_cwd"))
                if gateway is not None and gateway.get("default_cwd") is not None
                else None
            )
        )
        workspace_targets = tuple(
            dict.fromkeys(
                value
                for value in (
                    task.cwd if task is not None else None,
                    project_path,
                    (
                        str(gateway.get("default_cwd"))
                        if gateway is not None and gateway.get("default_cwd") is not None
                        else None
                    ),
                    target_cwd,
                )
                if value
            )
        )
        operator_id = (
            int(gateway["operator_id"])
            if gateway is not None and gateway.get("operator_id") is not None
            else None
        )
        task_id = (
            task.id
            if task is not None
            else int(gateway["task_blueprint_id"])
            if gateway is not None and gateway.get("task_blueprint_id") is not None
            else None
        )
        strict_remote = bool(gateway is not None and str(gateway.get("setup_mode")) == "remote")
        last_route_instance_id = (
            int(gateway["last_route_instance_id"])
            if gateway is not None and gateway.get("last_route_instance_id") is not None
            else None
        )
        last_route_instance = (
            instances_by_id.get(last_route_instance_id)
            if last_route_instance_id is not None
            else None
        )
        route_binding_mode = self._resolve_mode(task=task, gateway=gateway)
        session_key = self._build_session_key(
            mode=route_binding_mode,
            preferred_instance_id=preferred_instance_id,
            task_id=task_id,
            project_id=project_id,
            operator_id=operator_id,
        )

        warnings: list[str] = []
        matched_by: LaunchRouteMatch = "unavailable"
        status: LaunchRouteStatus = "staged"
        headline = "Launch route is staged"
        summary = "Save or reconnect a lane before trusting the next draft."
        resolved_instance: InstanceView | None = None

        candidate_instances = sorted(
            instances,
            key=lambda instance: (
                0
                if executor_candidate_supported(
                    preferred_executor,
                    instance=instance,
                    target_cwd=target_cwd,
                )
                else 1,
                *executor_candidate_rank(
                    preferred_executor,
                    instance=instance,
                    target_cwd=target_cwd,
                ),
                (
                    0
                    if last_route_instance_id is not None and instance.id == last_route_instance_id
                    else 1
                ),
                0 if _path_matches_any_project(instance.cwd, workspace_targets) else 1,
                0 if instance.connected else 1,
                len(instance.unresolved_requests),
                instance.id,
            ),
        )
        eligible_candidate_instances = [
            instance
            for instance in candidate_instances
            if executor_candidate_supported(
                preferred_executor,
                instance=instance,
                target_cwd=target_cwd,
            )
        ]

        if route_binding_mode == "task_lane":
            matched_by = "task.instance"
            resolved_instance = preferred_instance
            if resolved_instance is None:
                status = "repair"
                headline = "Task route needs repair"
                summary = "The task is pinned to a lane that no longer exists."
                warnings.append("The task-specific lane binding no longer exists.")
            elif resolved_instance.connected:
                status = "ready"
                headline = "Task route is pinned"
                summary = "This recurring task stays on its pinned lane for continuity."
            else:
                status = "staged"
                headline = "Task route is pinned but idle"
                summary = "The task stays pinned to its saved lane until that lane reconnects."
                warnings.append(
                    "The task-specific lane is saved, but it is not connected right now."
                )
        elif route_binding_mode == "saved_lane":
            matched_by = "gateway.preferred_instance"
            resolved_instance = preferred_instance
            if resolved_instance is None:
                status = "repair" if gateway is not None else "staged"
                headline = (
                    "Saved lane route needs repair"
                    if gateway is not None
                    else "Launch route is staged"
                )
                summary = (
                    "The saved gateway profile no longer has a usable default lane."
                    if gateway is not None
                    else "No pinned lane is saved yet, so launch routing is waiting on a lane."
                )
                warnings.append(
                    "The saved launch lane is missing."
                    if gateway is not None
                    else "No saved lane is configured yet."
                )
            elif resolved_instance.connected:
                status = "ready"
                headline = "Saved lane route is ready"
                summary = "Local launch handoffs stay pinned to the configured default lane."
            else:
                status = "staged"
                headline = "Saved lane route is staged"
                summary = "The saved lane remains the continuity target even while it is offline."
                warnings.append("The saved launch lane is not connected right now.")
        else:
            if (
                last_route_instance is not None
                and last_route_instance.connected
                and executor_candidate_supported(
                    preferred_executor,
                    instance=last_route_instance,
                    target_cwd=target_cwd,
                )
                and _path_matches_any_project(last_route_instance.cwd, workspace_targets)
            ):
                matched_by = "workspace.last_route"
                resolved_instance = last_route_instance
            else:
                project_match = next(
                    (
                        instance
                        for instance in (eligible_candidate_instances or candidate_instances)
                        if instance.connected
                        and _path_matches_any_project(instance.cwd, workspace_targets)
                    ),
                    None,
                )
                if project_match is not None:
                    matched_by = "workspace.project_lane"
                    resolved_instance = project_match
                else:
                    connected_instance = next(
                        (
                            instance
                            for instance in (eligible_candidate_instances or candidate_instances)
                            if instance.connected
                        ),
                        None,
                    )
                    if connected_instance is not None:
                        matched_by = "workspace.connected_lane"
                        resolved_instance = connected_instance
                    elif not strict_remote and (
                        eligible_candidate_instances or candidate_instances
                    ):
                        matched_by = "workspace.saved_lane"
                        resolved_instance = (eligible_candidate_instances or candidate_instances)[0]

            if resolved_instance is None:
                status = "staged"
                headline = "Workspace-affinity route is staged"
                summary = "Remote-first launches are waiting for a connected lane."
                warnings.append(
                    "No connected lane is available yet for workspace-affinity routing."
                )
            elif resolved_instance.connected:
                status = "ready"
                headline = "Workspace-affinity route is ready"
                if matched_by == "workspace.last_route":
                    summary = (
                        "Launches will stick to the last healthy workspace lane "
                        "while it remains available."
                    )
                elif matched_by == "workspace.project_lane":
                    summary = (
                        "Launches prefer a connected lane already attached to the saved workspace."
                    )
                else:
                    summary = (
                        "Launches will use the healthiest connected lane until a "
                        "workspace-specific lane appears."
                    )
            else:
                status = "staged"
                headline = "Workspace-affinity route is staged"
                summary = (
                    "No connected lane is available, so the route can only point at "
                    "a saved lane for now."
                )
                warnings.append("Launch continuity is saved, but the chosen lane is not connected.")

        executor_assessment = build_executor_launch_assessment(
            preferred_executor,
            instance=resolved_instance,
            instances=instances,
            target_cwd=target_cwd,
        )
        warnings.extend(executor_assessment.warnings)
        if executor_assessment.status == "repair":
            status = "repair"
            headline = f"{executor_assessment.summary.split('.', 1)[0]}"
            summary = executor_assessment.summary
        elif executor_assessment.status == "staged" and status == "ready":
            status = "staged"
            headline = "Launch route is staged"
            summary = executor_assessment.summary
        elif executor_assessment.summary:
            summary = f"{summary} {executor_assessment.summary}"

        if (
            persist
            and gateway is not None
            and route_binding_mode == "workspace_affinity"
            and resolved_instance is not None
            and resolved_instance.connected
            and last_route_instance_id != resolved_instance.id
        ):
            await self.database.update_gateway_bootstrap_route_state(
                last_route_instance_id=resolved_instance.id,
                last_route_resolved_at=utcnow(),
            )
            gateway = await self.database.get_gateway_bootstrap()
            if project_id is not None:
                matched_by = "workspace.last_route"
                summary = (
                    "Launches will stick to the last healthy workspace lane "
                    "while it remains available."
                )

        route_last_resolved_at = (
            str(gateway.get("last_route_resolved_at"))
            if gateway is not None and gateway.get("last_route_resolved_at") is not None
            else None
        )

        candidate_views = [
            _instance_resource(
                instance,
                detail=(
                    "Last successful workspace lane."
                    if last_route_instance_id is not None and instance.id == last_route_instance_id
                    else "Workspace match."
                    if _path_matches_any_project(instance.cwd, workspace_targets)
                    else "Connected lane."
                    if instance.connected
                    else "Saved lane."
                ),
            )
            for instance in candidate_instances[:4]
        ]

        return LaunchRouteView(
            status=status,
            mode=route_binding_mode,
            matched_by=matched_by,
            headline=headline,
            summary=summary,
            session_key=session_key,
            warnings=warnings,
            preferred_instance=_instance_resource(preferred_instance),
            resolved_instance=_instance_resource(resolved_instance),
            candidates=[candidate for candidate in candidate_views if candidate is not None],
            last_resolved_at=route_last_resolved_at,
        )

    def _resolve_mode(
        self,
        *,
        task: TaskBlueprintView | None,
        gateway: dict | None,
    ) -> LaunchRouteBindingMode:
        if task is not None and task.instance_id is not None:
            return "task_lane"
        if gateway is not None:
            route_binding_mode = str(gateway.get("route_binding_mode") or "").strip().lower()
            if route_binding_mode == "workspace_affinity":
                return "workspace_affinity"
            if route_binding_mode == "saved_lane":
                return "saved_lane"
            if str(gateway.get("setup_mode") or "local") == "remote":
                return "workspace_affinity"
            return "saved_lane"
        return "workspace_affinity"

    def default_gateway_route_binding_mode(self, setup_mode: str) -> GatewayRouteBindingMode:
        return "workspace_affinity" if setup_mode == "remote" else "saved_lane"

    def _build_session_key(
        self,
        *,
        mode: LaunchRouteBindingMode,
        preferred_instance_id: int | None,
        task_id: int | None,
        project_id: int | None,
        operator_id: int | None,
    ) -> str:
        parts = ["launch", f"mode:{mode}"]
        if task_id is not None:
            parts.append(f"task:{task_id}")
        if project_id is not None:
            parts.append(f"project:{project_id}")
        if operator_id is not None:
            parts.append(f"operator:{operator_id}")
        if mode in {"task_lane", "saved_lane"} and preferred_instance_id is not None:
            parts.append(f"lane:{preferred_instance_id}")
        return ":".join(parts)
