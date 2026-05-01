from __future__ import annotations

import asyncio
import io
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from openzues.app import create_app
from openzues.database import Database
from openzues.schemas import (
    ConversationTargetView,
    InstanceView,
    IntegrationView,
    MissionStatus,
    MissionView,
    NotificationRouteCreate,
    PlaybookView,
    ProjectView,
    SkillPinView,
)
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.gateway_canvas_documents import create_canvas_document
from openzues.services.gateway_cron import build_gateway_cron_task_blueprint
from openzues.services.gateway_message_actions import GatewayMessageActionDispatchRequest
from openzues.services.gateway_outbound_runtime import (
    GatewayOutboundRuntimeMessageRequest,
    GatewayOutboundRuntimePollRequest,
    GatewayOutboundRuntimeService,
    GatewayOutboundRuntimeUnavailableError,
)
from openzues.services.gateway_wake import GatewayWakeService
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
from openzues.services.ops_mesh import (
    OUTBOUND_DELIVERY_MAX_RETRIES,
    OpsMeshService,
    _saved_outbound_delivery_replay_message,
    _serialize_task,
    build_ops_mesh,
)
from openzues.services.session_keys import build_launch_session_key, resolve_thread_session_keys
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


def test_post_json_webhook_includes_provider_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(*args: object, timeout: int = 10) -> object:
        del args, timeout
        raise HTTPError(
            "https://slack.com/api/chat.postMessage",
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":"channel_not_found","detail":"missing channel"}'),
        )

    monkeypatch.setattr("openzues.services.ops_mesh.urlopen", fake_urlopen)
    service = object.__new__(OpsMeshService)

    with pytest.raises(RuntimeError) as exc_info:
        service._post_json_webhook(
            "https://slack.com/api/chat.postMessage",
            {"channel": "missing", "text": "test"},
        )

    assert str(exc_info.value) == "Webhook returned 400: channel_not_found"


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
async def test_ops_mesh_service_launches_cron_announce_target_into_mission_draft(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

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
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Cron Announce Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Route this cron run through the announce target.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "7200373102",
                    "accountId": "coordinator",
                },
            }
        )
    )

    await service.run_task_blueprint_now(task.id, trigger="schedule")

    assert len(fake_missions.created_payloads) == 1
    payload = fake_missions.created_payloads[0]
    assert payload.conversation_target is not None
    assert payload.conversation_target.channel == "telegram"
    assert payload.conversation_target.account_id == "coordinator"
    assert payload.conversation_target.peer_kind == "channel"
    assert payload.conversation_target.peer_id == "7200373102"


