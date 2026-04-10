from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TransportType = Literal["desktop", "stdio", "websocket"]
PlaybookKind = Literal["command", "turn", "thread_turn", "review"]
DiagnosticStatus = Literal["ok", "warn", "fail", "info"]
MissionStatus = Literal["active", "paused", "blocked", "completed", "failed"]
SignalLevel = Literal["critical", "warn", "ready", "info"]
SignalLane = Literal["attention", "throughput", "reliability", "capacity"]


class InstanceCreate(BaseModel):
    name: str
    transport: TransportType = "desktop"
    command: str | None = None
    args: str | None = None
    websocket_url: str | None = None
    cwd: str | None = None
    auto_connect: bool = False


class InstanceView(BaseModel):
    id: int
    name: str
    transport: TransportType
    command: str | None
    args: str | None
    websocket_url: str | None
    cwd: str | None
    auto_connect: bool
    connected: bool
    resolved_transport: Literal["stdio", "websocket"] | None = None
    resolved_command: str | None = None
    resolved_args: str | None = None
    transport_note: str | None = None
    pid: int | None = None
    error: str | None = None
    initialized: bool = False
    client_user_agent: str | None = None
    auth_state: dict[str, Any] | None = None
    models: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_modes: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    apps: list[dict[str, Any]] = Field(default_factory=list)
    plugins: list[dict[str, Any]] = Field(default_factory=list)
    mcp_servers: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] | None = None
    threads: list[dict[str, Any]] = Field(default_factory=list)
    loaded_thread_ids: list[str] = Field(default_factory=list)
    unresolved_requests: list[dict[str, Any]] = Field(default_factory=list)
    last_event_at: str | None = None


class ProjectCreate(BaseModel):
    path: str
    label: str | None = None


class ProjectView(BaseModel):
    id: int
    path: str
    label: str
    exists: bool
    is_git_repo: bool
    branch: str | None = None
    git_status: str | None = None
    recent_commits: list[dict[str, Any]] = Field(default_factory=list)
    pull_requests: list[dict[str, Any]] = Field(default_factory=list)
    last_scan_at: str | None = None


class ThreadCreate(BaseModel):
    model: str = "gpt-5.4"
    cwd: str | None = None
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None


class TurnCreate(BaseModel):
    thread_id: str
    text: str
    cwd: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None


class CommandCreate(BaseModel):
    command: list[str]
    cwd: str | None = None
    timeout_ms: int | None = 10000
    tty: bool = False


class ReviewCreate(BaseModel):
    thread_id: str


class RequestResolution(BaseModel):
    result: Any


class EventView(BaseModel):
    id: int
    instance_id: int | None
    thread_id: str | None
    method: str
    payload: dict[str, Any]
    created_at: datetime


class PlaybookCreate(BaseModel):
    name: str
    description: str | None = None
    kind: PlaybookKind
    template: str
    instance_id: int | None = None
    cwd: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None
    timeout_ms: int | None = 10000
    thread_id: str | None = None


class PlaybookView(PlaybookCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class PlaybookRun(BaseModel):
    instance_id: int | None = None
    cwd: str | None = None
    thread_id: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)


class PlaybookRunResult(BaseModel):
    kind: PlaybookKind
    rendered_template: str
    resolved_instance_id: int
    resolved_cwd: str | None = None
    thread_id: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class DiagnosticCheck(BaseModel):
    key: str
    label: str
    status: DiagnosticStatus
    detail: str
    value: str | None = None
    action: str | None = None


class DiagnosticsView(BaseModel):
    checks: list[DiagnosticCheck]
    checked_at: str


class MissionCreate(BaseModel):
    name: str
    objective: str
    instance_id: int
    project_id: int | None = None
    cwd: str | None = None
    thread_id: str | None = None
    model: str = "gpt-5.4"
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None
    max_turns: int | None = Field(default=None, ge=1)
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = True
    pause_on_approval: bool = True
    start_immediately: bool = True


class MissionCheckpointView(BaseModel):
    id: int
    mission_id: int
    thread_id: str | None = None
    turn_id: str | None = None
    kind: str
    summary: str
    created_at: datetime


class MissionView(BaseModel):
    id: int
    name: str
    objective: str
    status: MissionStatus
    instance_id: int
    instance_name: str | None = None
    project_id: int | None = None
    project_label: str | None = None
    thread_id: str | None = None
    cwd: str | None = None
    model: str
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None
    max_turns: int | None = None
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = True
    pause_on_approval: bool = True
    in_progress: bool = False
    phase: str | None = None
    current_command: str | None = None
    command_count: int = 0
    total_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    last_commentary: str | None = None
    suggested_action: str | None = None
    turns_started: int = 0
    turns_completed: int = 0
    failure_count: int = 0
    last_turn_id: str | None = None
    last_error: str | None = None
    last_checkpoint: str | None = None
    last_activity_at: str | None = None
    checkpoints: list[MissionCheckpointView] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DashboardBriefView(BaseModel):
    status: Literal["idle", "active", "blocked", "mixed"]
    headline: str
    summary: str
    focus_mission_id: int | None = None
    next_actions: list[str] = Field(default_factory=list)


class DashboardSignalView(BaseModel):
    id: str
    lane: SignalLane
    level: SignalLevel
    title: str
    detail: str
    action: str | None = None
    mission_id: int | None = None
    instance_id: int | None = None
    freshness_minutes: int | None = None


class DashboardRadarView(BaseModel):
    posture: Literal["steady", "watch", "hot"]
    summary: str
    signals: list[DashboardSignalView] = Field(default_factory=list)


class DashboardView(BaseModel):
    brief: DashboardBriefView
    radar: DashboardRadarView
    instances: list[InstanceView]
    missions: list[MissionView]
    projects: list[ProjectView]
    playbooks: list[PlaybookView]
    events: list[EventView]
