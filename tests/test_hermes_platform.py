from __future__ import annotations

from pathlib import Path

import pytest

from openzues.database import Database
from openzues.services.access import AccessService
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.github import GitHubService
from openzues.services.hermes_platform import HermesPlatformService
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.missions import MissionService
from openzues.services.projects import ProjectService
from openzues.settings import Settings


def _write_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# stub\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_hermes_platform_promotes_learning_toolsets_into_task_and_gateway(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir(parents=True, exist_ok=True)
    hermes_root = tmp_path / "hermes-agent-main"
    _write_file(hermes_root / "plugins" / "memory" / "mem0" / "__init__.py")
    _write_file(hermes_root / "gateway" / "platforms" / "telegram.py")
    _write_file(hermes_root / "gateway" / "platforms" / "webhook.py")
    _write_file(hermes_root / "acp_adapter" / "server.py")
    _write_file(hermes_root / "hermes_cli" / "curses_ui.py")
    _write_file(hermes_root / "trajectory_compressor.py")

    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues.db",
        hermes_source_path=hermes_root,
    )
    database = Database(settings.effective_db_path)
    await database.initialize()
    access = AccessService(database)
    await access.initialize()

    instance_id = await database.create_instance(
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=str(project_dir),
        auto_connect=False,
    )
    project_id = await database.create_project(path=str(project_dir), label="Beacon")
    team_id = await database.create_team(name="Operators", slug="operators", description=None)
    operator_id = await database.create_operator(
        team_id=team_id,
        name="Builder",
        email="builder@example.com",
        role="owner",
        enabled=True,
        api_key_hash="hash",
        api_key_preview="oz_test",
        api_key_issued_at="2026-04-11T00:00:00+00:00",
    )
    task_id = await database.create_task_blueprint(
        name="Beacon Loop",
        summary="Ship the next verified Beacon slice.",
        project_id=project_id,
        instance_id=instance_id,
        cadence_minutes=180,
        enabled=True,
        payload={
            "objective_template": "Improve the Beacon web interface and verify it.",
            "cwd": str(project_dir),
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
            "toolsets": ["terminal"],
            "run_until_complete": False,
            "continuation_cooldown_minutes": 10,
            "completion_marker": None,
        },
    )
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=instance_id,
        preferred_project_id=project_id,
        team_id=team_id,
        operator_id=operator_id,
        task_blueprint_id=task_id,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(project_dir),
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
        toolsets=["terminal"],
    )

    hub = BroadcastHub()
    manager = RuntimeManager(database, hub)
    await manager.load(auto_connect=False)
    missions = MissionService(database, manager, hub)
    project_service = ProjectService(GitHubService())
    gateway_bootstrap = GatewayBootstrapService(database, manager, access)
    hermes_platform = HermesPlatformService(
        database,
        manager,
        missions,
        project_service,
        gateway_bootstrap,
        settings,
        hub=hub,
    )

    stable_toolsets = ["terminal", "browser", "debugging", "delegation"]
    first_mission = await database.create_mission(
        name="Beacon Ship 1",
        objective="Improve the Beacon interface and verify it.",
        status="completed",
        instance_id=instance_id,
        project_id=project_id,
        task_blueprint_id=task_id,
        thread_id="thread-beacon-1",
        session_key="beacon",
        cwd=str(project_dir),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
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
        toolsets=stable_toolsets,
    )
    await database.update_mission(
        first_mission,
        last_checkpoint="Checkpoint landed with browser-led verification.",
        command_count=3,
        turns_completed=2,
        total_tokens=24000,
    )
    second_mission = await database.create_mission(
        name="Beacon Ship 2",
        objective="Improve the Beacon interface and verify it again.",
        status="completed",
        instance_id=instance_id,
        project_id=project_id,
        task_blueprint_id=task_id,
        thread_id="thread-beacon-2",
        session_key="beacon",
        cwd=str(project_dir),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
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
        toolsets=stable_toolsets,
    )
    await database.update_mission(
        second_mission,
        last_checkpoint="Checkpoint landed after browser and debugging proof.",
        command_count=4,
        turns_completed=2,
        total_tokens=28000,
    )
    risky_mission = await database.create_mission(
        name="Beacon Drift",
        objective="Keep changing Beacon until it feels right.",
        status="failed",
        instance_id=instance_id,
        project_id=project_id,
        task_blueprint_id=task_id,
        thread_id="thread-beacon-3",
        session_key="beacon",
        cwd=str(project_dir),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=4,
        use_builtin_agents=True,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["terminal"],
    )
    await database.update_mission(
        risky_mission,
        command_count=10,
        total_tokens=90000,
        last_error="Drifted without a durable checkpoint.",
    )

    promotion = await hermes_platform.promote_learning()
    assert promotion.applied_count >= 2

    task = await database.get_task_blueprint(task_id)
    gateway = await database.get_gateway_bootstrap()
    assert task is not None
    assert gateway is not None
    for toolset in ("browser", "debugging", "delegation"):
        assert toolset in task["toolsets"]
        assert toolset in gateway["toolsets"]

    doctor = await hermes_platform.get_doctor_view()
    assert doctor.profile.preferred_memory_provider == "openzues_recall"
    assert any(item.label == "Mem0" for item in doctor.memory.items)
    assert any(item.label == "Gateway API + Webhooks" for item in doctor.delivery.items)
    assert doctor.promotion_loop.already_armed_count >= 2


