from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.schemas import (
    InstanceView,
    IntegrationView,
    MissionStatus,
    MissionView,
    PlaybookView,
    ProjectView,
    SkillPinView,
)
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.hub import BroadcastHub
from openzues.services.memory_protocol import (
    MEMPALACE_MEMORY_TASK_NAME,
    MEMPALACE_MEMORY_TASK_SUMMARY,
    MEMPALACE_ROUNDTRIP_AT_PREFIX,
    MEMPALACE_ROUNDTRIP_DETAIL_PREFIX,
    MEMPALACE_ROUNDTRIP_SCOPE_PREFIX,
    MEMPALACE_ROUNDTRIP_STATUS_PREFIX,
    MEMPALACE_WRITEBACK_AT_PREFIX,
    MEMPALACE_WRITEBACK_SCOPE_PREFIX,
    MEMPALACE_WRITEBACK_STATUS_PREFIX,
    build_mempalace_maintenance_objective,
    mempalace_maintenance_cadence_minutes,
)
from openzues.services.ops_mesh import OpsMeshService, _serialize_task, build_ops_mesh
from openzues.services.vault import VaultService
from openzues.settings import Settings


@pytest.fixture(autouse=True)
def _reset_external_catalogs() -> None:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    yield
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)


def make_instance(
    *,
    instance_id: int = 1,
    connected: bool = True,
    name: str = "Local Codex Desktop",
    cwd: str = "C:/workspace",
    skills: list[dict] | None = None,
    apps: list[dict] | None = None,
    plugins: list[dict] | None = None,
    mcp_servers: list[dict] | None = None,
    unresolved_requests: list[dict] | None = None,
) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name=name,
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd=cwd,
        auto_connect=False,
        connected=connected,
        skills=skills or [],
        models=[],
        apps=apps or [],
        plugins=plugins or [],
        mcp_servers=mcp_servers or [],
        threads=[],
        unresolved_requests=unresolved_requests or [],
    )


def make_project(*, project_id: int = 1, label: str = "OpenZues Workspace") -> ProjectView:
    return ProjectView(
        id=project_id,
        path="C:/workspace",
        label=label,
        exists=True,
        is_git_repo=True,
        branch="main",
        git_status="On branch main\nnothing to commit, working tree clean",
        recent_commits=[],
        pull_requests=[],
        last_scan_at=datetime.now(UTC).isoformat(),
    )


def make_mission(
    *,
    mission_id: int = 1,
    task_blueprint_id: int | None = None,
    name: str = "Nightly Ship",
    objective: str = "Ship the next verified slice.",
    status: MissionStatus = "active",
    instance_id: int = 1,
    instance_name: str = "Local Codex Desktop",
    phase: str = "ready",
    thread_id: str | None = "thread_1",
    in_progress: bool = False,
    current_command: str | None = None,
    command_count: int = 0,
    total_tokens: int = 0,
    turns_completed: int = 0,
    failure_count: int = 0,
    last_error: str | None = None,
    last_checkpoint: str | None = "Verified and ready.",
    last_commentary: str | None = None,
    last_activity_at: str | None = None,
    suggested_action: str = "Run now.",
) -> MissionView:
    now = datetime.now(UTC)
    return MissionView(
        id=mission_id,
        name=name,
        objective=objective,
        status=status,
        instance_id=instance_id,
        instance_name=instance_name,
        project_id=1,
        project_label="OpenZues Workspace",
        task_blueprint_id=task_blueprint_id,
        thread_id=thread_id,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=2,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        in_progress=in_progress,
        phase=phase,
        current_command=current_command,
        command_count=command_count,
        total_tokens=total_tokens,
        output_tokens=0,
        reasoning_tokens=0,
        last_commentary=last_commentary,
        suggested_action=suggested_action,
        turns_started=0,
        turns_completed=turns_completed,
        failure_count=failure_count,
        last_turn_id=None,
        last_error=last_error,
        last_checkpoint=last_checkpoint,
        last_reflex_kind=None,
        last_reflex_at=None,
        last_activity_at=last_activity_at or now.isoformat(),
        checkpoints=[],
        created_at=now,
        updated_at=now,
    )


def make_client(tmp_path: Path) -> TestClient:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    return TestClient(create_app(app_settings))


def make_vault(database: Database, tmp_path: Path) -> VaultService:
    return VaultService(
        database,
        Settings(
            data_dir=tmp_path / "data",
            db_path=tmp_path / "data" / "openzues-test.db",
        ),
    )


def test_build_ops_mesh_surfaces_due_task_inventory() -> None:
    now = datetime.now(UTC)
    task_blueprints = [
        {
            "id": 7,
            "name": "Daily Drift Sweep",
            "summary": "Check for risky repo drift.",
            "objective_template": "Inspect the repo and report drift.",
            "instance_id": 1,
            "project_id": 1,
            "cadence_minutes": 60,
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "enabled": True,
            "last_launched_at": (
                now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
            ).isoformat(),
            "last_status": "completed",
            "last_result_summary": "Last run shipped a verified slice.",
            "created_at": now,
            "updated_at": now,
        }
    ]
    task_view = _serialize_task(task_blueprints[0])
    ops_mesh = build_ops_mesh(
        [make_instance()],
        [],
        [make_project()],
        [],
        [task_view],
        [],
        [],
        [],
        [],
        [],
    )

    assert ops_mesh.task_inbox.tasks
    assert ops_mesh.task_inbox.tasks[0].status == "due"
    assert ops_mesh.task_inbox.tasks[0].cadence_label == "Every 1h"
    assert ops_mesh.auth_posture.headline == "Integration auth is idle"
    assert ops_mesh.task_inbox.items[0].kind == "task_due"


