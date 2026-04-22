from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from openzues.database import Database
from openzues.schemas import GatewayBootstrapUpdate
from openzues.services.access import AccessService
from openzues.services.device_bootstrap_profile import default_device_bootstrap_profile
from openzues.services.gateway_bootstrap import (
    BOOT_SILENT_REPLY_TOKEN,
    GatewayBootstrapService,
)


class FakeManager:
    def __init__(
        self,
        *,
        thread_result: dict[str, object] | None = None,
        start_thread_error: Exception | None = None,
        start_turn_error: Exception | None = None,
        list_views_result: list[SimpleNamespace] | None = None,
        mcp_server_status_result: list[dict[str, object]] | None = None,
    ) -> None:
        self.thread_result = (
            {"thread": {"id": "thread-boot-123"}} if thread_result is None else thread_result
        )
        self.start_thread_error = start_thread_error
        self.start_turn_error = start_turn_error
        self.list_views_result = [] if list_views_result is None else list_views_result
        self.mcp_server_status_result = (
            [] if mcp_server_status_result is None else mcp_server_status_result
        )
        self.start_thread_calls: list[dict[str, object]] = []
        self.start_turn_calls: list[dict[str, object]] = []

    async def start_thread(
        self,
        instance_id: int,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, object]:
        self.start_thread_calls.append(
            {
                "instance_id": instance_id,
                "model": model,
                "cwd": cwd,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        if self.start_thread_error is not None:
            raise self.start_thread_error
        return self.thread_result

    async def start_turn(
        self,
        instance_id: int,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, object]:
        self.start_turn_calls.append(
            {
                "instance_id": instance_id,
                "thread_id": thread_id,
                "text": text,
                "cwd": cwd,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "collaboration_mode": collaboration_mode,
            }
        )
        if self.start_turn_error is not None:
            raise self.start_turn_error
        return {"turn": {"id": "turn-boot-123", "threadId": thread_id}}

    async def list_views(self) -> list[SimpleNamespace]:
        return self.list_views_result

    async def list_mcp_server_status(
        self,
        instance_id: int,
        *,
        limit: int = 50,
        refresh: bool = True,
    ) -> list[dict[str, object]]:
        return [dict(item) for item in self.mcp_server_status_result]


class FakeLaunchRouting:
    def __init__(self, *, resolved_instance_id: int | None) -> None:
        self.resolved_instance_id = resolved_instance_id
        self.calls: list[dict[str, object]] = []

    async def describe(self, *, task: object, persist: bool) -> SimpleNamespace:
        self.calls.append({"task": task, "persist": persist})
        resolved_instance = None
        if self.resolved_instance_id is not None:
            resolved_instance = SimpleNamespace(id=self.resolved_instance_id)
        return SimpleNamespace(resolved_instance=resolved_instance)


async def _build_service(
    tmp_path: Path,
    *,
    manager: FakeManager | None = None,
    launch_routing: FakeLaunchRouting | None = None,
    save_bootstrap: bool = True,
) -> tuple[GatewayBootstrapService, Path, FakeManager]:
    database = Database(tmp_path / "openzues.db")
    await database.initialize()
    access = AccessService(database)
    await access.initialize()

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    active_manager = manager or FakeManager()
    service = GatewayBootstrapService(
        database,
        active_manager,  # type: ignore[arg-type]
        access,
        launch_routing=launch_routing,  # type: ignore[arg-type]
    )

    if save_bootstrap:
        await database.upsert_gateway_bootstrap(
            setup_mode="local",
            setup_flow="quickstart",
            route_binding_mode="saved_lane",
            preferred_instance_id=None,
            preferred_project_id=None,
            team_id=None,
            operator_id=None,
            task_blueprint_id=None,
            last_route_instance_id=None,
            last_route_resolved_at=None,
            default_cwd=str(workspace_dir),
            bootstrap_roles=None,
            bootstrap_scopes=None,
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
            toolsets=["hermes-cli"],
        )

    return service, workspace_dir, active_manager


@pytest.mark.asyncio
async def test_run_startup_boot_once_dispatches_boot_prompt_to_resolved_launch_lane(
    tmp_path: Path,
) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text(
        "Check the workspace and report only if operator action is required.\n",
        encoding="utf-8",
    )

    result = await service.run_startup_boot_once()

    assert result.status == "ran"
    assert result.thread_id == "thread-boot-123"
    assert launch_routing.calls == [{"task": None, "persist": True}]
    assert manager.start_thread_calls == [
        {
            "instance_id": 41,
            "model": "gpt-5.4",
            "cwd": str(workspace_dir.resolve()),
            "reasoning_effort": None,
            "collaboration_mode": None,
        }
    ]
    assert len(manager.start_turn_calls) == 1
    turn_call = manager.start_turn_calls[0]
    assert turn_call["instance_id"] == 41
    assert turn_call["thread_id"] == "thread-boot-123"
    assert turn_call["cwd"] == str(workspace_dir.resolve())
    assert "Follow BOOT.md instructions exactly." in str(turn_call["text"])
    assert "Check the workspace and report only if operator action is required." in str(
        turn_call["text"]
    )
    assert "message tool (action=send with channel + target)" in str(turn_call["text"])
    assert "Use the `target` field (not `to`) for message tool destinations." in str(
        turn_call["text"]
    )
    assert (
        f"After sending with the message tool, reply with ONLY: {BOOT_SILENT_REPLY_TOKEN}."
        in str(turn_call["text"])
    )
    assert "NO_REPLY" in str(turn_call["text"])
    assert BOOT_SILENT_REPLY_TOKEN in str(turn_call["text"])


@pytest.mark.asyncio
async def test_save_defaults_bootstrap_profile_when_first_record_omits_profile(
    tmp_path: Path,
) -> None:
    service, _, _ = await _build_service(tmp_path, save_bootstrap=False)

    view = await service.save(GatewayBootstrapUpdate())

    expected_roles, expected_scopes = default_device_bootstrap_profile()
    assert view.bootstrap_roles == expected_roles
    assert view.bootstrap_scopes == expected_scopes

    row = await service.database.get_gateway_bootstrap()
    assert row is not None
    assert row["bootstrap_roles"] == expected_roles
    assert row["bootstrap_scopes"] == expected_scopes


@pytest.mark.asyncio
async def test_save_normalizes_partial_bootstrap_profile_without_stale_persisted_values(
    tmp_path: Path,
) -> None:
    service, _, _ = await _build_service(tmp_path)

    view = await service.save(
        GatewayBootstrapUpdate(bootstrap_scopes=["operator.write", "operator.write"])
    )

    assert view.bootstrap_roles == []
    assert view.bootstrap_scopes == ["operator.read", "operator.write"]

    row = await service.database.get_gateway_bootstrap()
    assert row is not None
    assert row["bootstrap_roles"] == []
    assert row["bootstrap_scopes"] == ["operator.read", "operator.write"]


@pytest.mark.asyncio
async def test_save_preserves_workspace_affinity_route_hint_for_same_project(
    tmp_path: Path,
) -> None:
    service, workspace_dir, _ = await _build_service(tmp_path, save_bootstrap=False)

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Workspace Affinity Project",
    )
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=None,
        preferred_project_id=project_id,
        team_id=None,
        operator_id=None,
        task_blueprint_id=None,
        last_route_instance_id=41,
        last_route_resolved_at="2026-04-15T12:00:00Z",
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=None,
        bootstrap_scopes=None,
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
        toolsets=["hermes-cli"],
    )

    await service.save(
        GatewayBootstrapUpdate(
            setup_mode="remote",
            setup_flow="advanced",
            route_binding_mode="workspace_affinity",
            preferred_project_id=project_id,
            default_cwd=str(workspace_dir.resolve()),
            model="gpt-5.4-mini",
            max_turns=3,
            use_builtin_agents=False,
            run_verification=True,
            auto_commit=False,
            pause_on_approval=True,
            allow_auto_reflexes=True,
            auto_recover=True,
            auto_recover_limit=2,
            reflex_cooldown_seconds=900,
            allow_failover=True,
            toolsets=["hermes-cli"],
        )
    )

    row = await service.database.get_gateway_bootstrap()
    assert row is not None
    assert row["last_route_instance_id"] == 41
    assert row["last_route_resolved_at"] == "2026-04-15T12:00:00Z"