@pytest.mark.asyncio
async def test_ops_mesh_service_posts_explicit_cron_webhook_delivery_for_completed_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Cron Webhook Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Ship the cron webhook delivery seam.",
                },
                "delivery": {
                    "mode": "webhook",
                    "to": "https://example.invalid/cron-finished",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Cron Webhook Delivery",
        objective="Ship the cron webhook delivery seam.",
        status="completed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_webhook",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="Webhook summary ready.",
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    webhook_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self, secret_header_name, secret_token
        webhook_calls.append((target, payload))

    monkeypatch.setattr(
        OpsMeshService,
        "_post_json_webhook",
        fake_post_json_webhook,
        raising=False,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert webhook_calls == [
        (
            "https://example.invalid/cron-finished",
            {
                "action": "finished",
                "missionId": mission_id,
                "taskId": task.id,
                "jobId": f"task-blueprint:{task.id}",
                "jobName": "Cron Webhook Delivery",
                "status": "ok",
                "summary": "Webhook summary ready.",
            },
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_id is None
    assert deliveries[0].route_kind == "webhook"
    assert deliveries[0].route_target == "https://example.invalid/cron-finished"
    assert deliveries[0].event_type == "cron/finished"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["jobId"] == f"task-blueprint:{task.id}"
    assert deliveries[0].event_payload["summary"] == "Webhook summary ready."


@pytest.mark.asyncio
async def test_ops_mesh_service_posts_legacy_notify_cron_webhook_when_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        cron_webhook_url="https://legacy.example.invalid/cron-finished",
        cron_webhook_token="cron-webhook-token",
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Legacy Notify Webhook",
                "enabled": True,
                "notify": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "main",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "systemEvent",
                    "text": "Use the legacy cron webhook fallback.",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Legacy Notify Webhook",
        objective="Use the legacy cron webhook fallback.",
        status="completed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_legacy_notify",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="Legacy webhook summary ready.",
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    webhook_calls: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self
        webhook_calls.append((target, payload, secret_header_name, secret_token))

    monkeypatch.setattr(
        OpsMeshService,
        "_post_json_webhook",
        fake_post_json_webhook,
        raising=False,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert webhook_calls == [
        (
            "https://legacy.example.invalid/cron-finished",
            {
                "action": "finished",
                "missionId": mission_id,
                "taskId": task.id,
                "jobId": f"task-blueprint:{task.id}",
                "jobName": "Legacy Notify Webhook",
                "status": "ok",
                "summary": "Legacy webhook summary ready.",
            },
            "Authorization",
            "Bearer cron-webhook-token",
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_target == "https://legacy.example.invalid/cron-finished"
    assert deliveries[0].event_type == "cron/finished"
    assert deliveries[0].delivery_state == "delivered"


@pytest.mark.asyncio
async def test_ops_mesh_service_skips_explicit_cron_webhook_delivery_without_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Silent Cron Webhook",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Do not send a webhook without a real summary.",
                },
                "delivery": {
                    "mode": "webhook",
                    "to": "https://example.invalid/cron-finished",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Silent Cron Webhook",
        objective="Do not send a webhook without a real summary.",
        status="completed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_webhook_silent",
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
    await database.update_mission(
        mission_id,
        last_checkpoint=None,
        last_error=None,
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    webhook_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self, secret_header_name, secret_token
        webhook_calls.append((target, payload))

    monkeypatch.setattr(
        OpsMeshService,
        "_post_json_webhook",
        fake_post_json_webhook,
        raising=False,
    )

    await service.handle_mission_event("mission/completed", {"missionId": mission_id})

    assert webhook_calls == []
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert deliveries == []


@pytest.mark.asyncio
async def test_ops_mesh_service_posts_cron_failure_destination_webhook_for_failed_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Failure Destination Webhook",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Send a failure destination webhook on isolated cron failure.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "19098680",
                    "failureDestination": {
                        "mode": "webhook",
                        "to": "https://example.invalid/failure-destination",
                    },
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Failure Destination Webhook",
        objective="Send a failure destination webhook on isolated cron failure.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_destination",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="delivery failed",
        last_error=None,
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    webhook_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self, secret_header_name, secret_token
        webhook_calls.append((target, payload))

    monkeypatch.setattr(
        OpsMeshService,
        "_post_json_webhook",
        fake_post_json_webhook,
        raising=False,
    )

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert webhook_calls == [
        (
            "https://example.invalid/failure-destination",
            {
                "missionId": mission_id,
                "taskId": task.id,
                "jobId": f"task-blueprint:{task.id}",
                "jobName": "Failure Destination Webhook",
                "message": 'Cron job "Failure Destination Webhook" failed: unknown error',
                "status": "error",
                "error": None,
            },
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_target == "https://example.invalid/failure-destination"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"


@pytest.mark.asyncio
async def test_ops_mesh_service_applies_cron_failure_alert_threshold_and_cooldown(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    alert_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        alert_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Failure Alert Threshold",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Send a thresholded cron failure alert.",
                },
                "failureAlert": {
                    "after": 2,
                    "cooldownMs": 60_000,
                    "channel": "last",
                },
            }
        )
    )
    session_key = "agent:main:telegram:direct:19098680"
    started_at = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)

    async def record_failed_run(offset_seconds: int) -> dict[str, object]:
        launched_at = started_at + timedelta(seconds=offset_seconds)
        ended_at = launched_at + timedelta(seconds=5)
        await database.update_task_blueprint(
            task.id,
            last_launched_at=launched_at.isoformat(),
            last_status="active",
        )
        mission_id = await database.create_mission(
            name="Failure Alert Threshold",
            objective="Send a thresholded cron failure alert.",
            status="failed",
            instance_id=task.instance_id or 1,
            project_id=task.project_id,
            task_blueprint_id=task.id,
            thread_id="thread_cron_failure_alert",
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
        await database.update_mission(
            mission_id,
            last_checkpoint=None,
            last_error="request timed out",
            last_activity_at=ended_at.isoformat(),
            session_key=session_key,
        )

        await service.handle_mission_event("mission/failed", {"missionId": mission_id})
        stored = await database.get_task_blueprint(task.id)
        assert stored is not None
        return stored["cron_state"]

    first_state = await record_failed_run(0)

    assert first_state["consecutiveErrors"] == 1
    assert first_state["lastRunStatus"] == "error"
    assert first_state["lastStatus"] == "error"
    assert first_state["lastError"] == "request timed out"
    assert first_state["lastErrorReason"] == "timeout"
    assert first_state["lastDurationMs"] == 5_000
    assert first_state["lastDeliveryStatus"] == "not-requested"
    assert "lastFailureAlertAtMs" not in first_state
    assert alert_deliveries == []

    second_state = await record_failed_run(30)

    assert second_state["consecutiveErrors"] == 2
    assert isinstance(second_state["lastFailureAlertAtMs"], int)
    assert alert_deliveries == [
        (
            session_key,
            'Cron job "Failure Alert Threshold" failed 2 times\n'
            "Last error: request timed out",
        )
    ]

    third_state = await record_failed_run(45)

    assert third_state["consecutiveErrors"] == 3
    assert third_state["lastFailureAlertAtMs"] == second_state["lastFailureAlertAtMs"]
    assert len(alert_deliveries) == 1


@pytest.mark.asyncio
async def test_ops_mesh_service_applies_global_cron_failure_alert_threshold_and_cooldown(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    alert_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        alert_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
        cron_failure_alert={
            "enabled": True,
            "after": 2,
            "cooldownMs": 60_000,
        },
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Global Failure Alert",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Use the global cron failure alert config.",
                },
            }
        )
    )
    session_key = "agent:main:telegram:direct:19098680"
    started_at = datetime(2026, 4, 29, 13, 0, tzinfo=UTC)

    async def record_failed_run(offset_seconds: int) -> dict[str, object]:
        launched_at = started_at + timedelta(seconds=offset_seconds)
        ended_at = launched_at + timedelta(seconds=5)
        await database.update_task_blueprint(
            task.id,
            last_launched_at=launched_at.isoformat(),
            last_status="active",
        )
        mission_id = await database.create_mission(
            name="Global Failure Alert",
            objective="Use the global cron failure alert config.",
            status="failed",
            instance_id=task.instance_id or 1,
            project_id=task.project_id,
            task_blueprint_id=task.id,
            thread_id="thread_global_cron_failure_alert",
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
        await database.update_mission(
            mission_id,
            last_checkpoint=None,
            last_error="server overloaded",
            last_activity_at=ended_at.isoformat(),
            session_key=session_key,
        )

        await service.handle_mission_event("mission/failed", {"missionId": mission_id})
        stored = await database.get_task_blueprint(task.id)
        assert stored is not None
        return stored["cron_state"]

    first_state = await record_failed_run(0)

    assert first_state["consecutiveErrors"] == 1
    assert "lastFailureAlertAtMs" not in first_state
    assert alert_deliveries == []

    second_state = await record_failed_run(30)

    assert second_state["consecutiveErrors"] == 2
    assert isinstance(second_state["lastFailureAlertAtMs"], int)
    assert alert_deliveries == [
        (
            session_key,
            'Cron job "Global Failure Alert" failed 2 times\n'
            "Last error: server overloaded",
        )
    ]

    third_state = await record_failed_run(45)

    assert third_state["consecutiveErrors"] == 3
    assert third_state["lastFailureAlertAtMs"] == second_state["lastFailureAlertAtMs"]
    assert len(alert_deliveries) == 1


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_last_channel_cron_failure_destination_to_session_key(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Failure Destination Session Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Send a failure destination session delivery on isolated cron failure."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "19098680",
                    "failureDestination": {
                        "mode": "announce",
                        "channel": "last",
                    },
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Failure Destination Session Delivery",
        objective="Send a failure destination session delivery on isolated cron failure.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_destination_session_delivery",
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
    session_key = "agent:main:telegram:direct:123:thread:99"
    await database.update_mission(
        mission_id,
        last_checkpoint="failure destination session delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key=session_key,
    )

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert session_deliveries == [
        (
            session_key,
            '\u26a0\ufe0f Cron job "Failure Destination Session Delivery" failed: lane timed out',
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "session"
    assert deliveries[0].route_target == session_key
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == session_key


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_explicit_cron_failure_to_announce_target(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Explicit Announce Failure Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Deliver the cron failure directly to the explicit announce target."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "deploy-room",
                    "accountId": "coordinator",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Explicit Announce Failure Delivery",
        objective=(
            "Deliver the cron failure directly to the explicit announce target."
        ),
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_explicit_announce_failure_delivery",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="explicit announce delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:explicit-announce-failure-route",
    )

    await service.handle_mission_event(
        "mission/failed",
        {"missionId": mission_id},
    )

    expected_session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    assert session_deliveries == [
        (
            expected_session_key,
            '\u26a0\ufe0f Cron job "Explicit Announce Failure Delivery" failed: lane timed out',
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "announce"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == expected_session_key
    assert deliveries[0].route_scope.route_match == "explicitTarget"
    assert deliveries[0].conversation_target is not None
    assert deliveries[0].conversation_target.channel == "telegram"
    assert deliveries[0].conversation_target.account_id == "coordinator"
    assert deliveries[0].conversation_target.peer_kind == "channel"
    assert deliveries[0].conversation_target.peer_id == "deploy-room"
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["sessionKey"] == expected_session_key
    payload_conversation_target = deliveries[0].event_payload["conversationTarget"]
    assert payload_conversation_target["channel"] == "telegram"
    assert payload_conversation_target["account_id"] == "coordinator"
    assert payload_conversation_target["peer_kind"] == "channel"
    assert payload_conversation_target["peer_id"] == "deploy-room"
    assert str(payload_conversation_target["summary"]).startswith("telegram")


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_known_channel_default_account(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-default-account"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Account Inventory",
        kind="webhook",
        target="https://example.invalid/slack-account",
        events=["mission/completed"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        return {"messageId": "42"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship parity.",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)
    delivery_views = await service.list_outbound_delivery_views(limit=1)

    assert result == {
        "ok": True,
        "channel": "slack",
        "messageId": "42",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
    }
    assert session_deliveries == [(expected_session_key, "Ship parity.")]
    assert delivery is not None
    assert delivery["route_kind"] == "announce"
    assert delivery["session_key"] == expected_session_key
    assert delivery["conversation_target"]["account_id"] == "workspace-bot"
    assert delivery["event_payload"]["accountId"] == "workspace-bot"
    assert delivery["route_scope"]["resolved_account_id"] == "workspace-bot"
    assert delivery["delivery_message_id"] == "42"
    assert delivery_views[0].delivery_message_id == "42"
    assert delivery_views[0].transport is not None
    assert delivery_views[0].transport.runtime == "session-backed"
    assert delivery_views[0].transport.channel == "slack"
    assert delivery_views[0].transport.target == "channel:C123"
    assert delivery_views[0].transport.account_id == "workspace-bot"
    assert delivery_views[0].transport.session_key == expected_session_key


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_shared_outbound_runtime_owner(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-runtime-owner"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    runtime_calls: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        runtime_calls.append((session_key, message))
        return {"messageId": "runtime-42"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            session_deliverer=fake_session_delivery
        ),
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship parity through the runtime owner.",
        account_id="default",
        thread_id="1710000000.9999",
        idempotency_key="idem-runtime-owner-send",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-runtime-owner-send",
        "channel": "slack",
        "messageId": "runtime-42",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert runtime_calls == [
        (expected_session_key, "Ship parity through the runtime owner."),
    ]
    assert delivery is not None
    assert delivery["delivery_message_id"] == "runtime-42"
    assert delivery["route_scope"]["idempotency_key"] == "idem-runtime-owner-send"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_prefers_provider_runtime(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-provider-owner"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, str]:
        provider_requests.append(request)
        return {"messageId": "provider-send-42"}

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        raise AssertionError(f"session fallback should not run: {session_key} {message}")

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            session_deliverer=fake_session_delivery,
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship parity.",
        media_urls=["https://example.com/parity.png"],
        gif_playback=False,
        account_id="default",
        agent_id="release-bot",
        thread_id="1710000000.9999",
        gateway_client_scopes=["operator.write"],
        idempotency_key="idem-provider-runtime-send",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="default",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-provider-runtime-send",
        "channel": "slack",
        "messageId": "provider-send-42",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert provider_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="slack",
            target="channel:C123",
            message=(
                "Ship parity.\n\n"
                "Media:\n"
                "1. https://example.com/parity.png\n\n"
                "Settings: gifPlayback=false"
            ),
            media_urls=("https://example.com/parity.png",),
            gif_playback=False,
            account_id="default",
            thread_id="1710000000.9999",
            session_key=expected_session_key,
            agent_id="release-bot",
            gateway_client_scopes=("operator.write",),
        )
    ]
    assert delivery is not None
    assert delivery["delivery_state"] == "delivered"
    assert delivery["delivery_message_id"] == "provider-send-42"
    assert delivery["event_payload"]["agentId"] == "release-bot"
    assert delivery["event_payload"]["gatewayClientScopes"] == ["operator.write"]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_mirrors_explicit_session_key(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-source-session"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, str]:
        provider_requests.append(request)
        return {"messageId": "provider-source-session-42"}

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        raise AssertionError(f"session fallback should not run: {session_key} {message}")

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            session_deliverer=fake_session_delivery,
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Mirror source session.",
        account_id="workspace-bot",
        session_key="agent:Work:Slack:channel:C123",
        idempotency_key="idem-provider-source-session",
    )

    expected_source_session_key = "agent:work:slack:channel:c123"
    expected_target_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-provider-source-session",
        "channel": "slack",
        "messageId": "provider-source-session-42",
        "sessionKey": expected_target_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_source_session_key,
        },
    }
    assert provider_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="slack",
            target="channel:C123",
            message="Mirror source session.",
            account_id="workspace-bot",
            session_key=expected_source_session_key,
        )
    ]
    assert delivery is not None
    assert delivery["session_key"] == expected_target_session_key
    assert delivery["event_payload"]["sessionKey"] == expected_target_session_key
    assert delivery["event_payload"]["sourceSessionKey"] == expected_source_session_key
    assert delivery["route_scope"]["source_session_key"] == expected_source_session_key
    assert delivery["route_scope"]["runtime_session_key"] == expected_source_session_key


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_forwards_requester_context(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-requester-context"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, str]:
        provider_requests.append(request)
        return {"messageId": "provider-requester-context-42"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Carry requester context.",
        account_id="destination-workspace",
        session_key="agent:work:slack:channel:C123",
        requester_session_key="agent:main:discord:channel:ops",
        requester_account_id="source-workspace",
        requester_sender_id="discord-user-1",
        requester_sender_name="Alice",
        requester_sender_username="alice_u",
        requester_sender_e164="+15551234567",
        idempotency_key="idem-provider-requester-context",
    )

    expected_runtime_session_key = "agent:work:slack:channel:c123"
    expected_target_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="destination-workspace",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["sessionKey"] == expected_target_session_key
    assert result["transport"]["sessionKey"] == expected_runtime_session_key
    assert provider_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="slack",
            target="channel:C123",
            message="Carry requester context.",
            account_id="destination-workspace",
            session_key=expected_runtime_session_key,
            requester_session_key="agent:main:discord:channel:ops",
            requester_account_id="source-workspace",
            requester_sender_id="discord-user-1",
            requester_sender_name="Alice",
            requester_sender_username="alice_u",
            requester_sender_e164="+15551234567",
        )
    ]
    assert delivery is not None
    assert delivery["event_payload"]["sessionKey"] == expected_target_session_key
    assert delivery["event_payload"]["sourceSessionKey"] == expected_runtime_session_key
    assert delivery["event_payload"]["requesterSessionKey"] == "agent:main:discord:channel:ops"
    assert delivery["event_payload"]["requesterAccountId"] == "source-workspace"
    assert delivery["event_payload"]["requesterSenderId"] == "discord-user-1"
    assert delivery["event_payload"]["requesterSenderName"] == "Alice"
    assert delivery["event_payload"]["requesterSenderUsername"] == "alice_u"
    assert delivery["event_payload"]["requesterSenderE164"] == "+15551234567"


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_react_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-react"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="react",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0001",
                "emoji": ":white_check_mark:",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-react-action",
        )
    )

    assert result == {"ok": True, "added": "white_check_mark"}
    assert slack_posts == [
        (
            "https://slack.test/api/reactions.add",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "name": "white_check_mark",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_react_remove_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-react-remove"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="react",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0001",
                "emoji": "eyes",
                "remove": True,
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-react-remove-action",
        )
    )

    assert result == {"ok": True, "removed": "eyes"}
    assert slack_posts == [
        (
            "https://slack.test/api/reactions.remove",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "name": "eyes",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_reactions_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-reactions"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    reactions = [{"name": "eyes", "count": 2, "users": ["U123", "U456"]}]

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "message": {"reactions": reactions}}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="reactions",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0001",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-reactions-action",
        )
    )

    assert result == {"ok": True, "reactions": reactions}
    assert slack_posts == [
        (
            "https://slack.test/api/reactions.get",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "full": True,
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_edit_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-edit"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "channel": "C123", "ts": "1710000000.0001"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="edit",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0001",
                "message": "Updated from message.action.",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-edit-action",
        )
    )

    assert result == {
        "ok": True,
        "edited": True,
        "channelId": "C123",
        "messageId": "1710000000.0001",
    }
    assert slack_posts == [
        (
            "https://slack.test/api/chat.update",
            {
                "channel": "C123",
                "ts": "1710000000.0001",
                "text": "Updated from message.action.",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_delete_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-delete"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "channel": "C123", "ts": "1710000000.0002"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="delete",
            params={
                "to": "channel:C123",
                "messageId": "1710000000.0002",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-delete-action",
        )
    )

    assert result == {
        "ok": True,
        "deleted": True,
        "channelId": "C123",
        "messageId": "1710000000.0002",
    }
    assert slack_posts == [
        (
            "https://slack.test/api/chat.delete",
            {
                "channel": "C123",
                "ts": "1710000000.0002",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_pin_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-pin"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="pin",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0003",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-pin-action",
        )
    )

    assert result == {
        "ok": True,
        "pinned": True,
        "channelId": "C123",
        "messageId": "1710000000.0003",
    }
    assert slack_posts == [
        (
            "https://slack.test/api/pins.add",
            {
                "channel": "C123",
                "timestamp": "1710000000.0003",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_unpin_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-unpin"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="unpin",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0004",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-unpin-action",
        )
    )

    assert result == {
        "ok": True,
        "unpinned": True,
        "channelId": "C123",
        "messageId": "1710000000.0004",
    }
    assert slack_posts == [
        (
            "https://slack.test/api/pins.remove",
            {
                "channel": "C123",
                "timestamp": "1710000000.0004",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_list_pins_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-list-pins"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    pins = [
        {
            "type": "message",
            "message": {"ts": "1710000000.0005", "text": "Pinned build note"},
        }
    ]

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "items": pins}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="list-pins",
            params={"to": "channel:C123"},
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-list-pins-action",
        )
    )

    assert result == {
        "ok": True,
        "channelId": "C123",
        "pins": pins,
    }
    assert slack_posts == [
        (
            "https://slack.test/api/pins.list",
            {"channel": "C123"},
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_read_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-read"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    messages = [
        {"ts": "1710000000.0006", "text": "latest"},
        {"ts": "1710000000.0005", "text": "previous"},
    ]

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "messages": messages, "has_more": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="read",
            params={
                "channelId": "channel:C123",
                "limit": 2,
                "before": "1710000000.0007",
                "after": "1710000000.0004",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-read-action",
        )
    )

    assert result == {
        "ok": True,
        "channelId": "C123",
        "messages": messages,
        "hasMore": True,
    }
    assert slack_posts == [
        (
            "https://slack.test/api/conversations.history",
            {
                "channel": "C123",
                "limit": 2,
                "latest": "1710000000.0007",
                "oldest": "1710000000.0004",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_thread_read_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-thread-read"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    thread_id = "1710000000.0007"
    replies = [
        {"ts": thread_id, "text": "parent"},
        {"ts": "1710000000.0008", "text": "first reply"},
    ]

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "messages": replies, "has_more": False}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="read",
            params={
                "channelId": "channel:C123",
                "threadId": thread_id,
                "limit": 3,
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-thread-read-action",
        )
    )

    assert result == {
        "ok": True,
        "channelId": "C123",
        "messages": [{"ts": "1710000000.0008", "text": "first reply"}],
        "hasMore": False,
    }
    assert slack_posts == [
        (
            "https://slack.test/api/conversations.replies",
            {
                "channel": "C123",
                "ts": thread_id,
                "limit": 3,
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_member_info_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-member-info"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    user_info = {"id": "U123", "name": "alice"}

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "user": user_info}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="member-info",
            params={"userId": "U123"},
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-member-info-action",
        )
    )

    assert result == {"ok": True, "info": {"ok": True, "user": user_info}}
    assert slack_posts == [
        (
            "https://slack.test/api/users.info",
            {"user": "U123"},
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_emoji_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-emoji-list"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "emoji": {
                "wave": "https://example.com/wave.png",
                "party": "https://example.com/party.png",
                "tada": "https://example.com/tada.png",
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="emoji-list",
            params={"limit": 2},
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-emoji-list-action",
        )
    )

    assert result == {
        "ok": True,
        "emojis": {
            "ok": True,
            "emoji": {
                "party": "https://example.com/party.png",
                "tada": "https://example.com/tada.png",
            },
        },
    }
    assert slack_posts == [
        (
            "https://slack.test/api/emoji.list",
            {},
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_upload_file_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-upload-file"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_forms: list[tuple[str, dict[str, object], str]] = []
    uploaded_files: list[tuple[str, bytes]] = []
    media_path = tmp_path / "report.png"
    media_path.write_bytes(b"fake-report")

    def fake_post_slack_form(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_token: str,
    ) -> dict[str, object]:
        del self
        slack_forms.append((target, payload, secret_token))
        if target.endswith("/files.getUploadURLExternal"):
            return {
                "ok": True,
                "upload_url": "https://upload.slack.test/report",
                "file_id": "F222",
            }
        return {"ok": True, "files": [{"id": "F222", "title": "Build Report"}]}

    def fake_upload_slack_file_bytes(
        self: OpsMeshService,
        *,
        upload_url: str,
        file_bytes: bytes,
    ) -> None:
        del self
        uploaded_files.append((upload_url, file_bytes))

    monkeypatch.setattr(OpsMeshService, "_post_slack_form", fake_post_slack_form)
    monkeypatch.setattr(
        OpsMeshService,
        "_upload_slack_file_bytes",
        fake_upload_slack_file_bytes,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="upload-file",
            params={
                "to": "channel:C123",
                "filePath": str(media_path),
                "initialComment": "fresh build",
                "filename": "report-final.png",
                "title": "Build Report",
                "threadId": "1710000000.0010",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-upload-file-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {
            "messageId": "F222",
            "channelId": "C123",
        },
    }
    assert slack_forms == [
        (
            "https://slack.test/api/files.getUploadURLExternal",
            {
                "filename": "report-final.png",
                "length": "11",
            },
            "xoxb-action-token",
        ),
        (
            "https://slack.test/api/files.completeUploadExternal",
            {
                "files": '[{"id": "F222", "title": "Build Report"}]',
                "channel_id": "C123",
                "initial_comment": "fresh build",
                "thread_ts": "1710000000.0010",
            },
            "xoxb-action-token",
        ),
    ]
    assert uploaded_files == [("https://upload.slack.test/report", b"fake-report")]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_download_file_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-download-file"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []
    downloaded_urls: list[tuple[str, str | None, int]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "file": {
                "id": "F123",
                "name": "image.png",
                "mimetype": "image/png",
                "url_private_download": "https://files.slack.test/image.png",
                "channels": ["C123"],
                "shares": {
                    "private": {
                        "C123": [{"ts": "1710000000.0011", "thread_ts": "1710000000.0011"}]
                    }
                },
            },
        }

    def fake_download_slack_private_file(
        self: OpsMeshService,
        url: str,
        *,
        secret_token: str | None,
        max_bytes: int,
    ) -> tuple[bytes, str | None]:
        del self
        downloaded_urls.append((url, secret_token, max_bytes))
        return b"fake-png", "image/png"

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    monkeypatch.setattr(
        OpsMeshService,
        "_download_slack_private_file",
        fake_download_slack_private_file,
        raising=False,
    )
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        canvas_state_dir=tmp_path / "data",
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="download-file",
            params={
                "fileId": "F123",
                "to": "channel:C123",
                "replyTo": "1710000000.0011",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-download-file-action",
        )
    )

    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["fileId"] == "F123"
    assert result["placeholder"] == "[Slack file: image.png]"
    assert result["contentType"] == "image/png"
    saved_path = Path(str(result["path"]))
    assert saved_path.read_bytes() == b"fake-png"
    assert result["media"] == {
        "mediaUrl": str(saved_path),
        "contentType": "image/png",
    }
    assert slack_posts == [
        (
            "https://slack.test/api/files.info",
            {"file": "F123"},
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]
    assert downloaded_urls == [
        ("https://files.slack.test/image.png", "xoxb-action-token", 20 * 1024 * 1024)
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_slack_download_file_scope_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-download-scope"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, target, payload, secret_header_name, secret_token
        return {
            "ok": True,
            "file": {
                "id": "F123",
                "name": "image.png",
                "mimetype": "image/png",
                "url_private_download": "https://files.slack.test/image.png",
                "channels": ["C999"],
            },
        }

    def fail_download_slack_private_file(
        self: OpsMeshService,
        url: str,
        *,
        secret_token: str | None,
        max_bytes: int,
    ) -> tuple[bytes, str | None]:
        del self, url, secret_token, max_bytes
        raise AssertionError("scope mismatch should stop before media download")

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    monkeypatch.setattr(
        OpsMeshService,
        "_download_slack_private_file",
        fail_download_slack_private_file,
        raising=False,
    )
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        canvas_state_dir=tmp_path / "data",
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="download-file",
            params={
                "fileId": "F123",
                "channelId": "channel:C123",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-download-file-scope",
        )
    )

    assert result == {
        "ok": False,
        "error": "File could not be downloaded (not found, too large, or inaccessible).",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_send_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-send"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "channel": "C123", "ts": "1710000000.0012"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="send",
            params={
                "to": "channel:C123",
                "message": "Ship Slack send action parity.",
                "threadId": "1710000000.0010",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-send-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {
            "messageId": "1710000000.0012",
            "channelId": "C123",
        },
    }
    assert slack_posts == [
        (
            "https://slack.test/api/chat.postMessage",
            {
                "channel": "C123",
                "text": "Ship Slack send action parity.",
                "thread_ts": "1710000000.0010",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_telegram_send_document_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-telegram-send"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Action Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 44,
                "chat": {"id": -100123},
                "document": {"file_id": "telegram-document-44"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="telegram",
            action="send",
            params={
                "to": "channel:-100123",
                "message": "Ship Telegram send action parity.",
                "media": "https://example.com/report.pdf",
                "replyTo": "41",
                "threadId": "forum-42",
                "silent": True,
                "asDocument": True,
            },
            account_id="telegram-bot",
            requester_sender_id="12345",
            sender_is_owner=True,
            session_key="agent:main:telegram:channel:-100123",
            idempotency_key="idem-telegram-send-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {
            "messageId": "44",
            "channelId": "-100123",
            "mediaIds": ["telegram-document-44"],
        },
    }
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendDocument",
            {
                "chat_id": "-100123",
                "message_thread_id": "forum-42",
                "reply_to_message_id": "41",
                "disable_notification": True,
                "document": "https://example.com/report.pdf",
                "disable_content_type_detection": True,
                "caption": "Ship Telegram send action parity.",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_telegram_poll_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-telegram-poll"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Poll Action Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 45,
                "chat": {"id": -100123},
                "poll": {"id": "poll-action-telegram-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="telegram",
            action="poll",
            params={
                "to": "channel:-100123",
                "pollQuestion": "Ship Telegram action poll parity?",
                "pollOption": [" Yes ", "No"],
                "pollMulti": True,
                "replyTo": "41",
                "threadId": "forum-42",
                "silent": True,
            },
            account_id="telegram-bot",
            requester_sender_id="12345",
            sender_is_owner=True,
            session_key="agent:main:telegram:channel:-100123",
            idempotency_key="idem-telegram-poll-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {
            "messageId": "45",
            "channelId": "-100123",
            "conversationId": "-100123",
            "pollId": "poll-action-telegram-1",
        },
    }
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPoll",
            {
                "chat_id": "-100123",
                "question": "Ship Telegram action poll parity?",
                "options": ["Yes", "No"],
                "allows_multiple_answers": True,
                "disable_notification": True,
                "reply_to_message_id": "41",
                "message_thread_id": "forum-42",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_slack_react_remove_own_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-slack-react-remove-own"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Action Provider",
        kind="slack",
        target="https://slack.test/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-action-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        if target.endswith("/auth.test"):
            return {"ok": True, "user_id": "UBOT"}
        if target.endswith("/reactions.get"):
            return {
                "ok": True,
                "message": {
                    "reactions": [
                        {"name": "eyes", "users": ["UBOT", "U123"]},
                        {"name": "thumbsup", "users": ["U123"]},
                        {"name": "rocket", "users": ["UBOT"]},
                    ]
                },
            }
        return {"ok": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="slack",
            action="react",
            params={
                "channelId": "channel:C123",
                "messageId": "1710000000.0001",
                "emoji": "",
            },
            account_id="workspace-bot",
            requester_sender_id="U123",
            sender_is_owner=True,
            session_key="agent:main:slack:channel:C123",
            idempotency_key="idem-slack-react-remove-own-action",
        )
    )

    assert result == {"ok": True, "removed": ["eyes", "rocket"]}
    assert slack_posts == [
        (
            "https://slack.test/api/auth.test",
            {},
            "Authorization",
            "Bearer xoxb-action-token",
        ),
        (
            "https://slack.test/api/reactions.get",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "full": True,
            },
            "Authorization",
            "Bearer xoxb-action-token",
        ),
        (
            "https://slack.test/api/reactions.remove",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "name": "eyes",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        ),
        (
            "https://slack.test/api/reactions.remove",
            {
                "channel": "C123",
                "timestamp": "1710000000.0001",
                "name": "rocket",
            },
            "Authorization",
            "Bearer xoxb-action-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_telegram_react_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-telegram-react"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Action Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {"ok": True, "result": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="telegram",
            action="react",
            params={
                "chatId": "channel:-100123",
                "messageId": 456,
                "emoji": "\u2705",
            },
            account_id="telegram-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:telegram:channel:-100123",
            idempotency_key="idem-telegram-react-action",
        )
    )

    assert result == {"ok": True, "added": "\u2705"}
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/setMessageReaction",
            {
                "chat_id": "-100123",
                "message_id": 456,
                "reaction": [{"type": "emoji", "emoji": "\u2705"}],
            },
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "idempotency_key"),
    [
        ({"chatId": "channel:-100123", "messageId": 456, "emoji": ""}, "empty"),
        (
            {
                "chatId": "channel:-100123",
                "messageId": 456,
                "emoji": "\u2705",
                "remove": True,
            },
            "remove",
        ),
    ],
)
async def test_ops_mesh_service_message_action_dispatches_telegram_react_remove_route(
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, object],
    idempotency_key: str,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / f"ops-mesh-message-action-telegram-react-{idempotency_key}"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Action Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {"ok": True, "result": True}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="telegram",
            action="react",
            params=params,
            account_id="telegram-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:telegram:channel:-100123",
            idempotency_key=f"idem-telegram-react-{idempotency_key}-action",
        )
    )

    assert result == {"ok": True, "removed": True}
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/setMessageReaction",
            {
                "chat_id": "-100123",
                "message_id": 456,
                "reaction": [],
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_react_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-react"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="react",
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
                "emoji": "\u2705",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-react-action",
        )
    )

    assert result == {"ok": True, "added": "\u2705"}
    assert discord_requests == [
        (
            "PUT",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/%E2%9C%85/@me"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_react_remove_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-react-remove"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="react",
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
                "emoji": "\u2705",
                "remove": True,
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-react-remove-action",
        )
    )

    assert result == {"ok": True, "removed": "\u2705"}
    assert discord_requests == [
        (
            "DELETE",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/%E2%9C%85/@me"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_react_remove_own_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-react-own"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        if method == "GET":
            return {
                "reactions": [
                    {"emoji": {"name": "\u2705", "id": None}},
                    {"emoji": {"name": "party_blob", "id": "123"}},
                    {"emoji": {"name": None, "id": None}},
                ]
            }
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="react",
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
                "emoji": "",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-react-remove-own-action",
        )
    )

    assert result == {"ok": True, "removed": ["\u2705", "party_blob:123"]}
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321/messages/discord-message-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "DELETE",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/%E2%9C%85/@me"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "DELETE",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/party_blob%3A123/@me"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_reactions_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-reactions"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        if target.endswith("/messages/discord-message-1"):
            return {
                "reactions": [
                    {"count": 2, "emoji": {"name": "\u2705", "id": None}},
                    {"count": 1, "emoji": {"name": "party_blob", "id": "123"}},
                ]
            }
        if "%E2%9C%85" in target:
            return [
                {"id": "U1", "username": "alice", "discriminator": "1234"},
                {"id": "U2", "username": "bob"},
            ]
        return [{"id": "U3", "username": "carol", "discriminator": "0001"}]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="reactions",
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
                "limit": 2,
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-reactions-action",
        )
    )

    assert result == {
        "ok": True,
        "reactions": [
            {
                "emoji": {"id": None, "name": "\u2705", "raw": "\u2705"},
                "count": 2,
                "users": [
                    {"id": "U1", "username": "alice", "tag": "alice#1234"},
                    {"id": "U2", "username": "bob", "tag": "bob"},
                ],
            },
            {
                "emoji": {"id": "123", "name": "party_blob", "raw": "party_blob:123"},
                "count": 1,
                "users": [
                    {"id": "U3", "username": "carol", "tag": "carol#0001"},
                ],
            },
        ],
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321/messages/discord-message-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "GET",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/%E2%9C%85?limit=2"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "GET",
            (
                "https://discord.com/api/v10/channels/987654321/messages/"
                "discord-message-1/reactions/party_blob%3A123?limit=2"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_whatsapp_react_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-whatsapp-react"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Action Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+123",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+123", "wa_id": "123"}],
            "messages": [{"id": "wamid.react.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="whatsapp",
            action="react",
            params={
                "chatJid": "123@s.whatsapp.net",
                "messageId": "wamid.source.1",
                "emoji": "\u2705",
            },
            account_id="wa-business",
            requester_sender_id="123@s.whatsapp.net",
            sender_is_owner=True,
            session_key="agent:main:whatsapp:direct:+123",
            idempotency_key="idem-whatsapp-react-action",
        )
    )

    assert result == {"ok": True, "added": "\u2705"}
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+123",
                "type": "reaction",
                "reaction": {
                    "message_id": "wamid.source.1",
                    "emoji": "\u2705",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "idempotency_key"),
    [
        ({"to": "+123", "messageId": "wamid.source.1", "emoji": ""}, "empty"),
        (
            {
                "to": "+123",
                "messageId": "wamid.source.1",
                "emoji": "\u2705",
                "remove": True,
            },
            "remove",
        ),
    ],
)
async def test_ops_mesh_service_message_action_dispatches_whatsapp_react_remove_route(
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, object],
    idempotency_key: str,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / f"ops-mesh-message-action-whatsapp-react-{idempotency_key}"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Action Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789/messages",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="Bearer wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+123",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+123", "wa_id": "123"}],
            "messages": [{"id": "wamid.react.remove.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="whatsapp",
            action="react",
            params=params,
            account_id="wa-business",
            requester_sender_id="123@s.whatsapp.net",
            sender_is_owner=True,
            session_key="agent:main:whatsapp:direct:+123",
            idempotency_key=f"idem-whatsapp-react-{idempotency_key}-action",
        )
    )

    assert result == {"ok": True, "removed": True}
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+123",
                "type": "reaction",
                "reaction": {
                    "message_id": "wamid.source.1",
                    "emoji": "",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_whatsapp_react_current_message_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-whatsapp-react-context"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Action Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+123",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+123", "wa_id": "123"}],
            "messages": [{"id": "wamid.react.ctx"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="whatsapp",
            action="react",
            params={"to": "+123", "emoji": "\u2764\ufe0f"},
            account_id="wa-business",
            requester_sender_id="123@s.whatsapp.net",
            sender_is_owner=True,
            session_key="agent:main:whatsapp:direct:+123",
            idempotency_key="idem-whatsapp-react-context-action",
            tool_context={
                "currentChannelId": "whatsapp:123@s.whatsapp.net",
                "currentChannelProvider": "whatsapp",
                "currentMessageId": 12345,
            },
        )
    )

    assert result == {"ok": True, "added": "\u2764\ufe0f"}
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+123",
                "type": "reaction",
                "reaction": {
                    "message_id": "12345",
                    "emoji": "\u2764\ufe0f",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_rejects_whatsapp_cross_chat_context_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "ops-mesh-message-action-whatsapp-react-cross-chat"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Action Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+999",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {"messaging_product": "whatsapp", "messages": [{"id": "unexpected"}]}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(RuntimeError, match="messageId is required"):
        await service.dispatch_message_action(
            GatewayMessageActionDispatchRequest(
                channel="whatsapp",
                action="react",
                params={"to": "+999", "emoji": "\u2705"},
                account_id="wa-business",
                requester_sender_id="123@s.whatsapp.net",
                sender_is_owner=True,
                session_key="agent:main:whatsapp:direct:+999",
                idempotency_key="idem-whatsapp-react-cross-chat-action",
                tool_context={
                    "currentChannelId": "whatsapp:+123",
                    "currentChannelProvider": "whatsapp",
                    "currentMessageId": "ctx-msg-42",
                },
            )
        )

    assert whatsapp_posts == []


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_zalo_send_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-zalo-send"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Zalo Native Action Provider",
        kind="zalo",
        target="https://bot-api.zaloplatforms.test",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="zalo-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "zalo",
            "account_id": "zalo-bot",
            "peer_kind": "direct",
            "peer_id": "direct:dm-chat-1",
        },
    )
    zalo_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        zalo_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "result": {
                "message_id": "zalo-action-1",
                "chat": {"id": "dm-chat-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="zalo",
            action="send",
            params={
                "to": "direct:dm-chat-1",
                "message": "Ship Zalo action parity.",
            },
            account_id="zalo-bot",
            requester_sender_id="zalo-user-1",
            sender_is_owner=True,
            session_key="agent:main:zalo:direct:dm-chat-1",
            idempotency_key="idem-zalo-send-action",
        )
    )

    assert result == {
        "ok": True,
        "to": "direct:dm-chat-1",
        "messageId": "zalo-action-1",
    }
    assert zalo_posts == [
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendMessage",
            {
                "chat_id": "dm-chat-1",
                "text": "Ship Zalo action parity.",
            },
            None,
            None,
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_zalo_send_media_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-zalo-send-media"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Zalo Native Action Provider",
        kind="zalo",
        target="https://bot-api.zaloplatforms.test",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="zalo-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "zalo",
            "account_id": "zalo-bot",
            "peer_kind": "direct",
            "peer_id": "direct:dm-chat-1",
        },
    )
    zalo_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        zalo_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "result": {
                "message_id": "zalo-photo-action-1",
                "chat": {"id": "dm-chat-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="zalo",
            action="send",
            params={
                "to": "direct:dm-chat-1",
                "message": "Caption",
                "media": "https://example.com/zalo.jpg",
            },
            account_id="zalo-bot",
            requester_sender_id="zalo-user-1",
            sender_is_owner=True,
            session_key="agent:main:zalo:direct:dm-chat-1",
            idempotency_key="idem-zalo-send-media-action",
        )
    )

    assert result == {
        "ok": True,
        "to": "direct:dm-chat-1",
        "messageId": "zalo-photo-action-1",
    }
    assert zalo_posts == [
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendPhoto",
            {
                "chat_id": "dm-chat-1",
                "photo": "https://example.com/zalo.jpg",
                "caption": "Caption",
            },
            None,
            None,
        )
    ]


def test_notification_route_create_accepts_zalo_native_route_kind() -> None:
    route = NotificationRouteCreate(
        name="Zalo Native Provider",
        kind="zalo",
        target="https://bot-api.zaloplatforms.test",
        events=["gateway/send"],
        conversation_target=ConversationTargetView(
            channel="zalo",
            account_id="zalo-bot",
            peer_kind="direct",
            peer_id="direct:dm-chat-1",
        ),
        secret_token="zalo-access-token",
    )

    assert route.kind == "zalo"
    assert route.conversation_target is not None
    assert route.conversation_target.channel == "zalo"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_preserves_provider_native_options(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-provider-options"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, object]:
        provider_requests.append(request)
        return {
            "messageId": "provider-send-options-1",
            "conversationId": "thread:topic-42",
        }

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="chat:ops",
        message="Send provider-native options.",
        media_urls=["https://example.com/report.pdf"],
        account_id="alerts",
        thread_id="topic-42",
        reply_to_id="message-99",
        silent=True,
        force_document=True,
        idempotency_key="idem-provider-runtime-send-options",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="telegram",
                account_id="alerts",
                peer_kind="channel",
                peer_id="chat:ops",
            ),
        ),
        thread_id="topic-42",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert provider_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="telegram",
            target="chat:ops",
            message="Send provider-native options.\n\nMedia:\n1. https://example.com/report.pdf",
            media_urls=("https://example.com/report.pdf",),
            account_id="alerts",
            thread_id="topic-42",
            session_key=expected_session_key,
            reply_to_id="message-99",
            silent=True,
            force_document=True,
        )
    ]
    assert result == {
        "ok": True,
        "runId": "idem-provider-runtime-send-options",
        "channel": "telegram",
        "messageId": "provider-send-options-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "telegram",
            "target": "chat:ops",
            "accountId": "alerts",
            "threadId": "topic-42",
            "sessionKey": expected_session_key,
        },
        "conversationId": "thread:topic-42",
    }
    assert delivery is not None
    assert delivery["event_payload"]["replyToId"] == "message-99"
    assert delivery["event_payload"]["silent"] is True
    assert delivery["event_payload"]["forceDocument"] is True
    assert delivery["route_scope"]["provider_result"] == {
        "messageId": "provider-send-options-1",
        "conversationId": "thread:topic-42"
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_preserves_audio_as_voice(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-audio-voice"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, object]:
        provider_requests.append(request)
        return {
            "messageId": "provider-send-audio-voice-1",
            "conversationId": "chat:ops",
        }

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="chat:ops",
        message="voice caption",
        media_urls=["file:///tmp/clip.mp3"],
        audio_as_voice=True,
        idempotency_key="idem-provider-runtime-audio-voice",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="telegram",
            peer_kind="channel",
            peer_id="chat:ops",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert len(provider_requests) == 1
    assert provider_requests[0] == GatewayOutboundRuntimeMessageRequest(
        channel="telegram",
        target="chat:ops",
        message="voice caption\n\nMedia:\n1. file:///tmp/clip.mp3\n\nSettings: audioAsVoice=true",
        media_urls=("file:///tmp/clip.mp3",),
        audio_as_voice=True,
        session_key=expected_session_key,
    )
    assert result == {
        "ok": True,
        "runId": "idem-provider-runtime-audio-voice",
        "channel": "telegram",
        "messageId": "provider-send-audio-voice-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "telegram",
            "target": "chat:ops",
            "sessionKey": expected_session_key,
        },
        "conversationId": "chat:ops",
    }
    assert delivery is not None
    assert delivery["event_payload"]["audioAsVoice"] is True


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_native_adapter_binding(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-native-adapter"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    native_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_native_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, object]:
        native_requests.append(request)
        return {
            "messageId": "native-slack-send-1",
            "chatId": "C123",
            "channelId": "slack:C123",
            "mediaIds": ["file-1"],
        }

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, str]:
        raise AssertionError(f"generic provider should not run: {request}")

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        raise AssertionError(f"session fallback should not run: {session_key} {message}")

    runtime = GatewayOutboundRuntimeService(
        session_deliverer=fake_session_delivery,
        provider_message_deliverer=fake_provider_delivery,
    )
    runtime.bind_native_message_deliverer(
        channel="slack",
        account_id="workspace-bot",
        deliverer=fake_native_delivery,
    )
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=runtime,
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship the native adapter path.",
        media_urls=["https://example.com/native.png"],
        account_id="workspace-bot",
        idempotency_key="idem-native-runtime-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-runtime-send",
        "channel": "slack",
        "messageId": "native-slack-send-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "C123",
        "channelId": "slack:C123",
        "mediaIds": ["file-1"],
    }
    assert native_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="slack",
            target="channel:C123",
            message="Ship the native adapter path.\n\nMedia:\n1. https://example.com/native.png",
            media_urls=("https://example.com/native.png",),
            account_id="workspace-bot",
            session_key=expected_session_key,
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "messageId": "native-slack-send-1",
        "chatId": "C123",
        "channelId": "slack:C123",
        "mediaIds": ["file-1"],
    }