def test_build_ops_mesh_auto_skillbook_includes_claw_style_builtin_skills() -> None:
    now = datetime.now(UTC)
    task_view = _serialize_task(
        {
            "id": 8,
            "name": "UI polish loop",
            "summary": "Keep tightening the product UI.",
            "objective_template": (
                "Keep improving the frontend chat interface until the UI is cleaner, "
                "more polished, and easier to use."
            ),
            "instance_id": 1,
            "project_id": 1,
            "cadence_minutes": None,
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "enabled": True,
            "last_launched_at": now.isoformat(),
            "last_status": "completed",
            "last_result_summary": "Ready for the next refinement pass.",
            "created_at": now,
            "updated_at": now,
        }
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [],
        [make_project()],
        [],
        [task_view],
        [],
        [],
        [],
        [],
        [],
    )

    assert ops_mesh.skillbooks
    skill_names = [skill.name for skill in ops_mesh.skillbooks[0].skills]
    assert "Superhuman Skill" in skill_names
    assert "Loop Skill" in skill_names
    assert "Front-end / UX UI Pro Skill" in skill_names
    assert "Project skillbook:" in ops_mesh.task_inbox.tasks[0].mission_draft.objective


@pytest.mark.asyncio
async def test_openclaw_parity_draft_anchors_checkpoint_without_harness_dossier(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    project_root = tmp_path / "workspace"
    project_root.mkdir()
    await database.create_project(path=str(project_root), label="OpenZues Workspace")
    await database.create_skill_pin(
        project_id=1,
        name="Browser Verify",
        prompt_hint=(
            "Use this after meaningful UI changes or dashboard flows that need visual "
            "confirmation."
        ),
        source="agent-browser",
        enabled=True,
    )
    await database.create_integration(
        project_id=1,
        name="GitHub Inventory",
        kind="github",
        base_url="https://api.github.com",
        auth_scheme="none",
        notes="Primary repo automation context for OpenZues tasks.",
        vault_secret_id=None,
        secret_label=None,
        secret_value=None,
        enabled=True,
    )
    await database.create_task_blueprint(
        name="OpenClaw Total Parity Program",
        summary="Keep closing OpenClaw parity until the product is genuinely done.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": (
                "Use C:/openclaw-main as the source of truth and C:/workspace as the target "
                "product. First inventory the OpenClaw surface area across gateway, onboarding, "
                "CLI, channels, routing, voice, canvas, nodes, skills, browser, packaging, and "
                "companion apps. Then choose the highest-leverage missing parity slice in "
                "OpenZues, implement it end to end in production quality, run the relevant "
                "verification, and leave a checkpoint that names what was completed, what "
                "remains, and the next best slice."
            ),
            "run_until_complete": True,
            "completion_marker": "PARITY COMPLETE",
            "cwd": str(project_root),
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "collaboration_mode": None,
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["debugging", "delegation", "browser"],
        },
    )

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    task_row = await database.get_task_blueprint(1)
    assert task_row is not None

    draft = await service._build_draft_for_task(_serialize_task(task_row))

    assert "OpenClaw parity anchor:" in draft.objective
    assert "docs/openclaw-parity-checkpoint-2026-04-10.md" in draft.objective
    assert "First inventory the OpenClaw surface area" not in draft.objective
    assert "Project skillbook:" not in draft.objective
    assert "Known integration inventory:" not in draft.objective
    assert "ECC workspace surface:" not in draft.objective
    assert "Hermes runtime posture prefers" not in draft.objective
    assert draft.toolsets == ["debugging", "delegation", "memory", "session_search"]
    assert "browser" not in draft.toolsets


def test_build_ops_mesh_synthesizes_operator_inbox_items() -> None:
    now = datetime.now(UTC)
    task_view = _serialize_task(
        {
            "id": 7,
            "name": "Morning Sweep",
            "summary": "Run the morning lane sweep.",
            "objective_template": "Inspect the repo, ship the next small slice, and checkpoint it.",
            "instance_id": 1,
            "project_id": 1,
            "cadence_minutes": 60,
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "enabled": True,
            "last_launched_at": (now - timedelta(hours=2)).isoformat(),
            "last_status": "completed",
            "last_result_summary": "Ready to sweep again.",
            "created_at": now,
            "updated_at": now,
        }
    )
    instance = make_instance(
        unresolved_requests=[
            {
                "id": 44,
                "request_id": "req_orphan",
                "thread_id": "thread_orphan",
                "method": "approval/request",
                "payload": {"tool": "shell_command"},
                "status": "pending",
                "created_at": (now - timedelta(minutes=12)).isoformat(),
                "resolved_at": None,
            }
        ]
    )
    missions = [
        make_mission(
            mission_id=10,
            name="Approval Ship",
            status="blocked",
            phase="approval",
            thread_id="thread_approval",
            last_error="Waiting for approval: write a release artifact.",
            last_checkpoint=None,
            suggested_action="Review the approval and let the mission continue.",
        ),
        make_mission(
            mission_id=11,
            name="Fragile Scout",
            status="active",
            thread_id="thread_fragile",
            last_checkpoint=None,
            total_tokens=50000,
            failure_count=2,
            last_activity_at=(now - timedelta(minutes=20)).isoformat(),
            suggested_action="Land a checkpoint before the next long stretch.",
        ),
        make_mission(
            mission_id=12,
            name="Burning Sweep",
            status="active",
            thread_id="thread_reflex",
            last_checkpoint=None,
            total_tokens=350000,
            last_activity_at=(now - timedelta(minutes=2)).isoformat(),
            suggested_action="Run the verification spike before the thread sprawls.",
        ),
        make_mission(
            mission_id=13,
            name="Paused Review",
            status="paused",
            last_checkpoint="Verified checkpoint ready for review.",
            suggested_action="Resume from the handoff when you want the next slice.",
        ),
    ]

    ops_mesh = build_ops_mesh(
        [instance],
        missions,
        [make_project()],
        [],
        [task_view],
        [],
        [],
        [],
        [],
        [],
    )

    item_kinds = {item.kind for item in ops_mesh.task_inbox.items}
    assert ops_mesh.task_inbox.headline == "Operator inbox is active"
    assert "approval_required" in item_kinds
    assert "approval_orphaned" in item_kinds
    assert "continuity_fragile" in item_kinds
    assert "reflex_armed" in item_kinds
    assert "checkpoint_ready" in item_kinds
    assert "task_due" in item_kinds


def test_build_ops_mesh_surfaces_scope_drift_item() -> None:
    mission = make_mission(
        mission_id=14,
        name="Moderation queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        current_command=(
            'powershell.exe -Command "Get-Content src\\\\openzues\\\\web\\\\static\\\\app.css"'
        ),
        last_commentary="Polishing gradients and chat bubble spacing in the dashboard shell.",
        last_checkpoint=None,
        suggested_action="Keep going.",
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [mission],
        [make_project()],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )

    assert any(item.kind == "scope_drift" for item in ops_mesh.task_inbox.items)


