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
LaunchImpact = Literal["high", "medium", "low"]
ContinuityState = Literal["anchored", "warming", "fragile"]
LaunchKind = Literal[
    "workspace_scout",
    "ship_slice",
    "drift_sweep",
    "checkpoint_hardener",
    "recovery_run",
    "shadow_scout",
]
ReflexKind = Literal[
    "checkpoint_now",
    "verification_spike",
    "heartbeat_nudge",
    "recovery_triangle",
    "resume_handoff",
]


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
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = Field(default=2, ge=0)
    reflex_cooldown_seconds: int = Field(default=900, ge=60)
    allow_failover: bool = True
    start_immediately: bool = True


class MissionDraftView(MissionCreate):
    pass


class MissionReflexRun(BaseModel):
    kind: ReflexKind
    title: str
    prompt: str


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
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = 2
    reflex_cooldown_seconds: int = 900
    allow_failover: bool = True
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
    last_reflex_kind: str | None = None
    last_reflex_at: str | None = None
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


class DashboardOpportunityView(BaseModel):
    id: str
    kind: LaunchKind
    impact: LaunchImpact
    title: str
    summary: str
    why_now: str
    action_label: str = "Load draft"
    mission_draft: MissionDraftView


class DashboardLaunchpadView(BaseModel):
    headline: str
    summary: str
    opportunities: list[DashboardOpportunityView] = Field(default_factory=list)


class DashboardContinuityPacketView(BaseModel):
    id: str
    mission_id: int
    mission_name: str
    project_label: str | None = None
    state: ContinuityState
    score: int = Field(ge=0, le=100)
    freshness_minutes: int | None = None
    drift_signatures: list[str] = Field(default_factory=list)
    summary: str
    anchor: str
    drift: str
    next_handoff: str
    relay_prompt: str


class DashboardContinuityView(BaseModel):
    headline: str
    summary: str
    packets: list[DashboardContinuityPacketView] = Field(default_factory=list)


class DashboardDoctrineView(BaseModel):
    id: str
    project_id: int | None = None
    project_label: str
    confidence: Literal["forming", "solid", "strong"]
    summary: str
    rationale: str
    mission_count: int = 0
    checkpoint_count: int = 0
    unstable_count: int = 0
    recommended_model: str
    recommended_max_turns: int | None = None
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = True
    pause_on_approval: bool = True


class DashboardInoculationView(BaseModel):
    id: str
    level: SignalLevel
    title: str
    summary: str
    prescription: str
    project_id: int | None = None
    mission_id: int | None = None


class DashboardCortexView(BaseModel):
    headline: str
    summary: str
    doctrines: list[DashboardDoctrineView] = Field(default_factory=list)
    inoculations: list[DashboardInoculationView] = Field(default_factory=list)


class DashboardReflexView(BaseModel):
    id: str
    kind: ReflexKind
    level: SignalLevel
    mission_id: int
    mission_name: str
    project_label: str | None = None
    title: str
    summary: str
    prompt: str
    action_label: str = "Fire reflex"


class DashboardReflexDeckView(BaseModel):
    headline: str
    summary: str
    reflexes: list[DashboardReflexView] = Field(default_factory=list)


class DashboardView(BaseModel):
    brief: DashboardBriefView
    launchpad: DashboardLaunchpadView
    radar: DashboardRadarView
    continuity: DashboardContinuityView
    cortex: DashboardCortexView
    reflex_deck: DashboardReflexDeckView
    instances: list[InstanceView]
    missions: list[MissionView]
    projects: list[ProjectView]
    playbooks: list[PlaybookView]
    events: list[EventView]