@pytest.mark.asyncio
async def test_provider_result_persistence_keeps_message_id_runtime_and_meta() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-provider-result-metadata"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    async def fake_native_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, object]:
        assert request.channel == "slack"
        return {
            "runtime": "native-provider-backed",
            "messageId": "native-meta-1",
            "channel": "slack",
            "chatId": "C123",
            "channelId": "slack:C123",
            "conversationId": "thread:C123",
            "pollId": "poll-123",
            "roomId": "room-9",
            "timestamp": 1713980000,
            "meta": {"hook": "ok", "attempt": 1},
        }

    runtime = GatewayOutboundRuntimeService()
    runtime.bind_native_message_deliverer(
        channel="slack",
        deliverer=fake_native_delivery,
    )
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=runtime,
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Preserve provider metadata.",
        idempotency_key="idem-provider-result-metadata",
    )

    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "native-meta-1"
    assert result["chatId"] == "C123"
    assert result["channelId"] == "slack:C123"
    assert result["conversationId"] == "thread:C123"
    assert result["pollId"] == "poll-123"
    assert result["roomId"] == "room-9"
    assert result["timestamp"] == 1713980000
    assert result["meta"] == {"hook": "ok", "attempt": 1}
    assert delivery is not None
    assert delivery["delivery_message_id"] == "native-meta-1"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "native-meta-1",
        "channel": "slack",
        "chatId": "C123",
        "channelId": "slack:C123",
        "conversationId": "thread:C123",
        "pollId": "poll-123",
        "roomId": "room-9",
        "timestamp": 1713980000,
        "meta": {"hook": "ok", "attempt": 1},
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_slack_reply_to_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-slack-reply-to"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Reply Native Provider",
        kind="slack",
        target="https://slack.com/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-route-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        slack_posts.append((target, payload))
        return {
            "ok": True,
            "channel": "C123",
            "ts": "1713980000.000300",
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Reply in the existing Slack thread.",
        account_id="workspace-bot",
        reply_to_id="1712000000.000001",
        idempotency_key="idem-native-slack-reply-to",
    )

    assert slack_posts == [
        (
            "https://slack.com/api/chat.postMessage",
            {
                "channel": "C123",
                "text": "Reply in the existing Slack thread.",
                "thread_ts": "1712000000.000001",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_send_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-send"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        discord_posts.append((target, payload))
        return {"id": "discord-message-2", "channel_id": "987654321"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="send",
            params={
                "to": "channel:987654321",
                "message": "Ship Discord send action parity.",
                "replyTo": "discord-message-1",
                "silent": True,
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-send-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {
            "messageId": "discord-message-2",
            "channelId": "987654321",
        },
    }
    assert discord_posts == [
        (
            "https://discord.com/api/webhooks/webhook-id/webhook-token?wait=true",
            {
                "content": "Ship Discord send action parity.",
                "flags": 1 << 12,
                "message_reference": {
                    "message_id": "discord-message-1",
                    "fail_if_not_exists": False,
                },
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_edit_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-edit"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {
            "id": "discord-message-1",
            "channel_id": "987654321",
            "content": "Edited Discord message.",
        }

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="edit",
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
                "message": "Edited Discord message.",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-edit-action",
        )
    )

    assert result == {
        "ok": True,
        "message": {
            "id": "discord-message-1",
            "channel_id": "987654321",
            "content": "Edited Discord message.",
        },
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/channels/987654321/messages/discord-message-1",
            {"content": "Edited Discord message."},
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_delete_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-delete"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="delete",
            params={
                "to": "channel:987654321",
                "messageId": "discord-message-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-delete-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "DELETE",
            "https://discord.com/api/v10/channels/987654321/messages/discord-message-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_method"),
    [
        ("pin", "PUT"),
        ("unpin", "DELETE"),
    ],
)
async def test_ops_mesh_service_message_action_dispatches_discord_pin_mutation_route(
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    expected_method: str,
) -> None:
    tmp_path = Path.cwd() / f".tmp-pytest-local/ops-mesh-message-action-discord-{action}"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action=action,
            params={
                "channelId": "channel:987654321",
                "messageId": "discord-message-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key=f"idem-discord-{action}-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            expected_method,
            "https://discord.com/api/v10/channels/987654321/pins/discord-message-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_list_pins_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-list-pins"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [
            {
                "id": "pinned-message-1",
                "channel_id": "987654321",
                "content": "Pinned Discord message.",
                "timestamp": "2024-01-01T00:00:00.000Z",
            }
        ]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="list-pins",
            params={
                "to": "channel:987654321",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-list-pins-action",
        )
    )

    assert result == {
        "ok": True,
        "pins": [
            {
                "id": "pinned-message-1",
                "channel_id": "987654321",
                "content": "Pinned Discord message.",
                "timestamp": "2024-01-01T00:00:00.000Z",
                "timestampMs": 1704067200000,
                "timestampUtc": "2024-01-01T00:00:00.000Z",
            }
        ],
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321/pins",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_read_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-read"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [
            {
                "id": "discord-message-2",
                "channel_id": "987654321",
                "content": "Read Discord history.",
                "timestamp": "2024-01-02T00:00:00.000Z",
            }
        ]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="read",
            params={
                "channelId": "channel:987654321",
                "limit": "250.9",
                "before": "30",
                "after": "10",
                "around": "20",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-read-action",
        )
    )

    assert result == {
        "ok": True,
        "messages": [
            {
                "id": "discord-message-2",
                "channel_id": "987654321",
                "content": "Read Discord history.",
                "timestamp": "2024-01-02T00:00:00.000Z",
                "timestampMs": 1704153600000,
                "timestampUtc": "2024-01-02T00:00:00.000Z",
            }
        ],
    }
    assert discord_requests == [
        (
            "GET",
            (
                "https://discord.com/api/v10/channels/987654321/messages"
                "?limit=100&before=30&after=10&around=20"
            ),
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_fetch_message_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-fetch"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "789", "timestamp": "2026-01-15T11:00:00.000Z"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="fetch-message",
            params={"messageLink": "https://discord.com/channels/123/456/789"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-fetch-message-action",
        )
    )

    expected_ms = 1768474800000
    assert result == {
        "ok": True,
        "message": {
            "id": "789",
            "timestamp": "2026-01-15T11:00:00.000Z",
            "timestampMs": expected_ms,
            "timestampUtc": "2026-01-15T11:00:00.000Z",
        },
        "guildId": "123",
        "channelId": "456",
        "messageId": "789",
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/456/messages/789",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_permissions_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-permissions"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        if target.endswith("/channels/987654321"):
            return {
                "id": "987654321",
                "guild_id": "guild-1",
                "type": 0,
                "permission_overwrites": [
                    {"id": "guild-1", "allow": "0", "deny": "2048"},
                    {"id": "role-writer", "allow": "2048", "deny": "0"},
                    {"id": "bot-user", "allow": "0", "deny": "32768"},
                ],
            }
        if target.endswith("/users/@me"):
            return {"id": "bot-user"}
        if target.endswith("/guilds/guild-1"):
            return {
                "roles": [
                    {
                        "id": "guild-1",
                        "permissions": str(1024 + 2048 + 32768 + 65536),
                    },
                    {"id": "role-writer", "permissions": "0"},
                ]
            }
        if target.endswith("/guilds/guild-1/members/bot-user"):
            return {"roles": ["role-writer"]}
        raise AssertionError(f"unexpected Discord API target {target}")

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="permissions",
            params={
                "channelId": "channel:987654321",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-permissions-action",
        )
    )

    assert result == {
        "ok": True,
        "permissions": {
            "channelId": "987654321",
            "guildId": "guild-1",
            "permissions": ["ReadMessageHistory", "SendMessages", "ViewChannel"],
            "raw": "68608",
            "isDm": False,
            "channelType": 0,
        },
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "GET",
            "https://discord.com/api/v10/users/@me",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/members/bot-user",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_thread_create_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-thread-create"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        if method == "GET" and target.endswith("/channels/987654321"):
            return {"id": "987654321", "type": 0}
        if method == "POST" and target.endswith("/channels/987654321/threads"):
            return {"id": "thread-1", "name": "Parity thread"}
        if method == "POST" and target.endswith("/channels/thread-1/messages"):
            return {"id": "thread-message-1", "channel_id": "thread-1"}
        raise AssertionError(f"unexpected Discord API request {method} {target}")

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="thread-create",
            params={
                "channelId": "channel:987654321",
                "threadName": "Parity thread",
                "message": "Thread starter",
                "autoArchiveMin": "1440.8",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-thread-create-action",
        )
    )

    assert result == {"ok": True, "thread": {"id": "thread-1", "name": "Parity thread"}}
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "POST",
            "https://discord.com/api/v10/channels/987654321/threads",
            {
                "name": "Parity thread",
                "auto_archive_duration": 1440,
                "type": 11,
            },
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "POST",
            "https://discord.com/api/v10/channels/thread-1/messages",
            {"content": "Thread starter"},
            "Authorization",
            "Bot discord-bot-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_sticker_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-sticker"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "sticker-message-1", "channel_id": "987654321"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="sticker",
            params={
                "to": "channel:987654321",
                "message": "Sticker drop",
                "stickerId": ["sticker-1", "sticker-2"],
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-sticker-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/channels/987654321/messages",
            {
                "content": "Sticker drop",
                "sticker_ids": ["sticker-1", "sticker-2"],
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_poll_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-poll"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "poll-message-1", "channel_id": "987654321"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="poll",
            params={
                "to": "channel:987654321",
                "content": "Vote now.",
                "question": "Lunch?",
                "answers": ["Pizza", "Sushi"],
                "allowMultiselect": "true",
                "durationHours": "24.9",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-poll-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/channels/987654321/messages",
            {
                "content": "Vote now.",
                "poll": {
                    "question": {"text": "Lunch?"},
                    "answers": [
                        {"poll_media": {"text": "Pizza"}},
                        {"poll_media": {"text": "Sushi"}},
                    ],
                    "duration": 24,
                    "allow_multiselect": True,
                    "layout_type": 1,
                },
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_set_presence_runtime() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-presence"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    class FakeDiscordPresenceRuntime:
        def __init__(self) -> None:
            self.calls: list[tuple[str | None, dict[str, object]]] = []

        def update_presence(
            self,
            account_id: str | None,
            presence: dict[str, object],
        ) -> None:
            self.calls.append((account_id, presence))

    presence_runtime = FakeDiscordPresenceRuntime()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        discord_presence_runtime=presence_runtime,
    )

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="set-presence",
            params={
                "status": "dnd",
                "activityType": "streaming",
                "activityName": "Parity stream",
                "activityUrl": "https://twitch.tv/openzues",
                "activityState": "Shipping parity",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-set-presence-action",
        )
    )

    assert result == {
        "ok": True,
        "status": "dnd",
        "activities": [
            {
                "type": 1,
                "name": "Parity stream",
                "url": "https://twitch.tv/openzues",
                "state": "Shipping parity",
            }
        ],
    }
    assert presence_runtime.calls == [
        (
            "discord-bot",
            {
                "since": None,
                "activities": [
                    {
                        "name": "Parity stream",
                        "type": 1,
                        "url": "https://twitch.tv/openzues",
                        "state": "Shipping parity",
                    }
                ],
                "status": "dnd",
                "afk": False,
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_presence_unavailable() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-presence-missing"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(
        GatewayOutboundRuntimeUnavailableError,
        match='Discord gateway not available for account "discord-bot"',
    ):
        await service.dispatch_message_action(
            GatewayMessageActionDispatchRequest(
                channel="discord",
                action="set-presence",
                params={"status": "online"},
                account_id="discord-bot",
                requester_sender_id="1234",
                sender_is_owner=True,
                session_key="agent:main:discord:channel:987654321",
                idempotency_key="idem-discord-set-presence-unavailable",
            )
        )


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_member_info_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-member-info"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {
            "user": {"id": "user-1", "username": "Ada"},
            "roles": ["role-1"],
            "nick": "Countess",
        }

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="member-info",
            params={
                "guildId": "guild-1",
                "userId": "user-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-member-info-action",
        )
    )

    assert result == {
        "ok": True,
        "member": {
            "user": {"id": "user-1", "username": "Ada"},
            "roles": ["role-1"],
            "nick": "Countess",
        },
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/members/user-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_role_info_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-role-info"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [{"id": "role-1", "name": "Writers", "permissions": "68608"}]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="role-info",
            params={"guildId": "guild-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-role-info-action",
        )
    )

    assert result == {
        "ok": True,
        "roles": [{"id": "role-1", "name": "Writers", "permissions": "68608"}],
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/roles",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_emoji_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-emoji-list"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [{"id": "emoji-1", "name": "party_blob", "animated": True}]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="emoji-list",
            params={"guildId": "guild-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-emoji-list-action",
        )
    )

    assert result == {
        "ok": True,
        "emojis": [{"id": "emoji-1", "name": "party_blob", "animated": True}],
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/emojis",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_emoji_upload_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-emoji-upload"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "emoji-1", "name": "party"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="emoji-upload",
            params={
                "guildId": "guild-1",
                "emojiName": " party ",
                "media": "data:image/png;base64,aGVsbG8=",
                "roleIds": [" role-1 ", "", "role-2"],
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-emoji-upload-action",
        )
    )

    assert result == {"ok": True, "emoji": {"id": "emoji-1", "name": "party"}}
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/guilds/guild-1/emojis",
            {
                "name": "party",
                "image": "data:image/png;base64,aGVsbG8=",
                "roles": ["role-1", "role-2"],
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_sticker_upload_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-sticker-upload"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    sticker_uploads: list[
        tuple[str, str, str, str, bytes, str, str | None]
    ] = []

    def fake_request_discord_sticker_upload(
        self: OpsMeshService,
        *,
        guild_id: str,
        name: str,
        description: str,
        tags: str,
        media_bytes: bytes,
        content_type: str,
        secret_token: str | None,
    ) -> dict[str, object]:
        del self
        sticker_uploads.append(
            (guild_id, name, description, tags, media_bytes, content_type, secret_token)
        )
        return {"id": "sticker-1", "name": "party_sticker"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_discord_sticker_upload",
        fake_request_discord_sticker_upload,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="sticker-upload",
            params={
                "guildId": "guild-1",
                "stickerName": " party_sticker ",
                "stickerDesc": " celebratory sticker ",
                "stickerTags": " party ",
                "media": "data:image/png;base64,aGVsbG8=",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-sticker-upload-action",
        )
    )

    assert result == {"ok": True, "sticker": {"id": "sticker-1", "name": "party_sticker"}}
    assert sticker_uploads == [
        (
            "guild-1",
            "party_sticker",
            "celebratory sticker",
            "party",
            b"hello",
            "image/png",
            "discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_info_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-info"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "987654321", "guild_id": "guild-1", "name": "general", "type": 0}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-info",
            params={"channelId": "channel:987654321"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-info-action",
        )
    )

    assert result == {
        "ok": True,
        "channel": {"id": "987654321", "guild_id": "guild-1", "name": "general", "type": 0},
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-list"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [{"id": "987654321", "guild_id": "guild-1", "name": "general", "type": 0}]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-list",
            params={"guildId": "guild-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-list-action",
        )
    )

    assert result == {
        "ok": True,
        "channels": [{"id": "987654321", "guild_id": "guild-1", "name": "general", "type": 0}],
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/channels",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_voice_status_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-voice-status"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"guild_id": "guild-1", "channel_id": "voice-1", "user_id": "user-1"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="voice-status",
            params={"guildId": "guild-1", "userId": "user-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-voice-status-action",
        )
    )

    assert result == {
        "ok": True,
        "voice": {"guild_id": "guild-1", "channel_id": "voice-1", "user_id": "user-1"},
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/voice-states/user-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_event_list_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-event-list"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return [{"id": "event-1", "name": "Planning"}]

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="event-list",
            params={"guildId": "guild-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-event-list-action",
        )
    )

    assert result == {"ok": True, "events": [{"id": "event-1", "name": "Planning"}]}
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/scheduled-events",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_event_create_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-event-create"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "event-1", "name": "Planning", "entity_type": 3}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="event-create",
            params={
                "guildId": "guild-1",
                "name": "Planning",
                "description": "Roadmap sync",
                "startTime": "2026-05-01T12:00:00.000Z",
                "endTime": "2026-05-01T13:00:00.000Z",
                "entityType": "external",
                "location": "Main Hall",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-event-create-action",
        )
    )

    assert result == {"ok": True, "event": {"id": "event-1", "name": "Planning", "entity_type": 3}}
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/guilds/guild-1/scheduled-events",
            {
                "name": "Planning",
                "description": "Roadmap sync",
                "scheduled_start_time": "2026-05-01T12:00:00.000Z",
                "scheduled_end_time": "2026-05-01T13:00:00.000Z",
                "entity_type": 3,
                "entity_metadata": {"location": "Main Hall"},
                "privacy_level": 2,
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_event_create_cover_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-event-cover"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "event-1", "name": "Planning", "image": "cover-hash"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="event-create",
            params={
                "guildId": "guild-1",
                "name": "Planning",
                "startTime": "2026-05-01T12:00:00.000Z",
                "channelId": "stage-1",
                "entityType": "stage",
                "image": "data:image/png;base64,aGVsbG8=",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-event-create-cover-action",
        )
    )

    assert result == {
        "ok": True,
        "event": {"id": "event-1", "name": "Planning", "image": "cover-hash"},
    }
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/guilds/guild-1/scheduled-events",
            {
                "name": "Planning",
                "scheduled_start_time": "2026-05-01T12:00:00.000Z",
                "entity_type": 1,
                "privacy_level": 2,
                "channel_id": "stage-1",
                "image": "data:image/png;base64,aGVsbG8=",
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_timeout_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-timeout"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        }

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="timeout",
            params={
                "guildId": "guild-1",
                "userId": "user-1",
                "until": "2026-05-01T12:30:00.000Z",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-timeout-action",
        )
    )

    assert result == {
        "ok": True,
        "member": {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        },
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/guilds/guild-1/members/user-1",
            {"communication_disabled_until": "2026-05-01T12:30:00.000Z"},
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_timeout_duration_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-timeout-duration"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        }

    monkeypatch.setattr("openzues.services.ops_mesh.datetime", FakeDatetime)
    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="timeout",
            params={"guildId": "guild-1", "userId": "user-1", "durationMin": "30.9"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-timeout-duration-action",
        )
    )

    assert result == {
        "ok": True,
        "member": {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        },
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/guilds/guild-1/members/user-1",
            {"communication_disabled_until": "2026-05-01T12:30:00.000Z"},
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_timeout_reason_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-timeout-reason"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[
        tuple[str, str, object | None, str | None, str | None, dict[str, str] | None]
    ] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> object:
        del self
        discord_requests.append(
            (method, target, payload, secret_header_name, secret_token, extra_headers)
        )
        return {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        }

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="timeout",
            params={
                "guildId": "guild-1",
                "userId": "user-1",
                "until": "2026-05-01T12:30:00.000Z",
                "reason": "Needs a pause",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-timeout-reason-action",
        )
    )

    assert result == {
        "ok": True,
        "member": {
            "user": {"id": "user-1"},
            "communication_disabled_until": "2026-05-01T12:30:00.000Z",
        },
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/guilds/guild-1/members/user-1",
            {"communication_disabled_until": "2026-05-01T12:30:00.000Z"},
            "Authorization",
            "Bot discord-bot-token",
            {"X-Audit-Log-Reason": "Needs%20a%20pause"},
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_kick_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-kick"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[
        tuple[str, str, object | None, str | None, str | None, dict[str, str] | None]
    ] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> object:
        del self
        discord_requests.append(
            (method, target, payload, secret_header_name, secret_token, extra_headers)
        )
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="kick",
            params={"guildId": "guild-1", "userId": "user-1", "reason": "Rule 7"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-kick-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "DELETE",
            "https://discord.com/api/v10/guilds/guild-1/members/user-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
            {"X-Audit-Log-Reason": "Rule%207"},
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_ban_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-ban"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[
        tuple[str, str, object | None, str | None, str | None, dict[str, str] | None]
    ] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> object:
        del self
        discord_requests.append(
            (method, target, payload, secret_header_name, secret_token, extra_headers)
        )
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="ban",
            params={
                "guildId": "guild-1",
                "userId": "user-1",
                "deleteDays": "9.8",
                "reason": "Rule 9",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-ban-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "PUT",
            "https://discord.com/api/v10/guilds/guild-1/bans/user-1",
            {"delete_message_days": 7},
            "Authorization",
            "Bot discord-bot-token",
            {"X-Audit-Log-Reason": "Rule%209"},
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_thread_list_active_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "ops-mesh-message-action-discord-thread-list-active"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"threads": [{"id": "thread-1", "name": "build"}], "members": []}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="thread-list",
            params={"guildId": "guild-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-thread-list-active-action",
        )
    )

    assert result == {
        "ok": True,
        "threads": {"threads": [{"id": "thread-1", "name": "build"}], "members": []},
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/threads/active",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_thread_list_archived_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "ops-mesh-message-action-discord-thread-list-archived"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"threads": [{"id": "archived-thread-1", "name": "old-build"}], "has_more": False}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="thread-list",
            params={
                "guildId": "guild-1",
                "channelId": "channel:987654321",
                "includeArchived": True,
                "before": "2026-05-01T12:00:00.000Z",
                "limit": "12.9",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-thread-list-archived-action",
        )
    )

    assert result == {
        "ok": True,
        "threads": {
            "threads": [{"id": "archived-thread-1", "name": "old-build"}],
            "has_more": False,
        },
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/channels/987654321/threads/archived/public"
            "?before=2026-05-01T12%3A00%3A00.000Z&limit=12",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_thread_reply_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-thread-reply"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "reply-message-1", "channel_id": "987654321"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="thread-reply",
            params={
                "threadId": "channel:987654321",
                "message": "Thread reply from parity.",
                "replyTo": "parent-message-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-thread-reply-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {"messageId": "reply-message-1", "channelId": "987654321"},
    }
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/channels/987654321/messages",
            {
                "content": "Thread reply from parity.",
                "message_reference": {
                    "message_id": "parent-message-1",
                    "fail_if_not_exists": False,
                },
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_thread_reply_media_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "ops-mesh-message-action-discord-thread-reply-media"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    upload_calls: list[dict[str, object]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self, target, method, payload, secret_header_name, secret_token
        return {"id": "json-reply-should-not-send", "channel_id": "987654321"}

    def fake_request_discord_message_upload(
        self: OpsMeshService,
        *,
        channel_id: str,
        payload: dict[str, object],
        media_bytes: bytes,
        content_type: str,
        filename: str,
        secret_token: str | None,
    ) -> dict[str, object]:
        del self
        upload_calls.append(
            {
                "channel_id": channel_id,
                "payload": payload,
                "media_bytes": media_bytes,
                "content_type": content_type,
                "filename": filename,
                "secret_token": secret_token,
            }
        )
        return {"id": "media-reply-1", "channel_id": "987654321"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
    )
    monkeypatch.setattr(
        OpsMeshService,
        "_request_discord_message_upload",
        fake_request_discord_message_upload,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="thread-reply",
            params={
                "threadId": "channel:987654321",
                "message": "Thread reply with media.",
                "mediaUrl": "data:image/png;base64,aGVsbG8=",
                "replyTo": "parent-message-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-thread-reply-media-action",
        )
    )

    assert result == {
        "ok": True,
        "result": {"messageId": "media-reply-1", "channelId": "987654321"},
    }
    assert upload_calls == [
        {
            "channel_id": "987654321",
            "payload": {
                "content": "Thread reply with media.",
                "message_reference": {
                    "message_id": "parent-message-1",
                    "fail_if_not_exists": False,
                },
            },
            "media_bytes": b"hello",
            "content_type": "image/png",
            "filename": "upload.png",
            "secret_token": "discord-bot-token",
        }
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_search_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-search"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"total_results": 1, "messages": [[{"id": "message-1", "content": "needle"}]]}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="search",
            params={
                "guildId": "guild-1",
                "query": "needle",
                "channelIds": ["channel:987654321", "222222222"],
                "authorId": "user-1",
                "limit": "99.9",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-search-action",
        )
    )

    assert result == {
        "ok": True,
        "results": {"total_results": 1, "messages": [[{"id": "message-1", "content": "needle"}]]},
    }
    assert discord_requests == [
        (
            "GET",
            "https://discord.com/api/v10/guilds/guild-1/messages/search"
            "?content=needle&channel_id=987654321&channel_id=222222222&author_id=user-1&limit=25",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_method"),
    [
        ("role-add", "PUT"),
        ("role-remove", "DELETE"),
    ],
)
async def test_ops_mesh_service_message_action_dispatches_discord_role_mutation_route(
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    expected_method: str,
) -> None:
    tmp_path = Path.cwd() / f".tmp-pytest-local/ops-mesh-message-action-discord-{action}"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action=action,
            params={
                "guildId": "guild-1",
                "userId": "user-1",
                "roleId": "role-1",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key=f"idem-discord-{action}-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            expected_method,
            "https://discord.com/api/v10/guilds/guild-1/members/user-1/roles/role-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_create_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-create"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "new-channel-1", "guild_id": "guild-1", "name": "parity-lab"}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-create",
            params={
                "guildId": "guild-1",
                "name": "parity-lab",
                "type": "0",
                "parentId": "parent-1",
                "topic": "Native parity",
                "position": "3.7",
                "nsfw": True,
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-create-action",
        )
    )

    assert result == {
        "ok": True,
        "channel": {"id": "new-channel-1", "guild_id": "guild-1", "name": "parity-lab"},
    }
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/guilds/guild-1/channels",
            {
                "name": "parity-lab",
                "type": 0,
                "parent_id": "parent-1",
                "topic": "Native parity",
                "position": 3,
                "nsfw": True,
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_category_create_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-category-create"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "category-1", "guild_id": "guild-1", "name": "team-space", "type": 4}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="category-create",
            params={"guildId": "guild-1", "name": "team-space", "position": "2.9"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-category-create-action",
        )
    )

    assert result == {
        "ok": True,
        "category": {"id": "category-1", "guild_id": "guild-1", "name": "team-space", "type": 4},
    }
    assert discord_requests == [
        (
            "POST",
            "https://discord.com/api/v10/guilds/guild-1/channels",
            {"name": "team-space", "type": 4, "position": 2},
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_category_edit_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-category-edit"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "222222222", "name": "renamed-space", "position": 5, "type": 4}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="category-edit",
            params={"categoryId": "222222222", "name": "renamed-space", "position": "5.6"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-category-edit-action",
        )
    )

    assert result == {
        "ok": True,
        "category": {"id": "222222222", "name": "renamed-space", "position": 5, "type": 4},
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/channels/222222222",
            {"name": "renamed-space", "position": 5},
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_category_delete_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-category-delete"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="category-delete",
            params={"categoryId": "222222222"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-category-delete-action",
        )
    )

    assert result == {"ok": True, "channelId": "222222222"}
    assert discord_requests == [
        (
            "DELETE",
            "https://discord.com/api/v10/channels/222222222",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_edit_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-edit"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"id": "987654321", "name": "renamed-parity-lab", "parent_id": None}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-edit",
            params={
                "channelId": "channel:987654321",
                "name": "renamed-parity-lab",
                "topic": "Native parity v2",
                "position": "4.2",
                "clearParent": True,
                "nsfw": False,
                "rateLimitPerUser": "30.8",
                "archived": True,
                "locked": False,
                "autoArchiveDuration": "60.9",
                "availableTags": [
                    {"id": "0", "name": "General", "emoji_id": None},
                    {"id": "1", "name": "Docs", "moderated": False, "emoji_name": "book"},
                    {"id": "bad"},
                ],
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-edit-action",
        )
    )

    assert result == {
        "ok": True,
        "channel": {"id": "987654321", "name": "renamed-parity-lab", "parent_id": None},
    }
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/channels/987654321",
            {
                "name": "renamed-parity-lab",
                "topic": "Native parity v2",
                "position": 4,
                "parent_id": None,
                "nsfw": False,
                "rate_limit_per_user": 30,
                "archived": True,
                "locked": False,
                "auto_archive_duration": 60,
                "available_tags": [
                    {"id": "0", "name": "General", "emoji_id": None},
                    {"id": "1", "name": "Docs", "moderated": False, "emoji_name": "book"},
                ],
            },
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_delete_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-delete"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"status": 204}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-delete",
            params={"channelId": "channel:987654321"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-delete-action",
        )
    )

    assert result == {"ok": True, "channelId": "987654321"}
    assert discord_requests == [
        (
            "DELETE",
            "https://discord.com/api/v10/channels/987654321",
            None,
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_move_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-message-action-discord-channel-move"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-move",
            params={
                "guildId": "guild-1",
                "channelId": "channel:987654321",
                "clearParent": True,
                "position": "6.3",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-move-action",
        )
    )

    assert result == {"ok": True}
    assert discord_requests == [
        (
            "PATCH",
            "https://discord.com/api/v10/guilds/guild-1/channels",
            [{"id": "987654321", "parent_id": None, "position": 6}],
            "Authorization",
            "Bot discord-bot-token",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_message_action_dispatches_discord_channel_permissions_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "ops-mesh-message-action-discord-channel-permissions"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Action Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="discord-bot-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-bot",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_requests: list[tuple[str, str, object | None, str | None, str | None]] = []

    def fake_request_json_provider_url(
        self: OpsMeshService,
        target: str,
        *,
        method: str = "GET",
        payload: object | None = None,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> object:
        del self
        discord_requests.append((method, target, payload, secret_header_name, secret_token))
        return {"ok": True}

    monkeypatch.setattr(
        OpsMeshService,
        "_request_json_provider_url",
        fake_request_json_provider_url,
        raising=False,
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

    role_result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-permission-set",
            params={
                "channelId": "channel:987654321",
                "targetId": "role-1",
                "targetType": "role",
                "allow": "1024",
                "deny": "2048",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-permission-set-action",
        )
    )
    member_result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-permission-set",
            params={
                "channelId": "channel:987654321",
                "targetId": "member-1",
                "targetType": "member",
                "allow": "4096",
            },
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-permission-member-set-action",
        )
    )
    remove_result = await service.dispatch_message_action(
        GatewayMessageActionDispatchRequest(
            channel="discord",
            action="channel-permission-remove",
            params={"channelId": "channel:987654321", "targetId": "role-1"},
            account_id="discord-bot",
            requester_sender_id="1234",
            sender_is_owner=True,
            session_key="agent:main:discord:channel:987654321",
            idempotency_key="idem-discord-channel-permission-remove-action",
        )
    )

    assert role_result == {"ok": True}
    assert member_result == {"ok": True}
    assert remove_result == {"ok": True}
    assert discord_requests == [
        (
            "PUT",
            "https://discord.com/api/v10/channels/987654321/permissions/role-1",
            {"type": 0, "allow": "1024", "deny": "2048"},
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "PUT",
            "https://discord.com/api/v10/channels/987654321/permissions/member-1",
            {"type": 1, "allow": "4096"},
            "Authorization",
            "Bot discord-bot-token",
        ),
        (
            "DELETE",
            "https://discord.com/api/v10/channels/987654321/permissions/role-1",
            None,
            "Authorization",
            "Bot discord-bot-token",
        ),
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_slack_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-slack-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Send Provider",
        kind="slack",
        target="https://slack.com/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-route-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_forms: list[tuple[str, dict[str, object], str]] = []
    uploaded_files: list[tuple[str, bytes]] = []

    def fake_post_slack_form(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_token: str,
    ) -> dict[str, object]:
        del self
        slack_forms.append((target, payload, secret_token))
        if target.endswith("/files.getUploadURLExternal"):
            return {
                "ok": True,
                "upload_url": "https://upload.slack.test/file-1",
                "file_id": "F111",
            }
        return {"ok": True, "files": [{"id": "F111", "title": "slack.png"}]}

    def fake_download_slack_media_url(self: OpsMeshService, media_url: str) -> bytes:
        del self
        assert media_url == "https://example.com/slack.png"
        return b"fake-png"

    def fake_upload_slack_file_bytes(
        self: OpsMeshService,
        *,
        upload_url: str,
        file_bytes: bytes,
    ) -> None:
        del self
        uploaded_files.append((upload_url, file_bytes))

    monkeypatch.setattr(OpsMeshService, "_post_slack_form", fake_post_slack_form)
    monkeypatch.setattr(
        OpsMeshService,
        "_download_slack_media_url",
        fake_download_slack_media_url,
    )
    monkeypatch.setattr(
        OpsMeshService,
        "_upload_slack_file_bytes",
        fake_upload_slack_file_bytes,
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

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship native Slack parity.",
        media_urls=["https://example.com/slack.png"],
        account_id="workspace-bot",
        idempotency_key="idem-native-slack-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-slack-send",
        "channel": "slack",
        "messageId": "F111",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "C123",
        "channelId": "C123",
        "mediaIds": ["F111"],
        "mediaUrls": ["https://example.com/slack.png"],
    }
    assert slack_forms == [
        (
            "https://slack.com/api/files.getUploadURLExternal",
            {
                "filename": "slack.png",
                "length": "8",
            },
            "xoxb-route-token",
        ),
        (
            "https://slack.com/api/files.completeUploadExternal",
            {
                "files": '[{"id": "F111", "title": "slack.png"}]',
                "channel_id": "C123",
                "initial_comment": (
                    "Ship native Slack parity.\n\nMedia:\n1. https://example.com/slack.png"
                ),
            },
            "xoxb-route-token",
        ),
    ]
    assert uploaded_files == [("https://upload.slack.test/file-1", b"fake-png")]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "F111",
        "chatId": "C123",
        "channelId": "C123",
        "mediaIds": ["F111"],
        "mediaUrls": ["https://example.com/slack.png"],
    }


@pytest.mark.asyncio
async def test_slack_media_download_resolves_managed_canvas_document_path(tmp_path) -> None:
    canvas_state_dir = tmp_path / "data"
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "photo.png").write_bytes(b"canvas-png")
    document = create_canvas_document(
        {
            "kind": "image",
            "entrypoint": {"type": "path", "value": "photo.png"},
        },
        state_dir=canvas_state_dir,
        workspace_dir=workspace_dir,
    )
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        canvas_state_dir=canvas_state_dir,
    )

    media_bytes = service._download_slack_media_url(
        f"/__openclaw__/canvas/documents/{document['id']}/photo.png"
    )

    assert media_bytes == b"canvas-png"


@pytest.mark.asyncio
async def test_ops_mesh_service_tests_slack_native_route_with_native_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-test-slack-native-route"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
        name="Slack Native Route Test",
        kind="slack",
        target="https://slack.com/api",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="xoxb-route-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {"ok": True, "ts": "1713980000.000300", "channel": "C123"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.test_notification_route(route_id, event_type="gateway/send")
    delivery = await database.get_outbound_delivery(1)
    route = (await database.list_notification_routes())[0]

    assert result.ok is True
    assert slack_posts == [
        (
            "https://slack.com/api/chat.postMessage",
            {
                "channel": "c123",
                "text": "OpenZues test delivery ping.",
            },
            "Authorization",
            "Bearer xoxb-route-token",
        )
    ]
    assert delivery is not None
    assert delivery["delivery_state"] == "delivered"
    assert delivery["delivery_message_id"] == "1713980000.000300"
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "1713980000.000300",
        "chatId": "C123",
        "channelId": "C123",
    }
    assert route["last_result"] == "Delivered gateway/send (test)"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_telegram_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-telegram-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Send Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"id": -100123},
                "photo": [{"file_id": "small-photo"}, {"file_id": "large-photo"}],
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="channel:-100123",
        message="Ship native Telegram parity.",
        media_urls=["https://example.com/telegram.png"],
        account_id="telegram-bot",
        idempotency_key="idem-native-telegram-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="telegram",
            account_id="telegram-bot",
            peer_kind="channel",
            peer_id="channel:-100123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-telegram-send",
        "channel": "telegram",
        "messageId": "42",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "telegram",
            "target": "channel:-100123",
            "accountId": "telegram-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "-100123",
        "channelId": "-100123",
        "mediaIds": ["large-photo"],
        "mediaUrls": ["https://example.com/telegram.png"],
    }
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPhoto",
            {
                "chat_id": "-100123",
                "photo": "https://example.com/telegram.png",
                "caption": (
                    "Ship native Telegram parity.\n\n"
                    "Media:\n"
                    "1. https://example.com/telegram.png"
                ),
            },
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "42",
        "chatId": "-100123",
        "channelId": "-100123",
        "mediaIds": ["large-photo"],
        "mediaUrls": ["https://example.com/telegram.png"],
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_telegram_native_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-telegram-options"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Send Options",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 43,
                "chat": {"id": -100123},
                "document": {"file_id": "report-document"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="channel:-100123",
        message="Ship native Telegram document parity.",
        media_urls=["https://example.com/report.pdf"],
        account_id="telegram-bot",
        thread_id="forum-42",
        reply_to_id="41",
        silent=True,
        force_document=True,
        idempotency_key="idem-native-telegram-send-options",
    )

    assert result["messageId"] == "43"
    assert result["mediaIds"] == ["report-document"]
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendDocument",
            {
                "chat_id": "-100123",
                "message_thread_id": "forum-42",
                "reply_to_message_id": "41",
                "disable_notification": True,
                "document": "https://example.com/report.pdf",
                "disable_content_type_detection": True,
                "caption": (
                    "Ship native Telegram document parity.\n\n"
                    "Media:\n"
                    "1. https://example.com/report.pdf"
                ),
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_parses_telegram_topic_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-telegram-topic-target"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Topic Target",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target=None,
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 44,
                "chat": {"id": -100123},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="telegram:group:-100123:topic:77",
        message="Ship Telegram topic target parity.",
        account_id="telegram-bot",
        idempotency_key="idem-native-telegram-topic-target",
    )

    assert result["messageId"] == "44"
    assert result["chatId"] == "-100123"
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendMessage",
            {
                "chat_id": "-100123",
                "message_thread_id": "77",
                "text": "Ship Telegram topic target parity.",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_routes_telegram_topic_to_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-telegram-topic-parent"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Topic Parent Route",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 45,
                "chat": {"id": -100123},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="telegram:group:-100123:topic:77",
        message="Ship Telegram topic parent route parity.",
        account_id="telegram-bot",
        idempotency_key="idem-native-telegram-topic-parent",
    )

    assert result["messageId"] == "45"
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendMessage",
            {
                "chat_id": "-100123",
                "message_thread_id": "77",
                "text": "Ship Telegram topic parent route parity.",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_telegram_media_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-telegram-media-group"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Media Group Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        if len(telegram_posts) == 1:
            return {
                "ok": True,
                "result": {
                    "message_id": 44,
                    "chat": {"id": -100123},
                    "photo": [{"file_id": "small-one"}, {"file_id": "large-one"}],
                },
            }
        return {
            "ok": True,
            "result": {
                "message_id": 45,
                "chat": {"id": -100123},
                "photo": [{"file_id": "small-two"}, {"file_id": "large-two"}],
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="telegram",
        to="channel:-100123",
        message="Ship the media bundle.",
        media_urls=[
            "https://example.com/one.png",
            "https://example.com/two.png",
        ],
        account_id="telegram-bot",
        idempotency_key="idem-native-telegram-media-group",
    )

    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "45"
    assert result["mediaIds"] == ["large-one", "large-two"]
    assert result["mediaUrls"] == [
        "https://example.com/one.png",
        "https://example.com/two.png",
    ]
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPhoto",
            {
                "chat_id": "-100123",
                "photo": "https://example.com/one.png",
                "caption": (
                    "Ship the media bundle.\n\n"
                    "Media:\n"
                    "1. https://example.com/one.png\n"
                    "2. https://example.com/two.png"
                ),
            },
        ),
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPhoto",
            {
                "chat_id": "-100123",
                "photo": "https://example.com/two.png",
            },
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["provider_result"]["mediaIds"] == [
        "large-one",
        "large-two",
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_discord_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-discord-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Send Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-webhook",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        discord_posts.append((target, payload))
        return {"id": "discord-message-1", "channel_id": "987654321"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="discord",
        to="channel:987654321",
        message="Ship native Discord parity.",
        media_urls=["https://example.com/discord.png"],
        account_id="discord-webhook",
        idempotency_key="idem-native-discord-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="discord",
            account_id="discord-webhook",
            peer_kind="channel",
            peer_id="channel:987654321",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-discord-send",
        "channel": "discord",
        "messageId": "discord-message-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "discord",
            "target": "channel:987654321",
            "accountId": "discord-webhook",
            "sessionKey": expected_session_key,
        },
        "chatId": "987654321",
        "channelId": "987654321",
        "mediaUrls": ["https://example.com/discord.png"],
    }
    assert discord_posts == [
        (
            "https://discord.com/api/webhooks/webhook-id/webhook-token?wait=true",
            {
                "content": "Ship native Discord parity.\n\nMedia:\n1. https://example.com/discord.png",
                "embeds": [{"image": {"url": "https://example.com/discord.png"}}],
            },
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "discord-message-1",
        "chatId": "987654321",
        "channelId": "987654321",
        "mediaUrls": ["https://example.com/discord.png"],
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_preserves_discord_reply_and_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-discord-reply"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Reply Native Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-webhook",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        discord_posts.append((target, payload))
        return {"id": "discord-reply-1", "channel_id": "987654321"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.send_direct_channel_message(
        channel="discord",
        to="channel:987654321",
        message="Reply without notifying everyone.",
        account_id="discord-webhook",
        reply_to_id="parent-message-1",
        silent=True,
        idempotency_key="idem-native-discord-reply-silent",
    )

    assert discord_posts == [
        (
            "https://discord.com/api/webhooks/webhook-id/webhook-token?wait=true",
            {
                "content": "Reply without notifying everyone.",
                "flags": 1 << 12,
                "message_reference": {
                    "message_id": "parent-message-1",
                    "fail_if_not_exists": False,
                },
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_whatsapp_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-whatsapp-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Send Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": "wamid.send.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="whatsapp",
        to="direct:+15551234567",
        message="Ship native WhatsApp parity.",
        media_urls=["https://example.com/whatsapp.png"],
        account_id="wa-business",
        idempotency_key="idem-native-whatsapp-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="whatsapp",
            account_id="wa-business",
            peer_kind="direct",
            peer_id="direct:+15551234567",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-whatsapp-send",
        "channel": "whatsapp",
        "messageId": "wamid.send.1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "whatsapp",
            "target": "direct:+15551234567",
            "accountId": "wa-business",
            "sessionKey": expected_session_key,
        },
        "chatId": "15551234567",
        "channelId": "15551234567",
        "mediaUrls": ["https://example.com/whatsapp.png"],
    }
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "type": "image",
                "image": {
                    "link": "https://example.com/whatsapp.png",
                    "caption": "Ship native WhatsApp parity.",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "wamid.send.1",
        "chatId": "15551234567",
        "channelId": "15551234567",
        "mediaUrls": ["https://example.com/whatsapp.png"],
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_chunks_whatsapp_long_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-whatsapp-long-text"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Long Text Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": f"wamid.chunk.{len(whatsapp_posts)}"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    long_text = "x" * 8500

    result = await service.send_direct_channel_message(
        channel="whatsapp",
        to="direct:+15551234567",
        message=long_text,
        account_id="wa-business",
        idempotency_key="idem-native-whatsapp-long-text",
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "wamid.chunk.3"
    assert len(whatsapp_posts) == 3
    bodies = [post[1]["text"]["body"] for post in whatsapp_posts]  # type: ignore[index]
    assert [len(body) for body in bodies] == [4000, 4000, 500]
    assert "".join(str(body) for body in bodies) == long_text
    assert all(
        post[0] == "https://graph.facebook.com/v20.0/123456789/messages"
        for post in whatsapp_posts
    )
    assert all(post[2] == "Authorization" for post in whatsapp_posts)
    assert all(post[3] == "Bearer wa-access-token" for post in whatsapp_posts)
    assert delivery is not None
    assert delivery["route_scope"]["provider_result"]["messageId"] == "wamid.chunk.3"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_zalo_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-zalo-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Zalo Native Send Provider",
        kind="zalo",
        target="https://bot-api.zaloplatforms.test",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="zalo-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "zalo",
            "account_id": "zalo-bot",
            "peer_kind": "direct",
            "peer_id": "direct:dm-chat-1",
        },
    )
    zalo_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        zalo_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "result": {
                "message_id": f"zalo-msg-{len(zalo_posts)}",
                "chat": {"id": "dm-chat-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    long_text = "z" * 3000

    result = await service.send_direct_channel_message(
        channel="zalo",
        to="direct:dm-chat-1",
        message=long_text,
        account_id="zalo-bot",
        idempotency_key="idem-native-zalo-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="zalo",
            account_id="zalo-bot",
            peer_kind="direct",
            peer_id="direct:dm-chat-1",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-zalo-send",
        "channel": "zalo",
        "messageId": "zalo-msg-2",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "zalo",
            "target": "direct:dm-chat-1",
            "accountId": "zalo-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "dm-chat-1",
        "channelId": "dm-chat-1",
    }
    assert zalo_posts == [
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendMessage",
            {
                "chat_id": "dm-chat-1",
                "text": "z" * 2000,
            },
            None,
            None,
        ),
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendMessage",
            {
                "chat_id": "dm-chat-1",
                "text": "z" * 1000,
            },
            None,
            None,
        ),
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "zalo-msg-2",
        "chatId": "dm-chat-1",
        "channelId": "dm-chat-1",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_splits_zalo_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-zalo-media"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Zalo Native Media Provider",
        kind="zalo",
        target="https://bot-api.zaloplatforms.test",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="zalo-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "zalo",
            "account_id": "zalo-bot",
            "peer_kind": "direct",
            "peer_id": "direct:dm-chat-1",
        },
    )
    zalo_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        zalo_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "result": {
                "message_id": f"zalo-photo-{len(zalo_posts)}",
                "chat": {"id": "dm-chat-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="zalo",
        to="direct:dm-chat-1",
        message="Caption",
        media_urls=[
            "https://example.com/one.jpg",
            "https://example.com/two.jpg",
        ],
        account_id="zalo-bot",
        idempotency_key="idem-native-zalo-media",
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "zalo-photo-2"
    assert result["chatId"] == "dm-chat-1"
    assert result["channelId"] == "dm-chat-1"
    assert result["mediaIds"] == ["zalo-photo-1", "zalo-photo-2"]
    assert result["mediaUrls"] == [
        "https://example.com/one.jpg",
        "https://example.com/two.jpg",
    ]
    assert zalo_posts == [
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendPhoto",
            {
                "chat_id": "dm-chat-1",
                "photo": "https://example.com/one.jpg",
                "caption": "Caption",
            },
            None,
            None,
        ),
        (
            "https://bot-api.zaloplatforms.test/botzalo-access-token/sendPhoto",
            {
                "chat_id": "dm-chat-1",
                "photo": "https://example.com/two.jpg",
            },
            None,
            None,
        ),
    ]
    assert delivery is not None
    assert delivery["route_scope"]["provider_result"]["messageId"] == "zalo-photo-2"
    assert delivery["route_scope"]["provider_result"]["mediaIds"] == [
        "zalo-photo-1",
        "zalo-photo-2",
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_splits_whatsapp_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-whatsapp-media"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Media Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789/messages",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="Bearer wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": f"wamid.media.{len(whatsapp_posts)}"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="whatsapp",
        to="direct:+15551234567",
        message="Ship both WhatsApp images.",
        media_urls=[
            "https://example.com/one.png",
            "https://example.com/two.png",
        ],
        account_id="wa-business",
        idempotency_key="idem-native-whatsapp-media",
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "wamid.media.2"
    assert result["mediaIds"] == ["wamid.media.1", "wamid.media.2"]
    assert result["mediaUrls"] == [
        "https://example.com/one.png",
        "https://example.com/two.png",
    ]
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "type": "image",
                "image": {
                    "link": "https://example.com/one.png",
                    "caption": "Ship both WhatsApp images.",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        ),
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "type": "image",
                "image": {"link": "https://example.com/two.png"},
            },
            "Authorization",
            "Bearer wa-access-token",
        ),
    ]
    assert delivery is not None
    assert delivery["route_scope"]["provider_result"]["messageId"] == "wamid.media.2"
    assert delivery["route_scope"]["provider_result"]["mediaIds"] == [
        "wamid.media.1",
        "wamid.media.2",
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_preserves_whatsapp_reply_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-whatsapp-document-reply"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Document Reply Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": "wamid.doc.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="whatsapp",
        to="direct:+15551234567",
        message="Ship doc reply.",
        media_urls=["https://example.com/report.pdf"],
        account_id="wa-business",
        reply_to_id="wamid.reply.99",
        force_document=True,
        idempotency_key="idem-native-whatsapp-document-reply",
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "wamid.doc.1"
    assert result["mediaUrls"] == ["https://example.com/report.pdf"]
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "context": {"message_id": "wamid.reply.99"},
                "type": "document",
                "document": {
                    "link": "https://example.com/report.pdf",
                    "caption": "Ship doc reply.",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]
    assert delivery is not None
    assert delivery["event_payload"]["replyToId"] == "wamid.reply.99"
    assert delivery["event_payload"]["forceDocument"] is True
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "wamid.doc.1",
        "chatId": "15551234567",
        "channelId": "15551234567",
        "mediaUrls": ["https://example.com/report.pdf"],
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_whatsapp_gif_video_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-whatsapp-gif-video"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native GIF Video Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token="wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": "wamid.video.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="whatsapp",
        to="direct:+15551234567",
        message="Ship loop.",
        media_urls=["https://example.com/loop.mp4"],
        account_id="wa-business",
        gif_playback=True,
        idempotency_key="idem-native-whatsapp-gif-video",
    )
    delivery = await database.get_outbound_delivery(1)

    assert result["messageId"] == "wamid.video.1"
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "type": "video",
                "video": {
                    "link": "https://example.com/loop.mp4",
                    "caption": "Ship loop.",
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]
    assert delivery is not None
    assert delivery["event_payload"]["gifPlayback"] is True
    assert delivery["route_scope"]["provider_result"]["mediaUrls"] == [
        "https://example.com/loop.mp4"
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_uses_gateway_route_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-route-provider"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Gateway Send Provider",
        kind="webhook",
        target="https://example.invalid/gateway-send",
        events=["gateway/send"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    provider_posts: list[tuple[dict[str, object], str, dict[str, object], str | None]] = []

    def fake_post_webhook(
        self: OpsMeshService,
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> dict[str, str]:
        del self
        provider_posts.append((route, event_type, event, secret_token))
        return {
            "messageId": "route-provider-send-1",
            "chatId": "C123",
            "channelId": "slack:C123",
            "toJid": "C123@slack",
        }

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship route-backed parity.",
        media_urls=["https://example.com/route.png"],
        account_id="workspace-bot",
        idempotency_key="idem-route-provider-send",
    )
    cached_result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="Ship route-backed parity.",
        media_urls=["https://example.com/route.png"],
        account_id="workspace-bot",
        idempotency_key="idem-route-provider-send",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)
    route = (await database.list_notification_routes())[0]

    assert result == {
        "ok": True,
        "runId": "idem-route-provider-send",
        "channel": "slack",
        "messageId": "route-provider-send-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "C123",
        "channelId": "slack:C123",
        "toJid": "C123@slack",
    }
    assert cached_result == result
    assert len(provider_posts) == 1
    _route, event_type, event, secret_token = provider_posts[0]
    assert event_type == "gateway/send"
    assert event["message"] == "Ship route-backed parity.\n\nMedia:\n1. https://example.com/route.png"
    assert event["mediaUrls"] == ["https://example.com/route.png"]
    assert event["routeMatch"] == "peer"
    conversation_target = event["conversationTarget"]
    assert isinstance(conversation_target, dict)
    assert conversation_target["channel"] == "slack"
    assert conversation_target["account_id"] == "workspace-bot"
    assert conversation_target["peer_kind"] == "channel"
    assert conversation_target["peer_id"] == "channel:c123"
    assert secret_token is None
    assert delivery is not None
    assert delivery["delivery_state"] == "delivered"
    assert delivery["delivery_message_id"] == "route-provider-send-1"
    assert delivery["route_scope"]["provider_result"] == {
        "messageId": "route-provider-send-1",
        "chatId": "C123",
        "channelId": "slack:C123",
        "toJid": "C123@slack",
    }
    assert route["last_result"] == "Delivered gateway/send provider runtime"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_dedupes_inflight_idempotent_retries(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-idempotent"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []
    delivery_started = asyncio.Event()
    release_delivery = asyncio.Event()

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        delivery_started.set()
        await release_delivery.wait()
        return {"messageId": "42"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    first_task = asyncio.create_task(
        service.send_direct_channel_message(
            channel="slack",
            to="channel:C123",
            message="Ship parity.",
            account_id="default",
            idempotency_key="idem-direct-send",
        )
    )
    await delivery_started.wait()
    second_task = asyncio.create_task(
        service.send_direct_channel_message(
            channel="slack",
            to="channel:C123",
            message="Ship parity.",
            account_id="default",
            idempotency_key="idem-direct-send",
        )
    )
    release_delivery.set()
    first_result, second_result = await asyncio.gather(first_task, second_task)

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="default",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    deliveries = await database.list_outbound_deliveries(limit=10)
    delivery_views = await service.list_outbound_delivery_views(limit=10)

    assert first_result == second_result == {
        "ok": True,
        "runId": "idem-direct-send",
        "channel": "slack",
        "messageId": "42",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "sessionKey": expected_session_key,
        },
    }
    assert session_deliveries == [(expected_session_key, "Ship parity.")]
    assert len(deliveries) == 1
    assert deliveries[0]["request_idempotency_key"] == "idem-direct-send"
    assert deliveries[0]["delivery_message_id"] == "42"
    assert delivery_views[0].request_idempotency_key == "idem-direct-send"
    assert delivery_views[0].delivery_message_id == "42"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_message_records_media_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-send-media"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Media Inventory",
        kind="webhook",
        target="https://example.invalid/slack-media",
        events=["mission/completed"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        return {"messageId": "88"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.send_direct_channel_message(
        channel="slack",
        to="channel:C123",
        message="",
        media_urls=["https://example.com/a.png", " https://example.com/b.png ", ""],
        gif_playback=True,
        thread_id="1710000000.9999",
        idempotency_key="idem-direct-media",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="workspace-bot",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-direct-media",
        "channel": "slack",
        "messageId": "88",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert session_deliveries == [
        (
            expected_session_key,
            (
                "Media:\n"
                "1. https://example.com/a.png\n"
                "2. https://example.com/b.png\n\n"
                "Settings: gifPlayback=true"
            ),
        )
    ]
    assert delivery is not None
    assert delivery["event_type"] == "gateway/send"
    assert delivery["message_summary"] == "Media delivery (2 items)"
    assert delivery["session_key"] == expected_session_key
    assert delivery["conversation_target"]["account_id"] == "workspace-bot"
    assert delivery["event_payload"]["accountId"] == "workspace-bot"
    assert delivery["event_payload"]["mediaUrls"] == [
        "https://example.com/a.png",
        "https://example.com/b.png",
    ]
    assert delivery["event_payload"]["gifPlayback"] is True
    assert delivery["route_scope"]["source"] == "gateway.send"
    assert delivery["route_scope"]["resolved_account_id"] == "workspace-bot"
    assert delivery["route_scope"]["idempotency_key"] == "idem-direct-media"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_records_session_backed_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Poll Inventory",
        kind="webhook",
        target="https://example.invalid/slack-poll",
        events=["mission/completed"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        return {"messageId": "77"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Ship it?",
        options=["Yes", "No"],
        max_selections=1,
        duration_hours=24,
        silent=True,
        is_anonymous=False,
        thread_id="1710000000.9999",
        idempotency_key="idem-direct-poll",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="workspace-bot",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-direct-poll",
        "channel": "slack",
        "messageId": "77",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert session_deliveries == [
        (
            expected_session_key,
            (
                "Poll: Ship it?\n"
                "1. Yes\n"
                "2. No\n\n"
                "Settings: maxSelections=1, durationHours=24, silent=true, "
                "isAnonymous=false"
            ),
        )
    ]
    assert delivery is not None
    assert delivery["event_type"] == "gateway/poll"
    assert delivery["route_kind"] == "announce"
    assert delivery["session_key"] == expected_session_key
    assert delivery["message_summary"] == "Ship it?"
    assert delivery["delivery_message_id"] == "77"
    assert delivery["conversation_target"]["account_id"] == "workspace-bot"
    assert delivery["event_payload"]["accountId"] == "workspace-bot"
    assert delivery["event_payload"]["question"] == "Ship it?"
    assert delivery["event_payload"]["options"] == ["Yes", "No"]
    assert delivery["event_payload"]["maxSelections"] == 1
    assert delivery["event_payload"]["durationHours"] == 24
    assert delivery["event_payload"]["silent"] is True
    assert delivery["event_payload"]["isAnonymous"] is False
    assert delivery["route_scope"]["source"] == "gateway.poll"
    assert delivery["route_scope"]["resolved_account_id"] == "workspace-bot"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_prefers_provider_runtime() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-provider"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    provider_requests: list[GatewayOutboundRuntimePollRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimePollRequest,
    ) -> dict[str, str]:
        provider_requests.append(request)
        return {"id": "provider-poll-77"}

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        raise AssertionError(f"session fallback should not run: {session_key} {message}")

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            session_deliverer=fake_session_delivery,
            provider_poll_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Ship the provider path?",
        options=["Yes", "No"],
        max_selections=1,
        duration_seconds=3600,
        silent=False,
        is_anonymous=True,
        account_id="workspace-bot",
        reply_to_id="message-42",
        thread_id="1710000000.9999",
        gateway_client_scopes=[],
        idempotency_key="idem-provider-runtime-poll",
    )

    expected_session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
            conversation_target=ConversationTargetView(
                channel="slack",
                account_id="workspace-bot",
                peer_kind="channel",
                peer_id="channel:C123",
            ),
        ),
        thread_id="1710000000.9999",
    ).session_key
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-provider-runtime-poll",
        "channel": "slack",
        "messageId": "provider-poll-77",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "threadId": "1710000000.9999",
            "sessionKey": expected_session_key,
        },
    }
    assert provider_requests == [
        GatewayOutboundRuntimePollRequest(
            channel="slack",
            target="channel:C123",
            question="Ship the provider path?",
            options=("Yes", "No"),
            max_selections=1,
            duration_seconds=3600,
            silent=False,
            is_anonymous=True,
            account_id="workspace-bot",
            reply_to_id="message-42",
            thread_id="1710000000.9999",
            session_key=expected_session_key,
            gateway_client_scopes=(),
        )
    ]
    assert delivery is not None
    assert delivery["delivery_state"] == "delivered"
    assert delivery["delivery_message_id"] == "provider-poll-77"
    assert delivery["event_payload"]["durationSeconds"] == 3600
    assert delivery["event_payload"]["gatewayClientScopes"] == []


@pytest.mark.asyncio
async def test_gateway_outbound_runtime_poll_defaults_max_selections_to_one() -> None:
    provider_requests: list[GatewayOutboundRuntimePollRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimePollRequest,
    ) -> dict[str, str]:
        provider_requests.append(request)
        return {"id": "provider-poll-default-1"}

    runtime = GatewayOutboundRuntimeService(
        provider_poll_deliverer=fake_provider_delivery,
    )

    result = await runtime.deliver_poll(
        session_key="launch:channel:slack:peer:channel:C123",
        message="Poll: Default max selections?",
        channel="slack",
        target="channel:C123",
        question="Default max selections?",
        options=("Yes", "No"),
    )

    assert result.message_id == "provider-poll-default-1"
    assert provider_requests == [
        GatewayOutboundRuntimePollRequest(
            channel="slack",
            target="channel:C123",
            question="Default max selections?",
            options=("Yes", "No"),
            max_selections=1,
            session_key="launch:channel:slack:peer:channel:C123",
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_native_adapter_binding() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-native-adapter"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    native_requests: list[GatewayOutboundRuntimePollRequest] = []

    async def fake_native_delivery(
        request: GatewayOutboundRuntimePollRequest,
    ) -> dict[str, str]:
        native_requests.append(request)
        return {
            "id": "native-slack-poll-1",
            "pollId": "poll-native-1",
            "conversationId": "conv-native-1",
        }

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimePollRequest,
    ) -> dict[str, str]:
        raise AssertionError(f"generic provider should not run: {request}")

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        raise AssertionError(f"session fallback should not run: {session_key} {message}")

    runtime = GatewayOutboundRuntimeService(
        session_deliverer=fake_session_delivery,
        provider_poll_deliverer=fake_provider_delivery,
    )
    runtime.bind_native_poll_deliverer(
        channel="slack",
        account_id="workspace-bot",
        deliverer=fake_native_delivery,
    )
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=runtime,
    )

    result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Use the native adapter?",
        options=["Yes", "No"],
        max_selections=1,
        account_id="workspace-bot",
        idempotency_key="idem-native-runtime-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-runtime-poll",
        "channel": "slack",
        "messageId": "native-slack-poll-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "conversationId": "conv-native-1",
        "pollId": "poll-native-1",
    }
    assert native_requests == [
        GatewayOutboundRuntimePollRequest(
            channel="slack",
            target="channel:C123",
            question="Use the native adapter?",
            options=("Yes", "No"),
            max_selections=1,
            account_id="workspace-bot",
            session_key=expected_session_key,
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "conversationId": "conv-native-1",
        "pollId": "poll-native-1",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_slack_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-slack-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Native Poll Provider",
        kind="slack",
        target="https://slack.com/api",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="Bearer xoxb-route-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    slack_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        slack_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "ok": True,
            "channel": "C123",
            "message": {"ts": "1713980000.000200", "channel": "C123"},
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Ship native Slack poll?",
        options=["Yes", "No"],
        max_selections=1,
        duration_hours=2,
        silent=True,
        account_id="workspace-bot",
        idempotency_key="idem-native-slack-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-slack-poll",
        "channel": "slack",
        "messageId": "1713980000.000200",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "C123",
        "channelId": "C123",
        "conversationId": "C123",
        "pollId": "1713980000.000200",
    }
    assert slack_posts == [
        (
            "https://slack.com/api/chat.postMessage",
            {
                "channel": "C123",
                "text": (
                    "Poll: Ship native Slack poll?\n"
                    "1. Yes\n"
                    "2. No\n\n"
                    "Settings: maxSelections=1, durationHours=2, silent=true"
                ),
            },
            "Authorization",
            "Bearer xoxb-route-token",
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "1713980000.000200",
        "chatId": "C123",
        "channelId": "C123",
        "conversationId": "C123",
        "pollId": "1713980000.000200",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_telegram_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-telegram-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Poll Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="bot123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 43,
                "chat": {"id": -100123},
                "poll": {"id": "poll-telegram-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="telegram",
        to="channel:-100123",
        question="Ship native Telegram poll?",
        options=[" Yes ", "   ", "No"],
        max_selections=2,
        duration_seconds=60,
        silent=True,
        is_anonymous=False,
        account_id="telegram-bot",
        reply_to_id="41",
        idempotency_key="idem-native-telegram-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="telegram",
            account_id="telegram-bot",
            peer_kind="channel",
            peer_id="channel:-100123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-telegram-poll",
        "channel": "telegram",
        "messageId": "43",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "telegram",
            "target": "channel:-100123",
            "accountId": "telegram-bot",
            "sessionKey": expected_session_key,
        },
        "chatId": "-100123",
        "channelId": "-100123",
        "conversationId": "-100123",
        "pollId": "poll-telegram-1",
    }
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPoll",
            {
                "chat_id": "-100123",
                "question": "Ship native Telegram poll?",
                "options": ["Yes", "No"],
                "allows_multiple_answers": True,
                "is_anonymous": False,
                "open_period": 60,
                "disable_notification": True,
                "reply_to_message_id": "41",
            },
        )
    ]
    assert delivery is not None
    assert delivery["event_payload"]["options"] == ["Yes", "No"]
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "43",
        "chatId": "-100123",
        "channelId": "-100123",
        "conversationId": "-100123",
        "pollId": "poll-telegram-1",
    }


@pytest.mark.parametrize(
    ("poll_kwargs", "expected_message"),
    [
        (
            {"duration_seconds": 601},
            "Telegram poll durationSeconds must be between 5 and 600",
        ),
        (
            {"duration_hours": 1},
            "Telegram poll durationHours is not supported. "
            "Use durationSeconds (5-600) instead.",
        ),
        (
            {"duration_seconds": 60, "duration_hours": 1},
            "durationSeconds and durationHours are mutually exclusive",
        ),
    ],
)
@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_rejects_invalid_telegram_durations(
    monkeypatch: pytest.MonkeyPatch,
    poll_kwargs: dict[str, int],
    expected_message: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-telegram-duration"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Poll Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="bot123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 43,
                "chat": {"id": -100123},
                "poll": {"id": "poll-telegram-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(ValueError, match=re.escape(expected_message)):
        await service.send_direct_channel_poll(
            channel="telegram",
            to="channel:-100123",
            question="Ship native Telegram poll?",
            options=["Yes", "No"],
            account_id="telegram-bot",
            idempotency_key="idem-native-telegram-poll-invalid-duration",
            **poll_kwargs,
        )

    assert telegram_posts == []


@pytest.mark.parametrize(
    ("question", "options", "expected_message"),
    [
        ("   ", ["Yes", "No"], "Poll question is required"),
        ("Pick one", ["Yes", "   "], "Poll requires at least 2 options"),
    ],
)
@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_rejects_invalid_poll_shape(
    monkeypatch: pytest.MonkeyPatch,
    question: str,
    options: list[str],
    expected_message: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-shape"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Poll Provider",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="bot123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 43,
                "chat": {"id": -100123},
                "poll": {"id": "poll-telegram-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(ValueError, match=re.escape(expected_message)):
        await service.send_direct_channel_poll(
            channel="telegram",
            to="channel:-100123",
            question=question,
            options=options,
            account_id="telegram-bot",
            idempotency_key="idem-native-telegram-poll-invalid-shape",
        )

    assert telegram_posts == []


@pytest.mark.parametrize(
    ("channel", "target", "account_id"),
    [
        ("telegram", "channel:-100123", "telegram-bot"),
        ("discord", "channel:987654321", "discord-webhook"),
    ],
)
@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_rejects_provider_option_caps(
    channel: str,
    target: str,
    account_id: str,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / f"ops-mesh-direct-poll-{channel}-options"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(ValueError, match="Poll supports at most 10 options"):
        await service.send_direct_channel_poll(
            channel=channel,
            to=target,
            question="Pick one",
            options=[f"Option {index}" for index in range(11)],
            account_id=account_id,
            idempotency_key=f"idem-native-{channel}-poll-options",
        )


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_rejects_max_selections_above_options(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-max-selections"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    with pytest.raises(ValueError, match="maxSelections cannot exceed option count"):
        await service.send_direct_channel_poll(
            channel="telegram",
            to="channel:-100123",
            question="Pick several",
            options=["Yes", "No"],
            max_selections=3,
            account_id="telegram-bot",
            idempotency_key="idem-native-poll-max-selections",
        )


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_parses_telegram_topic_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-telegram-topic"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Native Poll Topic Parent",
        kind="telegram",
        target="https://api.telegram.org",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="bot123456:telegram-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "telegram-bot",
            "peer_kind": "channel",
            "peer_id": "channel:-100123",
        },
    )
    telegram_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        telegram_posts.append((target, payload))
        return {
            "ok": True,
            "result": {
                "message_id": 47,
                "chat": {"id": -100123},
                "poll": {"id": "poll-telegram-topic-1"},
            },
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="telegram",
        to="telegram:group:-100123:topic:77",
        question="Ship native Telegram topic poll?",
        options=["Yes", "No"],
        account_id="telegram-bot",
        idempotency_key="idem-native-telegram-topic-poll",
    )

    assert result["messageId"] == "47"
    assert result["pollId"] == "poll-telegram-topic-1"
    assert telegram_posts == [
        (
            "https://api.telegram.org/bot123456:telegram-token/sendPoll",
            {
                "chat_id": "-100123",
                "question": "Ship native Telegram topic poll?",
                "options": ["Yes", "No"],
                "allows_multiple_answers": False,
                "message_thread_id": "77",
            },
        )
    ]


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_discord_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-discord-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Discord Native Poll Provider",
        kind="discord",
        target="https://discord.com/api/webhooks/webhook-id/webhook-token",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "discord",
            "account_id": "discord-webhook",
            "peer_kind": "channel",
            "peer_id": "channel:987654321",
        },
    )
    discord_posts: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self, secret_header_name, secret_token
        discord_posts.append((target, payload))
        return {"id": "discord-poll-1", "channel_id": "987654321"}

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="discord",
        to="channel:987654321",
        question="Ship native Discord poll?",
        options=["Yes", "No"],
        max_selections=2,
        duration_hours=2,
        account_id="discord-webhook",
        idempotency_key="idem-native-discord-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="discord",
            account_id="discord-webhook",
            peer_kind="channel",
            peer_id="channel:987654321",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-discord-poll",
        "channel": "discord",
        "messageId": "discord-poll-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "discord",
            "target": "channel:987654321",
            "accountId": "discord-webhook",
            "sessionKey": expected_session_key,
        },
        "chatId": "987654321",
        "channelId": "987654321",
        "conversationId": "987654321",
        "pollId": "discord-poll-1",
    }
    assert discord_posts == [
        (
            "https://discord.com/api/webhooks/webhook-id/webhook-token?wait=true",
            {
                "poll": {
                    "question": {"text": "Ship native Discord poll?"},
                    "answers": [
                        {"poll_media": {"text": "Yes"}},
                        {"poll_media": {"text": "No"}},
                    ],
                    "duration": 2,
                    "allow_multiselect": True,
                    "layout_type": 1,
                },
            },
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "discord-poll-1",
        "chatId": "987654321",
        "channelId": "987654321",
        "conversationId": "987654321",
        "pollId": "discord-poll-1",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_whatsapp_native_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-whatsapp-native"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="WhatsApp Native Poll Provider",
        kind="whatsapp",
        target="https://graph.facebook.com/v20.0/123456789/messages",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token="Bearer wa-access-token",
        vault_secret_id=None,
        conversation_target={
            "channel": "whatsapp",
            "account_id": "wa-business",
            "peer_kind": "direct",
            "peer_id": "direct:+15551234567",
        },
    )
    whatsapp_posts: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self: OpsMeshService,
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> dict[str, object]:
        del self
        whatsapp_posts.append((target, payload, secret_header_name, secret_token))
        return {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+15551234567", "wa_id": "15551234567"}],
            "messages": [{"id": "wamid.poll.1"}],
        }

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="whatsapp",
        to="direct:+15551234567",
        question="Ship native WhatsApp poll?",
        options=["Yes", "No", "Later", "Ignored"],
        account_id="wa-business",
        idempotency_key="idem-native-whatsapp-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="whatsapp",
            account_id="wa-business",
            peer_kind="direct",
            peer_id="direct:+15551234567",
        ),
    )
    delivery = await database.get_outbound_delivery(1)

    assert result == {
        "ok": True,
        "runId": "idem-native-whatsapp-poll",
        "channel": "whatsapp",
        "messageId": "wamid.poll.1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "native-provider-backed",
            "channel": "whatsapp",
            "target": "direct:+15551234567",
            "accountId": "wa-business",
            "sessionKey": expected_session_key,
        },
        "chatId": "15551234567",
        "channelId": "15551234567",
        "conversationId": "15551234567",
        "pollId": "wamid.poll.1",
    }
    assert whatsapp_posts == [
        (
            "https://graph.facebook.com/v20.0/123456789/messages",
            {
                "messaging_product": "whatsapp",
                "to": "+15551234567",
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Ship native WhatsApp poll?"},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": "option-1", "title": "Yes"},
                            },
                            {
                                "type": "reply",
                                "reply": {"id": "option-2", "title": "No"},
                            },
                            {
                                "type": "reply",
                                "reply": {"id": "option-3", "title": "Later"},
                            },
                        ],
                    },
                },
            },
            "Authorization",
            "Bearer wa-access-token",
        )
    ]
    assert delivery is not None
    assert delivery["route_scope"]["transport_runtime"] == "native-provider-backed"
    assert delivery["route_scope"]["provider_result"] == {
        "runtime": "native-provider-backed",
        "messageId": "wamid.poll.1",
        "chatId": "15551234567",
        "channelId": "15551234567",
        "conversationId": "15551234567",
        "pollId": "wamid.poll.1",
    }


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_uses_gateway_route_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-route-provider"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Slack Gateway Poll Provider",
        kind="webhook",
        target="https://example.invalid/gateway-poll",
        events=["gateway/poll"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "channel:C123",
        },
    )
    provider_posts: list[tuple[dict[str, object], str, dict[str, object], str | None]] = []

    def fake_post_webhook(
        self: OpsMeshService,
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> dict[str, str]:
        del self
        provider_posts.append((route, event_type, event, secret_token))
        return {
            "id": "route-provider-poll-1",
            "pollId": "poll-1",
            "conversationId": "conv-1",
        }

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Use the route provider?",
        options=["Yes", "No"],
        duration_hours=2,
        silent=True,
        account_id="workspace-bot",
        idempotency_key="idem-route-provider-poll",
    )
    cached_result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Use the route provider?",
        options=["Yes", "No"],
        duration_hours=2,
        silent=True,
        account_id="workspace-bot",
        idempotency_key="idem-route-provider-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="workspace-bot",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    delivery = await database.get_outbound_delivery(1)
    route = (await database.list_notification_routes())[0]

    assert result == {
        "ok": True,
        "runId": "idem-route-provider-poll",
        "channel": "slack",
        "messageId": "route-provider-poll-1",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "provider-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "workspace-bot",
            "sessionKey": expected_session_key,
        },
        "conversationId": "conv-1",
        "pollId": "poll-1",
    }
    assert cached_result == result
    assert len(provider_posts) == 1
    _route, event_type, event, secret_token = provider_posts[0]
    assert event_type == "gateway/poll"
    assert event["question"] == "Use the route provider?"
    assert event["options"] == ["Yes", "No"]
    assert event["maxSelections"] == 1
    assert event["durationHours"] == 2
    assert event["silent"] is True
    assert event["routeMatch"] == "peer"
    assert secret_token is None
    assert delivery is not None
    assert delivery["event_payload"]["maxSelections"] == 1
    assert delivery["delivery_state"] == "delivered"
    assert delivery["delivery_message_id"] == "route-provider-poll-1"
    assert delivery["route_scope"]["provider_result"] == {
        "conversationId": "conv-1",
        "pollId": "poll-1",
    }
    assert route["last_result"] == "Delivered gateway/poll provider runtime"