def test_build_ops_mesh_keeps_task_attention_visible_beside_failed_workflow() -> None:
    now = datetime.now(UTC)
    task_view = _serialize_task(
        {
            "id": 17,
            "name": "Repair release sweep",
            "summary": "Keep the scheduled release flow healthy.",
            "objective_template": "Repair the scheduled release lane and leave a checkpoint.",
            "instance_id": 1,
            "project_id": 1,
            "cadence_minutes": None,
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "enabled": True,
            "last_launched_at": (now - timedelta(hours=3)).isoformat(),
            "last_status": "failed",
            "last_result_summary": "Last scheduled run failed after the verification step.",
            "created_at": now,
            "updated_at": now,
        }
    )
    mission = make_mission(
        mission_id=31,
        task_blueprint_id=17,
        name="Repair release sweep",
        status="failed",
        last_checkpoint=None,
        last_error="Verification step failed in the release workflow.",
        suggested_action="Inspect the failed run and repair the schedule before relaunching it.",
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [mission],
        [make_project()],
        [],
        [task_view],
        [],
        [],
        [],
        [],
        [],
    )

    item_kinds = {item.kind for item in ops_mesh.task_inbox.items}
    assert "mission_failed" in item_kinds
    assert "task_attention" in item_kinds


def test_build_ops_mesh_surfaces_failed_scheduled_playbook() -> None:
    now = datetime.now(UTC)
    playbook = PlaybookView(
        id=3,
        name="Morning triage ping",
        description="Post the daily triage prompt.",
        kind="command",
        template="git status --short --branch",
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        cwd="C:/workspace",
        model=None,
        reasoning_effort=None,
        collaboration_mode=None,
        timeout_ms=10000,
        thread_id=None,
        default_variables={},
        last_run_at=(now - timedelta(minutes=20)).isoformat(),
        last_status="failed",
        last_result_summary=(
            "Playbook requires an instance_id either on the playbook or at run time."
        ),
        created_at=now,
        updated_at=now,
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [],
        [make_project()],
        [playbook],
        [],
        [],
        [],
        [],
        [],
        [],
    )

    item_kinds = {item.kind for item in ops_mesh.task_inbox.items}
    assert "playbook_attention" in item_kinds
    item = next(item for item in ops_mesh.task_inbox.items if item.kind == "playbook_attention")
    assert item.playbook_id == 3
    assert "Inspect the saved playbook inputs" in item.recommended_action


def test_build_ops_mesh_prompts_mempalace_writeback_for_completed_handoff() -> None:
    mission = make_mission(
        mission_id=31,
        name="Memory Handoff",
        status="completed",
        last_checkpoint="Checkpoint is ready for the next operator.",
        suggested_action=None,
    )
    integration = IntegrationView(
        id=4,
        name="MemPalace",
        kind="mempalace",
        project_id=1,
        base_url="python -m mempalace.mcp_server",
        auth_scheme="none",
        vault_secret_id=None,
        vault_secret_label=None,
        secret_label=None,
        has_secret=False,
        secret_preview=None,
        auth_status="satisfied",
        auth_detail=None,
        notes="Shared memory recall for project history.",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [mission],
        [make_project()],
        [],
        [],
        [],
        [],
        [integration],
        [],
        [],
    )

    item = next(item for item in ops_mesh.task_inbox.items if item.kind == "checkpoint_ready")
    assert "memory writeback" in item.title.lower()
    assert "write durable decisions" in item.recommended_action
    assert "MemPalace" in item.recommended_action


