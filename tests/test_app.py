from __future__ import annotations

import asyncio
import json
import shutil
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openzues.app import (
    build_brief,
    build_continuity,
    build_cortex,
    build_economy,
    build_interference,
    build_launchpad,
    build_radar,
    build_reflex_deck,
    create_app,
)
from openzues.schemas import (
    DashboardView,
    DiagnosticCheck,
    DiagnosticsView,
    GatewayCapabilityView,
    InstanceView,
    MissionLiveTelemetryView,
    MissionSwarmConflictView,
    MissionSwarmRuntimeView,
    MissionView,
    OperatorView,
    ProjectView,
    RemoteRequestView,
    TaskBlueprintView,
    TeamView,
)
from openzues.services.control_chat import plan_attention_queue, plan_control_chat
from openzues.services.control_plane import ControlPlaneLease
from openzues.services.dreams import build_dream_deck
from openzues.services.ecc_catalog import configure_ecc_catalog
from openzues.services.gateway_bootstrap import GatewayBootstrapBootResult, GatewayBootstrapService
from openzues.services.gateway_method_policy import (
    list_known_gateway_events,
    list_known_gateway_methods,
)
from openzues.services.hermes_skills import configure_hermes_skill_catalog
from openzues.services.launch_routing import LaunchRoutingService
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import (
    build_mempalace_control_plane_proof_signal,
    build_mempalace_roundtrip_signal,
    build_mempalace_writeback_signal,
)
from openzues.settings import Settings


@pytest.fixture(autouse=True)
def _reset_external_catalogs() -> None:
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)
    yield
    configure_hermes_skill_catalog(None)
    configure_ecc_catalog(None)


class FakeControlPlaneLease(ControlPlaneLease):
    def __init__(self, *, owner: bool, owner_pid: int | None = None) -> None:
        super().__init__(Path("control-plane.lock"))
        self._owner = owner
        self._simulated_owner_pid = owner_pid

    def acquire(self, *, metadata: dict[str, object] | None = None) -> bool:
        self.metadata = dict(metadata or {})
        self.acquired = self._owner
        self.owner_pid = self._simulated_owner_pid if not self._owner else 1001
        return self.acquired

    def release(self) -> None:
        self.acquired = False


def make_client(
    tmp_path,
    *,
    client_host: str = "testclient",
    attention_queue_enabled: bool = True,
    control_plane_lease: ControlPlaneLease | None = None,
    hermes_source_path: Path | None = None,
    ecc_source_path: Path | None = None,
    reset_data_dir: bool = False,
):
    data_dir = tmp_path / "data"
    if reset_data_dir and data_dir.exists():
        shutil.rmtree(data_dir)
    app_settings = Settings(
        data_dir=data_dir,
        db_path=data_dir / "openzues-test.db",
        attention_queue_enabled=attention_queue_enabled,
        hermes_source_path=hermes_source_path,
        ecc_source_path=ecc_source_path,
    )
    app = create_app(app_settings, control_plane_lease=control_plane_lease)
    return TestClient(app, client=(client_host, 50000))


def write_fake_hermes_skill(
    repo_root: Path,
    *,
    relative_dir: str,
    name: str,
    description: str,
    category: str,
    tags: list[str],
) -> Path:
    skill_dir = repo_root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "metadata:",
                "  hermes:",
                f"    category: {category}",
                f"    tags: [{', '.join(tags)}]",
                "---",
                "",
                f"# {name}",
                "",
                "## When to Use",
                "Load this skill when the task needs the documented workflow.",
                "",
                "## Procedure",
                "1. Open the skill.",
                "2. Follow its steps.",
            ]
        ),
        encoding="utf-8",
    )
    return skill_path


def write_fake_hermes_file(repo_root: Path, relative_path: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# stub\n", encoding="utf-8")
    return path


def write_fake_ecc_skill(
    repo_root: Path,
    *,
    relative_dir: str,
    name: str,
    description: str,
) -> Path:
    skill_dir = repo_root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "origin: ECC",
                "---",
                "",
                f"# {name}",
                "",
                "## When to Use",
                "Load this ECC skill when the task needs the documented workflow.",
                "",
                "## Procedure",
                "1. Open the skill.",
                "2. Follow the workflow.",
            ]
        ),
        encoding="utf-8",
    )
    return skill_path


def write_fake_ecc_install_manifests(repo_root: Path) -> None:
    manifests_root = repo_root / "manifests"
    manifests_root.mkdir(parents=True, exist_ok=True)
    (manifests_root / "install-profiles.json").write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "core": {
                        "description": "Minimal Codex-facing ECC baseline.",
                        "modules": [
                            "rules-core",
                            "agents-core",
                            "commands-core",
                            "hooks-runtime",
                            "platform-configs",
                            "workflow-quality",
                        ],
                    },
                    "developer": {
                        "description": "Default engineering profile for Codex project installs.",
                        "modules": [
                            "rules-core",
                            "agents-core",
                            "commands-core",
                            "hooks-runtime",
                            "platform-configs",
                            "workflow-quality",
                            "framework-language",
                            "database",
                            "orchestration",
                        ],
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (manifests_root / "install-components.json").write_text(
        json.dumps(
            {
                "version": 1,
                "components": [
                    {
                        "id": "baseline:agents",
                        "family": "baseline",
                        "description": "Agent definitions and shared AGENTS guidance.",
                        "modules": ["agents-core"],
                    },
                    {
                        "id": "baseline:commands",
                        "family": "baseline",
                        "description": "Core command library.",
                        "modules": ["commands-core"],
                    },
                    {
                        "id": "baseline:hooks",
                        "family": "baseline",
                        "description": "Hook runtime helpers.",
                        "modules": ["hooks-runtime"],
                    },
                    {
                        "id": "baseline:platform",
                        "family": "baseline",
                        "description": "Platform configs and Codex baseline files.",
                        "modules": ["platform-configs"],
                    },
                    {
                        "id": "baseline:workflow",
                        "family": "baseline",
                        "description": "Quality and learning workflow skills.",
                        "modules": ["workflow-quality"],
                    },
                    {
                        "id": "lang:python",
                        "family": "language",
                        "description": "Python application engineering guidance.",
                        "modules": ["framework-language"],
                    },
                    {
                        "id": "capability:database",
                        "family": "capability",
                        "description": "Database-oriented skills.",
                        "modules": ["database"],
                    },
                    {
                        "id": "capability:orchestration",
                        "family": "capability",
                        "description": "Worktree and terminal orchestration guidance.",
                        "modules": ["orchestration"],
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (manifests_root / "install-modules.json").write_text(
        json.dumps(
            {
                "version": 1,
                "modules": [
                    {
                        "id": "rules-core",
                        "kind": "rules",
                        "description": "Shared rules for non-Codex targets.",
                        "paths": ["rules"],
                        "targets": ["claude", "cursor"],
                        "dependencies": [],
                        "defaultInstall": True,
                        "cost": "light",
                        "stability": "stable",
                    },
                    {
                        "id": "agents-core",
                        "kind": "agents",
                        "description": "Agent definitions and AGENTS guidance.",
                        "paths": [".agents", "agents", "AGENTS.md"],
                        "targets": ["codex", "claude"],
                        "dependencies": [],
                        "defaultInstall": True,
                        "cost": "light",
                        "stability": "stable",
                    },
                    {
                        "id": "commands-core",
                        "kind": "commands",
                        "description": "Command shims for non-Codex targets.",
                        "paths": ["commands"],
                        "targets": ["claude", "cursor"],
                        "dependencies": [],
                        "defaultInstall": True,
                        "cost": "medium",
                        "stability": "stable",
                    },
                    {
                        "id": "hooks-runtime",
                        "kind": "hooks",
                        "description": "Hook runtime helpers for non-Codex targets.",
                        "paths": ["hooks", "scripts/hooks", "scripts/lib"],
                        "targets": ["claude"],
                        "dependencies": [],
                        "defaultInstall": True,
                        "cost": "medium",
                        "stability": "stable",
                    },
                    {
                        "id": "platform-configs",
                        "kind": "platform",
                        "description": "Codex platform configs and MCP catalog defaults.",
                        "paths": [".codex", "mcp-configs"],
                        "targets": ["codex", "claude"],
                        "dependencies": [],
                        "defaultInstall": True,
                        "cost": "light",
                        "stability": "stable",
                    },
                    {
                        "id": "workflow-quality",
                        "kind": "skills",
                        "description": "Workflow-quality and learning skills.",
                        "paths": ["skills/continuous-learning"],
                        "targets": ["codex", "claude"],
                        "dependencies": ["platform-configs"],
                        "defaultInstall": True,
                        "cost": "medium",
                        "stability": "stable",
                    },
                    {
                        "id": "framework-language",
                        "kind": "skills",
                        "description": "Language and framework guidance.",
                        "paths": ["skills/python-patterns"],
                        "targets": ["codex", "claude"],
                        "dependencies": [
                            "rules-core",
                            "agents-core",
                            "commands-core",
                            "platform-configs",
                        ],
                        "defaultInstall": False,
                        "cost": "medium",
                        "stability": "stable",
                    },
                    {
                        "id": "database",
                        "kind": "skills",
                        "description": "Database skills.",
                        "paths": ["skills/postgres-patterns"],
                        "targets": ["codex", "claude"],
                        "dependencies": ["platform-configs"],
                        "defaultInstall": False,
                        "cost": "medium",
                        "stability": "stable",
                    },
                    {
                        "id": "orchestration",
                        "kind": "skills",
                        "description": "Orchestration skills.",
                        "paths": ["skills/tmux-orchestrator"],
                        "targets": ["codex", "claude"],
                        "dependencies": ["platform-configs"],
                        "defaultInstall": False,
                        "cost": "medium",
                        "stability": "stable",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_fake_ecc_source_repo(repo_root: Path) -> Path:
    write_fake_ecc_skill(
        repo_root,
        relative_dir="skills/workspace-surface-audit",
        name="workspace-surface-audit",
        description="Audit the project harness surface, installed skills, and Codex-facing config.",
    )
    write_fake_ecc_skill(
        repo_root,
        relative_dir="skills/continuous-learning",
        name="continuous-learning",
        description="Capture project learnings and feed them back into the workflow.",
    )
    write_fake_ecc_skill(
        repo_root,
        relative_dir="skills/python-patterns",
        name="python-patterns",
        description="Python engineering guidance for application codebases.",
    )
    write_fake_ecc_skill(
        repo_root,
        relative_dir="skills/postgres-patterns",
        name="postgres-patterns",
        description="Database design and query guidance for Postgres-backed projects.",
    )
    write_fake_ecc_skill(
        repo_root,
        relative_dir="skills/tmux-orchestrator",
        name="tmux-orchestrator",
        description="Coordinate parallel terminal workflows for project execution.",
    )
    commands_dir = repo_root / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    agents_dir = repo_root / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "planner.md").write_text("# Planner\n", encoding="utf-8")
    project_agents_dir = repo_root / ".agents" / "coordination"
    project_agents_dir.mkdir(parents=True, exist_ok=True)
    (project_agents_dir / "README.md").write_text("# Coordination\n", encoding="utf-8")
    rules_dir = repo_root / "rules" / "common"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "testing.md").write_text("# Testing\n", encoding="utf-8")
    codex_agents_dir = repo_root / ".codex" / "agents"
    codex_agents_dir.mkdir(parents=True, exist_ok=True)
    mcp_configs_dir = repo_root / "mcp-configs"
    mcp_configs_dir.mkdir(parents=True, exist_ok=True)
    (mcp_configs_dir / "defaults.json").write_text(
        '{"mcpServers":{"github":{"command":"npx"},"context7":{"command":"npx"}}}\n',
        encoding="utf-8",
    )
    (repo_root / "AGENTS.md").write_text(
        "# Everything Claude Code (ECC) — Agent Instructions\n",
        encoding="utf-8",
    )
    (repo_root / ".codex" / "AGENTS.md").write_text(
        "# ECC for Codex CLI\n",
        encoding="utf-8",
    )
    (repo_root / ".codex" / "config.toml").write_text(
        '[mcp_servers.context7]\ncommand = "npx"\n\n[agents.explorer]\nmodel = "gpt-5.4"\n',
        encoding="utf-8",
    )
    (codex_agents_dir / "explorer.toml").write_text('model = "gpt-5.4"\n', encoding="utf-8")
    (repo_root / ".mcp.json").write_text(
        '{"mcpServers":{"github":{"command":"npx"},"context7":{"command":"npx"}}}',
        encoding="utf-8",
    )
    (repo_root / "package.json").write_text('{"name":"ecc-universal"}', encoding="utf-8")
    write_fake_ecc_install_manifests(repo_root)
    return repo_root


def write_fake_ecc_workspace(workspace_root: Path) -> Path:
    codex_agents_dir = workspace_root / ".codex" / "agents"
    codex_agents_dir.mkdir(parents=True, exist_ok=True)
    (workspace_root / ".codex" / "AGENTS.md").write_text(
        "# ECC for Codex CLI\n",
        encoding="utf-8",
    )
    (workspace_root / ".codex" / "config.toml").write_text(
        '[mcp_servers.github]\ncommand = "npx"\n\n[mcp_servers.context7]\ncommand = "npx"\n',
        encoding="utf-8",
    )
    (workspace_root / ".mcp.json").write_text(
        '{"mcpServers":{"github":{"command":"npx"}}}',
        encoding="utf-8",
    )
    (codex_agents_dir / "explorer.toml").write_text('model = "gpt-5.4"\n', encoding="utf-8")
    return workspace_root


def make_instance_view(
    *,
    instance_id: int = 1,
    name: str = "Local Codex Desktop",
    connected: bool = True,
    apps: list[dict[str, object]] | None = None,
    plugins: list[dict[str, object]] | None = None,
    mcp_servers: list[dict[str, object]] | None = None,
    unresolved_requests: list[dict[str, object]] | None = None,
) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name=name,
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=connected,
        apps=apps or [],
        plugins=plugins or [],
        mcp_servers=mcp_servers or [],
        unresolved_requests=unresolved_requests or [],
    )


class FakeMissionRuntimeClient:
    def __init__(self) -> None:
        self.thread_id = "thread-memory-proof-direct"
        self.turn_id = "turn-memory-proof-direct"
        self.turn_prompts: list[str] = []

    async def call(self, method: str, params: dict[str, object]) -> dict[str, object]:
        if method == "mcpServerStatus/list":
            return {
                "data": [
                    {
                        "name": "MemPalace MCP Server",
                        "source": "mempalace",
                        "status": "ready",
                        "authStatus": "ready",
                        "tools": [
                            "mempalace_status",
                            "mempalace_search",
                            "mempalace_diary_write",
                            "mempalace_diary_read",
                        ],
                    }
                ]
            }
        if method == "thread/list":
            return {
                "data": [
                    {
                        "id": self.thread_id,
                        "status": {"type": "idle"},
                    }
                ]
            }
        if method in {
            "account/read",
            "model/list",
            "collaborationMode/list",
            "skills/list",
            "app/list",
            "plugin/list",
            "thread/loaded/list",
        }:
            return {"data": []}
        if method == "config/read":
            return {"config": {}}
        return {}

    async def start_thread(
        self,
        *,
        model: str,
        cwd: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, object]:
        return {
            "thread": {
                "id": self.thread_id,
                "status": {"type": "idle"},
            }
        }

    async def start_turn(
        self,
        *,
        thread_id: str,
        text: str,
        cwd: str | None,
        model: str | None,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
    ) -> dict[str, object]:
        self.turn_prompts.append(text)
        return {
            "turn": {
                "id": self.turn_id,
            }
        }

    async def close(self) -> None:
        return None


def make_project_view(*, project_id: int = 1, label: str = "Sandbox") -> ProjectView:
    now = datetime.now(UTC)
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
        last_scan_at=now.isoformat(),
    )


def make_mission_view(
    *,
    mission_id: int,
    name: str,
    objective: str = "Keep shipping.",
    status: str = "active",
    phase: str | None = "ready",
    instance_id: int = 1,
    in_progress: bool = False,
    total_tokens: int = 0,
    command_count: int = 0,
    project_id: int | None = None,
    project_label: str | None = None,
    last_checkpoint: str | None = None,
    last_error: str | None = None,
    current_command: str | None = None,
    last_commentary: str | None = None,
    last_activity_at: str | None = None,
    suggested_action: str | None = "Inspect the mission and keep it moving.",
    model: str = "gpt-5.4",
    max_turns: int | None = None,
    use_builtin_agents: bool = True,
    run_verification: bool = True,
    auto_commit: bool = True,
    pause_on_approval: bool = True,
    allow_auto_reflexes: bool = True,
    auto_recover: bool = True,
    auto_recover_limit: int = 2,
    reflex_cooldown_seconds: int = 900,
    turns_completed: int = 0,
    failure_count: int = 0,
    last_reflex_kind: str | None = None,
    last_reflex_at: str | None = None,
    cwd: str = "C:/workspace",
    thread_id: str | None = None,
    swarm: MissionSwarmRuntimeView | None = None,
    toolsets: list[str] | None = None,
    updated_at: datetime | None = None,
) -> MissionView:
    now = datetime.now(UTC)
    return MissionView(
        id=mission_id,
        name=name,
        objective=objective,
        status=status,  # type: ignore[arg-type]
        instance_id=instance_id,
        instance_name="Local Codex Desktop",
        project_id=project_id,
        project_label=project_label,
        thread_id=thread_id or f"thread_{mission_id}",
        cwd=cwd,
        model=model,
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=max_turns,
        use_builtin_agents=use_builtin_agents,
        run_verification=run_verification,
        auto_commit=auto_commit,
        pause_on_approval=pause_on_approval,
        allow_auto_reflexes=allow_auto_reflexes,
        auto_recover=auto_recover,
        auto_recover_limit=auto_recover_limit,
        reflex_cooldown_seconds=reflex_cooldown_seconds,
        swarm_enabled=swarm is not None,
        swarm=swarm,
        toolsets=toolsets or [],
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
        last_reflex_kind=last_reflex_kind,
        last_reflex_at=last_reflex_at,
        last_activity_at=last_activity_at or now.isoformat(),
        checkpoints=[],
        created_at=now,
        updated_at=updated_at or now,
    )


def make_task_blueprint_view(
    *,
    task_id: int,
    name: str,
    project_id: int | None = None,
    cwd: str = "C:/workspace",
    cadence_minutes: int | None = None,
    enabled: bool = True,
) -> TaskBlueprintView:
    now = datetime.now(UTC)
    return TaskBlueprintView(
        id=task_id,
        name=name,
        summary=f"{name} summary",
        objective_template=f"{name} objective",
        instance_id=1,
        project_id=project_id,
        cadence_minutes=cadence_minutes,
        cwd=cwd,
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
        enabled=enabled,
        last_launched_at=None,
        last_status=None,
        last_result_summary=None,
        created_at=now,
        updated_at=now,
    )


def make_remote_request_view(
    *,
    request_id: int,
    operator_id: int,
    target_kind: str,
    target_id: int,
    requested_at: datetime | None = None,
) -> RemoteRequestView:
    now = requested_at or datetime.now(UTC)
    return RemoteRequestView(
        id=request_id,
        team_id=1,
        team_name="Local Control",
        operator_id=operator_id,
        operator_name=f"Operator {operator_id}",
        operator_role="operator",
        kind="mission.create" if target_kind == "mission" else "task.trigger",
        status="completed",
        source="api_key",
        source_ip="127.0.0.1",
        user_agent="pytest",
        target_kind=target_kind,
        target_id=target_id,
        target_label=f"{target_kind}-{target_id}",
        idempotency_key=f"req-{request_id}",
        summary="Remote request completed.",
        error=None,
        payload_preview=None,
        result_preview=None,
        requested_at=now,
        resolved_at=now,
    )


def make_gateway_capability_view(
    *,
    level: str = "ready",
    headline: str = "Gateway capability is operator-ready",
    summary: str = "1/1 lane(s) connected. 1 tracked capability(ies) ready. approval pauses armed.",
    warnings: list[str] | None = None,
    ready_count: int = 1,
    connected_count: int = 1,
    total_count: int = 1,
    warning_count: int = 0,
    offline_count: int = 0,
    approval_count: int = 0,
    tracked_ready_count: int = 1,
    tracked_gap_count: int = 0,
    route_status: str = "ready",
    route_warning: str | None = None,
) -> GatewayCapabilityView:
    return GatewayCapabilityView.model_validate(
        {
            "level": level,
            "headline": headline,
            "summary": summary,
            "warnings": warnings or ([] if route_warning is None else [route_warning]),
            "connected_lane_health": {
                "headline": "Connected lane health",
                "summary": (
                    "A launch-ready lane is available."
                    if ready_count
                    else "Connected lanes need repair before launch."
                ),
                "total_count": total_count,
                "connected_count": connected_count,
                "ready_count": ready_count,
                "warning_count": warning_count,
                "offline_count": offline_count,
                "approval_count": approval_count,
                "lanes": [
                    {
                        "instance_id": 1,
                        "instance_name": "Local Codex Desktop",
                        "connected": connected_count > 0,
                        "level": "ready" if ready_count else "warn",
                        "summary": "Lane summary",
                        "approval_count": approval_count,
                        "app_count": 0,
                        "plugin_count": 0,
                        "mcp_server_count": 0,
                        "warnings": [] if route_warning is None else [route_warning],
                        "last_event_at": None,
                    }
                ],
            },
            "inventory": {
                "headline": "Gateway inventory",
                "summary": (
                    "Tracked capability gaps need repair."
                    if tracked_gap_count
                    else "Tracked capabilities are ready."
                ),
                "app_count": 0,
                "plugin_count": 0,
                "mcp_server_count": 0,
                "tracked_ready_count": tracked_ready_count,
                "tracked_gap_count": tracked_gap_count,
                "tracked_count": max(tracked_ready_count + tracked_gap_count, 1),
                "observed_count": tracked_ready_count,
                "items": [],
            },
            "approval_posture": {
                "headline": "Approval posture",
                "summary": (
                    f"{approval_count} approval request(s) are waiting."
                    if approval_count
                    else "No approvals are waiting."
                ),
                "pause_on_approval": True,
                "approval_count": approval_count,
                "lane_count_with_approvals": 1 if approval_count else 0,
                "operator_api_key_count": 1,
                "recent_remote_request_count": 0,
            },
            "launch_policy": {
                "headline": "Saved launch policy",
                "summary": "Verification on, built-in agents on, approvals paused.",
                "setup_mode": "remote" if route_status == "repair" else "local",
                "setup_flow": "quickstart",
                "route_binding_mode": "saved_lane",
                "run_verification": True,
                "use_builtin_agents": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "auto_recover": True,
                "auto_recover_limit": 2,
                "allow_failover": True,
                "model": "gpt-5.4",
                "max_turns": 4,
                "launch_route": {
                    "status": route_status,
                    "mode": "saved_lane",
                    "matched_by": "gateway.preferred_instance",
                    "headline": "Saved launch route",
                    "summary": "Launch route summary",
                    "session_key": "session-gateway",
                    "main_session_key": "session-gateway-main",
                    "last_route_policy": "session",
                    "warnings": [] if route_warning is None else [route_warning],
                    "preferred_instance": {
                        "id": 1,
                        "label": "Local Codex Desktop",
                        "detail": "Preferred gateway lane",
                        "connected": connected_count > 0,
                    },
                    "resolved_instance": None,
                    "candidates": [],
                    "last_resolved_at": None,
                },
            },
            "diagnostics": {
                "headline": "Gateway diagnostics",
                "summary": "Diagnostics summary",
                "ok_count": 1,
                "warn_count": 0 if level != "critical" else 1,
                "fail_count": 1 if level == "critical" else 0,
                "evidence": [],
            },
            "checked_at": datetime.now(UTC).isoformat(),
        }
    )


def make_gateway_repair_opportunity(
    *,
    instance_id: int = 1,
    project_id: int | None = None,
    cwd: str = "C:/workspace",
    start_immediately: bool = True,
) -> dict[str, object]:
    return {
        "id": "gateway-repair",
        "kind": "gateway_repair",
        "impact": "high",
        "title": "Stabilize gateway posture",
        "summary": "Repair the saved gateway posture before broader launches.",
        "why_now": "Gateway Doctor says the saved launch posture still needs repair.",
        "action_label": "Load gateway repair",
        "mission_draft": {
            "name": "Stabilize Gateway Posture",
            "objective": "Repair the highest-risk gateway blocker and verify the fix.",
            "instance_id": instance_id,
            "project_id": project_id,
            "task_blueprint_id": None,
            "cwd": cwd,
            "thread_id": None,
            "model": "gpt-5.4-mini",
            "reasoning_effort": None,
            "collaboration_mode": None,
            "max_turns": 3,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "start_immediately": start_immediately,
        },
    }


def make_dashboard_view(
    *,
    instances: list[InstanceView] | None = None,
    missions: list[MissionView] | None = None,
    projects: list[ProjectView] | None = None,
    opportunities: list[dict[str, object]] | None = None,
) -> DashboardView:
    instances = instances or []
    missions = missions or []
    projects = projects or []
    return DashboardView.model_validate(
        {
            "brief": {
                "status": "active" if any(m.status == "active" for m in missions) else "idle",
                "headline": "Control plane summary",
                "summary": "Dashboard summary",
                "focus_mission_id": missions[0].id if missions else None,
                "next_actions": [],
            },
            "control_chat": {
                "headline": "Tell Zues what to do next",
                "summary": "Chat summary",
                "input_placeholder": "Describe the next thing",
                "messages": [],
            },
            "attention_queue": {
                "enabled": True,
                "headline": "Attention queue is standing by",
                "summary": "Queue summary",
                "actions": [],
            },
            "launchpad": {
                "headline": "Launchpad ready",
                "summary": "Launch summary",
                "opportunities": opportunities or [],
            },
            "radar": {"posture": "steady", "summary": "Radar summary", "signals": []},
            "gateway_capability": {
                "level": "info",
                "headline": "Gateway capability is steady",
                "summary": "Gateway capability summary",
                "warnings": [],
                "connected_lane_health": {
                    "headline": "Connected lanes are healthy",
                    "summary": "Lane health summary",
                    "total_count": len(instances),
                    "connected_count": len(
                        [instance for instance in instances if instance.connected]
                    ),
                    "ready_count": len([instance for instance in instances if instance.connected]),
                    "warning_count": 0,
                    "offline_count": len(
                        [instance for instance in instances if not instance.connected]
                    ),
                    "approval_count": 0,
                    "lanes": [],
                },
                "inventory": {
                    "headline": "Gateway inventory is ready",
                    "summary": "Inventory summary",
                    "app_count": 0,
                    "plugin_count": 0,
                    "mcp_server_count": 0,
                    "tracked_ready_count": 0,
                    "tracked_gap_count": 0,
                    "tracked_count": 0,
                    "observed_count": 0,
                    "items": [],
                },
                "approval_posture": {
                    "headline": "Approval posture is calm",
                    "summary": "No approvals are waiting.",
                    "pause_on_approval": True,
                    "approval_count": 0,
                    "lane_count_with_approvals": 0,
                    "operator_api_key_count": 0,
                    "recent_remote_request_count": 0,
                },
                "launch_policy": {
                    "headline": "Saved local launch policy",
                    "summary": "Verification on, built-in agents on, approvals paused.",
                    "setup_mode": "local",
                    "setup_flow": "quickstart",
                    "route_binding_mode": "saved_lane",
                    "run_verification": True,
                    "use_builtin_agents": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "allow_failover": True,
                    "model": "gpt-5.4",
                    "max_turns": 4,
                    "launch_route": None,
                },
                "diagnostics": {
                    "headline": "Diagnostics are healthy",
                    "summary": "No active diagnostic failures.",
                    "ok_count": 0,
                    "warn_count": 0,
                    "fail_count": 0,
                    "evidence": [],
                },
                "checked_at": datetime.now(UTC).isoformat(),
            },
            "gateway_bootstrap": {
                "status": "unconfigured",
                "headline": "Gateway bootstrap is not configured",
                "summary": "QuickStart has not been run yet.",
                "warnings": ["No gateway bootstrap profile has been saved yet."],
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance": None,
                "project": None,
                "team": None,
                "operator": None,
                "task_blueprint": None,
                "default_cwd": None,
                "model": "gpt-5.4",
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
                "launch_defaults_summary": (
                    "Verification on, built-in agents on, approvals paused, and auto-commit off."
                ),
            },
            "ops_mesh": {
                "headline": "Ops mesh ready",
                "summary": "Ops summary",
                "task_inbox": {"headline": "Task inbox", "summary": "No tasks", "tasks": []},
                "auth_posture": {
                    "headline": "Auth idle",
                    "summary": "No integrations",
                    "satisfied_count": 0,
                    "missing_count": 0,
                    "degraded_count": 0,
                },
                "access_posture": {
                    "headline": "Remote ingress is local-only",
                    "summary": "No remote keys",
                    "team_count": 0,
                    "operator_count": 0,
                    "api_key_count": 0,
                    "recent_remote_request_count": 0,
                },
                "integrations_inventory": {
                    "headline": "Integration inventory is idle",
                    "summary": "No inventory yet",
                    "ready_count": 0,
                    "gap_count": 0,
                    "tracked_count": 0,
                    "observed_count": 0,
                    "items": [],
                },
                "skills_registry": {
                    "headline": "Skills registry is idle",
                    "summary": "No live skills",
                    "lanes": [],
                    "projects": [],
                    "gaps": [],
                },
                "skillbooks": [],
                "teams": [],
                "operators": [],
                "remote_requests": [],
                "vault_secrets": [],
                "integrations": [],
                "notification_routes": [],
                "lane_snapshots": [],
            },
            "economy": {"headline": "Economy idle", "summary": "No economy yet", "scopes": []},
            "interference": {
                "headline": "Interference calm",
                "summary": "No overlaps",
                "vectors": [],
            },
            "continuity": {
                "headline": "Continuity ready",
                "summary": "No packets yet",
                "packets": [],
            },
            "recall": {
                "mode": "recent",
                "query": None,
                "headline": "Recent recall is ready",
                "summary": "Saved recall summary",
                "total_matches": 0,
                "items": [],
            },
            "dream_deck": {
                "headline": "No dream candidates yet",
                "summary": "No dreams",
                "dreams": [],
            },
            "cortex": {
                "headline": "Learning",
                "summary": "No doctrine yet",
                "doctrines": [],
                "inoculations": [],
            },
            "reflex_deck": {
                "headline": "No reflexes",
                "summary": "No reflexes yet",
                "reflexes": [],
            },
            "instances": [instance.model_dump(mode="json") for instance in instances],
            "missions": [mission.model_dump(mode="json") for mission in missions],
            "projects": [project.model_dump(mode="json") for project in projects],
            "playbooks": [],
            "task_blueprints": [],
            "integrations": [],
            "notification_routes": [],
            "skill_pins": [],
            "lane_snapshots": [],
            "events": [],
        }
    )


def test_health_endpoint(tmp_path) -> None:
    with make_client(tmp_path, reset_data_dir=True) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["control_plane"] == "leader"
    assert "runtime_update" in response.json()


def test_dashboard_merges_repeated_plugin_warning_events(tmp_path) -> None:
    duplicate_warning = (
        "\x1b[2m2026-04-11T01:37:30.455301Z\x1b[0m \x1b[33m WARN\x1b[0m "
        "\x1b[2mcodex_core::plugins::manager\x1b[0m\x1b[2m:\x1b[0m skipping duplicate "
        'plugin MCP server name \x1b[3mplugin\x1b[0m\x1b[2m=\x1b[0m"vercel@openai-curated" '
        '\x1b[3mprevious_plugin\x1b[0m\x1b[2m=\x1b[0m"build-web-apps@openai-curated" '
        '\x1b[3mserver\x1b[0m\x1b[2m=\x1b[0m"vercel"'
    )
    prompt_warning_a = (
        "\x1b[2m2026-04-11T01:37:30.459624Z\x1b[0m \x1b[33m WARN\x1b[0m "
        "\x1b[2mcodex_core::plugins::manifest\x1b[0m\x1b[2m:\x1b[0m ignoring "
        "interface.defaultPrompt: prompt must be at most 128 characters "
        "path=C:\\Users\\skull\\.codex\\.tmp\\plugins\\plugins\\build-ios-apps\\.codex-plugin\\plugin.json"
    )
    prompt_warning_b = (
        "\x1b[2m2026-04-11T01:37:30.460228Z\x1b[0m \x1b[33m WARN\x1b[0m "
        "\x1b[2mcodex_core::plugins::manifest\x1b[0m\x1b[2m:\x1b[0m ignoring "
        "interface.defaultPrompt: prompt must be at most 128 characters "
        "path=C:\\Users\\skull\\.codex\\.tmp\\plugins\\plugins\\life-science-research\\.codex-plugin\\plugin.json"
    )

    with make_client(tmp_path, reset_data_dir=True) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id=None,
                method="server/stderr",
                payload={"line": duplicate_warning},
            )
        )
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id=None,
                method="server/stderr",
                payload={"line": duplicate_warning},
            )
        )
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id=None,
                method="server/stderr",
                payload={"line": prompt_warning_a},
            )
        )
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id=None,
                method="server/stderr",
                payload={"line": prompt_warning_b},
            )
        )
        response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    stderr_events = [event for event in payload["events"] if event["method"] == "server/stderr"]
    assert len(stderr_events) == 2

    duplicate_event = next(
        event
        for event in stderr_events
        if "duplicate plugin MCP server name" in event["payload"]["line"]
    )
    assert duplicate_event["payload"]["repeatCount"] == 2
    assert duplicate_event["payload"]["line"].startswith("WARN codex_core::plugins::manager:")

    prompt_event = next(
        event for event in stderr_events if "interface.defaultPrompt" in event["payload"]["line"]
    )
    assert prompt_event["payload"]["repeatCount"] == 2
    assert prompt_event["payload"]["pathCount"] == 2
    assert len(prompt_event["payload"]["paths"]) == 2