@pytest.mark.asyncio
async def test_ops_mesh_service_send_direct_channel_poll_reuses_completed_idempotent_delivery(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-direct-poll-idempotent"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> dict[str, str]:
        session_deliveries.append((session_key, message))
        return {"messageId": "77"}

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    first_result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Ship it?",
        options=["Yes", "No"],
        max_selections=1,
        account_id="default",
        idempotency_key="idem-direct-poll",
    )
    second_result = await service.send_direct_channel_poll(
        channel="slack",
        to="channel:C123",
        question="Ship it?",
        options=["Yes", "No"],
        max_selections=1,
        account_id="default",
        idempotency_key="idem-direct-poll",
    )

    expected_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
        conversation_target=ConversationTargetView(
            channel="slack",
            account_id="default",
            peer_kind="channel",
            peer_id="channel:C123",
        ),
    )
    deliveries = await database.list_outbound_deliveries(limit=10)

    assert first_result == second_result == {
        "ok": True,
        "runId": "idem-direct-poll",
        "channel": "slack",
        "messageId": "77",
        "sessionKey": expected_session_key,
        "deliveryId": 1,
        "transport": {
            "runtime": "session-backed",
            "channel": "slack",
            "target": "channel:C123",
            "accountId": "default",
            "sessionKey": expected_session_key,
        },
    }
    assert session_deliveries == [
        (
            expected_session_key,
            "Poll: Ship it?\n1. Yes\n2. No\n\nSettings: maxSelections=1",
        )
    ]
    assert len(deliveries) == 1
    assert deliveries[0]["request_idempotency_key"] == "idem-direct-poll"
    assert deliveries[0]["delivery_message_id"] == "77"