def test_build_ops_mesh_skills_registry_maps_lane_coverage_and_gaps() -> None:
    instance_primary = make_instance(
        skills=[
            {"name": "Browser Verify", "source": "agent-browser", "status": "ready"},
            {"name": "GitHub", "source": "github", "status": "ready"},
        ]
    )
    instance_secondary = make_instance(
        instance_id=2,
        name="Fallback Lane",
        cwd="C:/workspace",
        skills=[{"name": "Filesystem Sweep", "source": "workspace-scout", "status": "ready"}],
    )
    pinned_skills = [
        SkillPinView(
            id=1,
            project_id=1,
            name="Browser Verify",
            prompt_hint="Use it for UI checks after meaningful changes.",
            source="agent-browser",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        SkillPinView(
            id=2,
            project_id=1,
            name="Slack",
            prompt_hint="Use it when the workflow needs operator messaging.",
            source="slack",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    missions = [
        make_mission(
            mission_id=20,
            name="Completed Browser Sweep",
            status="completed",
            instance_id=1,
            last_checkpoint="Browser Verify shipped the UI fix and validation passed.",
        ),
        make_mission(
            mission_id=21,
            name="Slack Escalation",
            status="active",
            instance_id=2,
            suggested_action="Move this mission to a lane with Slack or adjust the repo skillbook.",
        ),
    ]

    ops_mesh = build_ops_mesh(
        [instance_primary, instance_secondary],
        missions,
        [make_project()],
        [],
        [],
        pinned_skills,
        [],
        [],
        [],
        [],
    )

    assert ops_mesh.skills_registry.headline == "Skills registry has live gaps"
    assert ops_mesh.skills_registry.gaps[0].mission_name == "Slack Escalation"
    assert ops_mesh.skills_registry.gaps[0].missing_skills == ["Browser Verify", "Slack"]

    project_registry = ops_mesh.skills_registry.projects[0]
    assert project_registry.project_label == "OpenZues Workspace"
    assert project_registry.pinned_skill_count == 2
    assert project_registry.matched_skill_count == 1
    assert project_registry.missing_skills == ["Slack"]
    assert project_registry.skills[0].name == "Browser Verify"
    assert project_registry.skills[0].successful_run_count == 1

    primary_lane = next(
        lane for lane in ops_mesh.skills_registry.lanes if lane.instance_id == instance_primary.id
    )
    assert primary_lane.relevant_skill_count == 1
    assert primary_lane.gap_count == 0

    fallback_lane = next(
        lane for lane in ops_mesh.skills_registry.lanes if lane.instance_id == instance_secondary.id
    )
    assert fallback_lane.gap_count == 1


def test_build_ops_mesh_integrations_inventory_maps_lane_readiness() -> None:
    instance_primary = make_instance(
        plugins=[{"name": "GitHub", "enabled": True}],
        mcp_servers=[{"name": "GitHub MCP Server", "source": "github", "status": "ready"}],
    )
    instance_secondary = make_instance(
        instance_id=2,
        name="Slack Lane",
        plugins=[{"name": "Slack", "enabled": True}],
    )
    instance_observed = make_instance(
        instance_id=3,
        name="Observed Lane",
        apps=[{"name": "Figma", "enabled": True}],
    )
    integrations = [
        IntegrationView(
            id=1,
            name="GitHub",
            kind="github",
            project_id=1,
            base_url="https://api.github.com",
            auth_scheme="token",
            vault_secret_id=7,
            vault_secret_label="GITHUB_TOKEN",
            secret_label="GITHUB_TOKEN",
            has_secret=True,
            secret_preview="ghp_...1234",
            auth_status="satisfied",
            auth_detail="Vault secret 'GITHUB_TOKEN' is attached.",
            notes="Primary repo automation token.",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        IntegrationView(
            id=2,
            name="Slack",
            kind="slack",
            project_id=1,
            base_url="https://slack.com/api",
            auth_scheme="oauth",
            vault_secret_id=None,
            vault_secret_label=None,
            secret_label=None,
            has_secret=False,
            secret_preview=None,
            auth_status="missing",
            auth_detail="Attach a vault secret before using this integration.",
            notes="Operator escalation route.",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]

    ops_mesh = build_ops_mesh(
        [instance_primary, instance_secondary, instance_observed],
        [
            make_mission(mission_id=30, status="active", instance_id=1),
            make_mission(mission_id=31, status="active", instance_id=2, instance_name="Slack Lane"),
        ],
        [make_project()],
        [],
        [],
        [],
        [],
        integrations,
        [],
        [],
    )

    assert ops_mesh.integrations_inventory.headline == "Integration inventory has live gaps"

    github_item = next(
        item for item in ops_mesh.integrations_inventory.items if item.name == "GitHub"
    )
    assert github_item.tracked is True
    assert github_item.readiness == "ready"
    assert github_item.lane_ready_count == 1
    assert "integration" in github_item.source_kinds
    assert "plugin" in github_item.source_kinds
    assert "mcp_server" in github_item.source_kinds
    assert github_item.capabilities == [
        "mcp server: GitHub MCP Server",
        "plugin: GitHub",
    ]
    assert github_item.lanes[0].status == "ready"

    slack_item = next(
        item for item in ops_mesh.integrations_inventory.items if item.name == "Slack"
    )
    assert slack_item.readiness == "auth_gap"
    assert slack_item.lane_match_count == 1
    assert slack_item.lanes[0].status == "auth_gap"
    assert "Attach a vault secret" in slack_item.recommended_action

    figma_item = next(
        item for item in ops_mesh.integrations_inventory.items if item.name == "Figma"
    )
    assert figma_item.tracked is False
    assert figma_item.readiness == "observed"
    assert figma_item.lane_ready_count == 1
    assert figma_item.source_kinds == ["app"]


def test_build_ops_mesh_integrations_inventory_guides_mempalace_lane_gap() -> None:
    integration = IntegrationView(
        id=3,
        name="MemPalace",
        kind="mempalace",
        project_id=1,
        base_url="python -m mempalace.mcp_server",
        auth_scheme="none",
        vault_secret_id=None,
        vault_secret_label=None,
        secret_label=None,
        has_secret=False,
        secret_preview=None,
        auth_status="satisfied",
        auth_detail=None,
        notes="Shared memory recall for project history.",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    ops_mesh = build_ops_mesh(
        [make_instance()],
        [],
        [make_project()],
        [],
        [],
        [],
        [],
        [integration],
        [],
        [],
    )

    mempalace_item = next(
        item for item in ops_mesh.integrations_inventory.items if item.name == "MemPalace"
    )
    assert mempalace_item.readiness == "lane_gap"
    assert mempalace_item.lane_match_count == 0
    assert "mempalace.mcp_server" in mempalace_item.recommended_action
    assert "project memory" in mempalace_item.recommended_action


class FakeManager:
    def __init__(self, instance: InstanceView | None = None) -> None:
        self._instance = instance or make_instance()
        self.exec_calls: list[dict[str, object]] = []

    async def list_views(self) -> list[InstanceView]:
        return [self._instance]

    async def get(self, instance_id: int):  # noqa: ANN001
        class Runtime:
            def __init__(self, view: InstanceView) -> None:
                self._view = view

            def view(self) -> InstanceView:
                return self._view

        return Runtime(self._instance)

    async def exec_command(
        self,
        instance_id: int,
        *,
        command: list[str],
        cwd: str | None,
        timeout_ms: int | None,
        tty: bool,
    ) -> dict[str, int]:
        self.exec_calls.append(
            {
                "instance_id": instance_id,
                "command": command,
                "cwd": cwd,
                "timeout_ms": timeout_ms,
                "tty": tty,
            }
        )
        return {"exitCode": 0}

    async def start_thread(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("start_thread should not be called in this test.")

    async def start_turn(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("start_turn should not be called in this test.")

    async def start_review(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("start_review should not be called in this test.")


class FakeMissionService:
    def __init__(self, mission_views: list[MissionView] | None = None) -> None:
        self.created_payloads = []
        self._mission_views = mission_views or []

    async def create(self, payload):  # noqa: ANN001
        self.created_payloads.append(payload)
        return make_mission(mission_id=10, task_blueprint_id=payload.task_blueprint_id)

    async def list_views(self) -> list[MissionView]:
        return self._mission_views

    async def get_view(self, mission_id: int) -> MissionView:
        for mission in self._mission_views:
            if mission.id == mission_id:
                return mission
        return make_mission(mission_id=mission_id)


@pytest.mark.asyncio
async def test_ops_mesh_service_launches_due_task(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Ship the next verified slice.",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )
    await database.update_task_blueprint(
        1,
        last_launched_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    assert len(fake_missions.created_payloads) == 1
    payload = fake_missions.created_payloads[0]
    assert payload.task_blueprint_id == 1
    stored = await database.get_task_blueprint(1)
    assert stored is not None
    assert stored["last_status"] == "active"


@pytest.mark.asyncio
async def test_ops_mesh_service_launches_due_mempalace_memory_task(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="Memory Workspace")
    await database.create_integration(
        name="MemPalace",
        kind="mempalace",
        project_id=1,
        base_url="python -m mempalace.mcp_server",
        auth_scheme="none",
        vault_secret_id=None,
        secret_label=None,
        secret_value=None,
        notes="Durable workspace memory.",
        enabled=True,
    )
    cadence_minutes = mempalace_maintenance_cadence_minutes(180)
    await database.create_task_blueprint(
        name=MEMPALACE_MEMORY_TASK_NAME,
        summary=MEMPALACE_MEMORY_TASK_SUMMARY,
        project_id=1,
        instance_id=1,
        cadence_minutes=cadence_minutes,
        enabled=True,
        payload={
            "objective_template": build_mempalace_maintenance_objective(
                project_label="Memory Workspace",
                project_path="C:/workspace",
            ),
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": False,
            "run_verification": False,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": False,
            "auto_recover": False,
            "auto_recover_limit": 0,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )
    await database.update_task_blueprint(
        1,
        last_launched_at=(datetime.now(UTC) - timedelta(minutes=cadence_minutes + 30)).isoformat(),
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    assert len(fake_missions.created_payloads) == 1
    payload = fake_missions.created_payloads[0]
    assert payload.task_blueprint_id == 1
    assert payload.use_builtin_agents is False
    assert payload.run_verification is False
    assert "MemPalace automatic maintenance contract:" in payload.objective
    assert "Do not default to `mempalace compress`" in payload.objective
    assert "MemPalace memory protocol:" in payload.objective
    assert MEMPALACE_WRITEBACK_STATUS_PREFIX in payload.objective
    assert MEMPALACE_WRITEBACK_AT_PREFIX in payload.objective
    assert MEMPALACE_WRITEBACK_SCOPE_PREFIX in payload.objective
    assert MEMPALACE_ROUNDTRIP_STATUS_PREFIX in payload.objective
    assert MEMPALACE_ROUNDTRIP_AT_PREFIX in payload.objective
    assert MEMPALACE_ROUNDTRIP_SCOPE_PREFIX in payload.objective
    assert MEMPALACE_ROUNDTRIP_DETAIL_PREFIX in payload.objective


@pytest.mark.asyncio
async def test_ops_mesh_service_runs_due_scheduled_playbook(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    playbook_id = await database.create_playbook(
        name="Morning status",
        description="Check repo status on a cadence.",
        kind="command",
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "template": "git status --short --branch",
            "cwd": "C:/workspace",
            "model": None,
            "reasoning_effort": None,
            "collaboration_mode": None,
            "timeout_ms": 10000,
            "thread_id": None,
            "default_variables": {},
        },
    )
    await database.update_playbook(
        playbook_id,
        last_run_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
    )

    fake_manager = FakeManager()
    service = OpsMeshService(
        database,
        fake_manager,  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    assert len(fake_manager.exec_calls) == 1
    assert fake_manager.exec_calls[0]["command"] == ["git", "status", "--short", "--branch"]
    stored = await database.get_playbook(playbook_id)
    assert stored is not None
    assert stored["last_status"] == "completed"
    assert "Morning status" in stored["last_result_summary"]


@pytest.mark.asyncio
async def test_ops_mesh_service_auto_chains_continuous_task_after_completed_slice(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="OpenClaw Total Parity Program",
        summary="Keep closing OpenClaw parity until the product is genuinely done.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Keep iterating until parity is complete.",
            "run_until_complete": True,
            "continuation_cooldown_minutes": 5,
            "completion_marker": "PARITY COMPLETE",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "collaboration_mode": None,
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )
    await database.update_task_blueprint(
        1,
        last_launched_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_status="completed",
        last_result_summary="Completed another parity slice. Keep going.",
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    assert len(fake_missions.created_payloads) == 1
    payload = fake_missions.created_payloads[0]
    assert payload.task_blueprint_id == 1
    assert "PARITY COMPLETE" in payload.objective
    stored = await database.get_task_blueprint(1)
    assert stored is not None
    assert stored["last_status"] == "active"


@pytest.mark.asyncio
async def test_ops_mesh_service_stops_continuous_task_when_completion_marker_seen(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="OpenClaw Total Parity Program",
        summary="Keep closing OpenClaw parity until the product is genuinely done.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Keep iterating until parity is complete.",
            "run_until_complete": True,
            "continuation_cooldown_minutes": 5,
            "completion_marker": "PARITY COMPLETE",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "collaboration_mode": None,
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )
    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until parity is complete.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=1,
        thread_id="thread_parity",
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort="high",
        collaboration_mode=None,
        max_turns=8,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        mission_id,
        last_checkpoint="PARITY COMPLETE: OpenClaw parity is fully closed and verified.",
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    stored = await database.get_task_blueprint(1)
    assert stored is not None
    assert stored["enabled"] == 0
    assert stored["last_status"] == "completed"
    assert "PARITY COMPLETE" in stored["last_result_summary"]


@pytest.mark.asyncio
async def test_ops_mesh_service_appends_verified_parity_checkpoint_once(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path=str(tmp_path), label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="OpenClaw Total Parity Program",
        summary="Keep closing OpenClaw parity until the product is genuinely done.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Keep iterating until parity is complete.",
            "run_until_complete": True,
            "completion_marker": "PARITY COMPLETE",
            "cwd": str(tmp_path),
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "collaboration_mode": None,
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )
    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=1,
        thread_id="thread_parity",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort="high",
        collaboration_mode=None,
        max_turns=8,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    summary = (
        "Completed: shipped the next verified parity slice.\n\n"
        "Verified: targeted checks passed and the dashboard rendered cleanly.\n\n"
        "Tool evidence:\n"
        "- debugging: used rg/Get-Content/git diff to inspect the seam.\n"
        "- delegation: used built-in agents for architecture and planning.\n"
        "- browser: not used in this slice because the work stayed in CLI and schema seams.\n\n"
        "Next step: keep pushing the next gateway parity seam.\n\n"
        "Blockers: none."
    )
    await database.update_mission(
        mission_id,
        last_checkpoint=summary,
        last_activity_at=datetime.now(UTC).isoformat(),
    )
    checkpoint_path = tmp_path / "docs" / "openclaw-parity-checkpoint-2026-04-10.md"
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        parity_checkpoint_path=checkpoint_path,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})
    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    content = checkpoint_path.read_text(encoding="utf-8")
    assert "## Update: OpenClaw Total Parity Program" in content
    assert summary in content
    assert content.count(f"<!-- OPENZUES_PARITY_MISSION:{mission_id} -->") == 1


@pytest.mark.asyncio
async def test_ops_mesh_service_skips_verified_parity_checkpoint_without_tool_evidence(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=None,
        thread_id="thread_parity",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort="high",
        collaboration_mode=None,
        max_turns=8,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        mission_id,
        last_checkpoint=(
            "Completed: shipped the next verified parity slice.\n\n"
            "Verified: targeted checks passed.\n\n"
            "Next step: keep pushing the next gateway parity seam.\n\n"
            "Blockers: none."
        ),
        last_activity_at=datetime.now(UTC).isoformat(),
    )
    checkpoint_path = tmp_path / "docs" / "openclaw-parity-checkpoint-2026-04-10.md"
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        parity_checkpoint_path=checkpoint_path,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert not checkpoint_path.exists()


@pytest.mark.asyncio
async def test_ops_mesh_service_skips_unverified_parity_checkpoint_append(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    mission_id = await database.create_mission(
        name="OpenClaw Total Parity Program",
        objective="Keep iterating until OpenClaw parity is complete.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=None,
        thread_id="thread_parity",
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort="high",
        collaboration_mode=None,
        max_turns=8,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.update_mission(
        mission_id,
        last_checkpoint="Completed: made progress, but verification has not landed yet.",
        last_activity_at=datetime.now(UTC).isoformat(),
    )
    checkpoint_path = tmp_path / "docs" / "openclaw-parity-checkpoint-2026-04-10.md"
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        parity_checkpoint_path=checkpoint_path,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert not checkpoint_path.exists()


@pytest.mark.asyncio
async def test_ops_mesh_service_emits_derived_inbox_notifications_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Inbox Hook",
        kind="webhook",
        target="https://example.invalid/inbox",
        events=["ops/inbox/*"],
        conversation_target=None,
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )

    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    mission = make_mission(
        mission_id=10,
        name="Approval Ship",
        status="blocked",
        phase="approval",
        last_error="Waiting for approval: apply a workspace patch.",
        last_checkpoint=None,
        suggested_action="Review the approval and let the mission continue.",
    )
    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([mission]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()
    await service.tick_once()

    assert len(deliveries) == 1
    event_type, payload = deliveries[0]
    route_row = (await database.list_notification_routes())[0]
    assert event_type == "ops/inbox/approval-required"
    assert payload["kind"] == "approval_required"
    assert payload["missionId"] == 10
    assert route_row["last_result"] == "Delivered ops/inbox/approval-required"


@pytest.mark.asyncio
async def test_ops_mesh_service_emits_reflex_and_task_attention_notifications(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Inbox Hook",
        kind="webhook",
        target="https://example.invalid/inbox",
        events=["ops/inbox/*"],
        conversation_target=None,
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_task_blueprint(
        name="Repair release sweep",
        summary="Keep the scheduled release flow healthy.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Repair the scheduled release lane and leave a checkpoint.",
            "cwd": "C:/workspace",
            "model": "gpt-5.4",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 2,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
        },
    )

    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    missions = [
        make_mission(
            mission_id=41,
            task_blueprint_id=1,
            name="Repair release sweep",
            status="failed",
            failure_count=2,
            last_checkpoint=None,
            last_error="Verification step failed in the release workflow.",
            suggested_action=(
                "Inspect the failed run and repair the schedule before relaunching it."
            ),
        ),
        make_mission(
            mission_id=42,
            name="Burning Sweep",
            status="active",
            last_checkpoint=None,
            total_tokens=350000,
            last_activity_at=(datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
            suggested_action="Run the verification spike before the thread sprawls.",
        ),
    ]
    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService(missions),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()
    await service.tick_once()

    delivered_types = {event_type for event_type, _ in deliveries}
    assert "ops/inbox/mission-failed" in delivered_types
    assert "ops/inbox/task-attention" in delivered_types
    assert "ops/inbox/reflex-armed" in delivered_types
    assert sum(1 for event_type, _ in deliveries if event_type == "ops/inbox/task-attention") == 1
    assert sum(1 for event_type, _ in deliveries if event_type == "ops/inbox/reflex-armed") == 1


@pytest.mark.asyncio
async def test_test_notification_route_delivers_webhook_ping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
        name="Inbox Hook",
        kind="webhook",
        target="https://example.invalid/inbox",
        events=["ops/inbox/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.test_notification_route(route_id)
    route_row = next(
        row for row in await database.list_notification_routes() if int(row["id"]) == route_id
    )

    assert result.ok is True
    assert result.event_type == "ops/inbox/test"
    assert result.route.id == route_id
    assert deliveries[0][0] == "ops/inbox/test"
    assert deliveries[0][1]["test"] is True
    assert deliveries[0][1]["conversationTarget"]["peer_id"] == "deploy-room"
    assert deliveries[0][1]["routeConversationTarget"]["channel"] == "slack"
    assert route_row["last_result"] == "Delivered ops/inbox/test (test)"
    assert route_row["last_error"] is None


@pytest.mark.asyncio
async def test_test_notification_route_records_outbound_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
        name="Deploy Hook",
        kind="webhook",
        target="https://example.invalid/deploy",
        events=["ops/inbox/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, event_type, event, secret_token

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.test_notification_route(route_id)
    deliveries = await service.list_outbound_delivery_views()

    assert result.delivery is not None
    assert len(deliveries) == 1
    assert deliveries[0].id == result.delivery.id
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].test_delivery is True
    assert deliveries[0].route_scope.route_match == "test"
    assert deliveries[0].message_summary == "OpenZues test delivery ping."
    assert deliveries[0].conversation_target is not None
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["summary"] == "OpenZues test delivery ping."
    assert deliveries[0].event_payload["routeConversationTarget"]["peer_id"] == "deploy-room"
    assert "slack" in deliveries[0].conversation_target.summary
    assert "workspace-bot" in deliveries[0].conversation_target.summary
    assert "deploy-room" in deliveries[0].conversation_target.summary


@pytest.mark.asyncio
async def test_ops_mesh_service_records_outbound_delivery_for_matching_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Deploy Room",
        kind="webhook",
        target="https://example.invalid/deploy",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service._deliver_notifications(
        "mission/updated",
        {
            "summary": "Mission resumed on the routed channel.",
            "sessionKey": "route-session-1",
            "conversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
    )
    outbound_deliveries = await service.list_outbound_delivery_views()

    assert len(deliveries) == 1
    assert deliveries[0][0] == "mission/updated"
    assert deliveries[0][1]["routeMatch"] == "peer"
    assert outbound_deliveries[0].session_key == "route-session-1"
    assert outbound_deliveries[0].delivery_state == "delivered"
    assert outbound_deliveries[0].route_scope.route_match == "peer"
    assert outbound_deliveries[0].conversation_target is not None
    assert outbound_deliveries[0].conversation_target.peer_id == "deploy-room"
    assert outbound_deliveries[0].event_payload is not None
    assert outbound_deliveries[0].event_payload["routeMatch"] == "peer"
    assert outbound_deliveries[0].event_payload["summary"] == "Mission resumed on the routed channel."


@pytest.mark.asyncio
async def test_ops_mesh_service_filters_notification_routes_by_conversation_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Deploy Room",
        kind="webhook",
        target="https://example.invalid/deploy",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_notification_route(
        name="QA Room",
        kind="webhook",
        target="https://example.invalid/qa",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "qa-room",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_notification_route(
        name="Workspace Account",
        kind="webhook",
        target="https://example.invalid/account",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_notification_route(
        name="Slack Channel Catchall",
        kind="webhook",
        target="https://example.invalid/channel",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    await database.create_notification_route(
        name="Other Account",
        kind="webhook",
        target="https://example.invalid/other-account",
        events=["mission/*"],
        conversation_target={
            "channel": "slack",
            "account_id": "other-bot",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )
    mission_id = await database.create_mission(
        name="Deploy parity slice",
        objective="Ship the next routed parity seam.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread_route",
        session_key="launch:mode:workspace_affinity:task:7:operator:1:channel:slack",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        cwd=str(tmp_path),
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
        toolsets=[],
    )
    deliveries: list[tuple[str, str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del secret_token
        deliveries.append((str(route.get("name") or ""), event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert [item[0] for item in deliveries] == [
        "Deploy Room",
        "Workspace Account",
        "Slack Channel Catchall",
    ]
    assert [item[2]["routeMatch"] for item in deliveries] == ["peer", "account", "channel"]
    assert deliveries[0][1] == "mission/completed"
    assert deliveries[0][2]["conversationTarget"]["peer_id"] == "deploy-room"
    assert deliveries[0][2]["routeConversationTarget"]["peer_id"] == "deploy-room"
    assert deliveries[1][2]["routeConversationTarget"]["account_id"] == "workspace-bot"
    assert deliveries[2][2]["routeConversationTarget"]["channel"] == "slack"


@pytest.mark.asyncio
async def test_capture_lane_snapshot_includes_mission_state(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    instance = make_instance(
        unresolved_requests=[
            {
                "id": 55,
                "request_id": "req_approval",
                "thread_id": "thread_approval",
                "method": "approval/request",
                "payload": {"tool": "shell_command"},
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
                "resolved_at": None,
            }
        ]
    )
    mission = make_mission(
        mission_id=22,
        name="Lane Snapshot Mission",
        status="active",
        phase="executing",
        thread_id="thread_approval",
        current_command="pytest -q",
        command_count=7,
        total_tokens=3210,
        last_checkpoint="Snapshot-ready checkpoint.",
        suggested_action="Let the command finish, then checkpoint.",
    )
    service = OpsMeshService(
        database,
        FakeManager(instance),  # type: ignore[arg-type]
        FakeMissionService([mission]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    snapshot = await service.capture_lane_snapshot(1)

    assert snapshot.approvals_pending_count == 1
    assert snapshot.mission_id == 22
    assert snapshot.mission_name == "Lane Snapshot Mission"
    assert snapshot.thread_id == "thread_approval"
    assert snapshot.mission_status == "active"
    assert snapshot.phase == "executing"
    assert snapshot.current_command == "pytest -q"
    assert snapshot.command_burn == 7
    assert snapshot.token_burn == 3210
    assert snapshot.last_checkpoint_summary == "Snapshot-ready checkpoint."
    assert snapshot.continuity_state is not None
    assert snapshot.continuity_score is not None
    assert snapshot.safest_handoff is not None


def test_dashboard_ops_mesh_crud_round_trip(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        ).json()
        vault_secret_response = client.post(
            "/api/vault-secrets",
            json={
                "label": "Shared automation token",
                "kind": "token",
                "value": "super-secret-token",
                "notes": "Reusable across GitHub and webhook delivery.",
            },
        )
        vault_secret = vault_secret_response.json()

        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Daily Ship",
                "summary": "Ship the next slice.",
                "objective_template": "Ship the next verified slice.",
                "instance_id": instance["id"],
                "project_id": project["id"],
                "cadence_minutes": 60,
                "cwd": str(tmp_path),
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 2,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "allow_auto_reflexes": True,
                "auto_recover": True,
                "auto_recover_limit": 2,
                "reflex_cooldown_seconds": 900,
                "allow_failover": True,
                "enabled": True,
            },
        )
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Ops Webhook",
                "kind": "webhook",
                "target": "https://example.invalid/webhook",
                "events": ["task/*", "mission/completed"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
                "secret_header_name": "X-OpenZues-Key",
                "vault_secret_id": vault_secret["id"],
            },
        )
        integration_response = client.post(
            "/api/integrations",
            json={
                "name": "GitHub",
                "kind": "github",
                "project_id": project["id"],
                "base_url": "https://api.github.com",
                "auth_scheme": "token",
                "vault_secret_id": vault_secret["id"],
                "secret_label": "GITHUB_TOKEN",
                "notes": "Primary repo automation token.",
                "enabled": True,
            },
        )
        skill_response = client.post(
            "/api/skill-pins",
            json={
                "project_id": project["id"],
                "name": "Browser Verify",
                "prompt_hint": "Use it for browser checks after meaningful UI changes.",
                "source": "agent-browser",
                "enabled": True,
            },
        )
        snapshot_response = client.post(f"/api/instances/{instance['id']}/snapshots")
        delete_secret_response = client.delete(f"/api/vault-secrets/{vault_secret['id']}")
        dashboard = client.get("/api/dashboard").json()

    assert vault_secret_response.status_code == 200
    assert task_response.status_code == 200
    assert route_response.status_code == 200
    route_payload = route_response.json()
    assert integration_response.status_code == 200
    assert skill_response.status_code == 200
    assert snapshot_response.status_code == 200
    assert delete_secret_response.status_code == 409
    assert dashboard["ops_mesh"]["task_inbox"]["tasks"]
    assert dashboard["ops_mesh"]["task_inbox"]["items"][0]["kind"] == "task_due"
    assert dashboard["ops_mesh"]["notification_routes"][0]["has_secret"] is True
    assert dashboard["ops_mesh"]["notification_routes"][0]["vault_secret_label"] == (
        "Shared automation token"
    )
    route_summary = route_payload["conversation_target"]["summary"]
    assert "slack" in route_summary
    assert "workspace-bot" in route_summary
    assert "deploy-room" in route_summary
    dashboard_route_summary = dashboard["ops_mesh"]["notification_routes"][0][
        "conversation_target"
    ]["summary"]
    assert "slack" in dashboard_route_summary
    assert "workspace-bot" in dashboard_route_summary
    assert "deploy-room" in dashboard_route_summary
    assert dashboard["ops_mesh"]["integrations"][0]["secret_preview"]
    assert dashboard["ops_mesh"]["integrations"][0]["vault_secret_label"] == (
        "Shared automation token"
    )
    assert dashboard["ops_mesh"]["integrations"][0]["auth_status"] == "satisfied"
    assert dashboard["ops_mesh"]["auth_posture"]["satisfied_count"] == 1
    assert dashboard["ops_mesh"]["integrations_inventory"]["tracked_count"] == 1
    assert dashboard["ops_mesh"]["vault_secrets"][0]["usage_count"] == 2
    assert dashboard["ops_mesh"]["skills_registry"]["projects"][0]["project_label"] == (
        "OpenZues Workspace"
    )
    assert any(
        skill["name"] == "Browser Verify"
        for skillbook in dashboard["ops_mesh"]["skillbooks"]
        for skill in skillbook["skills"]
    )
    assert dashboard["ops_mesh"]["lane_snapshots"]
    assert dashboard["ops_mesh"]["lane_snapshots"][0]["approvals_pending_count"] == 0


def test_notification_route_test_api_updates_route_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deliveries: list[str] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del route, event, secret_token
        deliveries.append(event_type)

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    with make_client(tmp_path) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Ops Webhook",
                "kind": "webhook",
                "target": "https://example.invalid/webhook",
                "events": ["ops/inbox/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        route_id = route_response.json()["id"]
        test_response = client.post(f"/api/notification-routes/{route_id}/test")
        dashboard = client.get("/api/dashboard").json()

    assert route_response.status_code == 200
    assert test_response.status_code == 200
    payload = test_response.json()
    assert payload["ok"] is True
    assert payload["event_type"] == "ops/inbox/test"
    assert deliveries == ["ops/inbox/test"]
    route_summary = payload["route"]["conversation_target"]["summary"]
    assert "slack" in route_summary
    assert "workspace-bot" in route_summary
    assert "deploy-room" in route_summary
    assert payload["delivery"]["delivery_state"] == "delivered"
    assert payload["delivery"]["route_scope"]["route_match"] == "test"
    assert payload["delivery"]["conversation_target"]["peer_id"] == "deploy-room"
    assert payload["delivery"]["event_payload"]["routeConversationTarget"]["peer_id"] == "deploy-room"
    assert dashboard["ops_mesh"]["notification_routes"][0]["last_result"] == (
        "Delivered ops/inbox/test (test)"
    )
    assert dashboard["ops_mesh"]["outbound_deliveries"][0]["delivery_state"] == "delivered"
    assert dashboard["ops_mesh"]["outbound_deliveries"][0]["route_scope"]["route_match"] == "test"
    assert (
        dashboard["ops_mesh"]["outbound_deliveries"][0]["event_payload"]["summary"]
        == "OpenZues test delivery ping."
    )


@pytest.mark.asyncio
async def test_ops_mesh_service_migrates_legacy_secret_records(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    vault = make_vault(database, tmp_path)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        vault,
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    integration_id = await database.create_integration(
        name="Legacy GitHub",
        kind="github",
        project_id=None,
        base_url="https://api.github.com",
        auth_scheme="token",
        vault_secret_id=None,
        secret_label="LEGACY_GITHUB_TOKEN",
        secret_value="ghp_legacy_1234",
        notes="Migrated legacy record.",
        enabled=True,
    )
    route_id = await database.create_notification_route(
        name="Legacy Hook",
        kind="webhook",
        target="https://example.invalid/legacy",
        events=["task/*"],
        enabled=True,
        secret_header_name="X-Legacy-Key",
        secret_token="legacy-route-token",
        vault_secret_id=None,
    )

    integrations = await service.list_integration_views()
    routes = await service.list_notification_route_views()
    integration_row = await database.get_integration(integration_id)
    route_row = next(
        row for row in await database.list_notification_routes() if int(row["id"]) == route_id
    )

    assert integrations[0].vault_secret_label == "LEGACY_GITHUB_TOKEN"
    assert integrations[0].auth_status == "satisfied"
    assert routes[0].vault_secret_label == "Legacy Hook webhook secret"
    assert integration_row is not None
    assert integration_row["secret_value"] is None
    assert integration_row["vault_secret_id"] is not None
    assert route_row["secret_token"] is None
    assert route_row["vault_secret_id"] is not None
    assert (
        await vault.get_secret_value(int(integration_row["vault_secret_id"])) == "ghp_legacy_1234"
    )
    assert await vault.get_secret_value(int(route_row["vault_secret_id"])) == "legacy-route-token"