def test_dashboard_compacts_verbose_command_events(tmp_path) -> None:
    long_command = "python -c \"" + ("print('gateway bootstrap parity') " * 20) + "\""
    long_output = "gateway bootstrap checkpoint " * 80
    long_delta = "relay note " * 90

    with make_client(tmp_path, reset_data_dir=True) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id="thread_live",
                method="item/completed",
                payload={
                    "threadId": "thread_live",
                    "turnId": "turn_live",
                    "item": {
                        "type": "commandExecution",
                        "id": "cmd_1",
                        "command": long_command,
                        "aggregatedOutput": long_output,
                        "status": "completed",
                        "commandActions": [
                            {"type": "run", "command": long_command},
                            {"type": "run", "command": "rg -n gateway src/openzues"},
                            {"type": "run", "command": "pytest tests/test_gateway_bootstrap.py -q"},
                            {"type": "run", "command": "python -m compileall src/openzues"},
                        ],
                    },
                },
            )
        )
        asyncio.run(
            database.append_event(
                instance_id=2,
                thread_id="thread_live",
                method="item/commandExecution/outputDelta",
                payload={
                    "threadId": "thread_live",
                    "turnId": "turn_live",
                    "itemId": "cmd_1",
                    "delta": long_delta,
                },
            )
        )
        response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    command_event = next(
        event for event in payload["events"] if event["method"] == "item/completed"
    )
    delta_event = next(
        event
        for event in payload["events"]
        if event["method"] == "item/commandExecution/outputDelta"
    )

    item = command_event["payload"]["item"]
    assert item["command"].endswith("... [truncated]")
    assert item["commandLength"] == len(long_command)
    assert item["aggregatedOutput"].endswith("... [truncated]")
    assert item["aggregatedOutputLength"] == len(long_output)
    assert item["commandActionCount"] == 4
    assert item["commandActionsTruncated"] is True
    assert len(item["commandActions"]) == 3

    assert delta_event["payload"]["delta"].endswith("... [truncated]")
    assert delta_event["payload"]["deltaLength"] == len(long_delta)


def test_observer_mode_blocks_mutating_requests(tmp_path) -> None:
    lease = FakeControlPlaneLease(owner=False, owner_pid=4242)
    with make_client(tmp_path, control_plane_lease=lease) as client:
        health = client.get("/api/health")
        dashboard = client.get("/api/dashboard")
        response = client.post("/api/control-chat", json={"text": "continue building"})

    assert health.status_code == 200
    assert health.json()["control_plane"] == "observer"
    assert health.json()["owner_pid"] == 4242
    assert dashboard.status_code == 200
    assert dashboard.json()["control_chat"]["headline"] == "Observer mode is active"
    assert dashboard.json()["attention_queue"]["headline"] == "Observer mode is active"
    assert response.status_code == 409
    assert response.json()["control_plane"] == "observer"


def test_project_creation_appears_on_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        create_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Sandbox"},
        )
        dashboard_response = client.get("/api/dashboard")

    assert create_response.status_code == 200
    project = create_response.json()
    assert project["label"] == "Sandbox"
    assert project["exists"] is True
    dashboard = dashboard_response.json()
    assert dashboard["brief"]["headline"]
    assert dashboard["dream_deck"]["headline"]
    assert dashboard["economy"]["headline"]
    assert dashboard["missions"] == []
    assert dashboard["projects"][0]["label"] == "Sandbox"
    assert dashboard["playbooks"] == []


def test_dashboard_compacts_inactive_mission_cards_but_keeps_live_cards_rich(tmp_path) -> None:
    long_objective = (
        "Resume from the verified parity checkpoint, inspect the current gateway seam, design the "
        "next bounded slice, implement it end to end, run focused verification, and leave a clean "
        "operator handoff before broadening into the next OpenClaw parity milestone. "
    ) * 3
    long_checkpoint = (
        "Completed the gateway seam and left the next operator handoff with verification notes, "
        "follow-on repair steps, and lane routing caveats so the next autonomous cycle can resume "
        "without rebuilding the entire context map. "
    ) * 3

    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Dashboard Lane",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        ).json()
        client.app.state.manager.instances[instance["id"]].connected = True
        database = client.app.state.database

        completed_id = asyncio.run(
            database.create_mission(
                name="Completed parity slice",
                objective=long_objective,
                status="completed",
                instance_id=instance["id"],
                project_id=None,
                thread_id="thread_completed_dashboard",
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
                toolsets=["debugging", "delegation", "memory"],
            )
        )
        active_id = asyncio.run(
            database.create_mission(
                name="Active parity slice",
                objective=long_objective,
                status="active",
                instance_id=instance["id"],
                project_id=None,
                thread_id="thread_active_dashboard",
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
                toolsets=["debugging", "delegation", "memory"],
            )
        )
        asyncio.run(
            database.update_mission(
                completed_id,
                last_checkpoint=long_checkpoint,
                last_commentary=long_checkpoint,
            )
        )
        asyncio.run(
            database.update_mission(
                active_id,
                in_progress=1,
                phase="thinking",
                last_checkpoint=long_checkpoint,
                last_commentary=long_checkpoint,
            )
        )
        for index in range(3):
            summary = f"checkpoint {index}: {long_checkpoint}"
            asyncio.run(
                database.append_mission_checkpoint(
                    mission_id=completed_id,
                    thread_id="thread_completed_dashboard",
                    turn_id=f"turn_completed_{index}",
                    kind="checkpoint",
                    summary=summary,
                )
            )
            asyncio.run(
                database.append_mission_checkpoint(
                    mission_id=active_id,
                    thread_id="thread_active_dashboard",
                    turn_id=f"turn_active_{index}",
                    kind="checkpoint",
                    summary=summary,
                )
            )

        dashboard = client.get("/api/dashboard").json()

    missions = {mission["id"]: mission for mission in dashboard["missions"]}
    completed = missions[completed_id]
    active = missions[active_id]

    assert len(completed["checkpoints"]) == 2
    assert completed["objective"].endswith("...")
    assert len(completed["objective"]) < len(long_objective)
    assert completed["tool_evidence"]["items"] == []
    assert active["status"] == "active"
    assert len(active["checkpoints"]) == 3
    assert not active["objective"].endswith("...")
    assert len(active["objective"]) > len(completed["objective"])


def test_project_creation_surfaces_ecc_source_workspace(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        create_response = client.post(
            "/api/projects",
            json={"path": str(ecc_root), "label": "ECC Repo"},
        )
        dashboard_response = client.get("/api/dashboard")

    assert create_response.status_code == 200
    project = create_response.json()
    assert project["label"] == "ECC Repo"
    assert project["agent_harness"]["kind"] == "ecc_source"
    assert project["agent_harness"]["skill_count"] == 5
    assert project["agent_harness"]["command_count"] == 1
    assert project["agent_harness"]["agent_count"] == 1
    assert project["agent_harness"]["codex_role_count"] == 1
    assert project["agent_harness"]["mcp_servers"] == ["github", "context7"]
    assert "skills/" in project["agent_harness"]["surface_paths"]
    assert project["agent_harness"]["default_install_profile"] == "developer"
    assert [profile["id"] for profile in project["agent_harness"]["install_profiles"]] == [
        "core",
        "developer",
    ]
    assert project["agent_harness"]["doctor"]["level"] == "ready"
    assert project["agent_harness"]["doctor"]["baseline_path"] == str(ecc_root)

    dashboard = dashboard_response.json()
    assert dashboard["projects"][0]["agent_harness"]["headline"] == (
        "Everything Claude Code source detected"
    )


def test_project_creation_surfaces_ecc_install_candidate_for_plain_workspace(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    workspace_root = tmp_path / "plain-project"
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "README.md").write_text("# Plain Project\n", encoding="utf-8")

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        response = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Plain Project"},
        )

    assert response.status_code == 200
    project = response.json()
    assert project["agent_harness"]["kind"] == "ecc_candidate"
    assert project["agent_harness"]["default_install_profile"] == "developer"
    assert [profile["id"] for profile in project["agent_harness"]["install_profiles"]] == [
        "core",
        "developer",
    ]
    assert project["agent_harness"]["doctor"] is None


def test_playbook_creation_and_diagnostics_endpoint(tmp_path) -> None:
    with make_client(tmp_path) as client:
        create_response = client.post(
            "/api/playbooks",
            json={
                "name": "Status check",
                "description": "Run git status",
                "kind": "command",
                "template": "git status --short --branch",
                "instance_id": None,
                "cadence_minutes": 60,
                "enabled": True,
                "cwd": str(tmp_path),
                "model": None,
                "reasoning_effort": None,
                "collaboration_mode": None,
                "timeout_ms": 10000,
                "thread_id": None,
                "default_variables": {"branch": "main"},
            },
        )
        dashboard_response = client.get("/api/dashboard")
        diagnostics_response = client.get("/api/diagnostics")

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "Status check"
    assert created["cadence_minutes"] == 60
    assert created["default_variables"] == {"branch": "main"}
    dashboard = dashboard_response.json()
    assert dashboard["brief"]["summary"]
    assert dashboard["missions"] == []
    assert dashboard["playbooks"][0]["name"] == "Status check"
    diagnostics = diagnostics_response.json()
    assert diagnostics["checks"]


def test_desktop_instance_creation_is_supported(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

    assert response.status_code == 200
    created = response.json()
    assert created["transport"] == "desktop"
    assert created["command"] is None
    assert created["args"] is None
    assert created["resolved_transport"] is None


def test_onboarding_bootstrap_creates_first_run_bundle_and_launch_draft(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Bootstrap Lane",
                "project_path": str(tmp_path),
                "project_label": "Bootstrap Workspace",
                "operator_name": "Remote Builder",
                "operator_email": "builder@example.com",
                "issue_api_key": True,
                "vault_secret_label": "GITHUB_TOKEN",
                "vault_secret_value": "ghp_example_123",
                "integration_name": "GitHub Inventory",
                "integration_kind": "github",
                "integration_base_url": "https://api.github.com",
                "skill_name": "Browser Verify",
                "skill_prompt_hint": "Use it after meaningful UI changes.",
                "skill_source": "agent-browser",
                "task_name": "Autonomous Ship Loop",
                "objective_template": (
                    "Inspect the repo, ship the next verified slice, and checkpoint it."
                ),
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "cadence_minutes": 180,
                "model": "gpt-5.4",
                "max_turns": 4,
                "toolsets": ["hermes-cli", "browser", "debugging"],
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
        dashboard_response = client.get("/api/dashboard")
        setup_response = client.get("/api/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["instance"]["created"] is True
    assert payload["project"]["created"] is True
    assert payload["team"]["label"] == "Local Control"
    assert payload["operator"]["label"] == "Remote Builder"
    assert payload["vault_secret"]["label"] == "GITHUB_TOKEN"
    assert payload["integration"]["label"] == "GitHub Inventory"
    assert payload["skill_pin"]["label"] == "Browser Verify"
    assert payload["task_blueprint"]["label"] == "Autonomous Ship Loop"
    assert payload["api_key"].startswith("ozk_")
    assert payload["mission_draft"]["name"] == "Kick off Autonomous Ship Loop"
    assert "Project skillbook:" in payload["mission_draft"]["objective"]
    assert "Hermes tool policy:" in payload["mission_draft"]["objective"]
    assert "Known integration inventory:" in payload["mission_draft"]["objective"]
    assert payload["mission_draft"]["session_key"].startswith("launch:mode:task_lane:task:")
    assert payload["mission_draft"]["toolsets"] == ["hermes-cli", "browser", "debugging"]
    assert payload["mission_draft"]["tool_policy"]["toolsets"] == [
        "hermes-cli",
        "browser",
        "debugging",
    ]
    assert payload["mission_draft"]["conversation_target"]["channel"] == "slack"
    assert payload["mission_draft"]["conversation_target"]["account_id"] == "workspace-bot"
    assert payload["mission_draft"]["conversation_target"]["peer_kind"] == "channel"
    assert payload["mission_draft"]["conversation_target"]["peer_id"] == "deploy-room"
    assert payload["launch_route"]["mode"] == "task_lane"
    assert payload["launch_route"]["matched_by"] == "task.instance"
    assert payload["launch_route"]["resolved_instance"]["label"] == "Bootstrap Lane"
    assert payload["launch_route"]["session_key"] == payload["mission_draft"]["session_key"]
    assert payload["launch_route"]["main_session_key"] != payload["launch_route"]["session_key"]
    assert payload["launch_route"]["main_session_key"].startswith("launch:mode:task_lane:task:")
    assert ":lane:" not in payload["launch_route"]["main_session_key"]
    assert payload["launch_route"]["last_route_policy"] == "session"
    assert payload["launch_route"]["conversation_target"] == payload["mission_draft"][
        "conversation_target"
    ]

    dashboard = dashboard_response.json()
    assert dashboard["projects"][0]["label"] == "Bootstrap Workspace"
    assert dashboard["instances"][0]["name"] == "Bootstrap Lane"
    assert dashboard["ops_mesh"]["access_posture"]["api_key_count"] == 1
    assert dashboard["ops_mesh"]["vault_secrets"][0]["label"] == "GITHUB_TOKEN"
    assert dashboard["ops_mesh"]["integrations"][0]["name"] == "GitHub Inventory"
    assert dashboard["ops_mesh"]["skillbooks"][0]["skills"][0]["name"] == "Browser Verify"
    assert dashboard["task_blueprints"][0]["name"] == "Autonomous Ship Loop"
    assert dashboard["gateway_bootstrap"]["status"] == "staged"
    assert dashboard["gateway_bootstrap"]["setup_mode"] == "local"
    assert dashboard["gateway_bootstrap"]["setup_flow"] == "quickstart"
    assert dashboard["gateway_bootstrap"]["project"]["label"] == "Bootstrap Workspace"
    assert dashboard["gateway_bootstrap"]["operator"]["label"] == "Remote Builder"
    assert dashboard["gateway_bootstrap"]["task_blueprint"]["label"] == "Autonomous Ship Loop"
    assert dashboard["gateway_bootstrap"]["route_binding_mode"] == "saved_lane"
    assert dashboard["gateway_bootstrap"]["run_verification"] is True
    assert dashboard["gateway_bootstrap"]["auto_commit"] is False
    assert dashboard["gateway_bootstrap"]["bootstrap_roles"] == ["node", "operator"]
    assert dashboard["gateway_bootstrap"]["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]
    assert dashboard["gateway_bootstrap"]["toolsets"] == ["hermes-cli", "browser", "debugging"]
    assert dashboard["gateway_bootstrap"]["tool_policy"]["toolsets"] == [
        "hermes-cli",
        "browser",
        "debugging",
    ]
    assert dashboard["gateway_bootstrap"]["launch_route"]["mode"] == "task_lane"
    assert (
        dashboard["task_blueprints"][0]["conversation_target"]["summary"]
        == "slack · account workspace-bot · channel deploy-room"
    )

    setup = setup_response.json()
    assert setup["wizard_session"]["conversation_target"]["channel"] == "slack"
    assert setup["wizard_session"]["conversation_target"]["account_id"] == "workspace-bot"
    assert setup["wizard_session"]["bootstrap_roles"] == ["node", "operator"]
    assert setup["wizard_session"]["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]
    assert (
        setup["launch_handoff"]["launch_route"]["conversation_target"]["peer_id"]
        == "deploy-room"
    )


def test_dashboard_auto_attaches_matching_hermes_skill_to_task_draft(tmp_path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    hermes_skill_path = write_fake_hermes_skill(
        hermes_root,
        relative_dir="skills/research/arxiv-research",
        name="ArXiv Research",
        description="Search arXiv papers, summarize findings, and track citations for the topic",
        category="research",
        tags=["research", "arxiv", "papers", "citations"],
    )

    try:
        with make_client(tmp_path, hermes_source_path=hermes_root) as client:
            instance = client.post(
                "/api/instances",
                json={
                    "name": "Hermes Lane",
                    "transport": "desktop",
                    "cwd": str(tmp_path),
                    "auto_connect": False,
                },
            ).json()
            project = client.post(
                "/api/projects",
                json={"path": str(tmp_path), "label": "Hermes Workspace"},
            ).json()
            task_response = client.post(
                "/api/tasks",
                json={
                    "name": "Research Loop",
                    "summary": "Keep gathering primary literature.",
                    "objective_template": (
                        "Research arxiv papers, summarize the evidence, and cite the strongest "
                        "findings before proposing the next change."
                    ),
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
            dashboard = client.get("/api/dashboard").json()

        assert task_response.status_code == 200
        skill_names = [skill["name"] for skill in dashboard["ops_mesh"]["skillbooks"][0]["skills"]]
        assert "ArXiv Research" in skill_names
        hermes_skill = next(
            skill
            for skill in dashboard["ops_mesh"]["skillbooks"][0]["skills"]
            if skill["name"] == "ArXiv Research"
        )
        assert hermes_skill["id"] < 0
        assert hermes_skill["source"] == str(hermes_skill_path)
        task_objective = dashboard["ops_mesh"]["task_inbox"]["tasks"][0]["mission_draft"][
            "objective"
        ]
        assert str(hermes_skill_path) in task_objective
        assert "Read the linked Hermes SKILL.md" in task_objective
    finally:
        configure_hermes_skill_catalog(None)


def test_task_creation_roundtrips_conversation_target_into_dashboard_draft(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Routing Lane",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Routing Workspace"},
        ).json()
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Channel Route Loop",
                "summary": "Keep one routed conversation identity stable.",
                "objective_template": "Ship the next verified slice against the saved route.",
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "instance_id": instance["id"],
                "project_id": project["id"],
                "cadence_minutes": 90,
                "cwd": str(tmp_path),
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
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
        dashboard_response = client.get("/api/dashboard")

    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert task_payload["conversation_target"]["channel"] == "slack"
    assert task_payload["conversation_target"]["account_id"] == "workspace-bot"
    assert task_payload["conversation_target"]["peer_kind"] == "channel"
    assert task_payload["conversation_target"]["peer_id"] == "deploy-room"
    assert task_payload["conversation_target"]["summary"] == (
        "slack · account workspace-bot · channel deploy-room"
    )

    dashboard = dashboard_response.json()
    task = dashboard["task_blueprints"][0]
    assert task["conversation_target"]["summary"] == (
        "slack · account workspace-bot · channel deploy-room"
    )
    assert task["mission_draft"]["conversation_target"]["peer_id"] == "deploy-room"


def test_dashboard_auto_attaches_matching_ecc_skill_and_surface_to_task_draft(
    tmp_path,
) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    ecc_skill_path = ecc_root / "skills" / "workspace-surface-audit" / "SKILL.md"

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "ECC Lane",
                "transport": "desktop",
                "cwd": str(ecc_root),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(ecc_root), "label": "ECC Workspace"},
        ).json()
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "ECC Surface Loop",
                "summary": "Map the harness surface.",
                "objective_template": (
                    "Audit the workspace surface, inspect the Codex config, and summarize the "
                    "installed harness posture before changing anything."
                ),
                "instance_id": instance["id"],
                "project_id": project["id"],
                "cadence_minutes": 60,
                "cwd": str(ecc_root),
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
        dashboard = client.get("/api/dashboard").json()

    assert task_response.status_code == 200
    skill_names = [skill["name"] for skill in dashboard["ops_mesh"]["skillbooks"][0]["skills"]]
    assert "workspace-surface-audit" in skill_names
    ecc_skill = next(
        skill
        for skill in dashboard["ops_mesh"]["skillbooks"][0]["skills"]
        if skill["name"] == "workspace-surface-audit"
    )
    assert ecc_skill["source"] == str(ecc_skill_path)
    task_objective = dashboard["ops_mesh"]["task_inbox"]["tasks"][0]["mission_draft"]["objective"]
    assert "ECC workspace surface:" in task_objective
    assert "ECC source repo detected with 5 skill(s)" in task_objective
    assert "ECC doctor:" in task_objective
    assert str(ecc_skill_path) in task_objective


def test_project_harness_endpoint_reports_ecc_workspace_drift_and_repairs(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    (ecc_root / ".codex" / "agents" / "reviewer.toml").write_text(
        'model = "gpt-5.4"\n',
        encoding="utf-8",
    )
    (ecc_root / ".mcp.json").write_text(
        (
            '{"mcpServers":{"github":{"command":"npx"},"context7":{"command":"npx"},'
            '"memory":{"command":"npx"}}}'
        ),
        encoding="utf-8",
    )
    workspace_root = write_fake_ecc_workspace(tmp_path / "ecc-installed-workspace")

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "ECC Installed Workspace"},
        )
        project_id = project_response.json()["id"]
        harness_response = client.get(f"/api/projects/{project_id}/harness")

    assert project_response.status_code == 200
    project = project_response.json()
    assert project["agent_harness"]["kind"] == "ecc_workspace"
    assert project["agent_harness"]["doctor"]["level"] == "warn"

    assert harness_response.status_code == 200
    harness = harness_response.json()
    assert harness["doctor"]["baseline_path"] == str(ecc_root)
    assert harness["doctor"]["install_state_paths"] == []
    assert harness["doctor"]["missing_surface_paths"] == ["AGENTS.md"]
    assert harness["doctor"]["missing_mcp_servers"] == ["memory"]
    assert harness["doctor"]["missing_codex_roles"] == ["reviewer"]
    assert ".mcp.json" in harness["doctor"]["drifted_paths"]
    assert any(
        action["command"] and "repair.js" in action["command"]
        for action in harness["doctor"]["repair_actions"]
    )


def test_project_harness_actions_preview_and_apply_manifest_install(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    workspace_root = tmp_path / "plain-ecc-install-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "README.md").write_text("# Plain Project\n", encoding="utf-8")

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Plain Install Workspace"},
        ).json()
        preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_preview", "profile": "developer"},
        )
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "developer"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["mode"] == "install_preview"
    assert preview["status"] == "planned"
    assert preview["profile"] == "developer"
    assert preview["selected_modules"] == [
        "agents-core",
        "platform-configs",
        "workflow-quality",
        "framework-language",
        "database",
        "orchestration",
    ]
    assert preview["skipped_modules"] == [
        "rules-core",
        "commands-core",
        "hooks-runtime",
    ]
    assert "AGENTS.md" in preview["planned_paths"]
    assert ".agents/coordination/README.md" in preview["planned_paths"]
    assert ".mcp.json" in preview["planned_paths"]
    assert ".codex/AGENTS.md" in preview["planned_paths"]
    assert ".codex/config.toml" in preview["planned_paths"]
    assert "mcp-configs/defaults.json" in preview["planned_paths"]
    assert "skills/python-patterns/SKILL.md" in preview["planned_paths"]
    assert "skills/postgres-patterns/SKILL.md" in preview["planned_paths"]
    assert "skills/tmux-orchestrator/SKILL.md" in preview["planned_paths"]
    assert ".codex/ecc-install-state.json" in preview["planned_paths"]

    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["mode"] == "install_apply"
    assert applied["status"] == "installed"
    assert applied["profile"] == "developer"
    assert applied["selected_modules"] == preview["selected_modules"]
    assert applied["skipped_modules"] == preview["skipped_modules"]
    assert "AGENTS.md" in applied["changed_paths"]
    assert ".agents/coordination/README.md" in applied["changed_paths"]
    assert ".mcp.json" in applied["changed_paths"]
    assert ".codex/AGENTS.md" in applied["changed_paths"]
    assert ".codex/config.toml" in applied["changed_paths"]
    assert "skills/continuous-learning/SKILL.md" in applied["changed_paths"]
    assert "skills/python-patterns/SKILL.md" in applied["changed_paths"]
    assert "skills/postgres-patterns/SKILL.md" in applied["changed_paths"]
    assert "skills/tmux-orchestrator/SKILL.md" in applied["changed_paths"]
    assert ".codex/ecc-install-state.json" in applied["changed_paths"]

    assert (workspace_root / "AGENTS.md").read_text(encoding="utf-8") == (
        ecc_root / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert json.loads((workspace_root / ".mcp.json").read_text(encoding="utf-8")) == json.loads(
        (ecc_root / ".mcp.json").read_text(encoding="utf-8")
    )
    assert (workspace_root / ".codex" / "AGENTS.md").read_text(encoding="utf-8") == (
        ecc_root / ".codex" / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert (workspace_root / ".agents" / "coordination" / "README.md").exists()
    assert (workspace_root / "skills" / "python-patterns" / "SKILL.md").exists()
    assert (workspace_root / "skills" / "postgres-patterns" / "SKILL.md").exists()
    assert (workspace_root / "skills" / "tmux-orchestrator" / "SKILL.md").exists()

    install_state = json.loads(
        (workspace_root / ".codex" / "ecc-install-state.json").read_text(encoding="utf-8")
    )
    assert install_state["schemaVersion"] == "ecc.install.v1"
    assert install_state["request"]["profile"] == "developer"
    assert install_state["request"]["legacyMode"] is False
    assert install_state["resolution"]["selectedModules"] == preview["selected_modules"]
    assert install_state["resolution"]["skippedModules"] == preview["skipped_modules"]
    operation_paths = {operation["sourceRelativePath"] for operation in install_state["operations"]}
    assert ".mcp.json" in operation_paths
    assert ".agents/coordination/README.md" in operation_paths
    assert "skills/python-patterns/SKILL.md" in operation_paths

    assert harness_response.status_code == 200
    harness = harness_response.json()
    assert harness["kind"] == "ecc_workspace"
    assert harness["active_install_profile"] == "developer"
    assert harness["active_install_modules"] == preview["selected_modules"]
    assert harness["active_install_skipped_modules"] == preview["skipped_modules"]
    assert harness["doctor"]["level"] == "ready"
    assert harness["doctor"]["missing_surface_paths"] == []
    assert harness["doctor"]["missing_mcp_servers"] == []
    assert harness["doctor"]["missing_codex_roles"] == []
    assert harness["doctor"]["drifted_paths"] == []
    assert harness["doctor"]["install_state_paths"] == [".codex/ecc-install-state.json"]


def test_project_harness_install_merges_existing_codex_and_mcp_configs(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    (ecc_root / ".codex" / "config.toml").write_text(
        (
            'approval_policy = "never"\n'
            'sandbox_mode = "danger-full-access"\n'
            "web_search = true\n\n"
            "[features]\n"
            "fast_mode = true\n\n"
            "[agents.explorer]\n"
            'model = "gpt-5.4"\n\n'
            "[agents.reviewer]\n"
            'model = "gpt-5.4-mini"\n'
        ),
        encoding="utf-8",
    )

    workspace_root = tmp_path / "merged-install-workspace"
    (workspace_root / ".codex").mkdir(parents=True, exist_ok=True)
    (workspace_root / ".codex" / "config.toml").write_text(
        (
            'approval_policy = "on-request"\n'
            'notify = ["terminal"]\n\n'
            "[agents.explorer]\n"
            'model = "custom-explorer"\n'
        ),
        encoding="utf-8",
    )
    (workspace_root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "custom": {"command": "python", "args": ["-m", "custom"]},
                    "github": {"command": "bun"},
                }
            }
        ),
        encoding="utf-8",
    )

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Merged Install Workspace"},
        ).json()
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "developer"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert apply_response.status_code == 200
    config_payload = tomllib.loads(
        (workspace_root / ".codex" / "config.toml").read_text(encoding="utf-8")
    )
    assert config_payload["approval_policy"] == "on-request"
    assert config_payload["sandbox_mode"] == "danger-full-access"
    assert config_payload["web_search"] is True
    assert config_payload["notify"] == ["terminal"]
    assert config_payload["features"]["fast_mode"] is True
    assert config_payload["agents"]["explorer"]["model"] == "custom-explorer"
    assert config_payload["agents"]["reviewer"]["model"] == "gpt-5.4-mini"

    mcp_payload = json.loads((workspace_root / ".mcp.json").read_text(encoding="utf-8"))
    assert sorted(mcp_payload["mcpServers"]) == ["context7", "custom", "github"]
    assert mcp_payload["mcpServers"]["custom"]["command"] == "python"
    assert mcp_payload["mcpServers"]["github"]["command"] == "bun"
    assert mcp_payload["mcpServers"]["context7"]["command"] == "npx"

    install_state = json.loads(
        (workspace_root / ".codex" / "ecc-install-state.json").read_text(encoding="utf-8")
    )
    operations_by_path = {
        operation["destinationRelativePath"]: operation for operation in install_state["operations"]
    }
    assert operations_by_path[".codex/config.toml"]["kind"] == "render-template"
    assert (
        'approval_policy = "on-request"'
        in operations_by_path[".codex/config.toml"]["previousContent"]
    )
    assert operations_by_path[".mcp.json"]["kind"] == "merge-json"
    assert operations_by_path[".mcp.json"]["mergePayload"] == {
        "mcpServers": {"context7": {"command": "npx"}}
    }

    harness = harness_response.json()
    assert harness_response.status_code == 200
    assert harness["doctor"]["level"] == "ready"
    assert harness["doctor"]["drifted_paths"] == []


def test_project_harness_actions_preview_and_apply_uninstall(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    workspace_root = tmp_path / "uninstall-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Uninstall Workspace"},
        ).json()
        install_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "developer"},
        )
        preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "uninstall_preview"},
        )
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "uninstall_apply"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert install_response.status_code == 200

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["mode"] == "uninstall_preview"
    assert preview["status"] == "planned"
    assert "AGENTS.md" in preview["planned_paths"]
    assert ".mcp.json" in preview["planned_paths"]
    assert ".codex/config.toml" in preview["planned_paths"]
    assert ".codex/ecc-install-state.json" in preview["planned_paths"]

    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["mode"] == "uninstall_apply"
    assert applied["status"] == "uninstalled"
    assert "AGENTS.md" in applied["changed_paths"]
    assert ".mcp.json" in applied["changed_paths"]
    assert ".codex/config.toml" in applied["changed_paths"]
    assert ".codex/ecc-install-state.json" in applied["changed_paths"]

    assert not (workspace_root / "AGENTS.md").exists()
    assert not (workspace_root / ".mcp.json").exists()
    assert not (workspace_root / ".codex" / "config.toml").exists()
    assert not (workspace_root / "skills" / "python-patterns" / "SKILL.md").exists()
    assert not (workspace_root / ".codex" / "ecc-install-state.json").exists()

    assert harness_response.status_code == 200
    assert harness_response.json()["kind"] == "ecc_candidate"