@pytest.mark.asyncio
async def test_run_startup_boot_once_skips_when_boot_file_is_missing(tmp_path: Path) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, _workspace_dir, manager = await _build_service(
        tmp_path,
        launch_routing=launch_routing,
    )

    result = await service.run_startup_boot_once()

    assert result.status == "skipped"
    assert result.reason == "BOOT.md is missing."
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_run_startup_boot_once_skips_when_boot_file_is_empty(tmp_path: Path) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text(" \n\t\n", encoding="utf-8")

    result = await service.run_startup_boot_once()

    assert result.status == "skipped"
    assert result.reason == "BOOT.md is empty."
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_get_view_marks_connected_local_bootstrap_ready_without_remote_api_key(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
        apps=[{"name": "Slack"}],
        plugins=[{"name": "GitHub"}],
        mcp_servers=[{"name": "filesystem"}],
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "ready"
    assert view.headline == "Gateway bootstrap is launch-ready"
    assert view.instance is not None
    assert view.instance.connected is True
    assert view.operator is not None
    assert "local-only" in view.operator.detail
    assert not any("active API key" in warning for warning in view.warnings)
    assert view.runtime_inventory is not None
    assert view.runtime_inventory.app_names == ["Slack"]
    assert view.runtime_inventory.plugin_names == ["GitHub"]
    assert view.runtime_inventory.mcp_server_names == ["filesystem"]
    assert view.runtime_inventory.base_method_count == len(view.runtime_inventory.base_methods)
    assert view.runtime_inventory.base_method_count > 0
    assert view.runtime_inventory.method_catalog is not None
    assert (
        view.runtime_inventory.method_catalog.tool_count
        == view.runtime_inventory.base_method_count
    )
    assert view.runtime_inventory.method_catalog.tools == view.runtime_inventory.base_methods


@pytest.mark.asyncio
async def test_get_view_marks_local_bootstrap_staged_when_saved_operator_is_disabled(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.update_operator(1, enabled=False)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Gateway bootstrap is staged"
    assert view.operator is not None
    assert "local-only" in view.operator.detail
    assert "disabled" in view.operator.detail
    assert "The saved default operator is disabled." in view.warnings


@pytest.mark.asyncio
async def test_get_view_marks_bootstrap_degraded_when_saved_team_is_missing(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )
    await service.database.delete_team(1)

    view = await service.get_view()

    assert view.status == "degraded"
    assert view.headline == "Gateway bootstrap needs repair"
    assert view.team is None
    assert view.operator is not None
    assert "local-only" in view.operator.detail
    assert "The saved default team no longer exists." in view.warnings


@pytest.mark.asyncio
async def test_get_view_marks_bootstrap_degraded_when_saved_operator_moves_to_different_team(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )
    reassigned_team_id = await service.database.create_team(
        name="Field Operators",
        slug="field-operators",
        description="Alternate bootstrap team.",
    )
    await service.database.update_operator(1, team_id=reassigned_team_id)

    view = await service.get_view()

    assert view.status == "degraded"
    assert view.headline == "Gateway bootstrap needs repair"
    assert view.team is not None
    assert view.team.label == "Local Control"
    assert view.operator is not None
    assert "Field Operators" in view.operator.detail
    assert "local-only" in view.operator.detail
    assert (
        "The saved default operator no longer belongs to the saved team."
        in view.warnings
    )


@pytest.mark.asyncio
async def test_get_view_marks_local_bootstrap_staged_when_saved_task_is_disabled(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.update_task_blueprint(task_id, enabled=False)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Gateway bootstrap is staged"
    assert view.task_blueprint is not None
    assert "disabled" in view.task_blueprint.detail
    assert "The saved default recurring task is disabled." in view.warnings


@pytest.mark.asyncio
async def test_get_view_surfaces_live_plugin_published_gateway_methods_in_runtime_inventory(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
        apps=[{"name": "Slack"}],
        plugins=[{"name": "GitHub"}],
        mcp_servers=[{"name": "filesystem"}],
    )
    manager = FakeManager(
        list_views_result=[connected_instance],
        mcp_server_status_result=[
            {
                "name": "filesystem",
                "tools": [
                    {"name": "github.pulls.comment", "scope": "operator.write"},
                    {"name": "status"},
                ],
            }
        ],
    )
    service, _, _ = await _build_service(
        tmp_path,
        manager=manager,
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.runtime_inventory is not None
    assert view.runtime_inventory.resolved_method_count > view.runtime_inventory.base_method_count
    assert "github.pulls.comment" in view.runtime_inventory.resolved_methods
    assert view.runtime_inventory.method_catalog is not None
    assert view.runtime_inventory.method_catalog.server_count == 1
    assert view.runtime_inventory.method_catalog.lane_count == 1
    assert "plugin-published" in view.runtime_inventory.method_catalog.summary


@pytest.mark.asyncio
async def test_get_view_surfaces_browser_service_inventory_from_runtime_status(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
        apps=[],
        plugins=[],
        mcp_servers=[{"name": "browser-runtime"}],
    )
    manager = FakeManager(
        list_views_result=[connected_instance],
        mcp_server_status_result=[
            {
                "name": "browser-runtime",
                "source": "browser",
                "tools": [
                    {"name": "browser.request", "scope": "operator.write"},
                ],
                "services": [{"service": {"id": "browser-control"}}],
            }
        ],
    )
    service, _, _ = await _build_service(
        tmp_path,
        manager=manager,
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Browser Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Browser Loop",
        summary="Keep the browser lane moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified browser slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.runtime_inventory is not None
    assert "browser.request" in view.runtime_inventory.resolved_methods
    assert view.runtime_inventory.plugin_names == ["browser"]
    assert view.runtime_inventory.service_count == 1
    assert view.runtime_inventory.service_names == ["browser-control"]
    assert view.runtime_inventory.browser_runtime is not None
    assert view.runtime_inventory.browser_runtime.status == "ready"
    assert view.runtime_inventory.browser_runtime.method_count == 1
    assert view.runtime_inventory.browser_runtime.service_count == 1
    assert view.runtime_inventory.browser_runtime.methods == ["browser.request"]
    assert view.runtime_inventory.browser_runtime.services == ["browser-control"]
    assert view.runtime_inventory.browser_runtime.plugins == ["browser"]
    assert view.runtime_inventory.browser_runtime.servers == ["browser-runtime"]


@pytest.mark.asyncio
async def test_get_view_omits_browser_inventory_when_runtime_status_does_not_publish_it(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
        apps=[],
        plugins=[],
        mcp_servers=[{"name": "browser-runtime"}],
    )
    manager = FakeManager(
        list_views_result=[connected_instance],
        mcp_server_status_result=[],
    )
    service, _, _ = await _build_service(
        tmp_path,
        manager=manager,
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Browser Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Browser Loop",
        summary="Keep the browser lane moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified browser slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.runtime_inventory is not None
    assert "browser.request" not in view.runtime_inventory.resolved_methods
    assert view.runtime_inventory.plugin_names == []
    assert view.runtime_inventory.service_count == 0
    assert view.runtime_inventory.service_names == []
    assert view.runtime_inventory.browser_runtime is not None
    assert view.runtime_inventory.browser_runtime.status == "info"
    assert view.runtime_inventory.browser_runtime.method_count == 0
    assert view.runtime_inventory.browser_runtime.service_count == 0
    assert view.runtime_inventory.browser_runtime.methods == []
    assert view.runtime_inventory.browser_runtime.services == []
    assert view.runtime_inventory.browser_runtime.plugins == []
    assert view.runtime_inventory.browser_runtime.servers == []


@pytest.mark.asyncio
async def test_get_view_uses_cached_mcp_plugin_source_when_instance_plugin_metadata_is_missing(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Local Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
        apps=[{"name": "Slack"}],
        plugins=[],
        mcp_servers=[{"name": "filesystem"}],
    )
    manager = FakeManager(
        list_views_result=[connected_instance],
        mcp_server_status_result=[
            {
                "name": "filesystem",
                "source": "GitHub",
                "tools": [
                    {"name": "github.pulls.comment", "scope": "operator.write"},
                    {"name": "status"},
                ],
            }
        ],
    )
    service, _, _ = await _build_service(
        tmp_path,
        manager=manager,
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Local Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Local Loop",
        summary="Keep the local workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified local slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.runtime_inventory is not None
    assert view.runtime_inventory.plugin_names == ["GitHub"]
    assert view.runtime_inventory.plugin_count == 1
    assert "github.pulls.comment" in view.runtime_inventory.resolved_methods


@pytest.mark.asyncio
async def test_get_view_surfaces_saved_workspace_integration(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="OpenClaw Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://gateway.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="OPENCLAW_GATEWAY_TOKEN",
        secret_value=None,
        notes="Remote ingress",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "ready"
    assert view.headline == "Remote gateway bootstrap is launch-ready"
    assert view.integration is not None
    assert view.integration.label == "OpenClaw Gateway"
    assert view.integration.detail == (
        "openclaw · https://gateway.example.test · token · secret ready"
    )


@pytest.mark.asyncio
async def test_get_view_keeps_first_enabled_ingress_record_order(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Zulu Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://zulu.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="ZULU_GATEWAY_TOKEN",
        secret_value=None,
        notes="First ingress",
        enabled=True,
    )
    await service.database.create_integration(
        name="Alpha Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://alpha.example.test",
        auth_scheme="token",
        vault_secret_id=13,
        secret_label="ALPHA_GATEWAY_TOKEN",
        secret_value=None,
        notes="Second ingress",
        enabled=True,
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.integration is not None
    assert view.integration.label == "Zulu Gateway"
    assert view.integration.detail == (
        "openclaw · https://zulu.example.test · token · secret ready"
    )
    assert (
        "Multiple integrations are attached to the saved workspace; "
        "showing the first enabled ingress record."
    ) in view.warnings


@pytest.mark.asyncio
async def test_get_view_prefers_first_auth_ready_ingress_record(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Missing Secret Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://missing.example.test",
        auth_scheme="token",
        vault_secret_id=None,
        secret_label="MISSING_GATEWAY_TOKEN",
        secret_value=None,
        notes="First ingress without a usable secret",
        enabled=True,
    )
    await service.database.create_integration(
        name="Ready Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://ready.example.test",
        auth_scheme="token",
        vault_secret_id=13,
        secret_label="READY_GATEWAY_TOKEN",
        secret_value=None,
        notes="Second ingress with credentials wired",
        enabled=True,
    )
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.integration is not None
    assert view.integration.label == "Ready Gateway"
    assert view.integration.detail == (
        "openclaw · https://ready.example.test · token · secret ready"
    )
    assert (
        "Multiple integrations are attached to the saved workspace; "
        "showing the first auth-ready ingress record."
    ) in view.warnings


@pytest.mark.asyncio
async def test_get_view_does_not_claim_secret_ready_for_label_only_integration(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Label Only Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://label-only.example.test",
        auth_scheme="token",
        vault_secret_id=None,
        secret_label="LABEL_ONLY_GATEWAY_TOKEN",
        secret_value=None,
        notes="Ingress with a label but no usable secret",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Remote gateway bootstrap is staged"
    assert view.integration is not None
    assert view.integration.label == "Label Only Gateway"
    assert view.integration.detail == (
        "openclaw · https://label-only.example.test · token"
    )
    assert "The saved remote ingress is missing usable auth material." in view.warnings


@pytest.mark.asyncio
async def test_get_view_marks_remote_bootstrap_staged_without_enabled_ingress(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.access.issue_api_key(1)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Remote gateway bootstrap is staged"
    assert view.integration is None
    assert "The saved workspace does not have an enabled remote ingress yet." in view.warnings
    assert not any("active API key" in warning for warning in view.warnings)


@pytest.mark.asyncio
async def test_get_view_marks_remote_bootstrap_staged_when_saved_operator_is_disabled(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Remote Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://remote.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="REMOTE_GATEWAY_TOKEN",
        secret_value=None,
        notes="Remote ingress",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    await service.database.update_operator(1, enabled=False)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Remote gateway bootstrap is staged"
    assert view.operator is not None
    assert "remote key ready" in view.operator.detail
    assert "disabled" in view.operator.detail
    assert "The saved default operator is disabled." in view.warnings
    assert not any("active API key" in warning for warning in view.warnings)


@pytest.mark.asyncio
async def test_get_view_marks_remote_bootstrap_degraded_when_saved_team_is_missing(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Remote Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://remote.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="REMOTE_GATEWAY_TOKEN",
        secret_value=None,
        notes="Remote ingress",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )
    await service.database.delete_team(1)

    view = await service.get_view()

    assert view.status == "degraded"
    assert view.headline == "Gateway bootstrap needs repair"
    assert view.team is None
    assert view.operator is not None
    assert "remote key ready" in view.operator.detail
    assert "The saved default team no longer exists." in view.warnings


@pytest.mark.asyncio
async def test_get_view_marks_remote_bootstrap_degraded_when_saved_operator_moves_to_different_team(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Remote Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://remote.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="REMOTE_GATEWAY_TOKEN",
        secret_value=None,
        notes="Remote ingress",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )
    reassigned_team_id = await service.database.create_team(
        name="Field Operators",
        slug="field-operators",
        description="Alternate bootstrap team.",
    )
    await service.database.update_operator(1, team_id=reassigned_team_id)

    view = await service.get_view()

    assert view.status == "degraded"
    assert view.headline == "Gateway bootstrap needs repair"
    assert view.team is not None
    assert view.team.label == "Local Control"
    assert view.integration is not None
    assert view.operator is not None
    assert "Field Operators" in view.operator.detail
    assert "remote key ready" in view.operator.detail
    assert (
        "The saved default operator no longer belongs to the saved team."
        in view.warnings
    )


@pytest.mark.asyncio
async def test_get_view_marks_remote_bootstrap_staged_when_saved_task_is_disabled(
    tmp_path: Path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    connected_instance = SimpleNamespace(
        id=41,
        name="Remote Lane",
        transport="desktop",
        cwd=str(workspace_dir.resolve()),
        connected=True,
        error=None,
    )
    service, _, _manager = await _build_service(
        tmp_path,
        manager=FakeManager(list_views_result=[connected_instance]),
        save_bootstrap=False,
    )

    project_id = await service.database.create_project(
        path=str(workspace_dir.resolve()),
        label="Remote Workspace",
    )
    task_id = await service.database.create_task_blueprint(
        name="Remote Loop",
        summary="Keep the remote workspace moving.",
        project_id=project_id,
        instance_id=connected_instance.id,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified remote slice.",
            "conversation_target": None,
            "instance_id": connected_instance.id,
            "project_id": project_id,
            "cadence_minutes": 60,
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
            "cwd": str(workspace_dir.resolve()),
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 4,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["hermes-cli"],
            "enabled": True,
        },
    )
    await service.database.create_integration(
        name="Remote Gateway",
        kind="openclaw",
        project_id=project_id,
        base_url="https://remote.example.test",
        auth_scheme="token",
        vault_secret_id=12,
        secret_label="REMOTE_GATEWAY_TOKEN",
        secret_value=None,
        notes="Remote ingress",
        enabled=True,
    )
    await service.access.issue_api_key(1)
    await service.database.update_task_blueprint(task_id, enabled=False)
    bootstrap_roles, bootstrap_scopes = default_device_bootstrap_profile()
    await service.database.upsert_gateway_bootstrap(
        setup_mode="remote",
        setup_flow="advanced",
        route_binding_mode="workspace_affinity",
        preferred_instance_id=connected_instance.id,
        preferred_project_id=project_id,
        team_id=1,
        operator_id=1,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(workspace_dir.resolve()),
        bootstrap_roles=bootstrap_roles,
        bootstrap_scopes=bootstrap_scopes,
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
        toolsets=["hermes-cli"],
    )

    view = await service.get_view()

    assert view.status == "staged"
    assert view.headline == "Remote gateway bootstrap is staged"
    assert view.task_blueprint is not None
    assert "disabled" in view.task_blueprint.detail
    assert "The saved default recurring task is disabled." in view.warnings
    assert not any("active API key" in warning for warning in view.warnings)


@pytest.mark.asyncio
async def test_run_startup_boot_once_fails_when_boot_file_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text("Boot me.\n", encoding="utf-8")

    original_read_text = Path.read_text

    def _raise_boot_read_error(self: Path, *args: object, **kwargs: object) -> str:
        if self == workspace_dir / "BOOT.md":
            raise OSError("disk offline")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_boot_read_error)

    result = await service.run_startup_boot_once()

    assert result.status == "failed"
    assert result.reason == "Failed to read BOOT.md: disk offline"
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_run_startup_boot_once_skips_without_resolved_launch_lane(tmp_path: Path) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=None)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text("Boot me.\n", encoding="utf-8")

    result = await service.run_startup_boot_once()

    assert result.status == "skipped"
    assert result.reason == "Gateway bootstrap has no resolved launch lane for startup boot."
    assert manager.start_thread_calls == []
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_run_startup_boot_once_fails_when_thread_id_is_missing(tmp_path: Path) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        manager=FakeManager(thread_result={}),
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text("Boot me.\n", encoding="utf-8")

    result = await service.run_startup_boot_once()

    assert result.status == "failed"
    assert result.reason == "Startup boot did not return a thread id."
    assert len(manager.start_thread_calls) == 1
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_run_startup_boot_once_fails_when_thread_launch_raises(
    tmp_path: Path,
) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        manager=FakeManager(start_thread_error=RuntimeError("thread launch timeout")),
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text("Boot me.\n", encoding="utf-8")

    result = await service.run_startup_boot_once()

    assert result.status == "failed"
    assert result.reason == "Startup boot failed: thread launch timeout"
    assert len(manager.start_thread_calls) == 1
    assert manager.start_turn_calls == []


@pytest.mark.asyncio
async def test_run_startup_boot_once_fails_when_boot_turn_dispatch_raises(
    tmp_path: Path,
) -> None:
    launch_routing = FakeLaunchRouting(resolved_instance_id=41)
    service, workspace_dir, manager = await _build_service(
        tmp_path,
        manager=FakeManager(start_turn_error=RuntimeError("lane offline")),
        launch_routing=launch_routing,
    )
    (workspace_dir / "BOOT.md").write_text("Boot me.\n", encoding="utf-8")

    result = await service.run_startup_boot_once()

    assert result.status == "failed"
    assert result.reason == "Startup boot failed: lane offline"
    assert len(manager.start_thread_calls) == 1
    assert len(manager.start_turn_calls) == 1