@pytest.mark.asyncio
async def test_hermes_platform_can_arm_workspace_shell_from_saved_gateway_workspace(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues.db",
    )
    database = Database(settings.effective_db_path)
    await database.initialize()
    access = AccessService(database)
    await access.initialize()

    instance_id = await database.create_instance(
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=str(project_dir),
        auto_connect=False,
    )
    project_id = await database.create_project(path=str(project_dir), label="OpenZues Workspace")
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=instance_id,
        preferred_project_id=project_id,
        team_id=None,
        operator_id=None,
        task_blueprint_id=None,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(project_dir),
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
        toolsets=["terminal"],
    )

    hub = BroadcastHub()
    manager = RuntimeManager(database, hub)
    await manager.load(auto_connect=False)
    missions = MissionService(database, manager, hub)
    project_service = ProjectService(GitHubService())
    gateway_bootstrap = GatewayBootstrapService(database, manager, access)
    hermes_platform = HermesPlatformService(
        database,
        manager,
        missions,
        project_service,
        gateway_bootstrap,
        settings,
        hub=hub,
    )

    result = await hermes_platform.arm_workspace_shell(auto_connect=False)
    doctor = await hermes_platform.get_doctor_view()
    workspace_shell = next(item for item in doctor.executors.items if item.key == "workspace_shell")

    assert result.cwd == str(project_dir)
    assert result.derived_from == "gateway_default_cwd"
    assert result.instance.transport == "stdio"
    assert result.created is True
    assert result.connected is False
    assert "explicit arm" in workspace_shell.capabilities
    assert "shell-backed lane" in workspace_shell.summary