def test_project_harness_uninstall_blocks_when_managed_files_drift(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    workspace_root = tmp_path / "uninstall-drift-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Uninstall Drift Workspace"},
        ).json()
        install_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "developer"},
        )
        (workspace_root / "skills" / "python-patterns" / "SKILL.md").write_text(
            "# drifted\n",
            encoding="utf-8",
        )
        preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "uninstall_preview"},
        )
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "uninstall_apply"},
        )

    assert install_response.status_code == 200
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] == "planned"
    assert any("skills/python-patterns/SKILL.md" in warning for warning in preview["warnings"])

    assert apply_response.status_code == 400
    assert "managed files have drifted" in apply_response.json()["detail"]
    assert (workspace_root / "skills" / "python-patterns" / "SKILL.md").exists()


def test_project_harness_install_prunes_stale_files_on_profile_switch(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    workspace_root = tmp_path / "profile-switch-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "Profile Switch Workspace"},
        ).json()
        developer_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "developer"},
        )
        core_preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_preview", "profile": "core"},
        )
        core_apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "install_apply", "profile": "core"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert developer_response.status_code == 200

    assert core_preview_response.status_code == 200
    core_preview = core_preview_response.json()
    assert "skills/python-patterns/SKILL.md" in core_preview["planned_paths"]
    assert "skills/postgres-patterns/SKILL.md" in core_preview["planned_paths"]
    assert "skills/tmux-orchestrator/SKILL.md" in core_preview["planned_paths"]
    assert any("prune stale ECC-managed file" in warning for warning in core_preview["warnings"])

    assert core_apply_response.status_code == 200
    core_apply = core_apply_response.json()
    assert core_apply["profile"] == "core"
    assert "skills/python-patterns/SKILL.md" in core_apply["changed_paths"]
    assert "skills/postgres-patterns/SKILL.md" in core_apply["changed_paths"]
    assert "skills/tmux-orchestrator/SKILL.md" in core_apply["changed_paths"]

    assert not (workspace_root / "skills" / "python-patterns" / "SKILL.md").exists()
    assert not (workspace_root / "skills" / "postgres-patterns" / "SKILL.md").exists()
    assert not (workspace_root / "skills" / "tmux-orchestrator" / "SKILL.md").exists()
    assert (workspace_root / "skills" / "continuous-learning" / "SKILL.md").exists()

    assert harness_response.status_code == 200
    harness = harness_response.json()
    assert harness["active_install_profile"] == "core"
    assert harness["active_install_modules"] == [
        "agents-core",
        "platform-configs",
        "workflow-quality",
    ]


def test_project_harness_actions_preview_and_apply_repairs(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    (ecc_root / "AGENTS.md").write_text(
        "# Everything Claude Code (ECC) - Agent Instructions\n",
        encoding="utf-8",
    )
    (ecc_root / ".codex" / "agents" / "reviewer.toml").write_text(
        'model = "gpt-5.4"\n',
        encoding="utf-8",
    )
    (ecc_root / ".mcp.json").write_text(
        (
            '{"mcpServers":{"github":{"command":"npx"},"context7":{"command":"npx"},'
            '"memory":{"command":"npx"}}}'
        ),
        encoding="utf-8",
    )
    workspace_root = write_fake_ecc_workspace(tmp_path / "ecc-repair-workspace")
    (workspace_root / ".mcp.json").write_text(
        '{"mcpServers":{"github":{"command":"npx"}}}',
        encoding="utf-8",
    )

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "ECC Repair Workspace"},
        ).json()
        preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "repair_preview"},
        )
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "repair_apply"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] == "planned"
    assert "AGENTS.md" in preview["planned_paths"]
    assert ".mcp.json" in preview["planned_paths"]
    assert ".codex/agents/reviewer.toml" in preview["planned_paths"]
    assert ".codex/ecc-install-state.json" in preview["planned_paths"]

    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["status"] == "repaired"
    assert "AGENTS.md" in applied["changed_paths"]
    assert ".mcp.json" in applied["changed_paths"]
    assert ".codex/agents/reviewer.toml" in applied["changed_paths"]
    assert ".codex/ecc-install-state.json" in applied["changed_paths"]

    assert (workspace_root / "AGENTS.md").read_text(encoding="utf-8") == (
        ecc_root / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert (workspace_root / ".mcp.json").read_text(encoding="utf-8") == (
        ecc_root / ".mcp.json"
    ).read_text(encoding="utf-8")
    assert (workspace_root / ".codex" / "agents" / "reviewer.toml").exists()
    install_state = json.loads(
        (workspace_root / ".codex" / "ecc-install-state.json").read_text(encoding="utf-8")
    )
    assert install_state["schemaVersion"] == "ecc.install.v1"
    assert install_state["target"]["id"] == "codex-project"
    assert install_state["target"]["target"] == "codex"
    assert install_state["target"]["kind"] == "project"
    assert install_state["target"]["installStatePath"] == str(
        (workspace_root / ".codex" / "ecc-install-state.json").resolve(strict=False)
    )
    assert install_state["request"]["legacyMode"] is True
    assert install_state["resolution"]["selectedModules"] == ["legacy-codex-install"]
    operation_paths = {operation["sourceRelativePath"] for operation in install_state["operations"]}
    assert "AGENTS.md" in operation_paths
    assert ".mcp.json" in operation_paths
    assert ".codex/agents/reviewer.toml" in operation_paths

    assert harness_response.status_code == 200
    harness = harness_response.json()
    assert harness["doctor"]["missing_surface_paths"] == []
    assert harness["doctor"]["missing_mcp_servers"] == []
    assert harness["doctor"]["missing_codex_roles"] == []
    assert harness["doctor"]["drifted_paths"] == []
    assert harness["doctor"]["level"] == "ready"
    assert harness["doctor"]["install_state_paths"] == [".codex/ecc-install-state.json"]


def test_project_harness_actions_recreate_install_state_without_file_repairs(tmp_path) -> None:
    ecc_root = write_fake_ecc_source_repo(tmp_path / "everything-claude-code-main")
    (ecc_root / "AGENTS.md").write_text(
        "# Everything Claude Code (ECC) - Agent Instructions\n",
        encoding="utf-8",
    )
    (ecc_root / ".codex" / "agents" / "reviewer.toml").write_text(
        'model = "gpt-5.4"\n',
        encoding="utf-8",
    )
    (ecc_root / ".mcp.json").write_text(
        (
            '{"mcpServers":{"github":{"command":"npx"},"context7":{"command":"npx"},'
            '"memory":{"command":"npx"}}}'
        ),
        encoding="utf-8",
    )
    workspace_root = write_fake_ecc_workspace(tmp_path / "ecc-state-only-workspace")
    (workspace_root / "AGENTS.md").write_text(
        (ecc_root / "AGENTS.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (workspace_root / ".mcp.json").write_text(
        (ecc_root / ".mcp.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (workspace_root / ".codex" / "config.toml").write_text(
        (ecc_root / ".codex" / "config.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (workspace_root / ".codex" / "agents" / "reviewer.toml").write_text(
        (ecc_root / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with make_client(tmp_path, ecc_source_path=ecc_root) as client:
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_root), "label": "ECC State Only Workspace"},
        ).json()
        preview_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "repair_preview"},
        )
        apply_response = client.post(
            f"/api/projects/{project['id']}/harness/actions",
            json={"mode": "repair_apply"},
        )
        harness_response = client.get(f"/api/projects/{project['id']}/harness")

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] == "planned"
    assert preview["planned_paths"] == [".codex/ecc-install-state.json"]

    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["status"] == "repaired"
    assert applied["changed_paths"] == [".codex/ecc-install-state.json"]

    install_state = json.loads(
        (workspace_root / ".codex" / "ecc-install-state.json").read_text(encoding="utf-8")
    )
    assert install_state["schemaVersion"] == "ecc.install.v1"
    assert install_state["resolution"]["selectedModules"] == ["legacy-codex-install"]

    assert harness_response.status_code == 200
    harness = harness_response.json()
    assert harness["doctor"]["level"] == "ready"
    assert harness["doctor"]["missing_surface_paths"] == []
    assert harness["doctor"]["missing_mcp_servers"] == []
    assert harness["doctor"]["missing_codex_roles"] == []
    assert harness["doctor"]["drifted_paths"] == []
    assert harness["doctor"]["install_state_paths"] == [".codex/ecc-install-state.json"]


def test_onboarding_bootstrap_threads_mempalace_protocol_into_launch_draft(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "integration_name": "MemPalace",
                "integration_kind": "mempalace",
                "integration_base_url": "python -m mempalace.mcp_server",
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next slice with durable memory recall.",
            },
        )

    assert response.status_code == 200
    objective = response.json()["mission_draft"]["objective"]
    assert "MemPalace memory protocol:" in objective
    assert "query MemPalace first instead of guessing" in objective
    assert "write it back through MemPalace" in objective


def test_onboarding_bootstrap_use_mempalace_preset_registers_memory_integration(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next slice with durable memory recall.",
            },
        )
        dashboard_response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["integration"]["label"] == "MemPalace"
    assert payload["memory_task_blueprint"]["label"] == "MemPalace Memory Loop"
    assert "MemPalace memory protocol:" in payload["mission_draft"]["objective"]

    dashboard = dashboard_response.json()
    assert dashboard["ops_mesh"]["integrations"][0]["name"] == "MemPalace"
    assert dashboard["ops_mesh"]["integrations"][0]["kind"] == "mempalace"
    assert dashboard["ops_mesh"]["integrations"][0]["auth_scheme"] == "none"
    assert dashboard["ops_mesh"]["integrations_inventory"]["items"][0]["name"] == "MemPalace"
    task_names = [task["name"] for task in dashboard["task_blueprints"]]
    assert "Memory Ship Loop" in task_names
    assert "MemPalace Memory Loop" in task_names
    memory_task = next(
        task for task in dashboard["task_blueprints"] if task["name"] == "MemPalace Memory Loop"
    )
    assert memory_task["run_verification"] is False
    assert memory_task["use_builtin_agents"] is False


def test_onboarding_bootstrap_remote_mode_can_stage_without_default_lane(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "remote",
                "setup_flow": "advanced",
                "instance_mode": "existing",
                "instance_id": None,
                "project_path": str(tmp_path),
                "project_label": "Remote Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "task_name": "Remote Ship Loop",
                "objective_template": "Keep the remote workspace moving.",
            },
        )
        dashboard_response = client.get("/api/dashboard")
        setup_response = client.get("/api/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["instance"] is None
    assert payload["mission_draft"] is None
    assert "no lane available yet" in payload["warnings"][-1].lower()
    assert "Add or reconnect a lane" in payload["summary"]

    dashboard = dashboard_response.json()
    assert dashboard["gateway_bootstrap"]["setup_mode"] == "remote"
    assert dashboard["gateway_bootstrap"]["setup_flow"] == "advanced"
    assert dashboard["gateway_bootstrap"]["route_binding_mode"] == "workspace_affinity"
    assert dashboard["gateway_bootstrap"]["instance"] is None
    assert dashboard["gateway_bootstrap"]["task_blueprint"]["label"] == "Remote Ship Loop"
    assert dashboard["gateway_bootstrap"]["launch_route"]["mode"] == "workspace_affinity"
    assert dashboard["gateway_bootstrap"]["launch_route"]["resolved_instance"] is None

    setup = setup_response.json()
    assert setup["wizard_session"]["mode"] == "remote"
    assert setup["wizard_session"]["flow"] == "advanced"
    assert setup["wizard_session"]["remote_probe"]["status"] == "ready"
    assert setup["launch_handoff"]["launch_route"]["mode"] == "workspace_affinity"


def test_remote_workspace_affinity_prefers_project_lane_and_persists_last_route(tmp_path) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()
    other_path = tmp_path / "other"
    other_path.mkdir()

    with make_client(tmp_path) as client:
        first_instance = client.post(
            "/api/instances",
            json={
                "name": "Fallback Lane",
                "transport": "desktop",
                "cwd": str(other_path),
                "auto_connect": False,
            },
        ).json()
        matching_instance = client.post(
            "/api/instances",
            json={
                "name": "Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()

        manager = client.app.state.manager
        manager.instances[first_instance["id"]].connected = True
        manager.instances[matching_instance["id"]].connected = True

        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "remote",
                "setup_flow": "advanced",
                "instance_mode": "existing",
                "instance_id": None,
                "project_path": str(workspace_path),
                "project_label": "Remote Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "task_name": "Remote Ship Loop",
                "objective_template": "Keep the remote workspace moving.",
            },
        )
        launch_response = client.get("/api/setup/launch")
        payload = bootstrap_response.json()
        handoff = launch_response.json()

    assert bootstrap_response.status_code == 200
    assert payload["mission_draft"]["instance_id"] == matching_instance["id"]
    assert payload["mission_draft"]["session_key"].startswith("launch:mode:workspace_affinity:")
    assert payload["launch_route"]["mode"] == "workspace_affinity"
    assert payload["launch_route"]["matched_by"] == "workspace.last_route"
    assert payload["launch_route"]["resolved_instance"]["label"] == "Workspace Lane"
    assert payload["launch_route"]["candidates"][0]["label"] == "Workspace Lane"

    assert launch_response.status_code == 200
    assert handoff["mission_draft"]["instance_id"] == matching_instance["id"]
    assert handoff["mission_draft"]["session_key"] == payload["mission_draft"]["session_key"]
    assert handoff["launch_route"]["mode"] == "workspace_affinity"
    assert handoff["launch_route"]["matched_by"] == "workspace.last_route"
    assert handoff["launch_route"]["resolved_instance"]["label"] == "Workspace Lane"
    assert handoff["launch_route"]["last_resolved_at"] is not None


def test_workspace_shell_executor_prefers_lane_with_saved_cwd(tmp_path) -> None:
    project_path = tmp_path / "workspace"
    project_path.mkdir()
    shell_path = tmp_path / "shell"
    shell_path.mkdir()

    with make_client(tmp_path) as client:
        profile_response = client.put(
            "/api/hermes/profile",
            json={"preferred_executor": "workspace_shell"},
        )
        assert profile_response.status_code == 200

        lane_without_cwd = client.post(
            "/api/instances",
            json={
                "name": "Transient Lane",
                "transport": "desktop",
                "cwd": None,
                "auto_connect": False,
            },
        ).json()
        shell_lane = client.post(
            "/api/instances",
            json={
                "name": "Shell Lane",
                "transport": "desktop",
                "cwd": str(shell_path),
                "auto_connect": False,
            },
        ).json()

        manager = client.app.state.manager
        manager.instances[lane_without_cwd["id"]].connected = True
        manager.instances[shell_lane["id"]].connected = True

        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "remote",
                "setup_flow": "advanced",
                "instance_mode": "existing",
                "instance_id": None,
                "project_path": str(project_path),
                "project_label": "Shell Workspace",
                "operator_name": "Shell Builder",
                "issue_api_key": True,
                "task_name": "Shell Loop",
                "objective_template": "Keep the shell workspace moving.",
            },
        )
        payload = bootstrap_response.json()

    assert bootstrap_response.status_code == 200
    assert payload["launch_route"]["mode"] == "workspace_affinity"
    assert payload["launch_route"]["matched_by"] == "workspace.connected_lane"
    assert payload["launch_route"]["resolved_instance"]["label"] == "Shell Lane"
    assert payload["launch_route"]["status"] == "ready"


def test_workspace_shell_arm_api_uses_saved_gateway_workspace(tmp_path) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_path), "label": "Shell Workspace"},
        ).json()
        gateway_response = client.put(
            "/api/gateway/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "route_binding_mode": "saved_lane",
                "preferred_instance_id": instance["id"],
                "preferred_project_id": project["id"],
                "default_cwd": str(workspace_path),
                "model": "gpt-5.4",
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
            },
        )
        arm_response = client.post(
            "/api/hermes/executors/workspace-shell/arm",
            json={"cwd": None, "auto_connect": False},
        )
        doctor = client.get("/api/hermes/doctor").json()

    assert gateway_response.status_code == 200
    assert arm_response.status_code == 200
    payload = arm_response.json()
    assert payload["cwd"] == str(workspace_path)
    assert payload["derived_from"] == "gateway_default_cwd"
    assert payload["instance"]["transport"] == "stdio"
    assert payload["connected"] is False
    workspace_shell = next(
        item for item in doctor["executors"]["items"] if item["key"] == "workspace_shell"
    )
    assert "explicit arm" in workspace_shell["capabilities"]
    assert "shell-backed lane" in workspace_shell["summary"]


def test_docker_arm_api_uses_saved_gateway_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "openzues.services.hermes_platform._which", lambda command: command == "docker"
    )

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_path), "label": "Docker Workspace"},
        ).json()
        gateway_response = client.put(
            "/api/gateway/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "route_binding_mode": "saved_lane",
                "preferred_instance_id": instance["id"],
                "preferred_project_id": project["id"],
                "default_cwd": str(workspace_path),
                "model": "gpt-5.4",
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
            },
        )
        arm_response = client.post(
            "/api/hermes/executors/docker/arm",
            json={"cwd": None, "image": None, "auto_connect": False, "mount_workspace": False},
        )
        doctor = client.get("/api/hermes/doctor").json()

    assert gateway_response.status_code == 200
    assert arm_response.status_code == 200
    payload = arm_response.json()
    assert payload["cwd"] == str(workspace_path)
    assert payload["derived_from"] == "gateway_default_cwd"
    assert payload["instance"]["id"] == instance["id"]
    assert payload["instance"]["transport"] == "desktop"
    assert payload["connected"] is False
    assert payload["image"] == "nikolaik/python-nodejs:python3.11-nodejs20"
    docker = next(item for item in doctor["executors"]["items"] if item["key"] == "docker")
    assert "explicit arm" in docker["capabilities"]
    assert "Docker staging is armed" in docker["summary"]
    assert doctor["profile"]["executor_profiles"][0]["key"] == "docker"


def test_docker_preflight_api_reports_ready_backend(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "openzues.services.hermes_platform._which", lambda command: command == "docker"
    )
    monkeypatch.setattr(
        "openzues.services.hermes_platform.shutil.which",
        lambda command: "C:\\docker\\docker.exe" if command == "docker" else None,
    )

    async def fake_run_process_capture(
        *args: str, timeout_seconds: float = 20.0
    ) -> tuple[int, str, str]:
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

    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        instance = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        project = client.post(
            "/api/projects",
            json={"path": str(workspace_path), "label": "Docker Workspace"},
        ).json()
        client.put(
            "/api/gateway/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "route_binding_mode": "saved_lane",
                "preferred_instance_id": instance["id"],
                "preferred_project_id": project["id"],
                "default_cwd": str(workspace_path),
                "model": "gpt-5.4",
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
            },
        )
        client.post(
            "/api/hermes/executors/docker/arm",
            json={"cwd": None, "image": None, "auto_connect": False, "mount_workspace": False},
        )
        preflight_response = client.post(
            "/api/hermes/executors/docker/preflight",
            json={"cwd": None, "image": None},
        )
        doctor = client.get("/api/hermes/doctor").json()

    assert preflight_response.status_code == 200
    payload = preflight_response.json()
    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["image_present"] is True
    assert payload["daemon_version"] == "29.3.1"
    assert doctor["profile"]["executor_profiles"][0]["last_preflight_status"] == "ready"