def test_saved_outbound_delivery_replay_message_formats_gateway_send_media_payload() -> None:
    replay_message = _saved_outbound_delivery_replay_message(
        {
            "event_type": "gateway/send",
            "event_payload": {
                "message": "Ship parity.",
                "mediaUrls": ["https://example.com/a.png"],
                "gifPlayback": False,
            },
            "message_summary": "fallback summary",
        }
    )

    assert replay_message == (
        "Ship parity.\n\n"
        "Media:\n"
        "1. https://example.com/a.png\n\n"
        "Settings: gifPlayback=false"
    )


def test_saved_outbound_delivery_replay_message_formats_gateway_poll_payload() -> None:
    replay_message = _saved_outbound_delivery_replay_message(
        {
            "event_type": "gateway/poll",
            "event_payload": {
                "summary": "Ship parity?",
                "question": "Ship parity?",
                "options": ["Yes", "No"],
                "maxSelections": 1,
                "durationHours": 24,
                "silent": True,
                "isAnonymous": False,
            },
            "message_summary": "fallback summary",
        }
    )

    assert replay_message == (
        "Poll: Ship parity?\n"
        "1. Yes\n"
        "2. No\n\n"
        "Settings: maxSelections=1, durationHours=24, silent=true, isAnonymous=false"
    )


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_explicit_cron_failure_to_announce_thread_target(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Explicit Announce Failure Thread Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Deliver the cron failure directly to the explicit announce thread."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "deploy-room",
                    "accountId": "coordinator",
                    "threadId": 77,
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Explicit Announce Failure Thread Delivery",
        objective=(
            "Deliver the cron failure directly to the explicit announce thread."
        ),
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_explicit_announce_failure_thread_delivery",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="explicit announce thread delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:explicit-announce-failure-thread-route",
    )

    await service.handle_mission_event(
        "mission/failed",
        {"missionId": mission_id},
    )

    expected_base_session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    expected_session_key = resolve_thread_session_keys(
        base_session_key=expected_base_session_key,
        thread_id="77",
    ).session_key
    assert session_deliveries == [
        (
            expected_session_key,
            (
                '\u26a0\ufe0f Cron job "Explicit Announce Failure Thread Delivery" '
                "failed: lane timed out"
            ),
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "announce"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == expected_session_key
    assert deliveries[0].route_scope.route_match == "explicitTarget"
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["sessionKey"] == expected_session_key
    assert deliveries[0].event_payload["threadId"] == 77


@pytest.mark.asyncio
async def test_ops_mesh_service_dedupes_replayed_cron_failure_announce_delivery(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Replay Safe Announce Failure Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Deliver the cron failure once per execution.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "deploy-room",
                    "accountId": "coordinator",
                    "threadId": 77,
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Replay Safe Announce Failure Delivery",
        objective="Deliver the cron failure once per execution.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_replay_safe_announce_failure_delivery",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="explicit announce delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:replay-safe-announce-failure-route",
    )

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})
    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    expected_base_session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    expected_session_key = resolve_thread_session_keys(
        base_session_key=expected_base_session_key,
        thread_id="77",
    ).session_key
    assert session_deliveries == [
        (
            expected_session_key,
            (
                '\u26a0\ufe0f Cron job "Replay Safe Announce Failure Delivery" '
                "failed: lane timed out"
            ),
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].route_kind == "announce"
    assert deliveries[0].request_idempotency_key is not None
    assert deliveries[0].request_idempotency_key.startswith(
        "cron-direct-delivery:v1:"
    )


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_explicit_cron_failure_to_known_channel_default_account(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-cron-default-account"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Telegram Account Inventory",
        kind="webhook",
        target="https://example.invalid/telegram-account",
        events=["mission/completed"],
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
        conversation_target={
            "channel": "telegram",
            "account_id": "coordinator",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Explicit Announce Default Account Failure Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Deliver the cron failure directly to the explicit announce target."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "deploy-room",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Explicit Announce Default Account Failure Delivery",
        objective="Deliver the cron failure directly to the explicit announce target.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_explicit_announce_default_account_failure_delivery",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="explicit announce default-account delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:explicit-announce-default-account-failure-route",
    )

    await service.handle_mission_event(
        "mission/failed",
        {"missionId": mission_id},
    )

    expected_session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    assert session_deliveries == [
        (
            expected_session_key,
            (
                '\u26a0\ufe0f Cron job "Explicit Announce Default Account Failure Delivery" '
                "failed: lane timed out"
            ),
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    stored_delivery = await database.get_outbound_delivery(deliveries[0].id)
    assert len(deliveries) == 1
    assert deliveries[0].session_key == expected_session_key
    assert deliveries[0].conversation_target is not None
    assert deliveries[0].conversation_target.account_id == "coordinator"
    assert deliveries[0].route_scope.route_match == "explicitTarget"
    assert stored_delivery is not None
    assert stored_delivery["route_scope"]["resolved_account_id"] == "coordinator"
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["accountId"] == "coordinator"


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_explicit_cron_failure_destination_to_announce_target(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Explicit Announce Failure Destination",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Send the cron failure to the explicit failure destination."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "deploy-room",
                    "accountId": "coordinator",
                    "failureDestination": {
                        "mode": "announce",
                        "channel": "signal",
                        "to": "escalation-room",
                        "accountId": "escalations",
                    },
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Explicit Announce Failure Destination",
        objective="Send the cron failure to the explicit failure destination.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_explicit_announce_failure_destination",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="explicit announce failure destination failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:explicit-announce-failure-destination",
    )

    await service.handle_mission_event(
        "mission/failed",
        {"missionId": mission_id},
    )

    expected_session_key = (
        "launch:mode:workspace_affinity:channel:signal:account:escalations:"
        "peer:channel:escalation-room"
    )
    assert session_deliveries == [
        (
            expected_session_key,
            '\u26a0\ufe0f Cron job "Explicit Announce Failure Destination" failed: lane timed out',
        )
    ]
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "announce"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == expected_session_key
    assert deliveries[0].route_scope.route_match == "explicitTarget"
    assert deliveries[0].conversation_target is not None
    assert deliveries[0].conversation_target.channel == "signal"
    assert deliveries[0].conversation_target.account_id == "escalations"
    assert deliveries[0].conversation_target.peer_kind == "channel"
    assert deliveries[0].conversation_target.peer_id == "escalation-room"
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["sessionKey"] == expected_session_key
    payload_conversation_target = deliveries[0].event_payload["conversationTarget"]
    assert payload_conversation_target["channel"] == "signal"
    assert payload_conversation_target["account_id"] == "escalations"
    assert payload_conversation_target["peer_kind"] == "channel"
    assert payload_conversation_target["peer_id"] == "escalation-room"
    assert str(payload_conversation_target["summary"]).startswith("signal")


@pytest.mark.asyncio
async def test_ops_mesh_service_routes_cron_failure_to_matching_announce_notification_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Cron Failure Announce Route",
        kind="webhook",
        target="https://example.invalid/cron-failure-route",
        events=["cron/failure"],
        conversation_target={
            "channel": "telegram",
            "account_id": "coordinator",
            "peer_kind": "channel",
            "peer_id": "19098680",
        },
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
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
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Announce Failure Route",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Route cron failure through the announce target when no explicit "
                        "destination exists."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "19098680",
                    "accountId": "coordinator",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Announce Failure Route",
        objective=(
            "Route cron failure through the announce target when no explicit destination "
            "exists."
        ),
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_announce_route",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="announce delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:announce-failure-route",
    )

    webhook_calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, secret_token
        webhook_calls.append((str(route.get("target") or ""), event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert len(webhook_calls) == 1
    route_target, delivered_event_type, delivered_event = webhook_calls[0]
    assert route_target == "https://example.invalid/cron-failure-route"
    assert delivered_event_type == "cron/failure"
    assert delivered_event["missionId"] == mission_id
    assert delivered_event["taskId"] == task.id
    assert delivered_event["jobId"] == f"task-blueprint:{task.id}"
    assert delivered_event["jobName"] == "Announce Failure Route"
    assert delivered_event["message"] == 'Cron job "Announce Failure Route" failed: lane timed out'
    assert delivered_event["status"] == "error"
    assert delivered_event["error"] == "lane timed out"
    assert delivered_event["sessionKey"] == "agent:announce-failure-route"
    assert delivered_event["routeMatch"] == "peer"
    conversation_target = delivered_event["conversationTarget"]
    assert isinstance(conversation_target, dict)
    assert conversation_target["channel"] == "telegram"
    assert conversation_target["account_id"] == "coordinator"
    assert conversation_target["peer_kind"] == "channel"
    assert conversation_target["peer_id"] == "19098680"
    route_conversation_target = delivered_event["routeConversationTarget"]
    assert isinstance(route_conversation_target, dict)
    assert route_conversation_target["channel"] == "telegram"
    assert route_conversation_target["account_id"] == "coordinator"
    assert route_conversation_target["peer_kind"] == "channel"
    assert route_conversation_target["peer_id"] == "19098680"
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_target == "https://example.invalid/cron-failure-route"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == "agent:announce-failure-route"


@pytest.mark.asyncio
async def test_ops_mesh_service_routes_last_channel_cron_failure_without_conversation_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Cron Failure Session Route",
        kind="webhook",
        target="https://example.invalid/cron-failure-session-route",
        events=["cron/failure"],
        conversation_target=None,
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
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
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Last Channel Failure Route",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": (
                        "Route cron failure through the session-scoped last-channel fallback."
                    ),
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "last",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Last Channel Failure Route",
        objective="Route cron failure through the session-scoped last-channel fallback.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_last_channel_route",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="last-channel delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:main:telegram:direct:123:thread:99",
    )

    webhook_calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, secret_token
        webhook_calls.append((str(route.get("target") or ""), event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert len(webhook_calls) == 1
    route_target, delivered_event_type, delivered_event = webhook_calls[0]
    assert route_target == "https://example.invalid/cron-failure-session-route"
    assert delivered_event_type == "cron/failure"
    assert delivered_event["missionId"] == mission_id
    assert delivered_event["taskId"] == task.id
    assert delivered_event["jobId"] == f"task-blueprint:{task.id}"
    assert delivered_event["jobName"] == "Last Channel Failure Route"
    assert (
        delivered_event["message"]
        == 'Cron job "Last Channel Failure Route" failed: lane timed out'
    )
    assert delivered_event["status"] == "error"
    assert delivered_event["error"] == "lane timed out"
    assert delivered_event["sessionKey"] == "agent:main:telegram:direct:123:thread:99"
    assert "conversationTarget" not in delivered_event
    assert "routeConversationTarget" not in delivered_event
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_target == "https://example.invalid/cron-failure-session-route"
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == "agent:main:telegram:direct:123:thread:99"
    assert deliveries[0].conversation_target is None


@pytest.mark.asyncio
async def test_ops_mesh_service_delivers_last_channel_cron_failure_to_session_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Cron Failure Session Route",
        kind="webhook",
        target="https://example.invalid/cron-failure-session-route",
        events=["cron/failure"],
        conversation_target=None,
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Last Channel Failure Session Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Deliver cron failure through the live session key.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "last",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Last Channel Failure Session Delivery",
        objective="Deliver cron failure through the live session key.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_last_channel_session_delivery",
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
    session_key = "agent:main:telegram:direct:123:thread:99"
    await database.update_mission(
        mission_id,
        last_checkpoint="last-channel session delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key=session_key,
    )

    webhook_calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, secret_token
        webhook_calls.append((str(route.get("target") or ""), event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert session_deliveries == [
        (
            session_key,
            (
                '\u26a0\ufe0f Cron job "Last Channel Failure Session Delivery" failed: '
                "lane timed out"
            ),
        )
    ]
    assert webhook_calls == []
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "session"
    assert deliveries[0].route_target == session_key
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == session_key
    assert deliveries[0].conversation_target is None


@pytest.mark.asyncio
async def test_ops_mesh_service_prefers_stored_cron_session_key_for_last_channel_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-stored-cron-session-key"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_notification_route(
        name="Cron Failure Session Route",
        kind="webhook",
        target="https://example.invalid/cron-failure-session-route",
        events=["cron/failure"],
        conversation_target=None,
        enabled=True,
        secret_header_name=None,
        secret_token=None,
        vault_secret_id=None,
    )

    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(session_key: str, message: str) -> None:
        session_deliveries.append((session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Stored Session Key Failure Delivery",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionKey": "telegram:direct:123:thread:77",
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Deliver cron failure through the stored session key.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "last",
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Stored Session Key Failure Delivery",
        objective="Deliver cron failure through the stored session key.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_failure_stored_session_key",
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
    stored_session_key = "agent:openzues:telegram:direct:123:thread:77"
    await database.update_mission(
        mission_id,
        last_checkpoint="stored-session-key delivery failed",
        last_error="lane timed out",
        last_activity_at=datetime.now(UTC).isoformat(),
        session_key="agent:openzues:cron:task-blueprint:1:run:latest",
    )

    webhook_calls: list[tuple[str, str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, secret_token
        webhook_calls.append((str(route.get("target") or ""), event_type, event))

    monkeypatch.setattr(OpsMeshService, "_post_webhook", fake_post_webhook)

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert session_deliveries == [
        (
            stored_session_key,
            (
                '\u26a0\ufe0f Cron job "Stored Session Key Failure Delivery" failed: '
                "lane timed out"
            ),
        )
    ]
    assert webhook_calls == []
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    assert deliveries[0].route_kind == "session"
    assert deliveries[0].route_target == stored_session_key
    assert deliveries[0].event_type == "cron/failure"
    assert deliveries[0].delivery_state == "delivered"
    assert deliveries[0].session_key == stored_session_key
    assert deliveries[0].conversation_target is None
    assert deliveries[0].event_payload is not None
    assert deliveries[0].event_payload["sessionKey"] == stored_session_key


@pytest.mark.asyncio
async def test_ops_mesh_service_skips_cron_failure_destination_when_best_effort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )
    task = await service.create_task_blueprint(
        build_gateway_cron_task_blueprint(
            {
                "name": "Best Effort Failure Destination",
                "enabled": True,
                "schedule": {"kind": "every", "everyMs": 3_600_000},
                "sessionTarget": "isolated",
                "wakeMode": "next-heartbeat",
                "payload": {
                    "kind": "agentTurn",
                    "message": "Do not send failure destination when best effort is enabled.",
                },
                "delivery": {
                    "mode": "announce",
                    "channel": "telegram",
                    "to": "19098680",
                    "bestEffort": True,
                    "failureDestination": {
                        "mode": "webhook",
                        "to": "https://example.invalid/failure-destination",
                    },
                },
            }
        )
    )
    mission_id = await database.create_mission(
        name="Best Effort Failure Destination",
        objective="Do not send failure destination when best effort is enabled.",
        status="failed",
        instance_id=task.instance_id or 1,
        project_id=task.project_id,
        task_blueprint_id=task.id,
        thread_id="thread_cron_best_effort_failure_destination",
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
    await database.update_mission(
        mission_id,
        last_checkpoint="best-effort failed",
        last_error=None,
        last_activity_at=datetime.now(UTC).isoformat(),
    )

    webhook_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self, secret_header_name, secret_token
        webhook_calls.append((target, payload))

    monkeypatch.setattr(
        OpsMeshService,
        "_post_json_webhook",
        fake_post_json_webhook,
        raising=False,
    )

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    assert webhook_calls == []
    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert deliveries == []


@pytest.mark.asyncio
async def test_ops_mesh_service_launches_due_one_shot_task(tmp_path: Path) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="One Shot",
        summary="Run exactly once.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Run exactly once.",
            "schedule_kind": "at",
            "schedule_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
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
async def test_ops_mesh_service_routes_due_main_system_event_task_through_wake_queue(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="Wake Main Lane",
        summary="Nudge the main lane on the next heartbeat.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Resume the main lane from cron.",
            "cron_session_target": "main",
            "cron_wake_mode": "next-heartbeat",
            "cron_payload_kind": "systemEvent",
            "cron_payload_text": "Resume the main lane from cron.",
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
        last_status="completed",
        last_result_summary="Previous cron wake finished.",
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        wake_service=GatewayWakeService(database),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    wake_requests = await database.list_gateway_wake_requests()
    stored = await database.get_task_blueprint(1)

    assert fake_missions.created_payloads == []
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["text"] == "Resume the main lane from cron."
    assert wake_requests[0]["status"] == "pending"
    assert stored is not None
    assert stored["last_status"] == "completed"
    assert stored["last_result_summary"] == "Resume the main lane from cron."
    assert stored["cron_state"]["lastRunStatus"] == "ok"
    assert stored["cron_state"]["lastStatus"] == "ok"
    assert stored["cron_state"]["lastDurationMs"] == 0
    assert stored["cron_state"]["consecutiveErrors"] == 0
    assert stored["cron_state"]["lastDeliveryStatus"] == "not-requested"
    assert "lastFailureAlertAtMs" not in stored["cron_state"]


@pytest.mark.asyncio
async def test_ops_mesh_routes_due_main_system_event_session_key_through_wake_queue() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-cron-session-key-wake"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    stored_session_key = "agent:openzues:telegram:direct:123:thread:77"
    await database.create_task_blueprint(
        name="Wake Main Lane Session Key",
        summary="Nudge the main lane on the next heartbeat with a stored session key.",
        project_id=1,
        instance_id=1,
        cadence_minutes=60,
        enabled=True,
        payload={
            "objective_template": "Resume the main lane from cron.",
            "cron_session_target": "main",
            "cron_session_key": stored_session_key,
            "cron_wake_mode": "next-heartbeat",
            "cron_payload_kind": "systemEvent",
            "cron_payload_text": "Resume the main lane from cron.",
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
        last_status="completed",
        last_result_summary="Previous cron wake finished.",
    )

    fake_missions = FakeMissionService()
    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        fake_missions,  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        wake_service=GatewayWakeService(database),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    wake_requests = await database.list_gateway_wake_requests()
    events = await database.list_events()

    assert fake_missions.created_payloads == []
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["status"] == "pending"
    assert wake_requests[0]["session_key"] == stored_session_key
    assert len(events) == 1
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"]["sessionKey"] == stored_session_key


@pytest.mark.asyncio
async def test_ops_mesh_service_disables_consumed_one_shot_main_system_event_task_after_queueing(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="Wake Once",
        summary="Nudge the main lane once.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Wake the main lane once.",
            "schedule_kind": "at",
            "schedule_at": (datetime.now(UTC) - timedelta(minutes=1))
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "cron_session_target": "main",
            "cron_wake_mode": "next-heartbeat",
            "cron_payload_kind": "systemEvent",
            "cron_payload_text": "Wake the main lane once.",
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

    service = OpsMeshService(
        database,
        FakeManager(),  # type: ignore[arg-type]
        FakeMissionService(),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        wake_service=GatewayWakeService(database),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service.tick_once()

    wake_requests = await database.list_gateway_wake_requests()
    stored = await database.get_task_blueprint(1)

    assert len(wake_requests) == 1
    assert wake_requests[0]["text"] == "Wake the main lane once."
    assert stored is not None
    assert stored["enabled"] == 0
    assert stored["last_status"] == "completed"


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
async def test_ops_mesh_service_disables_consumed_one_shot_task_on_completion(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="One Shot",
        summary="Run exactly once.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Run exactly once.",
            "schedule_kind": "at",
            "schedule_at": "2026-04-18T12:00:00.000Z",
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
        last_launched_at="2026-04-18T12:05:00+00:00",
        last_status="active",
    )
    mission_id = await database.create_mission(
        name="One Shot",
        objective="Run exactly once.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=1,
        thread_id="thread_one_shot",
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
    )
    await database.update_mission(
        mission_id,
        last_checkpoint="Completed the one-shot reminder.",
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
    assert stored["last_result_summary"] == "Completed the one-shot reminder."


@pytest.mark.asyncio
async def test_ops_mesh_service_deletes_consumed_one_shot_task_when_delete_after_run_true(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="One Shot Delete",
        summary="Run exactly once.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Run exactly once.",
            "schedule_kind": "at",
            "schedule_at": "2026-04-18T12:00:00.000Z",
            "cron_delete_after_run": True,
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
        last_launched_at="2026-04-18T12:05:00+00:00",
        last_status="active",
    )
    mission_id = await database.create_mission(
        name="One Shot Delete",
        objective="Run exactly once.",
        status="completed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=1,
        thread_id="thread_one_shot_delete",
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
    )
    await database.update_mission(
        mission_id,
        last_checkpoint="Completed the one-shot reminder.",
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

    assert await database.get_task_blueprint(1) is None


@pytest.mark.asyncio
async def test_ops_mesh_service_schedules_transient_one_shot_retry_with_backoff(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    await database.create_project(path="C:/workspace", label="OpenZues Workspace")
    await database.create_task_blueprint(
        name="Retry Once",
        summary="Retry a transient one-shot failure.",
        project_id=1,
        instance_id=1,
        cadence_minutes=None,
        enabled=True,
        payload={
            "objective_template": "Retry a transient one-shot failure.",
            "schedule_kind": "at",
            "schedule_at": "2026-04-18T12:00:00.000Z",
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
    launched_at = datetime(2026, 4, 18, 12, 5, tzinfo=UTC)
    ended_at = launched_at + timedelta(seconds=10)
    await database.update_task_blueprint(
        1,
        last_launched_at=launched_at.isoformat(),
        last_status="active",
    )
    mission_id = await database.create_mission(
        name="Retry Once",
        objective="Retry a transient one-shot failure.",
        status="failed",
        instance_id=1,
        project_id=1,
        task_blueprint_id=1,
        thread_id="thread_one_shot_retry",
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
    )
    await database.update_mission(
        mission_id,
        last_error="request timed out",
        last_activity_at=ended_at.isoformat(),
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
        cron_retry={
            "maxAttempts": 2,
            "backoffMs": [60_000],
            "retryOn": ["timeout"],
        },
    )

    await service.handle_mission_event("mission/failed", {"missionId": mission_id})

    stored = await database.get_task_blueprint(1)
    assert stored is not None
    expected_retry_at_ms = int((ended_at + timedelta(milliseconds=60_000)).timestamp() * 1000)
    assert stored["enabled"] == 1
    assert stored["cron_state"]["consecutiveErrors"] == 1
    assert stored["cron_state"]["nextRunAtMs"] == expected_retry_at_ms

    await service.tick_once()

    assert len(fake_missions.created_payloads) == 1
    assert fake_missions.created_payloads[0].task_blueprint_id == 1


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
    assert (
        outbound_deliveries[0].event_payload["summary"]
        == "Mission resumed on the routed channel."
    )


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
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
    delivery_id = await database.create_outbound_delivery(
        route_id=route_id,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-replay",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission resumed on the routed channel.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission resumed on the routed channel.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary upstream timeout",
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert len(deliveries) == 1
    assert deliveries[0][0] == "mission/updated"
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_session_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-session-delivery"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = "agent:main:telegram:direct:123:thread:99"
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Session delivery for Replay Session Delivery",
        route_kind="session",
        route_target=session_key,
        event_type="cron/failure",
        session_key=session_key,
        conversation_target=None,
        route_scope={
            "route_name": "Session delivery for Replay Session Delivery",
            "route_kind": "session",
            "route_target": session_key,
            "route_match": "sessionKey",
        },
        event_payload={
            "missionId": 11,
            "taskId": 7,
            "jobId": "task-blueprint:7",
            "jobName": "Replay Session Delivery",
            "message": 'Cron job "Replay Session Delivery" failed: lane timed out',
            "status": "error",
            "error": "lane timed out",
            "sessionKey": session_key,
        },
        message_summary='Cron job "Replay Session Delivery" failed: lane timed out',
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(target_session_key: str, message: str) -> None:
        session_deliveries.append((target_session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert session_deliveries == [
        (
            session_key,
            '\u26a0\ufe0f Cron job "Replay Session Delivery" failed: lane timed out',
        )
    ]
    assert result.deliveries[0].route.kind == "session"
    assert result.deliveries[0].route.name == "Session delivery for Replay Session Delivery"
    assert result.deliveries[0].route.target == session_key
    assert result.deliveries[0].route.enabled is True
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_announce_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-announce-delivery"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Announce delivery for Replay Announce Delivery",
        route_kind="announce",
        route_target="telegram coordinator channel deploy-room",
        event_type="cron/failure",
        session_key=session_key,
        conversation_target={
            "channel": "telegram",
            "account_id": "coordinator",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
            "summary": "telegram account coordinator channel deploy-room",
        },
        route_scope={
            "route_name": "Announce delivery for Replay Announce Delivery",
            "route_kind": "announce",
            "route_target": "telegram coordinator channel deploy-room",
            "route_match": "explicitTarget",
        },
        event_payload={
            "missionId": 12,
            "taskId": 8,
            "jobId": "task-blueprint:8",
            "jobName": "Replay Announce Delivery",
            "message": 'Cron job "Replay Announce Delivery" failed: lane timed out',
            "status": "error",
            "error": "lane timed out",
            "sessionKey": session_key,
            "conversationTarget": {
                "channel": "telegram",
                "account_id": "coordinator",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "telegram account coordinator channel deploy-room",
            },
        },
        message_summary='Cron job "Replay Announce Delivery" failed: lane timed out',
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(target_session_key: str, message: str) -> None:
        session_deliveries.append((target_session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert session_deliveries == [
        (
            session_key,
            '\u26a0\ufe0f Cron job "Replay Announce Delivery" failed: lane timed out',
        )
    ]
    assert result.deliveries[0].route.kind == "announce"
    assert result.deliveries[0].route.name == "Announce delivery for Replay Announce Delivery"
    assert result.deliveries[0].route.target == "telegram coordinator channel deploy-room"
    assert result.deliveries[0].route.enabled is True
    assert result.deliveries[0].route.conversation_target is not None
    assert result.deliveries[0].route.conversation_target.channel == "telegram"
    assert result.deliveries[0].route.conversation_target.account_id == "coordinator"
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_announce_delivery_via_runtime_owner(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-announce-runtime-owner"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        "peer:channel:deploy-room"
    )
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Announce delivery for Runtime Owner Replay",
        route_kind="announce",
        route_target="telegram coordinator channel deploy-room",
        event_type="cron/failure",
        session_key=session_key,
        conversation_target={
            "channel": "telegram",
            "account_id": "coordinator",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
            "summary": "telegram account coordinator channel deploy-room",
        },
        route_scope={
            "route_name": "Announce delivery for Runtime Owner Replay",
            "route_kind": "announce",
            "route_target": "telegram coordinator channel deploy-room",
            "route_match": "explicitTarget",
        },
        event_payload={
            "missionId": 21,
            "taskId": 5,
            "jobId": "task-blueprint:5",
            "jobName": "Runtime Owner Replay",
            "message": 'Cron job "Runtime Owner Replay" failed: lane timed out',
            "status": "error",
            "error": "lane timed out",
            "sessionKey": session_key,
            "conversationTarget": {
                "channel": "telegram",
                "account_id": "coordinator",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "telegram account coordinator channel deploy-room",
            },
        },
        message_summary='Cron job "Runtime Owner Replay" failed: lane timed out',
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    runtime_calls: list[tuple[str, str]] = []

    async def fake_session_delivery(target_session_key: str, message: str) -> dict[str, str]:
        runtime_calls.append((target_session_key, message))
        return {"messageId": "runtime-replay-1"}

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            session_deliverer=fake_session_delivery
        ),
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.replayed_count == 1
    assert runtime_calls == [
        (
            session_key,
            '\u26a0\ufe0f Cron job "Runtime Owner Replay" failed: lane timed out',
        )
    ]
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["delivery_message_id"] == "runtime-replay-1"


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_gateway_poll_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-gateway-poll-delivery"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = (
        "launch:mode:workspace_affinity:channel:slack:account:workspace-bot:"
        "peer:channel:deploy-room:thread:1710000000.9999"
    )
    conversation_target = {
        "channel": "slack",
        "account_id": "workspace-bot",
        "peer_kind": "channel",
        "peer_id": "deploy-room",
        "summary": "slack account workspace-bot channel deploy-room",
    }
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Gateway poll to Replay Poll Delivery",
        route_kind="announce",
        route_target="slack account workspace-bot channel deploy-room",
        event_type="gateway/poll",
        session_key=session_key,
        conversation_target=conversation_target,
        route_scope={
            "route_name": "Gateway poll to Replay Poll Delivery",
            "route_kind": "announce",
            "route_target": "slack account workspace-bot channel deploy-room",
            "route_match": "explicitTarget",
            "source": "gateway.poll",
            "idempotency_key": "idem-replay-poll",
        },
        event_payload={
            "summary": "Ship parity?",
            "question": "Ship parity?",
            "options": ["Yes", "No"],
            "channel": "slack",
            "to": "channel:C123",
            "accountId": "workspace-bot",
            "maxSelections": 1,
            "durationHours": 24,
            "silent": True,
            "isAnonymous": False,
            "sessionKey": session_key,
            "conversationTarget": conversation_target,
        },
        message_summary="Ship parity?",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    session_deliveries: list[tuple[str, str]] = []

    async def fake_session_delivery(target_session_key: str, message: str) -> None:
        session_deliveries.append((target_session_key, message))

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        session_delivery_service=fake_session_delivery,
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert session_deliveries == [
        (
            session_key,
            (
                "Poll: Ship parity?\n"
                "1. Yes\n"
                "2. No\n\n"
                "Settings: maxSelections=1, durationHours=24, silent=true, "
                "isAnonymous=false"
            ),
        )
    ]
    assert result.deliveries[0].route.kind == "announce"
    assert result.deliveries[0].route.name == "Gateway poll to Replay Poll Delivery"
    assert result.deliveries[0].route.target == "slack account workspace-bot channel deploy-room"
    assert result.deliveries[0].route.enabled is True
    assert result.deliveries[0].route.conversation_target is not None
    assert result.deliveries[0].route.conversation_target.channel == "slack"
    assert result.deliveries[0].route.conversation_target.account_id == "workspace-bot"
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_gateway_send_via_provider_runtime(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-gateway-send-provider"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = (
        "launch:mode:workspace_affinity:channel:telegram:account:alerts:"
        "peer:chat:ops:thread:topic-42"
    )
    conversation_target = {
        "channel": "telegram",
        "account_id": "alerts",
        "peer_kind": "channel",
        "peer_id": "chat:ops",
        "summary": "telegram account alerts channel ops",
    }
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Gateway send to Replay Provider",
        route_kind="announce",
        route_target="telegram account alerts channel ops",
        event_type="gateway/send",
        session_key=session_key,
        conversation_target=conversation_target,
        route_scope={
            "route_name": "Gateway send to Replay Provider",
            "route_kind": "announce",
            "route_target": "telegram account alerts channel ops",
            "route_match": "explicitTarget",
            "source": "gateway.send",
            "idempotency_key": "idem-replay-send-provider",
            "thread_id": "topic-42",
        },
        event_payload={
            "message": "Replay provider send.",
            "channel": "telegram",
            "to": "chat:ops",
            "accountId": "alerts",
            "threadId": "topic-42",
            "replyToId": "message-99",
            "silent": True,
            "forceDocument": True,
            "mediaUrl": "https://example.com/replay.pdf",
            "mediaUrls": ["https://example.com/replay.pdf"],
            "gifPlayback": False,
            "agentId": "release-bot",
            "sessionKey": session_key,
            "conversationTarget": conversation_target,
        },
        message_summary="Replay provider send.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    provider_requests: list[GatewayOutboundRuntimeMessageRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimeMessageRequest,
    ) -> dict[str, object]:
        provider_requests.append(request)
        return {
            "runtime": "provider-backed",
            "messageId": "provider-replay-send-1",
            "conversationId": "topic-42",
            "roomId": "room-telegram",
        }

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            provider_message_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.replayed_count == 1
    assert provider_requests == [
        GatewayOutboundRuntimeMessageRequest(
            channel="telegram",
            target="chat:ops",
            message=(
                "Replay provider send.\n\n"
                "Media:\n"
                "1. https://example.com/replay.pdf\n\n"
                "Settings: gifPlayback=false"
            ),
            media_urls=("https://example.com/replay.pdf",),
            gif_playback=False,
            reply_to_id="message-99",
            silent=True,
            force_document=True,
            account_id="alerts",
            thread_id="topic-42",
            session_key=session_key,
            agent_id="release-bot",
        )
    ]
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["delivery_message_id"] == "provider-replay-send-1"
    assert refreshed_delivery["route_scope"]["transport_runtime"] == "provider-backed"
    assert refreshed_delivery["route_scope"]["provider_result"] == {
        "runtime": "provider-backed",
        "messageId": "provider-replay-send-1",
        "conversationId": "topic-42",
        "roomId": "room-telegram",
    }


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_gateway_poll_via_provider_runtime(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-gateway-poll-provider"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    session_key = (
        "launch:mode:workspace_affinity:channel:slack:account:workspace-bot:"
        "peer:channel:C123:thread:1710000000.9999"
    )
    conversation_target = {
        "channel": "slack",
        "account_id": "workspace-bot",
        "peer_kind": "channel",
        "peer_id": "channel:C123",
        "summary": "slack account workspace-bot channel C123",
    }
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Gateway poll to Replay Provider",
        route_kind="announce",
        route_target="slack account workspace-bot channel C123",
        event_type="gateway/poll",
        session_key=session_key,
        conversation_target=conversation_target,
        route_scope={
            "route_name": "Gateway poll to Replay Provider",
            "route_kind": "announce",
            "route_target": "slack account workspace-bot channel C123",
            "route_match": "explicitTarget",
            "source": "gateway.poll",
            "idempotency_key": "idem-replay-poll-provider",
            "thread_id": "1710000000.9999",
        },
        event_payload={
            "summary": "Replay provider poll?",
            "question": "Replay provider poll?",
            "options": ["Yes", "No"],
            "channel": "slack",
            "to": "channel:C123",
            "accountId": "workspace-bot",
            "maxSelections": 1,
            "durationSeconds": 3600,
            "silent": True,
            "isAnonymous": False,
            "threadId": "1710000000.9999",
            "sessionKey": session_key,
            "conversationTarget": conversation_target,
        },
        message_summary="Replay provider poll?",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary delivery timeout",
    )
    provider_requests: list[GatewayOutboundRuntimePollRequest] = []

    async def fake_provider_delivery(
        request: GatewayOutboundRuntimePollRequest,
    ) -> dict[str, object]:
        provider_requests.append(request)
        return {
            "runtime": "provider-backed",
            "messageId": "provider-replay-poll-1",
            "pollId": "poll-provider-1",
            "conversationId": "C123",
            "timestamp": 1713980000,
        }

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
        outbound_runtime_service=GatewayOutboundRuntimeService(
            provider_poll_deliverer=fake_provider_delivery,
        ),
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.replayed_count == 1
    assert provider_requests == [
        GatewayOutboundRuntimePollRequest(
            channel="slack",
            target="channel:C123",
            question="Replay provider poll?",
            options=("Yes", "No"),
            max_selections=1,
            duration_seconds=3600,
            silent=True,
            is_anonymous=False,
            account_id="workspace-bot",
            thread_id="1710000000.9999",
            session_key=session_key,
        )
    ]
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["delivery_message_id"] == "provider-replay-poll-1"
    assert refreshed_delivery["route_scope"]["transport_runtime"] == "provider-backed"
    assert refreshed_delivery["route_scope"]["provider_result"] == {
        "runtime": "provider-backed",
        "messageId": "provider-replay-poll-1",
        "conversationId": "C123",
        "timestamp": 1713980000,
        "pollId": "poll-provider-1",
    }


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retries_saved_failed_ad_hoc_webhook_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-ad-hoc-webhook-delivery"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Cron webhook for Replay Webhook Delivery",
        route_kind="webhook",
        route_target="https://example.invalid/replay-webhook",
        event_type="cron/finished",
        session_key="launch:mode:workspace_affinity",
        conversation_target=None,
        route_scope={
            "route_name": "Cron webhook for Replay Webhook Delivery",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/replay-webhook",
        },
        event_payload={
            "missionId": 13,
            "taskId": 9,
            "jobId": "task-blueprint:9",
            "summary": "Replay webhook ship landed.",
        },
        message_summary="Replay webhook ship landed.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary upstream timeout",
    )
    webhook_calls: list[tuple[str, dict[str, object]]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self, secret_header_name, secret_token
        webhook_calls.append((target, payload))

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        make_vault(database, tmp_path),
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert webhook_calls == [
        (
            "https://example.invalid/replay-webhook",
            {
                "missionId": 13,
                "taskId": 9,
                "jobId": "task-blueprint:9",
                "summary": "Replay webhook ship landed.",
            },
        )
    ]
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_ops_mesh_service_persists_secret_backed_replay_auth_for_ad_hoc_webhook_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-ad-hoc-webhook-replay-auth"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    webhook_calls: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self
        webhook_calls.append((target, payload, secret_header_name, secret_token))

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)

    vault = make_vault(database, tmp_path)
    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        vault,
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    await service._send_ad_hoc_webhook_delivery(
        route_name="Cron webhook for Authenticated Replay",
        route_target="https://example.invalid/authenticated-replay",
        event_type="cron/finished",
        payload={
            "missionId": 14,
            "taskId": 10,
            "jobId": "task-blueprint:10",
            "summary": "Authenticated replay webhook landed.",
        },
        session_key="launch:mode:workspace_affinity",
        conversation_target=None,
        secret_header_name="Authorization",
        secret_token="Bearer replayable-webhook-token",
    )

    deliveries = await service.list_outbound_delivery_views(limit=10)
    assert len(deliveries) == 1
    stored_delivery = await database.get_outbound_delivery(deliveries[0].id)

    assert webhook_calls == [
        (
            "https://example.invalid/authenticated-replay",
            {
                "missionId": 14,
                "taskId": 10,
                "jobId": "task-blueprint:10",
                "summary": "Authenticated replay webhook landed.",
            },
            "Authorization",
            "Bearer replayable-webhook-token",
        )
    ]
    assert stored_delivery is not None
    assert stored_delivery["delivery_state"] == "delivered"
    assert stored_delivery["route_scope"]["secret_header_name"] == "Authorization"
    secret_id = int(stored_delivery["route_scope"]["vault_secret_id"])
    secret_view = await vault.get_secret_view(secret_id)
    assert secret_view is not None
    assert secret_view.usage_count == 1
    assert await vault.get_secret_value(secret_id) == "Bearer replayable-webhook-token"


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_retry_secret_backed_ad_hoc_webhook_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "ops-mesh-replay-secret-ad-hoc-webhook"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    vault = make_vault(database, tmp_path)
    replay_secret = await vault.create_secret_value(
        label="Cron webhook for Replay Secret Webhook Delivery replay webhook secret",
        value="Bearer replay-auth-token",
        kind="webhook-token",
        notes="https://example.invalid/replay-auth-webhook",
    )
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Cron webhook for Replay Secret Webhook Delivery",
        route_kind="webhook",
        route_target="https://example.invalid/replay-auth-webhook",
        event_type="cron/finished",
        session_key="launch:mode:workspace_affinity",
        conversation_target=None,
        route_scope={
            "route_name": "Cron webhook for Replay Secret Webhook Delivery",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/replay-auth-webhook",
            "secret_header_name": "Authorization",
            "vault_secret_id": replay_secret.id,
        },
        event_payload={
            "missionId": 15,
            "taskId": 11,
            "jobId": "task-blueprint:11",
            "summary": "Replay secret-backed webhook landed.",
        },
        message_summary="Replay secret-backed webhook landed.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary upstream timeout",
    )
    webhook_calls: list[tuple[str, dict[str, object], str | None, str | None]] = []

    def fake_post_json_webhook(
        self,  # noqa: ANN001
        target: str,
        payload: dict[str, object],
        *,
        secret_header_name: str | None = None,
        secret_token: str | None = None,
    ) -> None:
        del self
        webhook_calls.append((target, payload, secret_header_name, secret_token))

    monkeypatch.setattr(OpsMeshService, "_post_json_webhook", fake_post_json_webhook)

    service = OpsMeshService(
        database,
        FakeManager(),
        FakeMissionService([]),  # type: ignore[arg-type]
        BroadcastHub(),
        vault,
        poll_interval_seconds=999,
        snapshot_interval_seconds=999999,
    )

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 1
    assert result.replayed_count == 1
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert webhook_calls == [
        (
            "https://example.invalid/replay-auth-webhook",
            {
                "missionId": 15,
                "taskId": 11,
                "jobId": "task-blueprint:11",
                "summary": "Replay secret-backed webhook landed.",
            },
            "Authorization",
            "Bearer replay-auth-token",
        )
    ]
    assert result.deliveries[0].route.kind == "webhook"
    assert result.deliveries[0].route.target == "https://example.invalid/replay-auth-webhook"
    assert result.deliveries[0].route.enabled is True
    assert result.deliveries[0].route.has_secret is True
    assert result.deliveries[0].route.secret_header_name == "Authorization"
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "delivered"
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "delivered"
    assert refreshed_delivery["attempt_count"] == 2
    assert refreshed_delivery["last_error"] is None


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_fails_when_route_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
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
    delivery_id = await database.create_outbound_delivery(
        route_id=route_id,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-disabled",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission resumed on the routed channel.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission resumed on the routed channel.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        last_error="temporary upstream timeout",
    )
    await database.update_notification_route(route_id, enabled=False)
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is False
    assert result.attempted_count == 1
    assert result.replayed_count == 0
    assert result.failed_count == 1
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert deliveries == []
    assert result.deliveries[0].error is not None
    assert "unavailable for replay" in result.deliveries[0].error
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.max_retries_reached is True
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert "unavailable for replay" in str(refreshed_delivery["last_error"])
    assert int(refreshed_delivery["attempt_count"]) > 1


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_fails_when_saved_route_row_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
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
    delivery_id = await database.create_outbound_delivery(
        route_id=route_id,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-missing-row",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission replay lost its saved route row.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission replay lost its saved route row.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
        last_error="temporary upstream timeout",
    )
    await database.delete_notification_route(route_id)
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)
    expected_error = f"Notification route {route_id} is unavailable for replay."

    assert result.ok is False
    assert result.attempted_count == 1
    assert result.replayed_count == 0
    assert result.failed_count == 1
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert deliveries == []
    assert result.deliveries[0].route_id == route_id
    assert result.deliveries[0].error == expected_error
    assert result.deliveries[0].route is not None
    assert result.deliveries[0].route.id == route_id
    assert result.deliveries[0].route.name == "Deploy Room"
    assert result.deliveries[0].route.enabled is False
    assert result.deliveries[0].delivery is not None
    assert result.deliveries[0].delivery.delivery_state == "failed"
    assert result.deliveries[0].delivery.max_retries_reached is True
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == expected_error


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_defers_saved_failed_delivery_in_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
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
    delivery_id = await database.create_outbound_delivery(
        route_id=route_id,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-deferred",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission resumed on the routed channel.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission resumed on the routed channel.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        last_error="temporary upstream timeout",
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 0
    assert result.replayed_count == 0
    assert result.failed_count == 0
    assert result.deferred_count == 1
    assert result.skipped_max_retries_count == 0
    assert result.deliveries == []
    assert deliveries == []
    assert "1 deferred by backoff" in result.summary
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == 1
    assert refreshed_delivery["last_error"] == "temporary upstream timeout"


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_skips_saved_failed_delivery_at_max_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    route_id = await database.create_notification_route(
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
    delivery_id = await database.create_outbound_delivery(
        route_id=route_id,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-maxed",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission remained failed after exhausting retries.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission remained failed after exhausting retries.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=OUTBOUND_DELIVERY_MAX_RETRIES,
        last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
        last_error="delivery retries exhausted",
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is True
    assert result.attempted_count == 0
    assert result.replayed_count == 0
    assert result.failed_count == 0
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 1
    assert result.deliveries == []
    assert deliveries == []
    assert "1 hit max retries" in result.summary
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "delivery retries exhausted"


@pytest.mark.asyncio
async def test_replay_outbound_deliveries_fails_when_saved_delivery_is_missing_route_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "ops.db")
    await database.initialize()
    delivery_id = await database.create_outbound_delivery(
        route_id=None,
        route_name="Deploy Room",
        route_kind="webhook",
        route_target="https://example.invalid/deploy",
        event_type="mission/updated",
        session_key="route-session-missing-id",
        conversation_target={
            "channel": "slack",
            "account_id": "workspace-bot",
            "peer_kind": "channel",
            "peer_id": "deploy-room",
        },
        route_scope={
            "route_name": "Deploy Room",
            "route_kind": "webhook",
            "route_target": "https://example.invalid/deploy",
            "route_match": "peer",
            "matched_value": "deploy-room",
        },
        event_payload={
            "summary": "Mission replay lost its saved route id.",
            "routeConversationTarget": {
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
        },
        message_summary="Mission replay lost its saved route id.",
        test_delivery=False,
        delivery_state="failed",
        attempt_count=1,
        last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
        last_error="temporary upstream timeout",
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

    result = await service.replay_outbound_deliveries(limit=10)
    refreshed_delivery = await database.get_outbound_delivery(delivery_id)

    assert result.ok is False
    assert result.attempted_count == 1
    assert result.replayed_count == 0
    assert result.failed_count == 1
    assert result.deferred_count == 0
    assert result.skipped_max_retries_count == 0
    assert deliveries == []
    assert result.deliveries[0].error == "Saved delivery is missing its notification route."
    assert result.deliveries[0].delivery is not None
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "Saved delivery is missing its notification route."


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
    assert (
        payload["delivery"]["event_payload"]["routeConversationTarget"]["peer_id"]
        == "deploy-room"
    )
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