@pytest.mark.asyncio
async def test_hermes_platform_can_arm_docker_backend_from_saved_gateway_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("openzues.services.hermes_platform._which", lambda command: command == "docker")

    project_dir = tmp_path / "workspace"
    project_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues.db",
    )
    database = Database(settings.effective_db_path)
    await database.initialize()
    access = AccessService(database)
    await access.initialize()

    instance_id = await database.create_instance(
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=str(project_dir),
        auto_connect=False,
    )
    project_id = await database.create_project(path=str(project_dir), label="OpenZues Workspace")
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=instance_id,
        preferred_project_id=project_id,
        team_id=None,
        operator_id=None,
        task_blueprint_id=None,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(project_dir),
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
        toolsets=["terminal"],
    )

    hub = BroadcastHub()
    manager = RuntimeManager(database, hub)
    await manager.load(auto_connect=False)
    missions = MissionService(database, manager, hub)
    project_service = ProjectService(GitHubService())
    gateway_bootstrap = GatewayBootstrapService(database, manager, access)
    hermes_platform = HermesPlatformService(
        database,
        manager,
        missions,
        project_service,
        gateway_bootstrap,
        settings,
        hub=hub,
    )

    result = await hermes_platform.arm_docker_backend(auto_connect=False)
    doctor = await hermes_platform.get_doctor_view()
    docker = next(item for item in doctor.executors.items if item.key == "docker")

    assert result.cwd == str(project_dir)
    assert result.derived_from == "gateway_default_cwd"
    assert result.instance.id == instance_id
    assert result.instance.transport == "desktop"
    assert result.image == "nikolaik/python-nodejs:python3.11-nodejs20"
    assert result.connected is False
    assert "explicit arm" in docker.capabilities
    assert "Docker staging is armed" in docker.summary
    assert doctor.profile.executor_profiles[0].key == "docker"
    assert doctor.profile.executor_profiles[0].image == result.image


@pytest.mark.asyncio
async def test_hermes_platform_can_preflight_docker_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("openzues.services.hermes_platform._which", lambda command: command == "docker")
    monkeypatch.setattr(
        "openzues.services.hermes_platform.shutil.which",
        lambda command: "C:\\docker\\docker.exe" if command == "docker" else None,
    )

    async def fake_run_process_capture(*args: str, timeout_seconds: float = 20.0) -> tuple[int, str, str]:
        del timeout_seconds
        command = tuple(args)
        if command[-1] == "--version":
            return 0, "Docker version 29.3.1, build c2be9cc", ""
        if command[1:3] == ("info", "--format"):
            return 0, "29.3.1", ""
        if command[1:4] == ("image", "inspect", "nikolaik/python-nodejs:python3.11-nodejs20"):
            return 0, "sha256:testimage", ""
        raise AssertionError(f"Unexpected docker command: {command}")

    monkeypatch.setattr(
        "openzues.services.hermes_platform._run_process_capture",
        fake_run_process_capture,
    )

    project_dir = tmp_path / "workspace"
    project_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues.db",
    )
    database = Database(settings.effective_db_path)
    await database.initialize()
    access = AccessService(database)
    await access.initialize()

    instance_id = await database.create_instance(
        name="Local Codex Desktop",
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=str(project_dir),
        auto_connect=False,
    )
    project_id = await database.create_project(path=str(project_dir), label="OpenZues Workspace")
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=instance_id,
        preferred_project_id=project_id,
        team_id=None,
        operator_id=None,
        task_blueprint_id=None,
        last_route_instance_id=None,
        last_route_resolved_at=None,
        default_cwd=str(project_dir),
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
        toolsets=["terminal"],
    )

    hub = BroadcastHub()
    manager = RuntimeManager(database, hub)
    await manager.load(auto_connect=False)
    missions = MissionService(database, manager, hub)
    project_service = ProjectService(GitHubService())
    gateway_bootstrap = GatewayBootstrapService(database, manager, access)
    hermes_platform = HermesPlatformService(
        database,
        manager,
        missions,
        project_service,
        gateway_bootstrap,
        settings,
        hub=hub,
    )

    await hermes_platform.arm_docker_backend(auto_connect=False)
    result = await hermes_platform.preflight_docker_backend()
    profile = await hermes_platform.get_runtime_profile()

    assert result.ok is True
    assert result.status == "ready"
    assert result.image_present is True
    assert result.daemon_version == "29.3.1"
    assert "image `nikolaik/python-nodejs:python3.11-nodejs20` is ready" in result.summary
    assert profile.executor_profiles[0].last_preflight_status == "ready"
    assert profile.executor_profiles[0].image_present is True