def test_launch_routing_uses_gateway_default_cwd_when_task_has_no_workspace_context(
    tmp_path,
) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()
    other_path = tmp_path / "other"
    other_path.mkdir()

    with make_client(tmp_path) as client:
        fallback_instance = client.post(
            "/api/instances",
            json={
                "name": "Fallback Lane",
                "transport": "desktop",
                "cwd": str(other_path),
                "auto_connect": False,
            },
        ).json()
        matching_instance = client.post(
            "/api/instances",
            json={
                "name": "Gateway Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()

        manager = client.app.state.manager
        manager.instances[fallback_instance["id"]].connected = True
        manager.instances[matching_instance["id"]].connected = True

        database = client.app.state.database
        asyncio.run(
            database.upsert_gateway_bootstrap(
                setup_mode="remote",
                setup_flow="advanced",
                route_binding_mode="workspace_affinity",
                preferred_instance_id=None,
                preferred_project_id=None,
                team_id=None,
                operator_id=1,
                task_blueprint_id=77,
                default_cwd=str(workspace_path),
                model="gpt-5.4",
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
        )

        task = make_task_blueprint_view(task_id=77, name="Fallback route").model_copy(
            update={"instance_id": None, "project_id": None, "cwd": None}
        )
        route = asyncio.run(LaunchRoutingService(database, manager).describe(task=task))
        gateway = asyncio.run(database.get_gateway_bootstrap())

    assert route.mode == "workspace_affinity"
    assert route.matched_by == "workspace.project_lane"
    assert route.resolved_instance is not None
    assert route.resolved_instance.id == matching_instance["id"]
    assert route.candidates[0].id == matching_instance["id"]
    assert route.session_key == "launch:mode:workspace_affinity:task:77:operator:1"
    assert route.main_session_key == route.session_key
    assert route.last_route_policy == "main"
    assert gateway is not None
    assert gateway["last_route_instance_id"] == matching_instance["id"]
    assert gateway["last_route_resolved_at"] is not None


def test_setup_launch_handoff_surfaces_session_conversation_reuse(tmp_path) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        lane = client.post(
            "/api/instances",
            json={
                "name": "Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        manager = client.app.state.manager
        manager.instances[lane["id"]].connected = True

        database = client.app.state.database
        project_id = asyncio.run(
            database.create_project(path=str(workspace_path), label="Workspace")
        )
        team_id = asyncio.run(
            database.create_team(
                name="Operators",
                slug="operators",
                description="Remote operators",
            )
        )
        operator_id = asyncio.run(
            database.create_operator(
                team_id=team_id,
                name="Operator",
                email="operator@example.com",
                role="operator",
                enabled=True,
                api_key_hash="hash123",
                api_key_preview="ozk_abcd...1234",
                api_key_issued_at="2026-04-12T00:00:00+00:00",
            )
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="OpenClaw Total Parity Program",
                summary="Continue the verified parity spine.",
                project_id=project_id,
                instance_id=None,
                cadence_minutes=180,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified parity slice.",
                    "conversation_target": {
                        "channel": "slack",
                        "account_id": "workspace-bot",
                        "peer_kind": "channel",
                        "peer_id": "deploy-room",
                    },
                    "cwd": str(workspace_path),
                    "model": "gpt-5.4",
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
                    "toolsets": ["debugging", "delegation"],
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                },
            )
        )
        asyncio.run(
            database.upsert_gateway_bootstrap(
                setup_mode="remote",
                setup_flow="advanced",
                route_binding_mode="workspace_affinity",
                preferred_instance_id=None,
                preferred_project_id=project_id,
                team_id=team_id,
                operator_id=operator_id,
                task_blueprint_id=task_id,
                default_cwd=str(workspace_path),
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
            )
        )
        session_key = (
            f"launch:mode:workspace_affinity:task:{task_id}:project:{project_id}:operator:{operator_id}:"
            "channel:slack:account:workspace-bot:peer:channel:deploy-room"
        )
        asyncio.run(
            database.create_mission(
                name="Previous parity run",
                objective="Ship the prior parity slice.",
                status="completed",
                instance_id=lane["id"],
                project_id=project_id,
                task_blueprint_id=task_id,
                thread_id="thread_saved",
                session_key=session_key,
                conversation_target={
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                cwd=str(workspace_path),
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
                toolsets=["debugging"],
            )
        )
        asyncio.run(
            database.create_mission(
                name="Queued parity continuation",
                objective="Land the next verified parity slice.",
                status="paused",
                instance_id=lane["id"],
                project_id=project_id,
                task_blueprint_id=task_id,
                thread_id=None,
                session_key=session_key,
                conversation_target={
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                cwd=str(workspace_path),
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
                toolsets=["debugging"],
            )
        )

        setup_response = client.get("/api/setup")

    assert setup_response.status_code == 200
    payload = setup_response.json()
    reuse = payload["launch_handoff"]["launch_route"]["conversation_reuse"]
    target = payload["launch_handoff"]["launch_route"]["conversation_target"]
    assert target["channel"] == "slack"
    assert target["account_id"] == "workspace-bot"
    assert target["peer_kind"] == "channel"
    assert target["peer_id"] == "deploy-room"
    assert reuse["reusable"] is True
    assert reuse["thread_id"] == "thread_saved"
    assert "reuse thread thread_saved" in reuse["summary"]
    assert payload["launch_handoff"]["mission_draft"]["thread_id"] == "thread_saved"
    assert payload["launch_handoff"]["mission_draft"]["session_key"] == session_key
    assert payload["launch_handoff"]["mission_draft"]["conversation_target"] == target


def test_setup_launch_handoff_preserves_thread_child_session_key_for_reuse(tmp_path) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        lane = client.post(
            "/api/instances",
            json={
                "name": "Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        manager = client.app.state.manager
        manager.instances[lane["id"]].connected = True

        database = client.app.state.database
        project_id = asyncio.run(
            database.create_project(path=str(workspace_path), label="Workspace")
        )
        team_id = asyncio.run(
            database.create_team(
                name="Operators",
                slug="operators",
                description="Remote operators",
            )
        )
        operator_id = asyncio.run(
            database.create_operator(
                team_id=team_id,
                name="Operator",
                email="operator@example.com",
                role="operator",
                enabled=True,
                api_key_hash="hash123",
                api_key_preview="ozk_abcd...1234",
                api_key_issued_at="2026-04-12T00:00:00+00:00",
            )
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="OpenClaw Total Parity Program",
                summary="Continue the verified parity spine.",
                project_id=project_id,
                instance_id=None,
                cadence_minutes=180,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified parity slice.",
                    "cwd": str(workspace_path),
                    "model": "gpt-5.4",
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
                    "toolsets": ["debugging", "delegation"],
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                },
            )
        )
        asyncio.run(
            database.upsert_gateway_bootstrap(
                setup_mode="remote",
                setup_flow="advanced",
                route_binding_mode="workspace_affinity",
                preferred_instance_id=None,
                preferred_project_id=project_id,
                team_id=team_id,
                operator_id=operator_id,
                task_blueprint_id=task_id,
                default_cwd=str(workspace_path),
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
            )
        )
        main_session_key = (
            f"launch:mode:workspace_affinity:task:{task_id}:project:{project_id}:operator:{operator_id}"
        )
        child_session_key = f"{main_session_key}:thread:thread_saved"
        asyncio.run(
            database.create_mission(
                name="Previous parity run",
                objective="Ship the prior parity slice.",
                status="completed",
                instance_id=lane["id"],
                project_id=project_id,
                task_blueprint_id=task_id,
                thread_id="thread_saved",
                session_key=child_session_key,
                cwd=str(workspace_path),
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
                toolsets=["debugging"],
            )
        )

        setup_response = client.get("/api/setup")

    assert setup_response.status_code == 200
    payload = setup_response.json()
    route = payload["launch_handoff"]["launch_route"]
    reuse = route["conversation_reuse"]
    assert route["main_session_key"] == main_session_key
    assert route["session_key"] == child_session_key
    assert route["last_route_policy"] == "session"
    assert reuse["reusable"] is True
    assert reuse["thread_id"] == "thread_saved"
    assert "reuse thread thread_saved" in reuse["summary"]
    assert payload["launch_handoff"]["mission_draft"]["thread_id"] == "thread_saved"
    assert payload["launch_handoff"]["mission_draft"]["session_key"] == child_session_key


def test_setup_launch_handoff_keeps_workspace_affinity_session_key_across_lane_churn(
    tmp_path,
) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        previous_lane = client.post(
            "/api/instances",
            json={
                "name": "Previous Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        current_lane = client.post(
            "/api/instances",
            json={
                "name": "Current Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        manager = client.app.state.manager
        manager.instances[previous_lane["id"]].connected = False
        manager.instances[current_lane["id"]].connected = True

        database = client.app.state.database
        project_id = asyncio.run(
            database.create_project(path=str(workspace_path), label="Workspace")
        )
        team_id = asyncio.run(
            database.create_team(
                name="Operators",
                slug="operators",
                description="Remote operators",
            )
        )
        operator_id = asyncio.run(
            database.create_operator(
                team_id=team_id,
                name="Operator",
                email="operator@example.com",
                role="operator",
                enabled=True,
                api_key_hash="hash123",
                api_key_preview="ozk_abcd...1234",
                api_key_issued_at="2026-04-12T00:00:00+00:00",
            )
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="OpenClaw Total Parity Program",
                summary="Continue the verified parity spine.",
                project_id=project_id,
                instance_id=None,
                cadence_minutes=180,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified parity slice.",
                    "conversation_target": {
                        "channel": "slack",
                        "account_id": "workspace-bot",
                        "peer_kind": "channel",
                        "peer_id": "deploy-room",
                    },
                    "cwd": str(workspace_path),
                    "model": "gpt-5.4",
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
                    "toolsets": ["debugging", "delegation"],
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                },
            )
        )
        asyncio.run(
            database.upsert_gateway_bootstrap(
                setup_mode="remote",
                setup_flow="advanced",
                route_binding_mode="workspace_affinity",
                preferred_instance_id=None,
                preferred_project_id=project_id,
                team_id=team_id,
                operator_id=operator_id,
                task_blueprint_id=task_id,
                default_cwd=str(workspace_path),
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
                last_route_instance_id=previous_lane["id"],
            )
        )
        session_key = (
            f"launch:mode:workspace_affinity:task:{task_id}:project:{project_id}:operator:{operator_id}:"
            "channel:slack:account:workspace-bot:peer:channel:deploy-room"
        )
        asyncio.run(
            database.create_mission(
                name="Previous parity run",
                objective="Ship the prior parity slice.",
                status="completed",
                instance_id=previous_lane["id"],
                project_id=project_id,
                task_blueprint_id=task_id,
                thread_id="thread_saved",
                session_key=session_key,
                conversation_target={
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                cwd=str(workspace_path),
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
                toolsets=["debugging"],
            )
        )

        setup_response = client.get("/api/setup")

    assert setup_response.status_code == 200
    payload = setup_response.json()
    reuse = payload["launch_handoff"]["launch_route"]["conversation_reuse"]
    assert payload["launch_handoff"]["launch_route"]["mode"] == "workspace_affinity"
    assert (
        payload["launch_handoff"]["launch_route"]["resolved_instance"]["label"]
        == "Current Workspace Lane"
    )
    assert reuse["reusable"] is False
    assert reuse["thread_id"] == "thread_saved"
    assert "current route resolves to Current Workspace Lane" in reuse["summary"]
    assert payload["launch_handoff"]["mission_draft"]["thread_id"] is None
    assert payload["launch_handoff"]["mission_draft"]["session_key"] == session_key


def test_gateway_backfill_does_not_overwrite_saved_remote_bootstrap(tmp_path) -> None:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()

    with make_client(tmp_path) as client:
        lane = client.post(
            "/api/instances",
            json={
                "name": "Workspace Lane",
                "transport": "desktop",
                "cwd": str(workspace_path),
                "auto_connect": False,
            },
        ).json()
        manager = client.app.state.manager
        manager.instances[lane["id"]].connected = True

        database = client.app.state.database
        gateway_service = client.app.state.gateway_bootstrap_service

        project_id = asyncio.run(
            database.create_project(path=str(workspace_path), label="Workspace")
        )
        team_id = asyncio.run(
            database.create_team(
                name="Operators",
                slug="operators",
                description="Remote operators",
            )
        )
        operator_id = asyncio.run(
            database.create_operator(
                team_id=team_id,
                name="Operator",
                email="operator@example.com",
                role="operator",
                enabled=True,
                api_key_hash="hash123",
                api_key_preview="ozk_abcd...1234",
                api_key_issued_at="2026-04-12T00:00:00+00:00",
            )
        )
        task_id = asyncio.run(
            database.create_task_blueprint(
                name="OpenClaw Total Parity Program",
                summary="Continue the verified parity spine.",
                project_id=project_id,
                instance_id=None,
                cadence_minutes=180,
                enabled=True,
                payload={
                    "objective_template": "Ship the next verified parity slice.",
                    "conversation_target": {
                        "channel": "slack",
                        "account_id": "workspace-bot",
                        "peer_kind": "channel",
                        "peer_id": "deploy-room",
                    },
                    "cwd": str(workspace_path),
                    "model": "gpt-5.4",
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
                    "toolsets": ["debugging", "delegation"],
                    "run_until_complete": False,
                    "continuation_cooldown_minutes": 10,
                },
            )
        )
        asyncio.run(
            database.upsert_gateway_bootstrap(
                setup_mode="remote",
                setup_flow="advanced",
                route_binding_mode="workspace_affinity",
                preferred_instance_id=None,
                preferred_project_id=project_id,
                team_id=team_id,
                operator_id=operator_id,
                task_blueprint_id=task_id,
                default_cwd=str(workspace_path),
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
            )
        )

        now = datetime.now(UTC)
        backfilled = asyncio.run(
            gateway_service._backfill_from_existing(
                instances={instance.id: instance for instance in asyncio.run(manager.list_views())},
                projects={
                    project_id: ProjectView(
                        id=project_id,
                        path=str(workspace_path),
                        label="Workspace",
                        exists=True,
                        is_git_repo=False,
                    )
                },
                teams={
                    team_id: TeamView(
                        id=team_id,
                        name="Operators",
                        slug="operators",
                        description="Remote operators",
                        created_at=now,
                        updated_at=now,
                    )
                },
                operators={
                    operator_id: OperatorView(
                        id=operator_id,
                        team_id=team_id,
                        team_name="Operators",
                        name="Operator",
                        email="operator@example.com",
                        role="operator",
                        enabled=True,
                        has_api_key=True,
                        api_key_preview="ozk_abcd...1234",
                        api_key_issued_at="2026-04-12T00:00:00+00:00",
                        created_at=now,
                        updated_at=now,
                    )
                },
                tasks={
                    task_id: TaskBlueprintView(
                        id=task_id,
                        name="OpenClaw Total Parity Program",
                        summary="Continue the verified parity spine.",
                        objective_template="Ship the next verified parity slice.",
                        conversation_target={
                            "channel": "slack",
                            "account_id": "workspace-bot",
                            "peer_kind": "channel",
                            "peer_id": "deploy-room",
                        },
                        instance_id=None,
                        project_id=project_id,
                        cadence_minutes=180,
                        run_until_complete=False,
                        continuation_cooldown_minutes=10,
                        completion_marker=None,
                        cwd=str(workspace_path),
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
                        toolsets=["debugging", "delegation"],
                        enabled=True,
                        created_at=now,
                        updated_at=now,
                    )
                },
            )
        )

        saved = asyncio.run(database.get_gateway_bootstrap())

    assert backfilled is False
    assert saved is not None
    assert saved["setup_mode"] == "remote"
    assert saved["setup_flow"] == "advanced"
    assert saved["route_binding_mode"] == "workspace_affinity"
    assert saved["preferred_instance_id"] is None
    assert saved["preferred_project_id"] == project_id
    assert saved["operator_id"] == operator_id


def test_setup_endpoint_reports_reentrant_posture_after_bootstrap(tmp_path) -> None:
    with make_client(tmp_path) as client:
        client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Bootstrap Lane",
                "project_path": str(tmp_path),
                "project_label": "Bootstrap Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "task_name": "Autonomous Ship Loop",
                "objective_template": (
                    "Inspect the repo, ship the next verified slice, and checkpoint it."
                ),
            },
        )
        setup_response = client.get("/api/setup")

    assert setup_response.status_code == 200
    payload = setup_response.json()
    assert payload["recommended_action"] == "modify"
    assert payload["available_actions"] == ["keep", "modify", "reset"]
    assert payload["gateway_bootstrap"]["status"] == "staged"
    assert payload["gateway_bootstrap"]["bootstrap_roles"] == ["node", "operator"]
    assert payload["gateway_bootstrap"]["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]
    assert payload["footprint"]["instance"]["label"] == "Bootstrap Lane"
    assert payload["wizard_session"]["mode"] == "local"
    assert payload["wizard_session"]["bootstrap_roles"] == ["node", "operator"]
    assert payload["wizard_session"]["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]
    assert payload["launch_handoff"]["status"] == "staged"
    assert payload["launch_handoff"]["launch_route"]["mode"] == "task_lane"
    assert payload["launch_handoff"]["recommended_action"] == "connect_lane"
    assert payload["launch_handoff"]["mission_draft"]["task_blueprint_id"] is not None
    assert payload["launch_handoff"]["mission_draft"]["instance_id"] == 1
    assert payload["launch_handoff"]["mission_draft"]["session_key"].startswith(
        "launch:mode:task_lane:task:"
    )
    assert "Reconnect the default lane" in payload["next_entrypoint"]
    assert "Saved setup handoff:" in payload["handoff_summary"]


def test_setup_wizard_endpoint_updates_saved_mode_and_flow(tmp_path) -> None:
    with make_client(tmp_path) as client:
        update_response = client.put(
            "/api/setup/wizard",
            json={"mode": "remote", "flow": "quickstart"},
        )
        setup_response = client.get("/api/setup")

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["mode"] == "remote"
    assert payload["flow"] == "advanced"
    assert payload["recommended_flow"] in {"quickstart", "advanced"}
    setup = setup_response.json()
    assert setup["wizard_session"]["mode"] == "remote"
    assert setup["wizard_session"]["flow"] == "advanced"


def test_setup_wizard_endpoint_persists_mempalace_toggle(tmp_path) -> None:
    with make_client(tmp_path) as client:
        update_response = client.put(
            "/api/setup/wizard",
            json={"mode": "local", "flow": "quickstart", "use_mempalace": True},
        )
        setup_response = client.get("/api/setup")

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["use_mempalace"] is True
    setup = setup_response.json()
    assert setup["wizard_session"]["use_mempalace"] is True


def test_setup_launch_endpoint_reports_saved_remote_handoff_gap(tmp_path) -> None:
    with make_client(tmp_path) as client:
        client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "remote",
                "setup_flow": "advanced",
                "instance_mode": "existing",
                "project_path": str(tmp_path),
                "project_label": "Remote Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "task_name": "Remote Ship Loop",
                "objective_template": (
                    "Inspect the repo, ship the next verified slice, and checkpoint it."
                ),
            },
        )
        launch_response = client.get("/api/setup/launch")

    assert launch_response.status_code == 200
    payload = launch_response.json()
    assert payload["status"] == "staged"
    assert payload["recommended_action"] == "connect_lane"
    assert payload["mission_draft"] is None
    assert payload["launch_route"]["mode"] == "workspace_affinity"
    assert payload["launch_route"]["resolved_instance"] is None
    assert payload["task_blueprint"]["label"] == "Remote Ship Loop"
    assert "Connect or quick-connect a lane" in payload["next_entrypoint"]


def test_setup_reset_config_and_credentials_clears_profile_and_api_key(tmp_path) -> None:
    with make_client(tmp_path) as client:
        client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Bootstrap Lane",
                "project_path": str(tmp_path),
                "project_label": "Bootstrap Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "task_name": "Autonomous Ship Loop",
                "objective_template": (
                    "Inspect the repo, ship the next verified slice, and checkpoint it."
                ),
            },
        )
        reset_response = client.post(
            "/api/setup/reset",
            json={"scope": "config+creds+sessions"},
        )
        gateway_response = client.get("/api/gateway/bootstrap")
        dashboard_response = client.get("/api/dashboard")

    assert reset_response.status_code == 200
    payload = reset_response.json()
    assert payload["scope"] == "config+creds+sessions"
    assert "gateway bootstrap profile" in payload["cleared"]
    assert "operator API key" in payload["cleared"]
    assert "setup wizard session" in payload["cleared"]
    assert gateway_response.status_code == 200
    assert gateway_response.json()["status"] == "unconfigured"
    dashboard = dashboard_response.json()
    assert dashboard["ops_mesh"]["access_posture"]["api_key_count"] == 0


def test_setup_reset_full_removes_bootstrap_managed_resources(tmp_path) -> None:
    with make_client(tmp_path) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Bootstrap Lane",
                "project_path": str(tmp_path),
                "project_label": "Bootstrap Workspace",
                "operator_name": "Remote Builder",
                "operator_email": "builder@example.com",
                "issue_api_key": True,
                "vault_secret_label": "GITHUB_TOKEN",
                "vault_secret_value": "ghp_example_123",
                "integration_name": "GitHub Inventory",
                "integration_kind": "github",
                "integration_base_url": "https://api.github.com",
                "skill_name": "Browser Verify",
                "skill_prompt_hint": "Use it after meaningful UI changes.",
                "skill_source": "agent-browser",
                "task_name": "Autonomous Ship Loop",
                "objective_template": (
                    "Inspect the repo, ship the next verified slice, and checkpoint it."
                ),
            },
        )
        reset_response = client.post("/api/setup/reset", json={"scope": "full"})
        dashboard_response = client.get("/api/dashboard")
        setup_response = client.get("/api/setup")

    assert bootstrap_response.status_code == 200
    assert reset_response.status_code == 200
    payload = reset_response.json()
    assert payload["scope"] == "full"
    assert "task blueprint 'Autonomous Ship Loop'" in payload["cleared"]
    assert "integration 'GitHub Inventory'" in payload["cleared"]
    assert "skill pin 'Browser Verify'" in payload["cleared"]
    assert "vault secret 'GITHUB_TOKEN'" in payload["cleared"]
    assert "setup footprint" in payload["cleared"]

    dashboard = dashboard_response.json()
    assert dashboard["task_blueprints"] == []
    assert dashboard["ops_mesh"]["vault_secrets"] == []
    assert dashboard["ops_mesh"]["integrations"] == []
    assert all(
        operator["name"] != "Remote Builder" for operator in dashboard["ops_mesh"]["operators"]
    )
    setup = setup_response.json()
    assert setup["recommended_action"] == "bootstrap"
    assert setup["footprint"] is None


def test_setup_reset_full_removes_bootstrap_managed_mempalace_loop(tmp_path) -> None:
    with make_client(tmp_path) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "issue_api_key": True,
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        reset_response = client.post("/api/setup/reset", json={"scope": "full"})
        dashboard_response = client.get("/api/dashboard")

    assert bootstrap_response.status_code == 200
    assert reset_response.status_code == 200
    payload = reset_response.json()
    assert "task blueprint 'Memory Ship Loop'" in payload["cleared"]
    assert "task blueprint 'MemPalace Memory Loop'" in payload["cleared"]
    dashboard = dashboard_response.json()
    assert dashboard["task_blueprints"] == []


def test_gateway_bootstrap_endpoint_updates_saved_launch_profile(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Gateway Workspace"},
        )
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Gateway Lane",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Gateway Loop",
                "summary": "Keep the gateway profile fresh.",
                "objective_template": "Ship the next verified slice.",
                "instance_id": instance_response.json()["id"],
                "project_id": project_response.json()["id"],
                "cadence_minutes": 120,
                "cwd": str(tmp_path),
                "model": "gpt-5.4-mini",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": False,
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
        profile_response = client.put(
            "/api/gateway/bootstrap",
            json={
                "preferred_instance_id": instance_response.json()["id"],
                "preferred_project_id": project_response.json()["id"],
                "team_id": 1,
                "operator_id": 1,
                "task_blueprint_id": task_response.json()["id"],
                "default_cwd": str(tmp_path),
                "model": "gpt-5.4-mini",
                "max_turns": 3,
                "use_builtin_agents": False,
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
        read_response = client.get("/api/gateway/bootstrap")

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["status"] == "staged"
    assert profile["instance"]["label"] == "Gateway Lane"
    assert profile["project"]["label"] == "Gateway Workspace"
    assert profile["task_blueprint"]["label"] == "Gateway Loop"
    assert profile["model"] == "gpt-5.4-mini"
    assert profile["use_builtin_agents"] is False
    assert "local-only" in profile["operator"]["detail"]

    assert read_response.status_code == 200
    assert read_response.json()["task_blueprint"]["label"] == "Gateway Loop"


def test_gateway_bootstrap_endpoint_marks_connected_local_lane_ready_without_api_key(
    tmp_path,
) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Gateway Workspace"},
        )
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Gateway Lane",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Gateway Loop",
                "summary": "Launch the next verified gateway slice.",
                "objective_template": "Inspect the repo and ship the next verified gateway slice.",
                "instance_id": instance_response.json()["id"],
                "project_id": project_response.json()["id"],
                "cadence_minutes": 120,
                "cwd": str(tmp_path),
                "model": "gpt-5.4-mini",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": False,
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
        runtime = client.app.state.manager.instances[instance_response.json()["id"]]
        runtime.connected = True
        runtime.initialized = True

        profile_response = client.put(
            "/api/gateway/bootstrap",
            json={
                "preferred_instance_id": instance_response.json()["id"],
                "preferred_project_id": project_response.json()["id"],
                "team_id": 1,
                "operator_id": 1,
                "task_blueprint_id": task_response.json()["id"],
                "default_cwd": str(tmp_path),
                "model": "gpt-5.4-mini",
                "max_turns": 3,
                "use_builtin_agents": False,
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
        read_response = client.get("/api/gateway/bootstrap")

    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["status"] == "ready"
    assert profile["headline"] == "Gateway bootstrap is launch-ready"
    assert profile["instance"]["connected"] is True
    assert "local-only" in profile["operator"]["detail"]
    assert not any("active API key" in warning for warning in profile["warnings"])

    assert read_response.status_code == 200
    assert read_response.json()["status"] == "ready"


def test_gateway_capability_stays_ready_with_offline_aux_lane_when_primary_lane_is_healthy(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Primary Lane",
                "project_path": str(tmp_path),
                "project_label": "Primary Workspace",
                "operator_name": "Local Builder",
                "task_name": "Primary Loop",
                "objective_template": "Ship the next verified slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        primary_instance_id = bootstrap_response.json()["instance"]["id"]
        primary_runtime = client.app.state.manager.instances[primary_instance_id]
        primary_runtime.connected = True
        primary_runtime.initialized = True

        aux_response = client.post(
            "/api/instances",
            json={
                "name": "Workspace Shell",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        assert aux_response.status_code == 200

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["level"] == "ready"
    assert capability["headline"] == "Gateway capability is operator-ready"
    assert capability["connected_lane_health"]["connected_count"] == 1
    assert capability["connected_lane_health"]["offline_count"] == 1
    assert capability["connected_lane_health"]["warning_count"] == 0

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["gateway_capability"]["level"] == "ready"


def test_status_endpoint_reuses_gateway_contract_and_surfaces_queue_plan(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Gateway Lane",
                "project_path": str(tmp_path),
                "project_label": "Gateway Workspace",
                "operator_name": "Gateway Builder",
                "task_name": "Gateway Loop",
                "objective_template": "Ship the next verified gateway slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        status_response = client.get("/api/status")
        capability_response = client.get("/api/gateway/capability")

    assert status_response.status_code == 200
    payload = status_response.json()
    capability_payload = capability_response.json()
    status_gateway = {
        key: value for key, value in payload["gateway_capability"].items() if key != "checked_at"
    }
    capability_payload = {
        key: value for key, value in capability_payload.items() if key != "checked_at"
    }
    if "diagnostics" in status_gateway and "diagnostics" in capability_payload:
        for key in ("ok_count", "warn_count", "fail_count"):
            status_gateway["diagnostics"].pop(key, None)
            capability_payload["diagnostics"].pop(key, None)

    assert payload["headline"]
    assert payload["status_plan"]["action_kind"] == "observe"
    assert payload["queue_plan"] is not None
    assert payload["queue_plan"]["signal_id"] is not None
    assert "Gateway Doctor says" in payload["queue_plan"]["reply"]
    assert status_gateway == capability_payload


def test_gateway_capability_endpoint_summarizes_connected_lane_health_inventory_and_warnings(
    tmp_path,
) -> None:
    class FakeEnvironmentService:
        def collect(self) -> DiagnosticsView:
            return DiagnosticsView(
                checks=[
                    DiagnosticCheck(
                        key="desktop_policy",
                        label="Desktop mission policy",
                        status="warn",
                        detail="Approval policy is set to default desktop handling.",
                        value="approval=default",
                        action=(
                            "Set OPENZUES_DESKTOP_APPROVAL_POLICY to override this launch policy."
                        ),
                    ),
                    DiagnosticCheck(
                        key="python",
                        label="Python runtime",
                        status="ok",
                        detail="Python executable is available.",
                        value="Python 3.12.0",
                    ),
                ],
                checked_at="2026-04-11T12:00:00Z",
            )

    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings, environment_service=FakeEnvironmentService())

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Gateway Lane",
                "project_path": str(tmp_path),
                "project_label": "Gateway Workspace",
                "operator_name": "Remote Builder",
                "issue_api_key": True,
                "vault_secret_label": "GITHUB_TOKEN",
                "vault_secret_value": "ghp_example_123",
                "integration_name": "GitHub Inventory",
                "integration_kind": "github",
                "integration_base_url": "https://api.github.com",
                "task_name": "Gateway Ship Loop",
                "objective_template": "Ship the next verified gateway slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = [{"name": "Figma", "enabled": True}]
        runtime.plugins = [
            {"name": "GitHub", "enabled": True},
            {"name": "Slack", "enabled": True},
        ]
        runtime.mcp_servers = [{"name": "GitHub MCP Server", "source": "github", "status": "ready"}]
        runtime.mcp_server_status = [
            {
                "name": "GitHub MCP Server",
                "source": "github",
                "status": "ready",
                "tools": [
                    "github_search",
                    "github_search_prs",
                    "github_create_pull_request",
                ],
            }
        ]

        database = client.app.state.database
        asyncio.run(
            database.upsert_server_request(
                instance_id=instance_id,
                request_id="approval-gateway-capability",
                thread_id="thread-gateway-capability",
                method="item/commandExecution/requestApproval",
                payload={
                    "command": 'powershell.exe -Command "git push"',
                    "availableDecisions": ["accept", "cancel"],
                },
                status="pending",
            )
        )
        runtime.unresolved_requests = asyncio.run(
            database.list_unresolved_server_requests(instance_id)
        )

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["connected_lane_health"]["connected_count"] == 1
    assert capability["connected_lane_health"]["approval_count"] == 1
    lane = capability["connected_lane_health"]["lanes"][0]
    assert lane["instance_name"] == "Gateway Lane"
    assert lane["plugin_count"] == 2
    assert lane["app_count"] == 1
    assert lane["mcp_server_count"] == 1
    assert lane["approval_count"] == 1

    assert capability["inventory"]["tracked_ready_count"] == 1
    assert capability["inventory"]["app_count"] == 1
    assert capability["inventory"]["plugin_count"] == 2
    assert capability["inventory"]["mcp_server_count"] == 1
    assert capability["inventory"]["method_catalog"]["tool_count"] == 3
    assert capability["inventory"]["method_catalog"]["server_count"] == 1
    assert capability["inventory"]["method_catalog"]["lane_count"] == 1
    assert capability["inventory"]["method_catalog"]["tools"][0] == "github_create_pull_request"
    assert capability["approval_posture"]["approval_count"] == 1
    assert capability["approval_posture"]["pause_on_approval"] is True
    assert capability["launch_policy"]["setup_mode"] == "local"
    assert capability["launch_policy"]["route_binding_mode"] == "saved_lane"
    assert capability["diagnostics"]["warn_count"] == 1
    assert "Desktop mission policy" in capability["diagnostics"]["evidence"][0]

    dashboard = dashboard_response.json()
    assert dashboard["gateway_capability"]["approval_posture"]["approval_count"] == 1
    assert dashboard["gateway_capability"]["inventory"]["tracked_ready_count"] == 1
    assert dashboard["gateway_capability"]["inventory"]["method_catalog"]["tool_count"] == 3
    assert (
        dashboard["gateway_capability"]["connected_lane_health"]["lanes"][0]["instance_name"]
        == "Gateway Lane"
    )


def test_gateway_capability_classifies_operator_scopes_and_reserved_admin_methods(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Registry Lane",
                "project_path": str(tmp_path),
                "project_label": "Registry Workspace",
                "operator_name": "Registry Builder",
                "task_name": "Registry Loop",
                "objective_template": "Ship the registry slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = []
        runtime.plugins = []
        runtime.mcp_servers = [
            {"name": "Control Plane MCP", "source": "control-plane", "status": "ready"}
        ]
        runtime.mcp_server_status = [
            {
                "name": "Control Plane MCP",
                "source": "control-plane",
                "status": "ready",
                "tools": [
                    "connect",
                    "config.reload",
                    "exec.approval.list",
                    "node.pending.drain",
                    "node.pair.request",
                    "send",
                    "skills.bins",
                    "status",
                    "github_search",
                    "wizard.bootstrap",
                ],
            }
        ]

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    method_catalog = capability["inventory"]["method_catalog"]
    assert method_catalog["tool_count"] == 10
    assert method_catalog["classified_method_count"] == 9
    assert method_catalog["reserved_admin_method_count"] == 2
    assert method_catalog["reserved_admin_scope"] == "operator.admin"
    assert method_catalog["reserved_admin_methods"] == [
        "config.reload",
        "wizard.bootstrap",
    ]
    assert method_catalog["scopes"] == [
        {
            "scope": "operator.admin",
            "method_count": 3,
            "methods": ["config.reload", "connect", "wizard.bootstrap"],
        },
        {
            "scope": "operator.read",
            "method_count": 1,
            "methods": ["status"],
        },
        {
            "scope": "operator.write",
            "method_count": 1,
            "methods": ["send"],
        },
        {
            "scope": "operator.approvals",
            "method_count": 1,
            "methods": ["exec.approval.list"],
        },
        {
            "scope": "operator.pairing",
            "method_count": 1,
            "methods": ["node.pair.request"],
        },
        {
            "scope": "node.role",
            "method_count": 2,
            "methods": ["node.pending.drain", "skills.bins"],
        },
    ]
    assert "Scope coverage: operator.admin 3, operator.read 1" in method_catalog["summary"]
    assert "node.role 2" in method_catalog["summary"]
    assert "2 reserved admin method(s) require operator.admin." in method_catalog["summary"]

    dashboard = dashboard_response.json()
    assert (
        dashboard["gateway_capability"]["inventory"]["method_catalog"][
            "reserved_admin_method_count"
        ]
        == 2
    )
    assert (
        dashboard["gateway_capability"]["inventory"]["method_catalog"][
            "classified_method_count"
        ]
        == 9
    )


def test_gateway_capability_tracks_reserved_admin_registry_prefixes_end_to_end(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Reserved Registry Lane",
                "project_path": str(tmp_path),
                "project_label": "Reserved Registry Workspace",
                "operator_name": "Reserved Registry Builder",
                "task_name": "Reserved Registry Loop",
                "objective_template": "Lock the reserved gateway registry seam.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = []
        runtime.plugins = []
        runtime.mcp_servers = [
            {"name": "Control Plane MCP", "source": "control-plane", "status": "ready"}
        ]
        runtime.mcp_server_status = [
            {
                "name": "Control Plane MCP",
                "source": "control-plane",
                "status": "ready",
                "tools": [
                    "config.patch",
                    "exec.approvals.node.set",
                    "node.pending.drain",
                    "status",
                    "update.run",
                    "wizard.status",
                ],
            }
        ]

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    method_catalog = capability_response.json()["inventory"]["method_catalog"]
    assert method_catalog["tool_count"] == 6
    assert method_catalog["classified_method_count"] == 6
    assert method_catalog["reserved_admin_method_count"] == 4
    assert method_catalog["reserved_admin_scope"] == "operator.admin"
    assert method_catalog["reserved_admin_methods"] == [
        "config.patch",
        "exec.approvals.node.set",
        "update.run",
        "wizard.status",
    ]
    assert method_catalog["scopes"] == [
        {
            "scope": "operator.admin",
            "method_count": 4,
            "methods": [
                "config.patch",
                "exec.approvals.node.set",
                "update.run",
                "wizard.status",
            ],
        },
        {
            "scope": "operator.read",
            "method_count": 1,
            "methods": ["status"],
        },
        {
            "scope": "node.role",
            "method_count": 1,
            "methods": ["node.pending.drain"],
        },
    ]
    assert "Scope coverage: operator.admin 4, operator.read 1, node.role 1." in method_catalog[
        "summary"
    ]
    assert "4 reserved admin method(s) require operator.admin." in method_catalog["summary"]

    dashboard_method_catalog = dashboard_response.json()["gateway_capability"]["inventory"][
        "method_catalog"
    ]
    assert dashboard_method_catalog["reserved_admin_method_count"] == 4
    assert dashboard_method_catalog["reserved_admin_methods"] == [
        "config.patch",
        "exec.approvals.node.set",
        "update.run",
        "wizard.status",
    ]


def test_gateway_capability_classifies_plugin_scoped_methods_from_catalog_metadata(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Plugin Registry Lane",
                "project_path": str(tmp_path),
                "project_label": "Plugin Registry Workspace",
                "operator_name": "Plugin Registry Builder",
                "task_name": "Plugin Registry Loop",
                "objective_template": "Classify plugin method scopes from live metadata.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = []
        runtime.plugins = []
        runtime.mcp_servers = [
            {
                "name": "Plugin Control Plane MCP",
                "source": "plugin-control-plane",
                "status": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "Plugin Control Plane MCP",
                "source": "plugin-control-plane",
                "status": "ready",
                "tools": [
                    {"name": "browser.request", "scope": "operator.write"},
                    {"name": "wizard.custom", "scope": "operator.read"},
                    "status",
                ],
            }
        ]

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    method_catalog = capability_response.json()["inventory"]["method_catalog"]
    assert method_catalog["tool_count"] == 3
    assert method_catalog["classified_method_count"] == 3
    assert method_catalog["reserved_admin_method_count"] == 1
    assert method_catalog["reserved_admin_scope"] == "operator.admin"
    assert method_catalog["reserved_admin_methods"] == ["wizard.custom"]
    assert method_catalog["scopes"] == [
        {
            "scope": "operator.admin",
            "method_count": 1,
            "methods": ["wizard.custom"],
        },
        {
            "scope": "operator.read",
            "method_count": 1,
            "methods": ["status"],
        },
        {
            "scope": "operator.write",
            "method_count": 1,
            "methods": ["browser.request"],
        },
    ]
    assert "Scope coverage: operator.admin 1, operator.read 1, operator.write 1." in method_catalog[
        "summary"
    ]
    assert "1 reserved admin method(s) require operator.admin." in method_catalog["summary"]

    dashboard_method_catalog = dashboard_response.json()["gateway_capability"]["inventory"][
        "method_catalog"
    ]
    assert dashboard_method_catalog["classified_method_count"] == 3
    assert dashboard_method_catalog["reserved_admin_methods"] == ["wizard.custom"]


def test_gateway_capability_falls_back_to_staged_local_registry_when_lane_catalogs_are_offline(
    tmp_path,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Offline Registry Lane",
                "project_path": str(tmp_path),
                "project_label": "Offline Registry Workspace",
                "operator_name": "Offline Registry Builder",
                "task_name": "Offline Registry Loop",
                "objective_template": "Prove the staged gateway registry fallback.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = []
        runtime.plugins = []
        runtime.mcp_servers = []
        runtime.mcp_server_status = []

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    method_catalog = capability_response.json()["inventory"]["method_catalog"]
    assert method_catalog["headline"] == "Gateway method registry is staged"
    assert method_catalog["tool_count"] == len(list_known_gateway_methods())
    assert method_catalog["server_count"] == 0
    assert method_catalog["lane_count"] == 0
    assert method_catalog["classified_method_count"] == len(list_known_gateway_methods())
    assert method_catalog["reserved_admin_method_count"] == 14
    assert method_catalog["reserved_admin_scope"] == "operator.admin"
    assert [
        (entry["scope"], entry["method_count"]) for entry in method_catalog["scopes"]
    ] == [
        ("operator.admin", 38),
        ("operator.read", 47),
        ("operator.write", 28),
        ("operator.approvals", 9),
        ("operator.pairing", 12),
        ("node.role", 7),
    ]
    assert method_catalog["reserved_admin_methods"] == [
        "config.apply",
        "config.openFile",
        "config.patch",
        "config.schema",
        "config.set",
        "exec.approvals.get",
        "exec.approvals.node.get",
        "exec.approvals.node.set",
        "exec.approvals.set",
        "update.run",
        "wizard.cancel",
        "wizard.next",
        "wizard.start",
        "wizard.status",
    ]
    assert method_catalog["summary"].startswith(
        "141 built-in gateway method(s) are registered locally while lane-published "
        "MCP catalogs are offline."
    )
    assert (
        "Scope coverage: operator.admin 38, operator.read 47, operator.write 28, "
        "operator.approvals 9, operator.pairing 12, node.role 7."
    ) in method_catalog["summary"]
    assert "14 reserved admin method(s) require operator.admin." in method_catalog["summary"]

    dashboard_method_catalog = dashboard_response.json()["gateway_capability"]["inventory"][
        "method_catalog"
    ]
    assert dashboard_method_catalog["headline"] == "Gateway method registry is staged"
    assert dashboard_method_catalog["tool_count"] == len(list_known_gateway_methods())
    assert dashboard_method_catalog["classified_method_count"] == len(list_known_gateway_methods())
    assert dashboard_method_catalog["reserved_admin_methods"] == [
        "config.apply",
        "config.openFile",
        "config.patch",
        "config.schema",
        "config.set",
        "exec.approvals.get",
        "exec.approvals.node.get",
        "exec.approvals.node.set",
        "exec.approvals.set",
        "update.run",
        "wizard.cancel",
        "wizard.next",
        "wizard.start",
        "wizard.status",
    ]


def test_gateway_capability_surfaces_mempalace_memory_posture(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["inventory"]["memory_status"] == "ready"
    assert "MemPalace is tracked and live" in capability["inventory"]["memory_summary"]
    assert "Automatic memory loop is armed" in capability["inventory"]["memory_summary"]
    assert "Callable tool proof passed" in capability["inventory"]["memory_summary"]
    assert "scheduled MemPalace loop" in capability["inventory"]["memory_recommended_action"]
    assert "mempalace_status" in capability["inventory"]["memory_evidence"][0]

    dashboard = dashboard_response.json()
    assert dashboard["gateway_capability"]["inventory"]["memory_status"] == "ready"


def test_gateway_capability_warns_when_mempalace_tool_contract_is_incomplete(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                ],
            }
        ]

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["level"] == "warn"
    assert capability["inventory"]["memory_status"] == "warn"
    assert "callable tool proof is not complete yet" in capability["inventory"]["memory_summary"]
    assert "missing mempalace_diary_write" in capability["inventory"]["memory_evidence"][0]
    assert (
        "Expose mempalace_status, mempalace_search, and mempalace_diary_write"
        in (capability["inventory"]["memory_recommended_action"])
    )

    dashboard = dashboard_response.json()
    assert dashboard["gateway_capability"]["level"] == "warn"
    assert dashboard["gateway_capability"]["inventory"]["memory_status"] == "warn"


def test_gateway_capability_uses_cached_mcp_status_when_live_refresh_times_out(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]
        calls: list[tuple[int, bool]] = []

        async def fake_list_mcp_server_status(
            instance_id: int,
            *,
            limit: int = 50,
            refresh: bool = True,
        ) -> list[dict[str, object]]:
            del limit
            calls.append((instance_id, refresh))
            raise TimeoutError

        monkeypatch.setattr(
            "openzues.services.gateway_capability.GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS",
            0.01,
        )
        monkeypatch.setattr(
            client.app.state.manager,
            "list_mcp_server_status",
            fake_list_mcp_server_status,
        )

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["inventory"]["memory_status"] == "ready"
    assert "Callable tool proof passed" in capability["inventory"]["memory_summary"]
    assert "mempalace_status" in capability["inventory"]["memory_evidence"][0]

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["gateway_capability"]["inventory"]["memory_status"] == "ready"
    assert calls == []


def test_gateway_capability_falls_back_to_staged_registry_without_cached_catalogs(
    tmp_path,
    monkeypatch,
) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Offline Timeout Lane",
                "project_path": str(tmp_path),
                "project_label": "Offline Timeout Workspace",
                "operator_name": "Offline Timeout Builder",
                "task_name": "Offline Timeout Loop",
                "objective_template": "Prove timeout fallback reaches the staged registry.",
            },
        )
        assert bootstrap_response.status_code == 200

        instance_id = bootstrap_response.json()["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.apps = []
        runtime.plugins = []
        runtime.mcp_servers = [
            {
                "name": "Control Plane MCP",
                "source": "control-plane",
                "status": "ready",
            }
        ]
        runtime.mcp_server_status = []

        async def fake_list_mcp_server_status(
            instance_id: int,
            *,
            limit: int = 50,
            refresh: bool = True,
        ) -> list[dict[str, object]]:
            del instance_id, limit, refresh
            raise TimeoutError

        monkeypatch.setattr(
            "openzues.services.gateway_capability.GATEWAY_MCP_STATUS_REFRESH_TIMEOUT_SECONDS",
            0.01,
        )
        monkeypatch.setattr(
            client.app.state.manager,
            "list_mcp_server_status",
            fake_list_mcp_server_status,
        )

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    method_catalog = capability_response.json()["inventory"]["method_catalog"]
    event_catalog = capability_response.json()["inventory"]["event_catalog"]
    assert method_catalog["headline"] == "Gateway method registry is staged"
    assert method_catalog["tool_count"] == len(list_known_gateway_methods())
    assert method_catalog["server_count"] == 0
    assert method_catalog["lane_count"] == 0
    assert method_catalog["classified_method_count"] == len(list_known_gateway_methods())
    assert (
        "lane-published MCP catalogs are offline" in method_catalog["summary"]
    )
    assert (
        "14 reserved admin method(s) require operator.admin." in method_catalog["summary"]
    )
    assert event_catalog == {
        "headline": "Gateway event registry is staged",
        "summary": (
            f"{len(list_known_gateway_events())} built-in gateway event(s) are registered "
            "locally to mirror the OpenClaw event surface while lane-published event "
            "catalogs are offline."
        ),
        "event_count": len(list_known_gateway_events()),
        "events": list(list_known_gateway_events()),
    }

    assert dashboard_response.status_code == 200
    dashboard_method_catalog = dashboard_response.json()["gateway_capability"]["inventory"][
        "method_catalog"
    ]
    dashboard_event_catalog = dashboard_response.json()["gateway_capability"]["inventory"][
        "event_catalog"
    ]
    assert dashboard_method_catalog["headline"] == "Gateway method registry is staged"
    assert dashboard_method_catalog["tool_count"] == len(list_known_gateway_methods())
    assert dashboard_event_catalog["event_count"] == len(list_known_gateway_events())


def test_gateway_capability_background_refresh_replaces_stale_cached_posture(
    tmp_path,
    monkeypatch,
) -> None:
    cache_settings = Settings(
        data_dir=tmp_path / "cache-data",
        db_path=tmp_path / "cache-data" / "openzues-test.db",
        hermes_source_path=None,
        ecc_source_path=None,
    )
    monkeypatch.setattr("openzues.app.settings", cache_settings)
    clock = {"now": 0.0}
    monkeypatch.setattr("openzues.app.perf_counter", lambda: clock["now"])
    cached_gateway = make_gateway_capability_view(headline="Cached gateway posture is available")
    refresh_calls = {"count": 0}

    async def fake_get_view() -> GatewayCapabilityView:
        refresh_calls["count"] += 1
        if refresh_calls["count"] == 1:
            return cached_gateway
        await asyncio.sleep(0.05)
        return cached_gateway.model_copy(
            update={"headline": "Background refresh replaced the cached posture"}
        )

    class FakeGatewayCapabilityService:
        async def get_view(self) -> GatewayCapabilityView:
            return await fake_get_view()

    app = create_app(gateway_capability_service=FakeGatewayCapabilityService())

    with TestClient(app, client=("testclient", 50000)) as client:
        initial_dashboard = client.get("/api/gateway/capability")
        assert initial_dashboard.status_code == 200
        assert (
            initial_dashboard.json()["headline"]
            == "Cached gateway posture is available"
        )

        clock["now"] = 5.0
        refreshed_gateway = client.get("/api/gateway/capability")
        assert refreshed_gateway.status_code == 200
        assert refreshed_gateway.json()["headline"] == "Cached gateway posture is available"

        time.sleep(0.1)
        clock["now"] = 7.0
        updated_gateway = client.get("/api/gateway/capability")

    assert refresh_calls["count"] >= 2
    assert updated_gateway.status_code == 200
    assert updated_gateway.json()["headline"] == "Background refresh replaced the cached posture"


def test_mutating_api_failure_invalidates_operator_surface_caches(
    tmp_path,
    monkeypatch,
) -> None:
    cache_settings = Settings(
        data_dir=tmp_path / "cache-data",
        db_path=tmp_path / "cache-data" / "openzues-test.db",
        hermes_source_path=None,
        ecc_source_path=None,
    )
    monkeypatch.setattr("openzues.app.settings", cache_settings)
    app = create_app()

    with TestClient(app, client=("testclient", 50000)) as client:
        initial_dashboard = client.get("/api/dashboard")
        assert initial_dashboard.status_code == 200
        assert initial_dashboard.json()["projects"] == []

        async def fail_bootstrap(_payload):
            raise RuntimeError("forced bootstrap failure")

        monkeypatch.setattr(client.app.state.onboarding_service, "bootstrap", fail_bootstrap)

        with pytest.raises(RuntimeError, match="forced bootstrap failure"):
            client.post(
                "/api/onboarding/bootstrap",
                json={
                    "setup_mode": "local",
                    "setup_flow": "quickstart",
                    "instance_mode": "create_desktop",
                    "instance_name": "Recovery Lane",
                    "project_path": str(tmp_path / "workspace"),
                    "project_label": "Recovered Workspace",
                    "operator_name": "Recovery Builder",
                    "task_name": "Recovery Loop",
                    "objective_template": "Recover the next parity slice.",
                },
            )

        asyncio.run(
            client.app.state.database.create_project(
                path=str(tmp_path / "workspace"),
                label="Recovered Workspace",
            )
        )

        refreshed_dashboard = client.get("/api/dashboard")

    assert refreshed_dashboard.status_code == 200
    assert any(
        project["label"] == "Recovered Workspace"
        for project in refreshed_dashboard.json()["projects"]
    )


def test_gateway_bootstrap_startup_failure_preserves_boot_reason(tmp_path, monkeypatch) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "startup-data",
        db_path=tmp_path / "startup-data" / "openzues-test.db",
        hermes_source_path=None,
        ecc_source_path=None,
    )
    boot_calls: list[str] = []
    close_calls: list[RuntimeManager] = []
    lease = FakeControlPlaneLease(owner=True)

    async def fail_startup_boot(self) -> GatewayBootstrapBootResult:
        boot_calls.append("called")
        return GatewayBootstrapBootResult(
            status="failed",
            reason="agent run failed: lane offline",
        )

    original_close = RuntimeManager.close

    async def track_close(self: RuntimeManager) -> None:
        close_calls.append(self)
        await original_close(self)

    monkeypatch.setattr(GatewayBootstrapService, "run_startup_boot_once", fail_startup_boot)
    monkeypatch.setattr(RuntimeManager, "close", track_close)
    app = create_app(
        app_settings,
        control_plane_lease=lease,
    )

    with pytest.raises(RuntimeError, match="agent run failed: lane offline"):
        with TestClient(app, client=("testclient", 50000)):
            pass

    assert boot_calls == ["called"]
    assert close_calls == [app.state.manager]
    assert lease.acquired is False


def test_gateway_capability_warns_when_mempalace_memory_loop_last_failed(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        memory_task_id = payload["memory_task_blueprint"]["id"]
        asyncio.run(
            client.app.state.database.update_task_blueprint_payload(
                memory_task_id,
                last_launched_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
                last_status="failed",
                last_result_summary="MemPalace lane was unreachable during the writeback pass.",
            )
        )

        capability_response = client.get("/api/gateway/capability")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["inventory"]["memory_status"] == "warn"
    assert "last failed" in capability["inventory"]["memory_summary"]
    assert (
        "Inspect the failed MemPalace maintenance run"
        in (capability["inventory"]["memory_recommended_action"])
    )
    assert any(
        "MemPalace Memory Loop last failed" in line
        for line in capability["inventory"]["memory_evidence"]
    )


def test_gateway_capability_surfaces_mempalace_writeback_timestamp(tmp_path) -> None:
    last_launched_at = (
        (datetime.now(UTC) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    )
    writeback_at = (datetime.now(UTC) - timedelta(minutes=8)).isoformat().replace("+00:00", "Z")
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        memory_task_id = payload["memory_task_blueprint"]["id"]
        asyncio.run(
            client.app.state.database.update_task_blueprint_payload(
                memory_task_id,
                last_launched_at=last_launched_at,
                last_status="completed",
                last_result_summary=build_mempalace_writeback_signal(
                    status="wrote",
                    at=writeback_at,
                    scope="Memory Workspace",
                ),
            )
        )

        capability_response = client.get("/api/gateway/capability")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["inventory"]["memory_status"] == "ready"
    assert "Last durable writeback was reported" in capability["inventory"]["memory_summary"]
    assert any(
        f"Memory Workspace writeback reported at {writeback_at}." in line
        for line in capability["inventory"]["memory_evidence"]
    )


def test_gateway_capability_surfaces_mempalace_roundtrip_from_latest_mission_checkpoint(
    tmp_path,
) -> None:
    last_launched_at = (
        (datetime.now(UTC) - timedelta(minutes=12)).isoformat().replace("+00:00", "Z")
    )
    writeback_at = (datetime.now(UTC) - timedelta(minutes=9)).isoformat().replace("+00:00", "Z")
    roundtrip_at = (datetime.now(UTC) - timedelta(minutes=8)).isoformat().replace("+00:00", "Z")
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        memory_task_id = payload["memory_task_blueprint"]["id"]
        database = client.app.state.database
        asyncio.run(
            database.update_task_blueprint_payload(
                memory_task_id,
                last_launched_at=last_launched_at,
                last_status="completed",
                last_result_summary=build_mempalace_writeback_signal(
                    status="wrote",
                    at=writeback_at,
                    scope="Memory Workspace",
                ),
            )
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="MemPalace Memory Loop",
                objective="Refresh durable project memory through MemPalace.",
                status="completed",
                instance_id=instance_id,
                project_id=payload["project"]["id"],
                task_blueprint_id=memory_task_id,
                thread_id="thread-memory-proof",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                last_checkpoint="\n".join(
                    [
                        build_mempalace_writeback_signal(
                            status="wrote",
                            at=writeback_at,
                            scope="Memory Workspace",
                        ),
                        build_mempalace_roundtrip_signal(
                            status="verified",
                            at=roundtrip_at,
                            scope="Memory Workspace",
                            detail=(
                                "mempalace_search returned the freshly written recovery handoff "
                                "for the active workspace."
                            ),
                        ),
                        "sources reviewed: latest checkpoint docs and active workspace files",
                    ]
                ),
            )
        )

        capability_response = client.get("/api/gateway/capability")
        dashboard_response = client.get("/api/dashboard")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["inventory"]["memory_status"] == "ready"
    assert (
        "Last MemPalace roundtrip proof was reported" in capability["inventory"]["memory_summary"]
    )
    assert any(
        f"Memory Workspace roundtrip verified at {roundtrip_at}." in line
        and "mempalace_search returned the freshly written recovery handoff" in line
        for line in capability["inventory"]["memory_evidence"]
    )
    proof_reference = capability["inventory"]["memory_proof_reference"]
    assert proof_reference["mission_id"] == mission_id
    assert proof_reference["proof_kind"] == "roundtrip"
    assert proof_reference["proof_status"] == "verified"
    assert proof_reference["continuity_path"] == f"/api/missions/{mission_id}/continuity"
    assert "verified MemPalace roundtrip recall" in proof_reference["summary"]

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert (
        dashboard["gateway_capability"]["inventory"]["memory_proof_reference"]["mission_id"]
        == mission_id
    )


def test_gateway_capability_warns_when_mempalace_roundtrip_is_unavailable(tmp_path) -> None:
    last_launched_at = (
        (datetime.now(UTC) - timedelta(minutes=12)).isoformat().replace("+00:00", "Z")
    )
    writeback_at = (datetime.now(UTC) - timedelta(minutes=9)).isoformat().replace("+00:00", "Z")
    roundtrip_at = (datetime.now(UTC) - timedelta(minutes=8)).isoformat().replace("+00:00", "Z")
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        memory_task_id = payload["memory_task_blueprint"]["id"]
        database = client.app.state.database
        asyncio.run(
            database.update_task_blueprint_payload(
                memory_task_id,
                last_launched_at=last_launched_at,
                last_status="completed",
                last_result_summary=build_mempalace_writeback_signal(
                    status="wrote",
                    at=writeback_at,
                    scope="Memory Workspace",
                ),
            )
        )
        mission_id = asyncio.run(
            database.create_mission(
                name="MemPalace Memory Loop",
                objective="Refresh durable project memory through MemPalace.",
                status="completed",
                instance_id=instance_id,
                project_id=payload["project"]["id"],
                task_blueprint_id=memory_task_id,
                thread_id="thread-memory-proof",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                last_checkpoint="\n".join(
                    [
                        build_mempalace_writeback_signal(
                            status="wrote",
                            at=writeback_at,
                            scope="Memory Workspace",
                        ),
                        build_mempalace_roundtrip_signal(
                            status="unavailable",
                            at=roundtrip_at,
                            scope="Memory Workspace",
                            detail=(
                                "mempalace_search could not confirm the freshly written handoff "
                                "on this lane."
                            ),
                        ),
                    ]
                ),
            )
        )

        capability_response = client.get("/api/gateway/capability")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert capability["level"] == "warn"
    assert capability["inventory"]["memory_status"] == "warn"
    assert "roundtrip status is 'unavailable'" in capability["inventory"]["memory_summary"]
    assert (
        "confirm the freshly written memory can be recalled"
        in (capability["inventory"]["memory_recommended_action"])
    )
    assert any(
        "mempalace_search could not confirm the freshly written handoff on this lane." in line
        for line in capability["inventory"]["memory_evidence"]
    )
    proof_reference = capability["inventory"]["memory_proof_reference"]
    assert proof_reference["mission_id"] == mission_id
    assert proof_reference["proof_kind"] == "roundtrip"
    assert proof_reference["proof_status"] == "unavailable"
    assert "roundtrip status 'unavailable'" in proof_reference["summary"]


def test_gateway_memory_prove_launches_direct_mission(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        fake_client = FakeMissionRuntimeClient()
        runtime.connected = True
        runtime.initialized = True
        runtime.client = fake_client
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        response = client.post(
            "/api/gateway/memory/prove",
            json={"instance_id": instance_id},
        )

    assert response.status_code == 200, response.text
    mission = response.json()
    assert mission["name"].startswith("MemPalace Direct Proof:")
    assert mission["instance_id"] == instance_id
    assert mission["project_label"] == "Memory Workspace"
    assert mission["thread_id"] == "thread-memory-proof-direct"
    assert mission["max_turns"] == 1
    assert mission["use_builtin_agents"] is False
    assert mission["run_verification"] is False
    assert mission["auto_commit"] is False
    assert mission["allow_auto_reflexes"] is False
    assert mission["auto_recover"] is False
    assert mission["allow_failover"] is False
    assert "MemPalace control-plane proof contract:" in mission["objective"]
    assert fake_client.turn_prompts
    assert "MemPalace control-plane proof contract:" in fake_client.turn_prompts[0]


def test_gateway_capability_prefers_direct_memory_proof_reference(tmp_path) -> None:
    app_settings = Settings(
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "openzues-test.db",
    )
    app = create_app(app_settings)

    with TestClient(app, client=("testclient", 50000)) as client:
        bootstrap_response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Memory Lane",
                "project_path": str(tmp_path),
                "project_label": "Memory Workspace",
                "operator_name": "Memory Builder",
                "use_mempalace": True,
                "task_name": "Memory Ship Loop",
                "objective_template": "Ship the next memory-backed slice.",
            },
        )
        assert bootstrap_response.status_code == 200

        payload = bootstrap_response.json()
        instance_id = payload["instance"]["id"]
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.initialized = True
        runtime.mcp_servers = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
            }
        ]
        runtime.mcp_server_status = [
            {
                "name": "MemPalace MCP Server",
                "source": "mempalace",
                "status": "ready",
                "authStatus": "ready",
                "tools": [
                    "mempalace_status",
                    "mempalace_search",
                    "mempalace_diary_write",
                    "mempalace_diary_read",
                ],
            }
        ]

        memory_task_id = payload["memory_task_blueprint"]["id"]
        database = client.app.state.database
        memory_loop_mission_id = asyncio.run(
            database.create_mission(
                name="MemPalace Memory Loop",
                objective="Refresh durable project memory through MemPalace.",
                status="completed",
                instance_id=instance_id,
                project_id=payload["project"]["id"],
                task_blueprint_id=memory_task_id,
                thread_id="thread-memory-proof",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
            )
        )
        asyncio.run(
            database.update_mission(
                memory_loop_mission_id,
                last_checkpoint="\n".join(
                    [
                        build_mempalace_writeback_signal(
                            status="wrote",
                            at="2026-04-11T15:12:00Z",
                            scope="Memory Workspace",
                        ),
                        build_mempalace_roundtrip_signal(
                            status="verified",
                            at="2026-04-11T15:13:00Z",
                            scope="Memory Workspace",
                            detail="mempalace_search returned the maintenance handoff.",
                        ),
                    ]
                ),
            )
        )

        direct_mission_id = asyncio.run(
            database.create_mission(
                name="MemPalace Direct Proof: Memory Workspace",
                objective="MemPalace control-plane proof contract:",
                status="completed",
                instance_id=instance_id,
                project_id=payload["project"]["id"],
                task_blueprint_id=None,
                thread_id="thread-memory-proof-direct",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=1,
                use_builtin_agents=False,
                run_verification=False,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=False,
                auto_recover=False,
                auto_recover_limit=0,
                reflex_cooldown_seconds=900,
                allow_failover=False,
            )
        )
        asyncio.run(
            database.update_mission(
                direct_mission_id,
                last_checkpoint="\n".join(
                    [
                        build_mempalace_control_plane_proof_signal(
                            status="verified",
                            at="2026-04-11T16:00:00Z",
                            scope="Memory Workspace",
                            detail=(
                                "mempalace_status and mempalace_search both succeeded from the "
                                "backend-triggered proof."
                            ),
                        ),
                        "lane memory tool status: live and callable",
                    ]
                ),
            )
        )

        capability_response = client.get("/api/gateway/capability")

    assert capability_response.status_code == 200
    capability = capability_response.json()
    assert (
        "Last backend-triggered control-plane proof verified live MemPalace access"
        in (capability["inventory"]["memory_summary"])
    )
    assert capability["inventory"]["memory_proof_launchable"] is True
    assert capability["inventory"]["memory_proof_target_instance_id"] == instance_id
    assert capability["inventory"]["memory_proof_launch_label"] == (
        "Run direct memory proof for Memory Workspace"
    )
    proof_reference = capability["inventory"]["memory_proof_reference"]
    assert proof_reference["mission_id"] == direct_mission_id
    assert proof_reference["proof_kind"] == "control_plane"
    assert proof_reference["proof_status"] == "verified"
    assert proof_reference["updated_at"]
    assert "verified backend-triggered MemPalace access" in proof_reference["summary"]
    proof_continuity = capability["inventory"]["memory_proof_continuity"]
    assert proof_continuity["mission_id"] == direct_mission_id
    assert proof_continuity["mission_name"] == "MemPalace Direct Proof: Memory Workspace"
    assert proof_continuity["state"] in {"anchored", "warming", "fragile"}
    assert proof_continuity["summary"]
    assert "mempalace_status and mempalace_search both succeeded" in proof_continuity["anchor"]
    assert proof_continuity["next_handoff"]


def test_dashboard_backfills_gateway_bootstrap_from_existing_quickstart_artifacts(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Backfill Workspace"},
        )
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Backfill Lane",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        client.post(
            "/api/tasks",
            json={
                "name": "Backfill Loop",
                "summary": "Recover the gateway profile from existing state.",
                "objective_template": "Ship the next verified slice.",
                "instance_id": instance_response.json()["id"],
                "project_id": project_response.json()["id"],
                "cadence_minutes": 90,
                "cwd": str(tmp_path),
                "model": "gpt-5.4-mini",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
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
        dashboard_response = client.get("/api/dashboard")
        profile_response = client.get("/api/gateway/bootstrap")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["gateway_bootstrap"]["status"] == "staged"
    assert dashboard["gateway_bootstrap"]["task_blueprint"]["label"] == "Backfill Loop"
    assert dashboard["gateway_bootstrap"]["project"]["label"] == "Backfill Workspace"
    assert dashboard["gateway_bootstrap"]["bootstrap_roles"] == ["node", "operator"]
    assert dashboard["gateway_bootstrap"]["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]

    assert profile_response.status_code == 200
    assert profile_response.json()["task_blueprint"]["label"] == "Backfill Loop"
    assert profile_response.json()["bootstrap_roles"] == ["node", "operator"]
    assert profile_response.json()["bootstrap_scopes"] == [
        "operator.approvals",
        "operator.read",
        "operator.talk.secrets",
        "operator.write",
    ]


def test_dashboard_bootstraps_remote_access_foundations(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/dashboard")

    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["ops_mesh"]["access_posture"]["team_count"] == 1
    assert dashboard["ops_mesh"]["teams"][0]["name"] == "Local Control"
    assert dashboard["ops_mesh"]["operators"][0]["role"] == "owner"
    assert dashboard["ops_mesh"]["remote_requests"] == []
    assert dashboard["control_chat"]["headline"]
    assert dashboard["control_chat"]["input_placeholder"]


def test_control_chat_waits_for_active_mission_instead_of_launching_hardener() -> None:
    active = make_mission_view(
        mission_id=41,
        name="Live Builder",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=7,
        project_label="OpenZues",
    )
    finished = make_mission_view(
        mission_id=42,
        name="Finished Builder",
        status="completed",
        phase="completed",
        project_id=7,
        project_label="OpenZues",
        last_checkpoint="Verified a clean checkpoint and left a handoff.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[active, finished],
        projects=[make_project_view(project_id=7, label="OpenZues")],
        opportunities=[
            {
                "id": "harden-42",
                "kind": "checkpoint_hardener",
                "impact": "high",
                "title": "Harden OpenZues",
                "summary": "Tighten the finished checkpoint.",
                "why_now": "A completed handoff is ready.",
                "action_label": "Load hardener",
                "mission_draft": {
                    "name": "Harden OpenZues",
                    "objective": "Continue from the checkpoint and verify it.",
                    "instance_id": 1,
                    "project_id": 7,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_42",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )

    decision = plan_control_chat("continue building", dashboard)

    assert decision.action_kind == "wait"
    assert decision.mission_id == 41
    assert "Live Builder" in decision.reply
    assert "Harden OpenZues" in decision.reply


def test_control_chat_launches_hardener_when_no_live_loop_is_running() -> None:
    finished = make_mission_view(
        mission_id=52,
        name="ForumForge Slice",
        status="completed",
        phase="completed",
        project_id=9,
        project_label="ForumForge",
        last_checkpoint="Feature shipped and verified.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[finished],
        projects=[make_project_view(project_id=9, label="ForumForge")],
        opportunities=[
            {
                "id": "harden-52",
                "kind": "checkpoint_hardener",
                "impact": "high",
                "title": "Harden ForumForge",
                "summary": "Verify and tighten the checkpoint.",
                "why_now": "The last run already landed a handoff.",
                "action_label": "Load hardener",
                "mission_draft": {
                    "name": "Harden ForumForge",
                    "objective": "Continue from the checkpoint and make it more durable.",
                    "instance_id": 1,
                    "project_id": 9,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_52",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )

    decision = plan_control_chat("continue", dashboard)

    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "harden-52"
    assert decision.mission_payload is not None
    assert decision.mission_payload.name == "Harden ForumForge"


def test_control_chat_status_cites_gateway_doctor_when_posture_needs_repair() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved launch posture has tracked gaps and no launch-ready lane.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is connected, but approvals are still waiting.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view(unresolved_requests=[{"id": "approval-1"}])],
        opportunities=[make_gateway_repair_opportunity()],
    ).model_copy(update={"gateway_capability": gateway_capability})

    decision = plan_control_chat("status", dashboard)

    assert decision.action_kind == "observe"
    assert "Gateway Doctor says: Saved launch posture has tracked gaps" in decision.reply
    assert "Stabilize gateway posture" in decision.reply


def test_control_chat_prefers_gateway_repair_before_hardener_when_posture_needs_repair() -> None:
    finished = make_mission_view(
        mission_id=52,
        name="ForumForge Slice",
        status="completed",
        phase="completed",
        project_id=9,
        project_label="ForumForge",
        last_checkpoint="Feature shipped and verified.",
    )
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning=None,
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[finished],
        projects=[make_project_view(project_id=9, label="ForumForge")],
        opportunities=[
            make_gateway_repair_opportunity(project_id=9),
            {
                "id": "harden-52",
                "kind": "checkpoint_hardener",
                "impact": "high",
                "title": "Harden ForumForge",
                "summary": "Verify and tighten the checkpoint.",
                "why_now": "The last run already landed a handoff.",
                "action_label": "Load hardener",
                "mission_draft": {
                    "name": "Harden ForumForge",
                    "objective": "Continue from the checkpoint and make it more durable.",
                    "instance_id": 1,
                    "project_id": 9,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_52",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            },
        ],
    ).model_copy(update={"gateway_capability": gateway_capability})

    decision = plan_control_chat("continue", dashboard)

    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "gateway-repair"
    assert decision.mission_payload is not None
    assert decision.mission_payload.name == "Stabilize Gateway Posture"
    assert "Gateway Doctor says Connected lanes need repair before launch" in decision.reply


def test_control_chat_stages_gateway_repair_when_saved_lane_is_offline() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved lane is offline, so gateway repair must wait for reconnect.",
        ready_count=0,
        connected_count=0,
        total_count=1,
        warning_count=0,
        offline_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is disconnected from the launch policy.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view(connected=False)],
        opportunities=[make_gateway_repair_opportunity(start_immediately=False)],
    ).model_copy(update={"gateway_capability": gateway_capability})

    decision = plan_control_chat("continue", dashboard)

    assert decision.action_kind == "observe"
    assert decision.opportunity_id == "gateway-repair"
    assert decision.mission_payload is None
    assert "staged `Stabilize gateway posture`" in decision.reply
    assert "offline" in decision.reply


def test_control_chat_builds_new_mission_from_freeform_request() -> None:
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        projects=[make_project_view(project_id=3, label="OpenZues")],
    )

    decision = plan_control_chat(
        "Build a remote notification digest for failed missions and verify the full path",
        dashboard,
    )

    assert decision.action_kind == "create_mission"
    assert decision.mission_payload is not None
    assert decision.mission_payload.instance_id == 1
    assert decision.mission_payload.project_id == 3
    assert decision.mission_payload.start_immediately is True


def test_control_chat_uses_loop_and_frontend_skill_profile_for_open_ended_ui_work() -> None:
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        projects=[make_project_view(project_id=3, label="OpenZues")],
    )

    decision = plan_control_chat(
        (
            "Keep improving the frontend dashboard chat interface until it looks cleaner "
            "and feels polished"
        ),
        dashboard,
    )

    assert decision.action_kind == "create_mission"
    assert decision.mission_payload is not None
    assert decision.mission_payload.reasoning_effort == "high"
    assert decision.mission_payload.max_turns == 8


def test_attention_queue_plans_recovery_from_failed_signal() -> None:
    failed = make_mission_view(
        mission_id=61,
        name="Vault Mesh Finish",
        status="failed",
        phase="failed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint exists",
        last_error="thread not found",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[failed],
        projects=[make_project_view(project_id=11, label="OpenZues")],
        opportunities=[
            {
                "id": "recover-61",
                "kind": "recovery_run",
                "impact": "high",
                "title": "Recover Vault Mesh Finish",
                "summary": "Resume from the failure checkpoint.",
                "why_now": "The failure already has thread context.",
                "action_label": "Recover run",
                "mission_draft": {
                    "name": "Recover Vault Mesh Finish",
                    "objective": "Recover from the failure and verify it.",
                    "instance_id": 1,
                    "project_id": 11,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_61",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            }
        ],
    )
    dashboard = dashboard.model_copy(
        update={
            "radar": build_radar(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
            "launchpad": build_launchpad(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "recover-61"
    assert decision.mission_payload is not None
    assert decision.status == "executed"


def test_attention_queue_prefers_gateway_repair_before_recovery_when_posture_needs_repair() -> None:
    failed = make_mission_view(
        mission_id=61,
        name="Vault Mesh Finish",
        status="failed",
        phase="failed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint exists",
        last_error="thread not found",
    )
    project = make_project_view(project_id=11, label="OpenZues")
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning=None,
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[failed],
        projects=[project],
        opportunities=[
            make_gateway_repair_opportunity(project_id=11),
            {
                "id": "recover-61",
                "kind": "recovery_run",
                "impact": "high",
                "title": "Recover Vault Mesh Finish",
                "summary": "Resume from the failure checkpoint.",
                "why_now": "The failure already has thread context.",
                "action_label": "Recover run",
                "mission_draft": {
                    "name": "Recover Vault Mesh Finish",
                    "objective": "Recover from the failure and verify it.",
                    "instance_id": 1,
                    "project_id": 11,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_61",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            },
        ],
    ).model_copy(
        update={
            "gateway_capability": gateway_capability,
            "radar": build_radar(
                [make_instance_view()],
                [failed],
                [project],
                gateway_capability=gateway_capability,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "gateway-repair"
    assert decision.mission_payload is not None
    assert decision.mission_payload.name == "Stabilize Gateway Posture"
    assert "Gateway Doctor says Connected lanes need repair before launch" in decision.reply


def test_attention_queue_targeted_signal_id_does_not_fall_back_to_gateway_repair() -> None:
    failed = make_mission_view(
        mission_id=61,
        name="Vault Mesh Finish",
        status="failed",
        phase="failed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint exists",
        last_error="thread not found",
    )
    project = make_project_view(project_id=11, label="OpenZues")
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning=None,
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[failed],
        projects=[project],
        opportunities=[
            make_gateway_repair_opportunity(project_id=11),
            {
                "id": "recover-61",
                "kind": "recovery_run",
                "impact": "high",
                "title": "Recover Vault Mesh Finish",
                "summary": "Resume from the failure checkpoint.",
                "why_now": "The failure already has thread context.",
                "action_label": "Recover run",
                "mission_draft": {
                    "name": "Recover Vault Mesh Finish",
                    "objective": "Recover from the failure and verify it.",
                    "instance_id": 1,
                    "project_id": 11,
                    "task_blueprint_id": None,
                    "cwd": "C:/workspace",
                    "thread_id": "thread_61",
                    "model": "gpt-5.4",
                    "reasoning_effort": None,
                    "collaboration_mode": None,
                    "max_turns": 3,
                    "use_builtin_agents": True,
                    "run_verification": True,
                    "auto_commit": False,
                    "pause_on_approval": True,
                    "allow_auto_reflexes": True,
                    "auto_recover": True,
                    "auto_recover_limit": 2,
                    "reflex_cooldown_seconds": 900,
                    "allow_failover": True,
                    "start_immediately": True,
                },
            },
        ],
    ).model_copy(
        update={
            "gateway_capability": gateway_capability,
            "radar": build_radar(
                [make_instance_view()],
                [failed],
                [project],
                gateway_capability=gateway_capability,
            ),
        }
    )
    failed_signal_id = next(
        signal.id for signal in dashboard.radar.signals if signal.id.endswith("-failed")
    )

    decision = plan_attention_queue(dashboard, target_signal_id=failed_signal_id)

    assert decision is not None
    assert decision.signal_id == failed_signal_id
    assert decision.action_kind == "launch_opportunity"
    assert decision.opportunity_id == "recover-61"
    assert "failed cycle already has enough context" in decision.reply


def test_attention_queue_targeted_signal_id_raises_for_unknown_signal() -> None:
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        opportunities=[make_gateway_repair_opportunity()],
    )

    with pytest.raises(
        ValueError,
        match="Attention-queue signal 'missing-signal' is not available right now.",
    ):
        plan_attention_queue(dashboard, target_signal_id="missing-signal")


def test_attention_queue_holds_when_gateway_posture_needs_repair_without_repair_draft() -> None:
    failed = make_mission_view(
        mission_id=61,
        name="Vault Mesh Finish",
        status="failed",
        phase="failed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint exists",
        last_error="thread not found",
    )
    project = make_project_view(project_id=11, label="OpenZues")
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning=None,
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[failed],
        projects=[project],
    ).model_copy(
        update={
            "gateway_capability": gateway_capability,
            "radar": build_radar(
                [make_instance_view()],
                [failed],
                [project],
                gateway_capability=gateway_capability,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "observe"
    assert decision.status == "escalated"
    assert decision.target_label == "Gateway capability has live gaps"
    assert "There is no bounded gateway repair draft attached yet" in decision.reply


def test_attention_queue_stages_gateway_repair_when_saved_lane_is_offline() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved lane is offline, so gateway repair must wait for reconnect.",
        ready_count=0,
        connected_count=0,
        total_count=1,
        warning_count=0,
        offline_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is disconnected from the launch policy.",
    )
    offline_instance = make_instance_view(connected=False)
    dashboard = make_dashboard_view(
        instances=[offline_instance],
        opportunities=[make_gateway_repair_opportunity(start_immediately=False)],
    ).model_copy(
        update={
            "gateway_capability": gateway_capability,
            "radar": build_radar(
                [offline_instance],
                [],
                [],
                gateway_capability=gateway_capability,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "observe"
    assert decision.status == "escalated"
    assert decision.opportunity_id == "gateway-repair"
    assert decision.target_label == "Stabilize gateway posture"
    assert "staged `Stabilize gateway posture`" in decision.reply
    assert "offline" in decision.reply


def test_attention_queue_failed_observation_dedupes_same_failed_cycle(tmp_path) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        mission_id = asyncio.run(
            database.create_mission(
                name="OpenClaw Total Parity Program",
                objective="Recover the parity seam from the saved checkpoint.",
                status="failed",
                instance_id=instance_id,
                project_id=None,
                task_blueprint_id=None,
                thread_id="thread-failed-cycle",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
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
        )
        asyncio.run(
            database.update_mission(
                mission_id,
                phase="failed",
                last_turn_id="turn-failed-once",
                failure_count=1,
                last_error="TimeoutError: Codex runtime failed to start the turn.",
                last_checkpoint="Checkpoint exists.",
            )
        )

        gateway_capability = make_gateway_capability_view(
            level="ready",
            headline="Gateway capability is ready",
            summary="Connected lanes are ready for launch.",
            ready_count=1,
            connected_count=1,
            total_count=1,
            warning_count=0,
            approval_count=0,
            tracked_ready_count=1,
            tracked_gap_count=0,
            route_status="ready",
            route_warning=None,
        )

        def ready_dashboard() -> DashboardView:
            dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
            return dashboard.model_copy(
                update={
                    "gateway_capability": gateway_capability,
                    "radar": build_radar(
                        dashboard.instances,
                        dashboard.missions,
                        dashboard.projects,
                        gateway_capability=gateway_capability,
                    ),
                }
            )

        dashboard = ready_dashboard()
        acted_once = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )

        asyncio.run(
            database.update_mission(
                mission_id,
                last_commentary="Still waiting for a safe follow-up.",
            )
        )

        dashboard = ready_dashboard()
        acted_twice = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted_once is True
    assert acted_twice is False
    assert len(actions) == 1
    assert actions[0]["action_kind"] == "observe"
    assert actions[0]["status"] == "escalated"
    assert "retrying blindly" in (actions[0]["summary"] or "")
    assert len(messages) == 1


def test_control_chat_view_cites_gateway_doctor_when_posture_needs_repair(tmp_path) -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is still waiting on approval.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view(unresolved_requests=[{"id": "approval-1"}])],
        opportunities=[make_gateway_repair_opportunity()],
    ).model_copy(update={"gateway_capability": gateway_capability})

    with make_client(tmp_path) as client:
        view = asyncio.run(client.app.state.control_chat_service.build_view(dashboard))

    assert view.headline == "Chat is steering from Gateway Doctor"
    assert "Connected lanes need repair before launch." in view.summary
    assert view.input_placeholder == "Try: continue, status, or repair the gateway posture"


def test_attention_queue_view_cites_gateway_posture_when_repair_is_needed(tmp_path) -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is still waiting on approval.",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view(unresolved_requests=[{"id": "approval-1"}])],
    ).model_copy(update={"gateway_capability": gateway_capability})

    with make_client(tmp_path) as client:
        view = asyncio.run(
            client.app.state.control_chat_service.build_attention_queue_view(
                dashboard,
                enabled=True,
            )
        )

    assert view.headline == "Attention queue is holding for gateway repair"
    assert "Connected lanes need repair before launch." in view.summary


def test_control_chat_view_hides_stale_failure_and_quiet_messages_for_active_target(
    tmp_path,
) -> None:
    active = make_mission_view(
        mission_id=40,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="reporting",
        in_progress=True,
    )
    dashboard = make_dashboard_view(missions=[active])

    with make_client(tmp_path) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content=(
                    "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                    "draft yet. I held the queue instead of retrying blindly."
                ),
                action_kind="observe",
                mission_id=35,
                target_label="OpenClaw Total Parity Program",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content=(
                    "I nudged `OpenClaw Total Parity Program` into another cycle because the "
                    "lane went quiet without closing the loop."
                ),
                action_kind="run_mission",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content="OpenClaw parity is active and still landing the next checkpoint.",
                action_kind="wait",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
            )
        )

        view = asyncio.run(client.app.state.control_chat_service.build_view(dashboard))

    assert [message.content for message in view.messages] == [
        "OpenClaw parity is active and still landing the next checkpoint."
    ]


def test_control_chat_view_collapses_repeated_identical_messages(tmp_path) -> None:
    dashboard = make_dashboard_view()

    with make_client(tmp_path) as client:
        database = client.app.state.database
        for _ in range(3):
            asyncio.run(
                database.append_control_chat_message(
                    role="assistant",
                    content=(
                        "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                        "draft yet. I held the queue instead of retrying blindly."
                    ),
                    action_kind="observe",
                    mission_id=40,
                    target_label="OpenClaw Total Parity Program",
                )
            )

        view = asyncio.run(client.app.state.control_chat_service.build_view(dashboard))

    assert len(view.messages) == 1
    assert "retrying blindly" in view.messages[0].content


def test_control_chat_view_hides_stale_failure_and_quiet_messages_after_completed_handoff(
    tmp_path,
) -> None:
    completed = make_mission_view(
        mission_id=40,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        in_progress=False,
        last_checkpoint="Completed: the latest parity slice is verified.",
    )
    dashboard = make_dashboard_view(missions=[completed])

    with make_client(tmp_path) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content=(
                    "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                    "draft yet. I held the queue instead of retrying blindly."
                ),
                action_kind="observe",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
            )
        )
        asyncio.run(
            database.append_control_chat_message(
                role="assistant",
                content=(
                    "I nudged `OpenClaw Total Parity Program` into another cycle because the "
                    "lane went quiet without closing the loop."
                ),
                action_kind="run_mission",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
            )
        )

        view = asyncio.run(client.app.state.control_chat_service.build_view(dashboard))

    assert view.messages == []


def test_attention_queue_view_hides_stale_failure_and_quiet_actions_for_active_target(
    tmp_path,
) -> None:
    active = make_mission_view(
        mission_id=40,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="reporting",
        in_progress=True,
    )
    dashboard = make_dashboard_view(missions=[active])

    with make_client(tmp_path) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_attention_queue_action(
                signal_id="mission-40-failed",
                signal_fingerprint="mission-40-failed|failed",
                signal_level="critical",
                action_kind="observe",
                status="escalated",
                mission_id=35,
                target_label="OpenClaw Total Parity Program",
                summary=(
                    "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                    "draft yet. I held the queue instead of retrying blindly."
                ),
            )
        )
        asyncio.run(
            database.append_attention_queue_action(
                signal_id="mission-40-quiet",
                signal_fingerprint="mission-40-quiet|active",
                signal_level="warn",
                action_kind="run_mission",
                status="executed",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
                summary=(
                    "I nudged `OpenClaw Total Parity Program` into another cycle because the "
                    "lane went quiet without closing the loop."
                ),
            )
        )
        asyncio.run(
            database.append_attention_queue_action(
                signal_id="gateway/capability",
                signal_fingerprint="gateway/capability|warn",
                signal_level="warn",
                action_kind="observe",
                status="observed",
                mission_id=None,
                target_label="Gateway capability",
                summary="Gateway Doctor still has one bounded repair left.",
            )
        )

        view = asyncio.run(
            client.app.state.control_chat_service.build_attention_queue_view(
                dashboard,
                enabled=True,
            )
        )

    assert [action.signal_id for action in view.actions] == ["gateway/capability"]


def test_attention_queue_view_hides_stale_failure_and_quiet_actions_after_completed_handoff(
    tmp_path,
) -> None:
    completed = make_mission_view(
        mission_id=40,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        in_progress=False,
        last_checkpoint="Completed: the latest parity slice is verified.",
    )
    dashboard = make_dashboard_view(missions=[completed])

    with make_client(tmp_path) as client:
        database = client.app.state.database
        asyncio.run(
            database.append_attention_queue_action(
                signal_id="mission-40-failed",
                signal_fingerprint="mission-40-failed|failed",
                signal_level="critical",
                action_kind="observe",
                status="escalated",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
                summary=(
                    "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                    "draft yet. I held the queue instead of retrying blindly."
                ),
            )
        )
        asyncio.run(
            database.append_attention_queue_action(
                signal_id="mission-40-quiet",
                signal_fingerprint="mission-40-quiet|active",
                signal_level="warn",
                action_kind="run_mission",
                status="executed",
                mission_id=40,
                target_label="OpenClaw Total Parity Program",
                summary=(
                    "I nudged `OpenClaw Total Parity Program` into another cycle because the "
                    "lane went quiet without closing the loop."
                ),
            )
        )

        view = asyncio.run(
            client.app.state.control_chat_service.build_attention_queue_view(
                dashboard,
                enabled=True,
            )
        )

    assert view.actions == []


def test_attention_queue_view_collapses_repeated_identical_actions(tmp_path) -> None:
    dashboard = make_dashboard_view()

    with make_client(tmp_path) as client:
        database = client.app.state.database
        for _ in range(3):
            asyncio.run(
                database.append_attention_queue_action(
                    signal_id="mission-40-failed",
                    signal_fingerprint="mission-40-failed|failed",
                    signal_level="critical",
                    action_kind="observe",
                    status="escalated",
                    mission_id=40,
                    target_label="OpenClaw Total Parity Program",
                    summary=(
                        "`OpenClaw Total Parity Program` failed, but there is no safe recovery "
                        "draft yet. I held the queue instead of retrying blindly."
                    ),
                )
            )

        view = asyncio.run(
            client.app.state.control_chat_service.build_attention_queue_view(
                dashboard,
                enabled=True,
            )
        )

    assert len(view.actions) == 1
    assert view.actions[0].signal_id == "mission-40-failed"


def test_build_launchpad_keeps_only_freshest_equivalent_checkpoint_hardener() -> None:
    now = datetime.now(UTC)
    newer = make_mission_view(
        mission_id=40,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        project_id=1,
        project_label="OpenZues Workspace",
        thread_id="thread_newer",
        last_checkpoint="Completed the newest parity slice.",
        updated_at=now,
    )
    older = make_mission_view(
        mission_id=35,
        name="OpenClaw Total Parity Program",
        status="paused",
        phase="paused",
        project_id=1,
        project_label="OpenZues Workspace",
        thread_id="thread_older",
        last_checkpoint="Older parity handoff.",
        updated_at=now - timedelta(hours=2),
    )
    project = make_project_view(project_id=1, label="OpenZues Workspace")

    launchpad = build_launchpad([make_instance_view()], [newer, older], [project])

    hardeners = [
        opportunity
        for opportunity in launchpad.opportunities
        if opportunity.kind == "checkpoint_hardener"
    ]
    assert len(hardeners) == 1
    assert hardeners[0].id == "harden-40"


def test_attention_queue_reuses_existing_hardener_instead_of_launching_duplicate() -> None:
    source = make_mission_view(
        mission_id=71,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        project_id=11,
        project_label="OpenZues",
        last_checkpoint="Checkpoint landed.",
    )
    existing = make_mission_view(
        mission_id=72,
        name="Harden OpenZues",
        status="blocked",
        phase="queued",
        project_id=11,
        project_label="OpenZues",
        thread_id="thread_71",
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission "
                "'OpenClaw Total Parity Program'. First read the existing handoff in the "
                "thread, verify what is already true, close the biggest gaps, and leave a "
                "stronger checkpoint with validation."
            )
        }
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[source, existing],
        projects=[make_project_view(project_id=11, label="OpenZues")],
    )
    dashboard = dashboard.model_copy(
        update={
            "radar": build_radar(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
            "launchpad": build_launchpad(
                dashboard.instances,
                dashboard.missions,
                dashboard.projects,
            ),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "run_mission"
    assert decision.mission_id == 72
    assert "reused the existing hardener" in decision.reply


def test_attention_queue_does_not_harden_a_hardener_again() -> None:
    hardener = make_mission_view(
        mission_id=81,
        name="Harden OpenZues Workspace",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="OpenZues Workspace",
        thread_id="thread_source",
        last_checkpoint="Verification is green and the checkpoint is already durable.",
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission "
                "'OpenClaw Total Parity Program'. First read the existing handoff in the "
                "thread, verify what is already true, close the biggest gaps, and leave a "
                "stronger checkpoint with validation."
            )
        }
    )
    dashboard = make_dashboard_view(
        missions=[hardener],
        opportunities=[],
    ).model_copy(
        update={
            "radar": build_radar([], [hardener], []),
        }
    )

    decision = plan_attention_queue(dashboard)

    assert decision is not None
    assert decision.action_kind == "observe"
    assert decision.mission_id == 81
    assert "hardening a hardener again" in decision.reply


def test_attention_queue_escalates_unsafe_orphan_approval_once(tmp_path) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        runtime = client.app.state.manager.instances[instance_id]
        asyncio.run(
            database.upsert_server_request(
                instance_id=instance_id,
                request_id="approval-unsafe",
                thread_id="thread-orphan",
                method="item/commandExecution/requestApproval",
                payload={
                    "command": 'powershell.exe -Command "Remove-Item -Recurse scratch"',
                    "commandActions": [
                        {
                            "type": "unknown",
                            "command": "Remove-Item -Recurse scratch",
                        }
                    ],
                    "availableDecisions": ["accept", "cancel"],
                },
                status="pending",
            )
        )
        runtime.unresolved_requests = asyncio.run(
            database.list_unresolved_server_requests(instance_id)
        )

        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted_once = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted_twice = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(dashboard)
        )
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted_once is True
    assert acted_twice is False
    assert len(actions) == 1
    assert actions[0]["status"] == "escalated"
    assert "surfaced it" in actions[0]["summary"]
    assert messages[-1]["action_kind"] == "observe"


def test_attention_queue_auto_approves_safe_orphan_request(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        manager = client.app.state.manager
        runtime = manager.instances[instance_id]
        asyncio.run(
            database.upsert_server_request(
                instance_id=instance_id,
                request_id="approval-safe",
                thread_id="thread-orphan",
                method="item/commandExecution/requestApproval",
                payload={
                    "command": 'powershell.exe -Command "rg -n \\"ForumForge\\" src"',
                    "commandActions": [
                        {
                            "type": "unknown",
                            "command": 'rg -n "ForumForge" src',
                        }
                    ],
                    "availableDecisions": ["accept", "cancel"],
                },
                status="pending",
            )
        )
        runtime.unresolved_requests = asyncio.run(
            database.list_unresolved_server_requests(instance_id)
        )
        resolved: list[dict[str, object]] = []

        async def fake_resolve(instance_id: int, request_id: str, result: object) -> None:
            resolved.append(
                {
                    "instance_id": instance_id,
                    "request_id": request_id,
                    "result": result,
                }
            )
            await database.resolve_server_request(
                instance_id=instance_id,
                request_id=request_id,
                status="resolved",
            )
            runtime.unresolved_requests = await database.list_unresolved_server_requests(
                instance_id
            )

        monkeypatch.setattr(manager, "resolve_request", fake_resolve)

        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted is True
    assert resolved == [
        {
            "instance_id": instance_id,
            "request_id": "approval-safe",
            "result": "accept",
        }
    ]
    assert len(actions) == 1
    assert actions[0]["action_kind"] == "resolve_request"
    assert actions[0]["status"] == "executed"
    assert "auto-approved" in (actions[0]["summary"] or "")
    assert messages[-1]["action_kind"] == "resolve_request"


def test_attention_queue_targeted_signal_skips_safe_approval_sweep(
    tmp_path,
    monkeypatch,
) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        database = client.app.state.database
        manager = client.app.state.manager
        resolved: list[dict[str, object]] = []
        launched_payloads: list[object] = []
        instance_id = 1
        project_id = 11

        async def fake_resolve(instance_id: int, request_id: str, result: object) -> None:
            resolved.append(
                {
                    "instance_id": instance_id,
                    "request_id": request_id,
                    "result": result,
                }
            )

        async def fake_create(payload) -> MissionView:
            launched_payloads.append(payload)
            return make_mission_view(
                mission_id=91,
                name=payload.name,
                objective=payload.objective,
                status="active",
                phase="thinking",
                instance_id=payload.instance_id,
                project_id=payload.project_id,
                project_label="OpenZues",
                thread_id=payload.thread_id,
                cwd=payload.cwd,
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
            )

        monkeypatch.setattr(manager, "resolve_request", fake_resolve)
        monkeypatch.setattr(client.app.state.control_chat_service.missions, "create", fake_create)

        failed = make_mission_view(
            mission_id=61,
            name="Vault Mesh Finish",
            status="failed",
            phase="failed",
            instance_id=instance_id,
            project_id=project_id,
            project_label="OpenZues",
            last_checkpoint="Checkpoint exists",
            last_error="thread not found",
        )
        project = make_project_view(project_id=project_id, label="OpenZues")
        gateway_capability = make_gateway_capability_view(
            level="warn",
            headline="Gateway capability has live gaps",
            summary="Connected lanes need repair before launch.",
            ready_count=0,
            connected_count=1,
            total_count=1,
            warning_count=1,
            approval_count=1,
            tracked_ready_count=0,
            tracked_gap_count=1,
            route_status="repair",
            route_warning="Saved lane is still waiting on approval.",
        )
        instance = make_instance_view(
            instance_id=instance_id,
            unresolved_requests=[
                {
                    "id": "approval-safe",
                    "method": "item/commandExecution/requestApproval",
                    "payload": {
                        "command": 'powershell.exe -Command "rg -n \\"ForumForge\\" src"',
                        "commandActions": [
                            {
                                "type": "unknown",
                                "command": 'rg -n "ForumForge" src',
                            }
                        ],
                        "availableDecisions": ["accept", "cancel"],
                    },
                }
            ]
        )
        dashboard = make_dashboard_view(
            instances=[instance],
            missions=[failed],
            projects=[project],
            opportunities=[
                make_gateway_repair_opportunity(
                    instance_id=instance_id,
                    project_id=project_id,
                ),
                {
                    "id": "recover-61",
                    "kind": "recovery_run",
                    "impact": "high",
                    "title": "Recover Vault Mesh Finish",
                    "summary": "Resume from the failure checkpoint.",
                    "why_now": "The failure already has thread context.",
                    "action_label": "Recover run",
                    "mission_draft": {
                        "name": "Recover Vault Mesh Finish",
                        "objective": "Recover from the failure and verify it.",
                        "instance_id": instance_id,
                        "project_id": project_id,
                        "task_blueprint_id": None,
                        "cwd": "C:/workspace",
                        "thread_id": "thread_61",
                        "model": "gpt-5.4",
                        "reasoning_effort": None,
                        "collaboration_mode": None,
                        "max_turns": 3,
                        "use_builtin_agents": True,
                        "run_verification": True,
                        "auto_commit": False,
                        "pause_on_approval": True,
                        "allow_auto_reflexes": True,
                        "auto_recover": True,
                        "auto_recover_limit": 2,
                        "reflex_cooldown_seconds": 900,
                        "allow_failover": True,
                        "start_immediately": True,
                    },
                },
            ],
        ).model_copy(
            update={
                "gateway_capability": gateway_capability,
                "radar": build_radar(
                    [instance],
                    [failed],
                    [project],
                    gateway_capability=gateway_capability,
                ),
            }
        )
        failed_signal_id = next(
            signal.id for signal in dashboard.radar.signals if signal.id.endswith("-failed")
        )

        acted = asyncio.run(
            client.app.state.control_chat_service.tick_attention_queue(
                dashboard,
                target_signal_id=failed_signal_id,
            )
        )
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted is True
    assert resolved == []
    assert len(launched_payloads) == 1
    assert len(actions) == 1
    assert actions[0]["signal_id"] == failed_signal_id
    assert actions[0]["action_kind"] == "launch_opportunity"
    assert actions[0]["status"] == "executed"
    assert "failed cycle already has enough context" in (actions[0]["summary"] or "")
    assert messages[-1]["action_kind"] == "launch_opportunity"


def test_attention_queue_pauses_long_stale_mission_to_free_queue(tmp_path) -> None:
    with make_client(tmp_path, attention_queue_enabled=False) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )

        assert instance_response.status_code == 200
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        runtime = client.app.state.manager.instances[instance_id]
        runtime.connected = True
        runtime.threads = [{"id": "thread-hot", "status": {"type": "notLoaded"}}]

        hot_id = asyncio.run(
            database.create_mission(
                name="ForumForge Inbox + Queue Build",
                objective="Keep building the inbox routes until the milestone is durable.",
                status="active",
                instance_id=instance_id,
                project_id=None,
                task_blueprint_id=None,
                thread_id="thread-hot",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
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
        )
        asyncio.run(
            database.update_mission(
                hot_id,
                phase="thinking",
                in_progress=1,
                command_count=4,
                total_tokens=770089,
                last_activity_at=(datetime.now(UTC) - timedelta(minutes=12)).isoformat(),
            )
        )
        queued_id = asyncio.run(
            database.create_mission(
                name="Vault Mesh Finish",
                objective="Continue when the lane is free.",
                status="blocked",
                instance_id=instance_id,
                project_id=None,
                task_blueprint_id=None,
                thread_id=None,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=None,
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
        )
        asyncio.run(
            database.update_mission(
                queued_id,
                phase="queued",
                last_error="Queued behind mission: ForumForge Inbox + Queue Build",
            )
        )

        dashboard = DashboardView.model_validate(client.get("/api/dashboard").json())
        acted = asyncio.run(client.app.state.control_chat_service.tick_attention_queue(dashboard))
        hot = asyncio.run(database.get_mission(hot_id))
        actions = asyncio.run(database.list_attention_queue_actions())
        messages = asyncio.run(database.list_control_chat_messages())

    assert acted is True
    assert hot is not None
    assert hot["status"] == "paused"
    assert hot["in_progress"] == 0
    assert hot["last_checkpoint"].startswith(
        "Auto-yielded the lane after a long run of 770,089 tokens"
    )
    assert actions[0]["action_kind"] == "pause_mission"
    assert actions[0]["status"] == "executed"
    assert "cooled `ForumForge Inbox + Queue Build` into a paused relay" in actions[0]["summary"]
    assert messages[-1]["action_kind"] == "pause_mission"


def test_control_chat_endpoint_persists_wait_messages(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "Sandbox"},
        )

        assert instance_response.status_code == 200
        project_id = project_response.json()["id"]
        database = client.app.state.database

        live_mission_id = asyncio.run(
            database.create_mission(
                name="Live Run",
                objective="Keep building.",
                status="active",
                instance_id=1,
                project_id=project_id,
                task_blueprint_id=None,
                thread_id="thread-live",
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
            )
        )
        asyncio.run(
            database.update_mission(
                live_mission_id,
                in_progress=1,
                phase="executing",
                last_activity_at=datetime.now(UTC).isoformat(),
            )
        )
        completed_mission_id = asyncio.run(
            database.create_mission(
                name="Finished Run",
                objective="Leave a checkpoint.",
                status="completed",
                instance_id=1,
                project_id=project_id,
                task_blueprint_id=None,
                thread_id="thread-done",
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
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
        )
        asyncio.run(
            database.append_mission_checkpoint(
                mission_id=completed_mission_id,
                thread_id="thread-done",
                turn_id="turn-done",
                kind="final_answer",
                summary="Completed the finished slice and verified it.",
            )
        )
        asyncio.run(
            database.update_mission(
                completed_mission_id,
                phase="completed",
                last_checkpoint="Completed the finished slice and verified it.",
                last_activity_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            )
        )

        response = client.post("/api/control-chat", json={"text": "continue building"})
        dashboard_response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_kind"] == "wait"
    assert payload["executed"] is False
    assert "Live Run" in payload["assistant"]["content"]

    dashboard = dashboard_response.json()
    assert [message["role"] for message in dashboard["control_chat"]["messages"][-2:]] == [
        "user",
        "assistant",
    ]
    assert dashboard["control_chat"]["messages"][-1]["action_kind"] == "wait"
    assert len(dashboard["missions"]) == 2


def test_remote_mission_endpoint_requires_api_key(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/remote/missions",
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "start_immediately": False,
            },
        )

    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_remote_management_requires_admin_auth(tmp_path) -> None:
    with make_client(tmp_path, client_host="203.0.113.7") as client:
        response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "owner",
                "issue_api_key": True,
            },
        )

    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_remote_owner_can_manage_teams_with_api_key(tmp_path) -> None:
    with make_client(tmp_path) as local_client:
        issue_response = local_client.post("/api/operators/1/api-key")
        api_key = issue_response.json()["api_key"]
        assert api_key
    with make_client(tmp_path, client_host="203.0.113.7") as remote_client:
        response = remote_client.post(
            "/api/teams",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"name": "Remote Ops"},
        )

    assert response.status_code == 200
    assert response.json()["slug"] == "remote-ops"


def test_remote_mission_rejects_unknown_project(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        api_key = operator_response.json()["api_key"]
        response = client.post(
            "/api/remote/missions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "instance_id": instance_id,
                "project_id": 999,
                "start_immediately": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown project 999"


def test_remote_requests_are_logged_in_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        operator_response = client.post(
            "/api/operators",
            json={
                "name": "Remote Builder",
                "role": "operator",
                "issue_api_key": True,
            },
        )
        api_key = operator_response.json()["api_key"]
        assert api_key
        headers = {"Authorization": f"Bearer {api_key}", "Idempotency-Key": "mission-req-1"}
        mission_response = client.post(
            "/api/remote/missions",
            headers=headers,
            json={
                "name": "Remote launch",
                "objective": "Create a mission from outside the browser.",
                "start_immediately": False,
            },
        )
        task_response = client.post(
            "/api/tasks",
            json={
                "name": "Remote task",
                "summary": "Task launched from a remote operator.",
                "objective_template": "Check the workspace and leave a checkpoint.",
                "instance_id": instance_id,
                "project_id": None,
                "cadence_minutes": None,
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
        task_id = task_response.json()["id"]
        task_remote_response = client.post(
            f"/api/remote/tasks/{task_id}/run",
            headers={"Authorization": f"Bearer {api_key}", "Idempotency-Key": "task-req-1"},
            json={"dry_run": True},
        )
        dashboard_response = client.get("/api/dashboard")

    assert mission_response.status_code == 200
    created_request = mission_response.json()
    assert created_request["status"] == "completed"
    assert created_request["target_kind"] == "mission"
    assert task_remote_response.status_code == 200
    assert task_remote_response.json()["status"] == "dry_run"
    dashboard = dashboard_response.json()
    assert dashboard["missions"][0]["name"] == "Remote launch"
    assert dashboard["ops_mesh"]["access_posture"]["api_key_count"] == 1
    assert dashboard["ops_mesh"]["access_posture"]["recent_remote_request_count"] == 2
    kinds = [request["kind"] for request in dashboard["ops_mesh"]["remote_requests"]]
    assert "mission.create" in kinds
    assert "task.trigger" in kinds


def test_mission_creation_rejects_unknown_project(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        response = client.post(
            "/api/missions",
            json={
                "name": "Ship autonomy loop",
                "objective": "Keep improving the product until the mission runner works.",
                "instance_id": instance_id,
                "project_id": 999,
                "cwd": str(tmp_path),
                "thread_id": None,
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown project 999"


def test_mission_creation_appears_on_dashboard(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Ship autonomy loop",
                "objective": "Keep improving the product until the mission runner works.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": None,
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        dashboard_response = client.get("/api/dashboard")

    assert mission_response.status_code == 200
    created = mission_response.json()
    assert created["status"] == "paused"
    dashboard = dashboard_response.json()
    assert dashboard["missions"][0]["name"] == "Ship autonomy loop"
    assert dashboard["brief"]["focus_mission_id"] == created["id"]


def test_mission_creation_normalizes_explicit_session_key_for_thread_reuse(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        asyncio.run(
            database.create_mission(
                name="Previous explicit session run",
                objective="Keep the explicit session alive.",
                status="completed",
                instance_id=instance_id,
                project_id=None,
                task_blueprint_id=None,
                thread_id="thread_saved",
                session_key="slack:deploy-room",
                conversation_target=None,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=["debugging"],
            )
        )

        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Follow the explicit session",
                "objective": "Continue the prior explicit session without forking it.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": None,
                "session_key": "  Slack:Deploy-Room  ",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )

    assert mission_response.status_code == 200, mission_response.text
    created = mission_response.json()
    assert created["session_key"] == "slack:deploy-room"
    assert created["thread_id"] == "thread_saved"


def test_mission_creation_reuses_default_agent_main_session_alias(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        database = client.app.state.database
        asyncio.run(
            database.create_mission(
                name="Previous default agent run",
                objective="Keep the default agent thread alive.",
                status="completed",
                instance_id=instance_id,
                project_id=None,
                task_blueprint_id=None,
                thread_id="thread_saved",
                session_key="main",
                conversation_target=None,
                cwd=str(tmp_path),
                model="gpt-5.4",
                reasoning_effort=None,
                collaboration_mode=None,
                max_turns=3,
                use_builtin_agents=True,
                run_verification=True,
                auto_commit=False,
                pause_on_approval=True,
                allow_auto_reflexes=True,
                auto_recover=True,
                auto_recover_limit=2,
                reflex_cooldown_seconds=900,
                allow_failover=True,
                toolsets=["debugging"],
            )
        )

        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Follow the default agent session",
                "objective": "Continue the prior default agent session without forking it.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": None,
                "session_key": " main ",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )

    assert mission_response.status_code == 200, mission_response.text
    created = mission_response.json()
    assert created["session_key"] == "agent:main:main"
    assert created["thread_id"] == "thread_saved"


def test_mission_creation_can_enable_swarm_from_api(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Ship with swarm",
                "objective": "Run the native swarm constitution from product through integration.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": None,
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 9,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "allow_auto_reflexes": True,
                "auto_recover": True,
                "auto_recover_limit": 2,
                "reflex_cooldown_seconds": 900,
                "allow_failover": True,
                "swarm_enabled": True,
                "start_immediately": False,
            },
        )
        dashboard_response = client.get("/api/dashboard")

    assert mission_response.status_code == 200
    created = mission_response.json()
    assert created["swarm_enabled"] is True
    assert created["collaboration_mode"] == "swarm_constitution"
    assert created["swarm"]["status"] == "ready"
    assert created["swarm"]["active_role"] == "product_manager"
    dashboard = dashboard_response.json()
    assert dashboard["missions"][0]["swarm_enabled"] is True
    assert dashboard["missions"][0]["swarm"]["active_role"] == "product_manager"


def test_dashboard_index_includes_swarm_launch_controls(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/")
        script_response = client.get("/static/app.js")

    assert response.status_code == 200
    assert script_response.status_code == 200
    assert 'name="swarm_enabled"' in response.text
    assert "Run as swarm" in response.text
    assert "Stage draft" in script_response.text
    assert "Stage as swarm" in script_response.text
    assert "Launch as swarm" in script_response.text
    assert 'launch-opportunity-swarm' in script_response.text


def test_dashboard_index_links_favicon_and_favicon_route_resolves(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/")
        favicon_response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert "favicon.svg" in response.text
    assert favicon_response.status_code == 200
    assert "image/svg+xml" in favicon_response.headers.get("content-type", "")


def test_mission_continuity_endpoint_returns_relay_packet(tmp_path) -> None:
    with make_client(tmp_path) as client:
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        mission_response = client.post(
            "/api/missions",
            json={
                "name": "Continuity probe",
                "objective": "Build a relay-safe mission.",
                "instance_id": instance_id,
                "project_id": None,
                "cwd": str(tmp_path),
                "thread_id": "thread_probe",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 3,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": True,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        mission_id = mission_response.json()["id"]
        continuity_response = client.get(f"/api/missions/{mission_id}/continuity")

    assert continuity_response.status_code == 200
    continuity = continuity_response.json()
    assert continuity["mission_id"] == mission_id
    assert continuity["state"] in {"anchored", "warming", "fragile"}
    assert continuity["relay_prompt"].startswith(
        "You are resuming or taking over an OpenZues mission."
    )


def test_build_radar_prioritizes_operator_risks() -> None:
    now = datetime.now(UTC)
    instance = make_instance_view()
    approval_mission = make_mission_view(
        mission_id=1,
        name="Approval aware",
        status="blocked",
        phase="approval",
        last_error="Waiting for approval: approval/request",
        last_activity_at=(now - timedelta(minutes=2)).isoformat(),
        suggested_action=(
            "Review the approval request and decide whether to let the mission continue."
        ),
    )
    burn_mission = make_mission_view(
        mission_id=2,
        name="Long runner",
        status="active",
        phase="thinking",
        in_progress=True,
        total_tokens=720000,
        last_checkpoint=None,
        last_activity_at=(now - timedelta(minutes=1)).isoformat(),
    )

    radar = build_radar([instance], [approval_mission, burn_mission], [make_project_view()])

    assert radar.posture == "hot"
    signal_ids = [signal.id for signal in radar.signals]
    assert "mission-1-approval" in signal_ids
    assert "mission-2-burn" in signal_ids
    assert radar.signals[0].level == "critical"
    assert any(
        signal.title == "Long runner is on a long run without a handoff" for signal in radar.signals
    )


def test_build_radar_does_not_flag_normal_gpt5_run_as_context_burn() -> None:
    now = datetime.now(UTC)
    radar = build_radar(
        [make_instance_view()],
        [
            make_mission_view(
                mission_id=2,
                name="Long runner",
                status="active",
                phase="thinking",
                in_progress=True,
                total_tokens=72000,
                last_checkpoint=None,
                last_activity_at=(now - timedelta(minutes=1)).isoformat(),
            )
        ],
        [make_project_view()],
    )

    signal_ids = [signal.id for signal in radar.signals]
    assert "mission-2-burn" not in signal_ids


def test_build_radar_flags_quiet_in_progress_thread_earlier() -> None:
    now = datetime.now(UTC)
    mission = make_mission_view(
        mission_id=41,
        name="Thread watcher",
        status="active",
        phase="thinking",
        in_progress=True,
        last_activity_at=(now - timedelta(minutes=1)).isoformat(),
    ).model_copy(
        update={
            "live_telemetry": MissionLiveTelemetryView(
                streaming=False,
                last_thread_event_age_seconds=240,
                summary=(
                    "Mission is marked in progress, but no fresh thread activity "
                    "has landed recently."
                ),
            )
        }
    )

    radar = build_radar([make_instance_view()], [mission], [make_project_view()])

    signal = next(signal for signal in radar.signals if signal.id == "mission-41-thread-quiet")
    assert "live thread went quiet" in signal.title
    assert signal.level == "warn"


def test_build_radar_does_not_flag_streaming_thread_as_quiet() -> None:
    now = datetime.now(UTC)
    mission = make_mission_view(
        mission_id=42,
        name="Streaming runner",
        status="active",
        phase="thinking",
        in_progress=True,
        last_activity_at=(now - timedelta(minutes=12)).isoformat(),
    ).model_copy(
        update={
            "live_telemetry": MissionLiveTelemetryView(
                streaming=True,
                last_thread_event_age_seconds=10,
                recent_event_count_30s=4,
                recent_output_delta_count_30s=2,
                summary="Streaming now with 4 thread events in the last 30s.",
            )
        }
    )

    radar = build_radar([make_instance_view()], [mission], [make_project_view()])

    signal_ids = {signal.id for signal in radar.signals}
    assert "mission-42-thread-quiet" not in signal_ids
    assert "mission-42-quiet" not in signal_ids


def test_build_radar_surfaces_scope_drift_signal() -> None:
    mission = make_mission_view(
        mission_id=5,
        name="Moderation queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        phase="executing",
        in_progress=True,
        current_command=(
            'powershell.exe -Command "Get-Content src\\\\openzues\\\\web\\\\static\\\\app.css"'
        ),
        last_commentary=(
            "Polishing gradients, font weight, and chat bubble spacing before returning "
            "to the queue."
        ),
        total_tokens=24000,
    )

    radar = build_radar([make_instance_view()], [mission], [make_project_view()])

    scope_signal = next(signal for signal in radar.signals if signal.id == "mission-5-scope")
    assert "drifting away from its charter" in scope_signal.title
    assert scope_signal.level in {"warn", "critical"}
    assert "Objective gravity" in scope_signal.detail


def test_build_radar_reports_ready_capacity_when_lane_is_clear() -> None:
    radar = build_radar([make_instance_view()], [], [make_project_view()])

    assert radar.posture == "steady"
    assert any(signal.id == "capacity/idle-connected" for signal in radar.signals)


def test_build_radar_collapses_large_ready_handoff_backlog() -> None:
    now = datetime.now(UTC)
    missions = [
        make_mission_view(
            mission_id=31,
            name="OpenClaw Total Parity Program",
            status="completed",
            phase="completed",
            project_id=5,
            project_label="OpenZues",
            last_checkpoint="Checkpoint ready.",
            last_activity_at=(now - timedelta(minutes=2)).isoformat(),
        ),
        make_mission_view(
            mission_id=32,
            name="Harden OpenZues Workspace",
            status="completed",
            phase="completed",
            project_id=5,
            project_label="OpenZues",
            last_checkpoint="Checkpoint ready.",
            last_activity_at=(now - timedelta(minutes=5)).isoformat(),
        ),
        make_mission_view(
            mission_id=33,
            name="Vault Mesh Finish",
            status="paused",
            phase="paused",
            project_id=5,
            project_label="OpenZues",
            last_checkpoint="Checkpoint ready.",
            last_activity_at=(now - timedelta(minutes=8)).isoformat(),
        ),
    ]

    radar = build_radar([make_instance_view()], missions, [make_project_view()])

    assert radar.posture == "steady"
    assert "ready handoffs are parked in reserve" in radar.summary
    assert any(signal.id == "attention/handoff-backlog" for signal in radar.signals)
    assert not any(signal.id == "mission-31-handoff" for signal in radar.signals)
    backlog = next(signal for signal in radar.signals if signal.id == "attention/handoff-backlog")
    assert "OpenClaw Total Parity Program" in backlog.detail
    assert "Harden OpenZues Workspace" in backlog.detail


def test_build_brief_ignores_passive_queued_recovery_followup() -> None:
    active = make_mission_view(
        mission_id=59,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="thinking",
        in_progress=True,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
    )
    queued_recovery = make_mission_view(
        mission_id=63,
        name="Recover OpenClaw Total Parity Program",
        objective=(
            "Continue the mission 'OpenClaw Total Parity Program' from its existing "
            "thread. Start by reading the last checkpoint and failure context, fix the "
            "blocker, verify the path forward, and leave a cleaner checkpoint when done."
        ),
        status="blocked",
        phase="queued",
        in_progress=False,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
        last_error="Queued behind mission: OpenClaw Total Parity Program",
    )

    brief = build_brief([make_instance_view()], [active, queued_recovery], [make_project_view()])

    assert brief.status == "active"
    assert brief.headline == "1 mission currently running"
    assert brief.focus_mission_id == 59


def test_build_radar_ignores_passive_queued_recovery_followup_signal() -> None:
    active = make_mission_view(
        mission_id=59,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="thinking",
        in_progress=True,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
    )
    queued_recovery = make_mission_view(
        mission_id=63,
        name="Recover OpenClaw Total Parity Program",
        objective=(
            "Continue the mission 'OpenClaw Total Parity Program' from its existing "
            "thread. Start by reading the last checkpoint and failure context, fix the "
            "blocker, verify the path forward, and leave a cleaner checkpoint when done."
        ),
        status="blocked",
        phase="queued",
        in_progress=False,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
        last_error="Queued behind mission: OpenClaw Total Parity Program",
    )

    radar = build_radar([make_instance_view()], [active, queued_recovery], [make_project_view()])

    assert not any(signal.id == "mission-63-queued" for signal in radar.signals)


def test_plan_control_chat_status_ignores_passive_queued_recovery_followup() -> None:
    active = make_mission_view(
        mission_id=59,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="thinking",
        in_progress=True,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
    )
    queued_recovery = make_mission_view(
        mission_id=63,
        name="Recover OpenClaw Total Parity Program",
        objective=(
            "Continue the mission 'OpenClaw Total Parity Program' from its existing "
            "thread. Start by reading the last checkpoint and failure context, fix the "
            "blocker, verify the path forward, and leave a cleaner checkpoint when done."
        ),
        status="blocked",
        phase="queued",
        in_progress=False,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-parity",
        last_error="Queued behind mission: OpenClaw Total Parity Program",
    )
    dashboard = make_dashboard_view(
        instances=[make_instance_view()],
        missions=[active, queued_recovery],
        projects=[make_project_view()],
    )

    plan = plan_control_chat("status", dashboard)

    assert "1 mission(s) are actively running, 0 are blocked" in plan.reply


def test_build_radar_keeps_small_ready_handoff_set_expanded() -> None:
    mission = make_mission_view(
        mission_id=34,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Milestone ready.",
    )

    radar = build_radar([make_instance_view()], [mission], [make_project_view()])

    assert any(signal.id == "mission-34-handoff" for signal in radar.signals)
    assert not any(signal.id == "attention/handoff-backlog" for signal in radar.signals)


def test_build_radar_ignores_historical_handoffs_for_active_lineage() -> None:
    active = make_mission_view(
        mission_id=59,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-live",
    ).model_copy(update={"task_blueprint_id": 2})
    historical = make_mission_view(
        mission_id=55,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-old",
        last_checkpoint="Checkpoint ready.",
    ).model_copy(update={"task_blueprint_id": 2})

    radar = build_radar([make_instance_view()], [active, historical], [make_project_view()])

    assert not any(signal.id == "attention/handoff-backlog" for signal in radar.signals)
    assert not any(signal.id == "mission-55-handoff" for signal in radar.signals)


def test_build_launchpad_ignores_historical_handoffs_for_active_lineage() -> None:
    active = make_mission_view(
        mission_id=59,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-live",
    ).model_copy(update={"task_blueprint_id": 2})
    historical = make_mission_view(
        mission_id=55,
        name="OpenClaw Total Parity Program",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="OpenZues",
        cwd="C:/workspace/openzues",
        thread_id="thread-old",
        last_checkpoint="Checkpoint ready.",
    ).model_copy(update={"task_blueprint_id": 2})

    launchpad = build_launchpad([make_instance_view()], [active, historical], [make_project_view()])

    assert not any(
        opportunity.kind == "checkpoint_hardener"
        for opportunity in launchpad.opportunities
    )


def test_build_launchpad_suggests_workspace_scout_without_projects() -> None:
    launchpad = build_launchpad(
        [make_instance_view()],
        [],
        [],
        preferred_memory_provider="mempalace",
        preferred_executor="workspace_shell",
    )

    assert launchpad.opportunities[0].kind == "workspace_scout"
    assert launchpad.opportunities[0].mission_draft.instance_id == 1
    assert launchpad.opportunities[0].mission_draft.model == "gpt-5.4-mini"
    assert launchpad.opportunities[0].mission_draft.preferred_memory_provider == "mempalace"
    assert launchpad.opportunities[0].mission_draft.preferred_executor == "workspace_shell"


def test_build_launchpad_prioritizes_checkpoint_hardener() -> None:
    mission = make_mission_view(
        mission_id=7,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Implemented the first milestone.",
    )
    project = make_project_view(project_id=5, label="Checkout")

    launchpad = build_launchpad([make_instance_view()], [mission], [project])

    assert launchpad.opportunities[0].kind == "checkpoint_hardener"
    assert launchpad.opportunities[0].mission_draft.thread_id == "thread_7"
    assert launchpad.opportunities[0].mission_draft.project_id == 5


def test_build_launchpad_skips_duplicate_checkpoint_hardener_when_followup_exists() -> None:
    source = make_mission_view(
        mission_id=7,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Implemented the first milestone.",
    )
    existing = make_mission_view(
        mission_id=8,
        name="Harden Checkout",
        status="blocked",
        phase="queued",
        project_id=5,
        project_label="Checkout",
        thread_id="thread_7",
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission 'Ship checkout'. "
                "First read the existing handoff in the thread, verify what is already true, "
                "close the biggest gaps, and leave a stronger checkpoint with validation."
            )
        }
    )
    project = make_project_view(project_id=5, label="Checkout")

    launchpad = build_launchpad([make_instance_view()], [source, existing], [project])

    assert not any(
        opportunity.kind == "checkpoint_hardener" for opportunity in launchpad.opportunities
    )


def test_build_launchpad_suppresses_recently_completed_checkpoint_hardener() -> None:
    now = datetime.now(UTC)
    source = make_mission_view(
        mission_id=7,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Implemented the first milestone.",
        updated_at=now - timedelta(minutes=3),
    )
    completed_followup = make_mission_view(
        mission_id=8,
        name="Harden Checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        thread_id="thread_7",
        updated_at=now - timedelta(minutes=10),
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission 'Ship checkout'. "
                "First read the existing handoff in the thread, verify what is already true, "
                "close the biggest gaps, and leave a stronger checkpoint with validation."
            )
        }
    )
    project = make_project_view(project_id=5, label="Checkout")

    launchpad = build_launchpad([make_instance_view()], [source, completed_followup], [project])

    assert not any(
        opportunity.kind == "checkpoint_hardener" for opportunity in launchpad.opportunities
    )


def test_build_launchpad_relabels_later_checkpoint_hardener_as_optional() -> None:
    now = datetime.now(UTC)
    source = make_mission_view(
        mission_id=7,
        name="Ship checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        last_checkpoint="Implemented the first milestone.",
        updated_at=now - timedelta(minutes=3),
    )
    completed_followup = make_mission_view(
        mission_id=8,
        name="Harden Checkout",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="Checkout",
        thread_id="thread_7",
        updated_at=now - timedelta(hours=2),
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission 'Ship checkout'. "
                "First read the existing handoff in the thread, verify what is already true, "
                "close the biggest gaps, and leave a stronger checkpoint with validation."
            )
        }
    )
    project = make_project_view(project_id=5, label="Checkout")

    launchpad = build_launchpad([make_instance_view()], [source, completed_followup], [project])

    hardener = next(
        opportunity
        for opportunity in launchpad.opportunities
        if opportunity.kind == "checkpoint_hardener"
    )
    assert hardener.action_label == "Load another hardener"
    assert "optional tightening pass" in hardener.summary


def test_build_launchpad_skips_recursive_checkpoint_hardener_for_followup_mission() -> None:
    followup = make_mission_view(
        mission_id=9,
        name="Harden OpenZues Workspace",
        status="completed",
        phase="completed",
        project_id=5,
        project_label="OpenZues Workspace",
        thread_id="thread_source",
        last_checkpoint="Verified the previous checkpoint and tightened the handoff.",
    ).model_copy(
        update={
            "objective": (
                "Continue from the latest checkpoint in the mission "
                "'OpenClaw Total Parity Program'. First read the existing handoff in the "
                "thread, verify what is already true, close the biggest gaps, and leave a "
                "stronger checkpoint with validation."
            )
        }
    )
    project = make_project_view(project_id=5, label="OpenZues Workspace")

    launchpad = build_launchpad([make_instance_view()], [followup], [project])

    assert not any(
        opportunity.kind == "checkpoint_hardener" for opportunity in launchpad.opportunities
    )


def test_build_launchpad_uses_drift_sweep_for_dirty_projects() -> None:
    project = make_project_view(project_id=3, label="OpenZues")
    project.git_status = " M src/openzues/app.py"

    launchpad = build_launchpad([make_instance_view()], [], [project])

    assert any(opportunity.kind == "drift_sweep" for opportunity in launchpad.opportunities)


def test_build_interference_detects_lane_braid() -> None:
    project = make_project_view(project_id=5, label="Checkout")
    first = make_mission_view(
        mission_id=31,
        name="Ship checkout",
        project_id=5,
        project_label="Checkout",
    )
    second = make_mission_view(
        mission_id=32,
        name="Harden checkout",
        instance_id=2,
        project_id=5,
        project_label="Checkout",
    )

    interference = build_interference([first, second], [project], [], [])

    assert interference.headline == "Interference forecast is watchful"
    assert interference.vectors[0].kind == "lane_braid"
    assert interference.vectors[0].mission_ids == [31, 32]


def test_build_interference_flags_checkpoint_eclipse() -> None:
    now = datetime.now(UTC)
    project = make_project_view(project_id=7, label="Atlas")
    anchor = make_mission_view(
        mission_id=41,
        name="Atlas anchor",
        status="completed",
        phase="completed",
        project_id=7,
        project_label="Atlas",
        last_checkpoint="Verified the current milestone.",
        thread_id="thread_anchor",
        updated_at=now - timedelta(minutes=5),
    )
    live = make_mission_view(
        mission_id=42,
        name="Atlas live",
        status="active",
        phase="thinking",
        project_id=7,
        project_label="Atlas",
        thread_id="thread_live",
    )

    interference = build_interference([anchor, live], [project], [], [])

    assert any(vector.kind == "checkpoint_eclipse" for vector in interference.vectors)


def test_build_interference_detects_remote_echo() -> None:
    now = datetime.now(UTC)
    project = make_project_view(project_id=8, label="ForumForge")
    task = make_task_blueprint_view(
        task_id=12,
        name="ForumForge loop",
        project_id=8,
        cadence_minutes=60,
    )
    requests = [
        make_remote_request_view(
            request_id=1,
            operator_id=7,
            target_kind="task",
            target_id=12,
            requested_at=now - timedelta(hours=1),
        ),
        make_remote_request_view(
            request_id=2,
            operator_id=8,
            target_kind="task",
            target_id=12,
            requested_at=now - timedelta(minutes=30),
        ),
    ]

    interference = build_interference([], [project], [task], requests)

    assert any(vector.kind == "remote_echo" for vector in interference.vectors)


def test_build_economy_marks_checkpointed_scope_as_compounding() -> None:
    project = make_project_view(project_id=9, label="Atlas")
    missions = [
        make_mission_view(
            mission_id=51,
            name="Ship Atlas",
            status="completed",
            phase="completed",
            project_id=9,
            project_label="Atlas",
            last_checkpoint="Milestone landed.",
            total_tokens=18000,
            command_count=7,
        ),
        make_mission_view(
            mission_id=52,
            name="Harden Atlas",
            status="paused",
            phase="paused",
            project_id=9,
            project_label="Atlas",
            last_checkpoint="Verified and ready.",
            total_tokens=12000,
            command_count=6,
        ),
    ]
    task = make_task_blueprint_view(
        task_id=20,
        name="Atlas upkeep",
        project_id=9,
        cadence_minutes=180,
    )

    economy = build_economy(missions, [project], [task], [])

    assert economy.headline == "Autonomy economy is compounding"
    assert economy.scopes[0].state == "compounding"
    assert economy.scopes[0].project_id == 9


def test_build_economy_marks_high_burn_scope_as_leaking() -> None:
    project = make_project_view(project_id=10, label="Checkout")
    mission = make_mission_view(
        mission_id=61,
        name="Checkout orbit",
        status="active",
        phase="thinking",
        project_id=10,
        project_label="Checkout",
        total_tokens=760000,
        command_count=18,
        last_checkpoint=None,
    )
    remote_requests = [
        make_remote_request_view(
            request_id=10,
            operator_id=1,
            target_kind="mission",
            target_id=61,
        ),
        make_remote_request_view(
            request_id=11,
            operator_id=2,
            target_kind="mission",
            target_id=61,
            requested_at=datetime.now(UTC) - timedelta(minutes=30),
        ),
        make_remote_request_view(
            request_id=12,
            operator_id=3,
            target_kind="mission",
            target_id=61,
            requested_at=datetime.now(UTC) - timedelta(minutes=10),
        ),
    ]

    economy = build_economy([mission], [project], [], remote_requests)

    assert economy.headline == "Autonomy economy is leaking"
    assert economy.scopes[0].state == "leaking"
    assert "compress" in economy.scopes[0].capital_prompt.lower()


def test_build_economy_docks_scope_drifted_work() -> None:
    project = make_project_view(project_id=11, label="ForumForge")
    aligned = make_mission_view(
        mission_id=71,
        name="Forum queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        project_id=11,
        project_label="ForumForge",
        current_command='powershell.exe -Command "Get-Content src\\\\forumforge\\\\queue.py"',
        last_commentary="Wiring the moderation queue route and verifying the filter logic.",
    )
    drifting = make_mission_view(
        mission_id=72,
        name="Forum queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        project_id=11,
        project_label="ForumForge",
        current_command=(
            'powershell.exe -Command "Get-Content src\\\\openzues\\\\web\\\\static\\\\app.css"'
        ),
        last_commentary="Tuning gradients, shadows, and bubble spacing in the dashboard shell.",
    )

    aligned_economy = build_economy([aligned], [project], [], [])
    drifting_economy = build_economy([drifting], [project], [], [])

    assert (
        aligned_economy.scopes[0].objective_gravity > drifting_economy.scopes[0].objective_gravity
    )
    assert aligned_economy.scopes[0].score > drifting_economy.scopes[0].score


def test_dashboard_and_project_economy_endpoint_surface_scope_profile(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        )
        project_id = project_response.json()["id"]
        instance_response = client.post(
            "/api/instances",
            json={
                "name": "Local Codex Desktop",
                "transport": "desktop",
                "cwd": str(tmp_path),
                "auto_connect": False,
            },
        )
        instance_id = instance_response.json()["id"]
        client.post(
            "/api/missions",
            json={
                "name": "Economy probe",
                "objective": "Land a durable checkpoint.",
                "instance_id": instance_id,
                "project_id": project_id,
                "cwd": str(tmp_path),
                "thread_id": "thread_probe",
                "model": "gpt-5.4",
                "reasoning_effort": None,
                "collaboration_mode": None,
                "max_turns": 2,
                "use_builtin_agents": True,
                "run_verification": True,
                "auto_commit": False,
                "pause_on_approval": True,
                "start_immediately": False,
            },
        )
        dashboard_response = client.get("/api/dashboard")
        economy_response = client.get("/api/economy")
        project_economy_response = client.get(f"/api/projects/{project_id}/economy")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["economy"]["headline"]
    assert economy_response.status_code == 200
    assert economy_response.json()["headline"]
    assert project_economy_response.status_code == 200
    project_economy = project_economy_response.json()
    assert project_economy["scopes"][0]["project_id"] == project_id


def test_dashboard_and_project_interference_endpoint_surface_scope_overlap(tmp_path) -> None:
    with make_client(tmp_path) as client:
        project_response = client.post(
            "/api/projects",
            json={"path": str(tmp_path), "label": "OpenZues Workspace"},
        )
        project_id = project_response.json()["id"]
        for offset in (0, 1):
            client.post(
                "/api/tasks",
                json={
                    "name": f"Overlap {offset}",
                    "summary": "Overlap detector",
                    "objective_template": "Keep the workspace healthy.",
                    "instance_id": 1,
                    "project_id": project_id,
                    "cadence_minutes": 60 + offset * 30,
                    "cwd": str(tmp_path),
                    "model": "gpt-5.4-mini",
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
        dashboard_response = client.get("/api/dashboard")
        project_interference_response = client.get(f"/api/projects/{project_id}/interference")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert any(vector["kind"] == "task_overlap" for vector in dashboard["interference"]["vectors"])
    assert project_interference_response.status_code == 200
    project_interference = project_interference_response.json()
    assert project_interference["vectors"][0]["project_id"] == project_id


def test_build_continuity_prioritizes_fragile_relay_packets() -> None:
    now = datetime.now(UTC)
    fragile = make_mission_view(
        mission_id=21,
        name="Orbiting relay",
        status="active",
        phase="thinking",
        command_count=12,
        turns_completed=1,
        last_checkpoint=None,
        last_activity_at=(now - timedelta(minutes=12)).isoformat(),
    )
    anchored = make_mission_view(
        mission_id=22,
        name="Anchored relay",
        status="paused",
        phase="paused",
        last_checkpoint="Verified milestone and ready for the next thin slice.",
        project_id=3,
        project_label="Atlas",
        last_activity_at=(now - timedelta(minutes=2)).isoformat(),
    )

    continuity = build_continuity(
        [make_instance_view()],
        [fragile, anchored],
        [make_project_view()],
    )

    assert continuity.headline
    assert continuity.packets[0].mission_id == 21
    assert continuity.packets[0].state == "fragile"
    assert continuity.packets[1].state in {"warming", "anchored"}
    assert continuity.packets[0].relay_prompt.startswith(
        "You are resuming or taking over an OpenZues mission."
    )


def test_build_cortex_learns_project_doctrine() -> None:
    project = make_project_view(project_id=4, label="Atlas")
    missions = [
        make_mission_view(
            mission_id=1,
            name="Ship Atlas",
            status="completed",
            project_id=4,
            project_label="Atlas",
            last_checkpoint="Milestone landed.",
            max_turns=4,
            model="gpt-5.4",
        ),
        make_mission_view(
            mission_id=2,
            name="Harden Atlas",
            status="paused",
            project_id=4,
            project_label="Atlas",
            last_checkpoint="Verified and ready.",
            max_turns=4,
            model="gpt-5.4",
        ),
    ]

    cortex = build_cortex([make_instance_view()], missions, [project])

    assert cortex.doctrines
    doctrine = cortex.doctrines[0]
    assert doctrine.project_id == 4
    assert doctrine.recommended_model == "gpt-5.4"
    assert doctrine.recommended_max_turns == 4


def test_build_reflex_deck_arms_scope_realign_for_drifting_mission() -> None:
    mission = make_mission_view(
        mission_id=81,
        name="Moderation queue",
        objective="Build the forum moderation queue end to end.",
        status="active",
        phase="executing",
        in_progress=True,
        current_command=(
            'powershell.exe -Command "Get-Content src\\\\openzues\\\\web\\\\static\\\\app.css"'
        ),
        last_commentary="Polishing gradients and chat bubble spacing in the dashboard shell.",
        total_tokens=18000,
    )

    reflex_deck = build_reflex_deck(
        [make_instance_view()],
        [mission],
        [make_project_view()],
    )

    assert reflex_deck.reflexes[0].kind == "scope_realign"
    assert "charter" in reflex_deck.reflexes[0].title.lower()


def test_build_cortex_surfaces_orbit_and_approval_inoculations() -> None:
    now = datetime.now(UTC)
    instance = make_instance_view(
        unresolved_requests=[{"thread_id": "thread_2", "method": "approval/request"}]
    )
    missions = [
        make_mission_view(
            mission_id=1,
            name="Orbiting",
            status="active",
            phase="thinking",
            in_progress=True,
            command_count=10,
            turns_completed=1,
            last_checkpoint=None,
        ),
        make_mission_view(
            mission_id=2,
            name="Approval gate",
            status="blocked",
            phase="approval",
            last_error="Waiting for approval: approval/request",
            last_activity_at=(now - timedelta(minutes=2)).isoformat(),
        ),
    ]

    cortex = build_cortex([instance], missions, [])

    inoculation_ids = [inoculation.id for inoculation in cortex.inoculations]
    assert "checkpoint-compression" in inoculation_ids
    assert "approval-sentry" in inoculation_ids


def test_build_cortex_surfaces_learning_reviews() -> None:
    project = make_project_view(project_id=7, label="Beacon")
    missions = [
        make_mission_view(
            mission_id=70,
            name="Beacon UI ship",
            status="completed",
            project_id=7,
            project_label="Beacon",
            last_checkpoint="Browser verification passed and the queue handoff is clean.",
            toolsets=["browser", "vision", "debugging", "delegation"],
            run_verification=True,
        ),
        make_mission_view(
            mission_id=71,
            name="Beacon queue hardening",
            status="paused",
            project_id=7,
            project_label="Beacon",
            last_checkpoint="Checkpoint landed after browser-led verification and review.",
            toolsets=["browser", "debugging", "delegation"],
            run_verification=True,
        ),
        make_mission_view(
            mission_id=72,
            name="Beacon drifted loop",
            status="active",
            project_id=7,
            project_label="Beacon",
            command_count=9,
            total_tokens=78000,
            run_verification=False,
            toolsets=["search"],
        ),
    ]

    cortex = build_cortex([make_instance_view()], missions, [project])

    assert cortex.reviews
    assert any(
        review.title == "Promote the winning tool posture for Beacon"
        and "browser" in review.recommended_toolsets
        for review in cortex.reviews
    )
    assert any(
        review.title == "Anchor Beacon with checkpoint-first recovery"
        and "memory" in review.recommended_toolsets
        for review in cortex.reviews
    )
    assert any(
        review.title == "Keep Beacon on proof-first loops"
        and "debugging" in review.recommended_toolsets
        for review in cortex.reviews
    )


def test_cortex_api_returns_review_contract(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/cortex")

        assert response.status_code == 200
        payload = response.json()
        assert "headline" in payload
        assert "doctrines" in payload
        assert "inoculations" in payload
        assert "reviews" in payload


def test_build_launchpad_applies_learned_doctrine_to_ship_slice() -> None:
    project = make_project_view(project_id=9, label="Beacon")
    completed = make_mission_view(
        mission_id=4,
        name="Ship Beacon",
        status="completed",
        project_id=9,
        project_label="Beacon",
        last_checkpoint="A visible milestone shipped.",
        model="gpt-5.4-mini",
        max_turns=3,
        auto_commit=False,
    )

    launchpad = build_launchpad([make_instance_view()], [completed], [project])

    ship_slice = next(
        opportunity for opportunity in launchpad.opportunities if opportunity.kind == "ship_slice"
    )
    assert ship_slice.mission_draft.model == "gpt-5.4-mini"
    assert ship_slice.mission_draft.max_turns == 3
    assert ship_slice.mission_draft.auto_commit is False


def test_build_radar_surfaces_gateway_capability_warning_signal() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved launch posture has tracked gaps and no launch-ready lane.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is connected, but approvals are still waiting.",
    )

    radar = build_radar(
        [make_instance_view(unresolved_requests=[{"id": "approval-1"}])],
        [],
        [],
        gateway_capability=gateway_capability,
    )

    gateway_signal = next(signal for signal in radar.signals if signal.id == "gateway/capability")
    assert gateway_signal.level == "warn"
    assert gateway_signal.title == "Gateway capability has live gaps"
    assert "tracked gaps" in gateway_signal.detail


def test_build_launchpad_prefers_gateway_ready_lanes_and_adds_gateway_repair_opportunity() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is still waiting on approval.",
    )

    launchpad = build_launchpad(
        [make_instance_view(unresolved_requests=[{"id": "approval-1"}])],
        [],
        [make_project_view(project_id=9, label="Beacon")],
        gateway_capability=gateway_capability,
    )

    assert launchpad.headline == "Gateway posture needs repair before broad launches"
    assert launchpad.summary == "Connected lanes need repair before launch."
    assert any(opportunity.kind == "gateway_repair" for opportunity in launchpad.opportunities)
    assert not any(opportunity.kind == "ship_slice" for opportunity in launchpad.opportunities)


def test_build_launchpad_stages_gateway_repair_when_saved_lane_is_offline() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved lane is offline, so gateway repair must wait for reconnect.",
        ready_count=0,
        connected_count=0,
        total_count=1,
        warning_count=0,
        offline_count=1,
        approval_count=0,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is disconnected from the launch policy.",
    )

    launchpad = build_launchpad(
        [make_instance_view(connected=False)],
        [],
        [make_project_view(project_id=9, label="Beacon")],
        gateway_capability=gateway_capability,
    )

    repair = next(
        opportunity
        for opportunity in launchpad.opportunities
        if opportunity.id == "gateway-repair"
    )
    assert launchpad.headline == "Gateway posture needs repair before broad launches"
    assert repair.kind == "gateway_repair"
    assert repair.mission_draft.instance_id == 1
    assert repair.mission_draft.start_immediately is False
    assert "saved lane posture" in repair.summary.lower()


def test_build_launchpad_does_not_treat_busy_lane_as_idle_capacity() -> None:
    active = make_mission_view(
        mission_id=35,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="reporting",
        instance_id=2,
        project_id=1,
        project_label="OpenZues Workspace",
    )

    launchpad = build_launchpad(
        [make_instance_view(instance_id=2)],
        [active],
        [make_project_view(project_id=2, label="OpenClaw Source")],
    )

    assert launchpad.headline == "Connected lanes are already busy"
    assert "already occupied by active missions" in launchpad.summary
    assert launchpad.opportunities == []


def test_build_launchpad_queues_gateway_repair_when_only_connected_lane_is_busy() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Connected lanes need repair before launch.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        approval_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is still waiting on approval.",
    )
    active = make_mission_view(
        mission_id=44,
        name="OpenClaw Total Parity Program",
        status="active",
        phase="executing",
        instance_id=1,
        project_id=9,
        project_label="Beacon",
    )

    launchpad = build_launchpad(
        [make_instance_view(instance_id=1, unresolved_requests=[{"id": "approval-1"}])],
        [active],
        [make_project_view(project_id=9, label="Beacon")],
        gateway_capability=gateway_capability,
    )

    repair = next(
        opportunity
        for opportunity in launchpad.opportunities
        if opportunity.id == "gateway-repair"
    )
    assert repair.kind == "gateway_repair"
    assert repair.mission_draft.instance_id == 1
    assert repair.mission_draft.start_immediately is False
    assert "active mission yields" in repair.summary.lower()


def test_build_interference_surfaces_gateway_posture_vector() -> None:
    gateway_capability = make_gateway_capability_view(
        level="warn",
        headline="Gateway capability has live gaps",
        summary="Saved launch posture has tracked gaps and no launch-ready lane.",
        ready_count=0,
        connected_count=1,
        total_count=1,
        warning_count=1,
        tracked_ready_count=0,
        tracked_gap_count=1,
        route_status="repair",
        route_warning="Saved lane is disconnected from the launch policy.",
    )

    interference = build_interference(
        [],
        [],
        [],
        [],
        gateway_capability=gateway_capability,
    )

    gateway_vector = next(
        vector for vector in interference.vectors if vector.kind == "gateway_posture"
    )
    assert gateway_vector.level == "warn"
    assert gateway_vector.scope_label == "Local Codex Desktop"
    assert "Gateway capability has live gaps" in gateway_vector.summary
    assert "Saved lane is disconnected" in gateway_vector.treaty_prompt


def test_build_reflex_deck_creates_checkpoint_reflex_for_orbiting_mission() -> None:
    mission = make_mission_view(
        mission_id=12,
        name="Orbiting builder",
        status="active",
        phase="thinking",
        in_progress=True,
        command_count=11,
        turns_completed=1,
        project_id=2,
        project_label="Atlas",
    )
    project = make_project_view(project_id=2, label="Atlas")

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [project])

    assert reflex_deck.reflexes
    reflex = reflex_deck.reflexes[0]
    assert reflex.kind == "checkpoint_now"
    assert reflex.mission_id == 12
    assert "Stop expanding scope." in reflex.prompt


def test_build_reflex_deck_arms_thread_heartbeat_for_quiet_in_progress_run() -> None:
    mission = make_mission_view(
        mission_id=52,
        name="Quiet thread",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=2,
        project_label="Atlas",
    ).model_copy(
        update={
            "live_telemetry": MissionLiveTelemetryView(
                streaming=False,
                last_thread_event_age_seconds=240,
                summary=(
                    "Mission is marked in progress, but no fresh thread activity "
                    "has landed recently."
                ),
            )
        }
    )

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [make_project_view()])

    reflex = next(reflex for reflex in reflex_deck.reflexes if reflex.mission_id == 52)
    assert reflex.kind == "heartbeat_nudge"
    assert "quiet live thread" in reflex.title.lower()


def test_build_reflex_deck_skips_thread_heartbeat_for_streaming_run() -> None:
    mission = make_mission_view(
        mission_id=53,
        name="Streaming thread",
        status="active",
        phase="executing",
        in_progress=True,
        project_id=2,
        project_label="Atlas",
    ).model_copy(
        update={
            "live_telemetry": MissionLiveTelemetryView(
                streaming=True,
                last_thread_event_age_seconds=15,
                recent_output_delta_count_30s=3,
                summary="Streaming now with 3 thread events in the last 30s.",
            )
        }
    )

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [make_project_view()])

    assert not any(reflex.mission_id == 53 for reflex in reflex_deck.reflexes)


def test_build_reflex_deck_offers_resume_reflex_for_paused_checkpoint() -> None:
    mission = make_mission_view(
        mission_id=13,
        name="Paused hardener",
        status="paused",
        phase="paused",
        project_id=5,
        project_label="Beacon",
        last_checkpoint="Verified the first slice.",
    )
    project = make_project_view(project_id=5, label="Beacon")

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [project])

    assert any(reflex.kind == "resume_handoff" for reflex in reflex_deck.reflexes)


def test_build_reflex_deck_surfaces_swarm_conflict_resolution() -> None:
    mission = make_mission_view(
        mission_id=71,
        name="Swarm conflict",
        status="blocked",
        phase="swarm_conflict",
        project_id=9,
        project_label="OpenZues",
        last_error=(
            "Swarm conflict: Backend and frontend ownership overlap on "
            "`src/openzues/app.py`."
        ),
        swarm=MissionSwarmRuntimeView(
            run_id="swarm-run-71",
            status="conflicted",
            stage_index=5,
            active_role="frontend_engineer",
            completed_roles=[
                "product_manager",
                "architect",
                "test_engineer",
                "backend_engineer",
            ],
            pending_roles=[
                "frontend_engineer",
                "security_auditor",
                "refactorer",
                "integration_tester",
            ],
            conflict=MissionSwarmConflictView(
                reason="ownership_overlap",
                summary="Backend and frontend ownership overlap on `src/openzues/app.py`.",
                roles=["backend_engineer", "frontend_engineer"],
                prompt="Reconcile the shared app seam and re-emit a structured JSON payload.",
            ),
        ),
    )
    project = make_project_view(project_id=9, label="OpenZues")

    reflex_deck = build_reflex_deck([make_instance_view()], [mission], [project])

    reflex = next(reflex for reflex in reflex_deck.reflexes if reflex.mission_id == 71)
    assert reflex.kind == "scope_realign"
    assert "swarm conflict" in reflex.title.lower()
    assert "structured json payload" in reflex.prompt.lower()


def test_build_dream_deck_surfaces_ready_project_memory_pass() -> None:
    project = make_project_view(project_id=8, label="OpenZues")
    missions = [
        make_mission_view(
            mission_id=31,
            name="Ship OpenZues",
            status="completed",
            phase="completed",
            project_id=8,
            project_label="OpenZues",
            last_checkpoint="Mission control shipped a stable relay lane.",
            max_turns=4,
            model="gpt-5.4",
        ),
        make_mission_view(
            mission_id=32,
            name="Harden OpenZues",
            status="paused",
            phase="paused",
            project_id=8,
            project_label="OpenZues",
            last_checkpoint="Autonomy radar now highlights operator risks earlier.",
            max_turns=4,
            model="gpt-5.4",
        ),
    ]

    deck = build_dream_deck(
        [make_instance_view()],
        missions,
        [project],
        preferred_memory_provider="mempalace",
        preferred_executor="workspace_shell",
    )

    assert deck.dreams
    dream = deck.dreams[0]
    assert dream.project_id == 8
    assert dream.status == "ready"
    assert dream.mission_draft.project_id == 8
    assert dream.mission_draft.preferred_memory_provider == "mempalace"
    assert dream.mission_draft.preferred_executor == "workspace_shell"
    assert dream.memory_prompt.startswith("# Dream: OpenZues Project Consolidation")


def test_build_dream_deck_stays_empty_without_project_signal() -> None:
    deck = build_dream_deck([make_instance_view()], [], [make_project_view()])

    assert deck.dreams == []
    assert deck.headline == "No dream candidates yet"


def test_hermes_doctor_api_reports_sections(tmp_path: Path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    write_fake_hermes_file(hermes_root, "plugins/memory/mem0/__init__.py")
    write_fake_hermes_file(hermes_root, "gateway/platforms/telegram.py")
    write_fake_hermes_file(hermes_root, "gateway/platforms/webhook.py")
    write_fake_hermes_file(hermes_root, "acp_adapter/server.py")
    write_fake_hermes_file(hermes_root, "hermes_cli/curses_ui.py")

    with make_client(tmp_path, hermes_source_path=hermes_root) as client:
        payload = client.get("/api/hermes/doctor").json()
        update_payload = client.get("/api/runtime/update").json()

    assert payload["headline"]
    assert "profile" in payload
    assert "promotion_loop" in payload
    assert "memory" in payload
    assert any(item["label"] == "Mem0" for item in payload["memory"]["items"])
    assert "executors" in payload
    assert "plugins" in payload
    assert "delivery" in payload
    assert any(item["label"] == "Gateway API + Webhooks" for item in payload["delivery"]["items"])
    assert "acp" in payload
    assert "updates" in payload
    assert update_payload["headline"]


def test_hermes_profile_update_persists_saved_defaults(tmp_path: Path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    write_fake_hermes_file(hermes_root, "plugins/memory/mem0/__init__.py")

    with make_client(tmp_path, hermes_source_path=hermes_root) as client:
        response = client.put(
            "/api/hermes/profile",
            json={
                "preferred_memory_provider": "mem0",
                "preferred_executor": "workspace_shell",
                "learning_autopromote_enabled": False,
                "plugin_discovery_enabled": False,
                "channel_inventory_enabled": False,
                "acp_inventory_enabled": False,
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["preferred_memory_provider"] == "mem0"
        assert payload["preferred_executor"] == "workspace_shell"
        assert payload["learning_autopromote_enabled"] is False
        assert payload["plugin_discovery_enabled"] is False
        assert payload["channel_inventory_enabled"] is False
        assert payload["acp_inventory_enabled"] is False

        fetched = client.get("/api/hermes/profile")
        assert fetched.status_code == 200
        refetched = fetched.json()
        assert refetched["preferred_memory_provider"] == "mem0"
        assert refetched["preferred_executor"] == "workspace_shell"


def test_hermes_profile_shapes_bootstrap_launch_draft(tmp_path: Path) -> None:
    hermes_root = tmp_path / "hermes-agent-main"
    write_fake_hermes_file(hermes_root, "plugins/memory/mem0/__init__.py")

    with make_client(tmp_path, hermes_source_path=hermes_root) as client:
        profile_response = client.put(
            "/api/hermes/profile",
            json={
                "preferred_memory_provider": "mem0",
                "preferred_executor": "workspace_shell",
            },
        )
        assert profile_response.status_code == 200

        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Hermes Lane",
                "project_path": str(tmp_path),
                "project_label": "Hermes Workspace",
                "operator_name": "Hermes Builder",
                "task_name": "Hermes Ship Loop",
                "objective_template": "Ship the next verified Hermes slice.",
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["mission_draft"]["preferred_memory_provider"] == "mem0"
        assert payload["mission_draft"]["preferred_executor"] == "workspace_shell"
        assert payload["mission_draft"]["preferred_memory_provider_label"] == "Mem0"
        assert payload["mission_draft"]["preferred_executor_label"] == "Workspace Shell Profile"
        assert (
            "Preferred executor profile: Workspace Shell Profile."
            in (payload["mission_draft"]["objective"])
        )
        assert "Preferred memory provider: Mem0." in payload["mission_draft"]["objective"]

        dashboard = client.get("/api/dashboard").json()
        assert "memory Mem0" in dashboard["gateway_bootstrap"]["launch_defaults_summary"]
        assert (
            "executor Workspace Shell Profile"
            in (dashboard["gateway_bootstrap"]["launch_defaults_summary"])
        )


def test_docker_executor_marks_launch_route_for_repair(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "openzues.services.hermes_runtime_profile.shutil.which",
        lambda _command: None,
    )

    with make_client(tmp_path) as client:
        profile_response = client.put(
            "/api/hermes/profile",
            json={"preferred_executor": "docker"},
        )
        assert profile_response.status_code == 200

        response = client.post(
            "/api/onboarding/bootstrap",
            json={
                "setup_mode": "local",
                "setup_flow": "quickstart",
                "instance_mode": "create_desktop",
                "instance_name": "Docker Lane",
                "project_path": str(tmp_path),
                "project_label": "Docker Workspace",
                "operator_name": "Docker Builder",
                "task_name": "Docker Ship Loop",
                "objective_template": "Stage the next backend-ready slice.",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["launch_route"]["status"] == "repair"
        assert "docker" in payload["launch_route"]["summary"].lower()

        dashboard = client.get("/api/dashboard").json()

    assert dashboard["gateway_bootstrap"]["launch_route"]["status"] == "repair"
    assert "docker" in dashboard["gateway_bootstrap"]["launch_route"]["summary"].lower()
