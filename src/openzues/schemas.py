from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TransportType = Literal["desktop", "stdio", "websocket"]
PlaybookKind = Literal["command", "turn", "thread_turn", "review"]
PlaybookStatus = Literal["completed", "failed"]
DiagnosticStatus = Literal["ok", "warn", "fail", "info"]
MissionStatus = Literal["active", "paused", "blocked", "completed", "failed"]
SignalLevel = Literal["critical", "warn", "ready", "info"]
SignalLane = Literal["attention", "throughput", "reliability", "capacity"]
LaunchImpact = Literal["high", "medium", "low"]
ContinuityState = Literal["anchored", "warming", "fragile"]
ScopeDriftLevel = Literal["aligned", "watch", "drifting", "critical"]
DreamStatus = Literal["forming", "ready", "fresh"]
EconomyState = Literal["compounding", "balanced", "speculative", "leaking", "hibernating"]
TaskStatus = Literal["idle", "due", "running", "attention", "completed", "disabled"]
NotificationRouteKind = Literal[
    "webhook",
    "slack",
    "telegram",
    "discord",
    "whatsapp",
    "zalo",
    "matrix",
]
NotificationRouteViewKind = Literal[
    "webhook",
    "slack",
    "telegram",
    "discord",
    "whatsapp",
    "zalo",
    "matrix",
    "session",
    "announce",
]
GatewayBootstrapStatus = Literal["unconfigured", "staged", "ready", "degraded"]
GatewayRouteBindingMode = Literal["saved_lane", "workspace_affinity"]
SetupRecommendedAction = Literal["bootstrap", "keep", "modify", "reset"]
SetupResetScope = Literal["config", "config+creds+sessions", "full"]
SetupMode = Literal["local", "remote"]
SetupFlow = Literal["quickstart", "advanced"]
SetupWizardStatus = Literal["unconfigured", "staged", "ready"]
LaunchRouteStatus = Literal["ready", "staged", "repair"]
LaunchRouteBindingMode = Literal["task_lane", "saved_lane", "workspace_affinity"]
LaunchRoutePolicy = Literal["main", "session"]
ConversationTargetPeerKind = Literal["direct", "group", "channel"]
LaunchRouteMatch = Literal[
    "task.instance",
    "gateway.preferred_instance",
    "workspace.last_route",
    "workspace.project_lane",
    "workspace.connected_lane",
    "workspace.saved_lane",
    "unavailable",
]
LaunchKind = Literal[
    "workspace_scout",
    "ship_slice",
    "drift_sweep",
    "checkpoint_hardener",
    "recovery_run",
    "shadow_scout",
    "gateway_repair",
]
ReflexKind = Literal[
    "checkpoint_now",
    "verification_spike",
    "heartbeat_nudge",
    "recovery_triangle",
    "resume_handoff",
    "scope_realign",
]
IntegrationAuthStatus = Literal["satisfied", "missing", "degraded"]
IntegrationInventorySourceKind = Literal[
    "integration",
    "app",
    "plugin",
    "mcp_server",
    "capability",
]
IntegrationInventoryReadiness = Literal[
    "ready",
    "auth_gap",
    "lane_gap",
    "degraded",
    "observed",
    "disabled",
]
LaneCapabilityStatus = Literal["ready", "auth_gap", "missing", "offline", "degraded", "disabled"]
OperatorRole = Literal["owner", "admin", "operator", "viewer"]
RemoteRequestKind = Literal["mission.create", "task.trigger"]
RemoteRequestStatus = Literal["accepted", "completed", "failed", "denied", "dry_run"]
BootstrapInstanceMode = Literal["quick_connect_desktop", "create_desktop", "existing"]
HermesToolPolicyEnforcement = Literal["advisory"]
HermesParityStatus = Literal["ready", "partial", "advisory", "missing"]
HermesPromotionStatus = Literal["pending", "applied", "already_armed"]
HermesPromotionTargetKind = Literal["gateway_bootstrap", "task_blueprint"]
InterferenceKind = Literal[
    "lane_braid",
    "checkpoint_eclipse",
    "task_overlap",
    "remote_echo",
    "gateway_posture",
]
ControlChatActionKind = Literal[
    "observe",
    "wait",
    "blocked",
    "resolve_request",
    "pause_mission",
    "resume_mission",
    "run_mission",
    "launch_opportunity",
    "create_mission",
    "unavailable",
]
AttentionQueueActionStatus = Literal["executed", "escalated", "observed"]
SwarmRole = Literal[
    "conductor",
    "product_manager",
    "architect",
    "test_engineer",
    "backend_engineer",
    "frontend_engineer",
    "security_auditor",
    "refactorer",
    "integration_tester",
]
SwarmStageStatus = Literal[
    "pending",
    "ready",
    "running",
    "completed",
    "blocked",
    "conflicted",
]
SwarmPayloadKind = Literal[
    "mission_brief",
    "role_directive",
    "product_spec",
    "architecture_plan",
    "test_strategy",
    "backend_plan",
    "frontend_plan",
    "security_review",
    "refactor_plan",
    "integration_report",
    "conflict_report",
    "final_handoff",
]
SwarmIsolationScope = Literal[
    "global_coordination",
    "product_scope_only",
    "system_design_only",
    "quality_strategy_only",
    "backend_surface_only",
    "frontend_surface_only",
    "security_posture_only",
    "refactor_surface_only",
    "integration_surface_only",
]
SwarmConflictReason = Literal[
    "ownership_overlap",
    "contract_mismatch",
    "verification_mismatch",
    "security_blocker",
    "integration_break",
]


class SwarmAcceptanceCriterionView(BaseModel):
    id: str
    summary: str
    owner: SwarmRole | None = None


class SwarmDecisionView(BaseModel):
    id: str
    summary: str
    rationale: str | None = None
    owner: SwarmRole | None = None


class SwarmRiskView(BaseModel):
    id: str
    summary: str
    severity: SignalLevel = "warn"
    mitigation: str | None = None
    owner: SwarmRole | None = None


class SwarmArtifactReferenceView(BaseModel):
    kind: Literal["file", "test", "api", "ui", "schema", "checkpoint", "note"]
    label: str
    path: str | None = None
    summary: str | None = None


class SwarmDirectiveView(BaseModel):
    objective: str
    required_outputs: list[SwarmPayloadKind] = Field(default_factory=list)
    owned_surfaces: list[str] = Field(default_factory=list)
    blocked_surfaces: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)


class SwarmProductSpecView(BaseModel):
    problem: str
    user_outcomes: list[str] = Field(default_factory=list)
    scope_in: list[str] = Field(default_factory=list)
    scope_out: list[str] = Field(default_factory=list)
    acceptance_criteria: list[SwarmAcceptanceCriterionView] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class SwarmArchitecturePlanView(BaseModel):
    headline: str
    system_shape: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    decisions: list[SwarmDecisionView] = Field(default_factory=list)
    risks: list[SwarmRiskView] = Field(default_factory=list)
    file_targets: list[SwarmArtifactReferenceView] = Field(default_factory=list)


class SwarmTestStrategyView(BaseModel):
    headline: str
    unit_checks: list[str] = Field(default_factory=list)
    integration_checks: list[str] = Field(default_factory=list)
    regression_guards: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)


class SwarmImplementationPlanView(BaseModel):
    headline: str
    role: SwarmRole
    tasks: list[str] = Field(default_factory=list)
    file_targets: list[SwarmArtifactReferenceView] = Field(default_factory=list)
    tests_to_touch: list[str] = Field(default_factory=list)
    contracts_to_honor: list[str] = Field(default_factory=list)
    risks: list[SwarmRiskView] = Field(default_factory=list)


class SwarmSecurityReviewView(BaseModel):
    headline: str
    findings: list[SwarmRiskView] = Field(default_factory=list)
    required_repairs: list[str] = Field(default_factory=list)
    approval_gates: list[str] = Field(default_factory=list)


class SwarmRefactorPlanView(BaseModel):
    headline: str
    cleanup_targets: list[SwarmArtifactReferenceView] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)


class SwarmIntegrationReportView(BaseModel):
    headline: str
    verified_checks: list[str] = Field(default_factory=list)
    failing_checks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommended_action: str | None = None


class SwarmConflictView(BaseModel):
    reason: SwarmConflictReason
    summary: str
    roles: list[SwarmRole] = Field(default_factory=list)
    recommended_reflex: ReflexKind = "scope_realign"


class SwarmWorkingSetView(BaseModel):
    product_spec: SwarmProductSpecView | None = None
    architecture_plan: SwarmArchitecturePlanView | None = None
    test_strategy: SwarmTestStrategyView | None = None
    backend_plan: SwarmImplementationPlanView | None = None
    frontend_plan: SwarmImplementationPlanView | None = None
    security_review: SwarmSecurityReviewView | None = None
    refactor_plan: SwarmRefactorPlanView | None = None
    integration_report: SwarmIntegrationReportView | None = None
    decisions: list[SwarmDecisionView] = Field(default_factory=list)
    risks: list[SwarmRiskView] = Field(default_factory=list)
    artifacts: list[SwarmArtifactReferenceView] = Field(default_factory=list)
    conflicts: list[SwarmConflictView] = Field(default_factory=list)


class SwarmRoleDefinitionView(BaseModel):
    role: SwarmRole
    label: str
    system_prompt: str
    isolation_scope: SwarmIsolationScope
    consumes: list[SwarmPayloadKind] = Field(default_factory=list)
    produces: list[SwarmPayloadKind] = Field(default_factory=list)


class SwarmStageDefinitionView(BaseModel):
    order: int = Field(ge=0)
    role: SwarmRole
    consumes: list[SwarmPayloadKind] = Field(default_factory=list)
    produces: list[SwarmPayloadKind] = Field(default_factory=list)
    next_role: SwarmRole | None = None


class SwarmConstitutionView(BaseModel):
    version: str = "swarm.constitution.v1"
    routing_mode: Literal["json_bus"] = "json_bus"
    no_free_chat: bool = True
    pause_on_conflict: bool = True
    conflict_policy: str = (
        "Pause the swarm and raise a reflex-visible conflict packet when two role outputs "
        "disagree on the same owned surface."
    )
    stages: list[SwarmStageDefinitionView] = Field(default_factory=list)
    roles: list[SwarmRoleDefinitionView] = Field(default_factory=list)


class SwarmEnvelopeView(BaseModel):
    schema_version: str = "swarm.payload.v1"
    mission_id: int | None = None
    run_id: str
    stage_index: int = Field(default=0, ge=0)
    from_role: SwarmRole
    to_role: SwarmRole
    kind: SwarmPayloadKind
    summary: str
    directive: SwarmDirectiveView | None = None
    working_set: SwarmWorkingSetView = Field(default_factory=SwarmWorkingSetView)
    notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class MissionSwarmConflictView(BaseModel):
    reason: SwarmConflictReason
    summary: str
    roles: list[SwarmRole] = Field(default_factory=list)
    prompt: str
    detected_at: str | None = None
    recommended_reflex: ReflexKind = "scope_realign"


class MissionSwarmRuntimeView(BaseModel):
    enabled: bool = True
    constitution_version: str = "swarm.constitution.v1"
    run_id: str | None = None
    status: Literal["ready", "running", "completed", "blocked", "conflicted"] = "ready"
    stage_index: int = Field(default=1, ge=0)
    active_role: SwarmRole | None = None
    completed_roles: list[SwarmRole] = Field(default_factory=list)
    pending_roles: list[SwarmRole] = Field(default_factory=list)
    last_payload_kind: SwarmPayloadKind | None = None
    last_output_summary: str | None = None
    active_envelope: SwarmEnvelopeView | None = None
    working_set: SwarmWorkingSetView = Field(default_factory=SwarmWorkingSetView)
    conflict: MissionSwarmConflictView | None = None


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


class ProjectHarnessCheckView(BaseModel):
    key: str
    label: str
    status: DiagnosticStatus
    detail: str
    expected: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ProjectHarnessRepairActionView(BaseModel):
    title: str
    detail: str
    command: str | None = None


class ProjectHarnessDoctorView(BaseModel):
    level: SignalLevel = "info"
    headline: str
    summary: str
    baseline_path: str | None = None
    install_state_paths: list[str] = Field(default_factory=list)
    expected_surface_paths: list[str] = Field(default_factory=list)
    missing_surface_paths: list[str] = Field(default_factory=list)
    expected_mcp_servers: list[str] = Field(default_factory=list)
    missing_mcp_servers: list[str] = Field(default_factory=list)
    expected_codex_roles: list[str] = Field(default_factory=list)
    missing_codex_roles: list[str] = Field(default_factory=list)
    drifted_paths: list[str] = Field(default_factory=list)
    drift_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[ProjectHarnessCheckView] = Field(default_factory=list)
    repair_actions: list[ProjectHarnessRepairActionView] = Field(default_factory=list)


class ProjectHarnessInstallProfileView(BaseModel):
    id: str
    description: str
    module_count: int
    installable_module_count: int
    skipped_module_count: int


class ProjectHarnessOperationCreate(BaseModel):
    mode: Literal[
        "repair_preview",
        "repair_apply",
        "install_preview",
        "install_apply",
        "uninstall_preview",
        "uninstall_apply",
    ]
    profile: str | None = None


class ProjectHarnessOperationView(BaseModel):
    mode: Literal[
        "repair_preview",
        "repair_apply",
        "install_preview",
        "install_apply",
        "uninstall_preview",
        "uninstall_apply",
    ]
    status: Literal["planned", "repaired", "installed", "uninstalled", "noop"]
    headline: str
    summary: str
    project_path: str
    baseline_path: str
    profile: str | None = None
    selected_modules: list[str] = Field(default_factory=list)
    skipped_modules: list[str] = Field(default_factory=list)
    planned_paths: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    doctor: ProjectHarnessDoctorView | None = None


class ProjectAgentHarnessView(BaseModel):
    kind: Literal["ecc_source", "ecc_workspace", "ecc_candidate"]
    headline: str
    summary: str
    skill_count: int = 0
    command_count: int = 0
    agent_count: int = 0
    rule_family_count: int = 0
    codex_role_count: int = 0
    mcp_servers: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    surface_paths: list[str] = Field(default_factory=list)
    baseline_path: str | None = None
    install_state_paths: list[str] = Field(default_factory=list)
    install_manifest_version: int | None = None
    install_profiles: list[ProjectHarnessInstallProfileView] = Field(default_factory=list)
    default_install_profile: str | None = None
    active_install_profile: str | None = None
    active_install_modules: list[str] = Field(default_factory=list)
    active_install_skipped_modules: list[str] = Field(default_factory=list)
    doctor: ProjectHarnessDoctorView | None = None


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
    agent_harness: ProjectAgentHarnessView | None = None


class TeamCreate(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None


class TeamView(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class OperatorCreate(BaseModel):
    team_id: int | None = None
    name: str
    email: str | None = None
    role: OperatorRole = "operator"
    enabled: bool = True
    issue_api_key: bool = False


class OperatorView(BaseModel):
    id: int
    team_id: int
    team_name: str | None = None
    name: str
    email: str | None = None
    role: OperatorRole
    enabled: bool = True
    has_api_key: bool = False
    api_key_preview: str | None = None
    api_key_issued_at: str | None = None
    api_key_last_used_at: str | None = None
    created_at: datetime
    updated_at: datetime


class OperatorCredentialView(BaseModel):
    operator: OperatorView
    api_key: str | None = None


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


class ControlChatCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ControlChatMessageView(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    canvas_previews: list[dict[str, Any]] = Field(default_factory=list)
    action_kind: ControlChatActionKind | None = None
    mission_id: int | None = None
    opportunity_id: str | None = None
    target_label: str | None = None
    created_at: datetime


class ControlChatResponse(BaseModel):
    user: ControlChatMessageView
    assistant: ControlChatMessageView
    action_kind: ControlChatActionKind
    executed: bool


class AttentionQueueActionView(BaseModel):
    id: int
    signal_id: str
    signal_fingerprint: str
    signal_level: SignalLevel
    mission_id: int | None = None
    opportunity_id: str | None = None
    target_label: str | None = None
    action_kind: ControlChatActionKind
    status: AttentionQueueActionStatus
    summary: str | None = None
    created_at: datetime
    updated_at: datetime


class PlaybookCreate(BaseModel):
    name: str
    description: str | None = None
    kind: PlaybookKind
    template: str
    instance_id: int | None = None
    cadence_minutes: int | None = Field(default=None, ge=1)
    enabled: bool = True
    cwd: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None
    timeout_ms: int | None = 10000
    thread_id: str | None = None
    default_variables: dict[str, str] = Field(default_factory=dict)


class PlaybookView(PlaybookCreate):
    id: int
    last_run_at: str | None = None
    last_status: PlaybookStatus | None = None
    last_result_summary: str | None = None
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


class GatewayCapabilityDiagnosticsView(BaseModel):
    headline: str
    summary: str
    ok_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    evidence: list[str] = Field(default_factory=list)


class GatewayCapabilityLaneView(BaseModel):
    instance_id: int
    instance_name: str
    connected: bool
    level: SignalLevel = "info"
    summary: str
    approval_count: int = 0
    app_count: int = 0
    plugin_count: int = 0
    mcp_server_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    last_event_at: str | None = None


class GatewayCapabilityConnectedLaneHealthView(BaseModel):
    headline: str
    summary: str
    total_count: int = 0
    connected_count: int = 0
    ready_count: int = 0
    warning_count: int = 0
    offline_count: int = 0
    approval_count: int = 0
    lanes: list[GatewayCapabilityLaneView] = Field(default_factory=list)


class GatewayCapabilityInventoryItemView(BaseModel):
    kind: Literal["app", "plugin", "mcp_server", "service"]
    name: str
    ready_lane_count: int = 0
    total_lane_count: int = 0
    summary: str
    lanes: list[str] = Field(default_factory=list)


class GatewayCapabilityMemoryProofReferenceView(BaseModel):
    mission_id: int
    mission_name: str
    task_blueprint_id: int | None = None
    task_name: str
    scope_label: str | None = None
    proof_kind: Literal["control_plane", "roundtrip", "writeback", "checkpoint"]
    proof_status: str
    summary: str
    checkpoint_excerpt: str | None = None
    continuity_path: str
    updated_at: datetime | None = None


class GatewayCapabilityMethodScopeView(BaseModel):
    scope: str
    method_count: int = 0
    methods: list[str] = Field(default_factory=list)


class GatewayCapabilityMethodCatalogView(BaseModel):
    headline: str
    summary: str
    tool_count: int = 0
    server_count: int = 0
    lane_count: int = 0
    classified_method_count: int = 0
    reserved_admin_method_count: int = 0
    reserved_admin_scope: str | None = None
    tools: list[str] = Field(default_factory=list)
    servers: list[str] = Field(default_factory=list)
    reserved_admin_methods: list[str] = Field(default_factory=list)
    scopes: list[GatewayCapabilityMethodScopeView] = Field(default_factory=list)


class GatewayCapabilityEventCatalogView(BaseModel):
    headline: str
    summary: str
    event_count: int = 0
    events: list[str] = Field(default_factory=list)


class GatewayCapabilityKnownNodeView(BaseModel):
    node_id: str
    display_name: str | None = None
    platform: str | None = None
    version: str | None = None
    core_version: str | None = None
    ui_version: str | None = None
    client_id: str | None = None
    client_mode: str | None = None
    remote_ip: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    path_env: str | None = None
    caps: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    permissions: dict[str, bool] | None = None
    paired: bool = False
    connected: bool = True
    connected_at_ms: int | None = None
    approved_at_ms: int | None = None


class GatewayCapabilityNodeCatalogView(BaseModel):
    headline: str
    summary: str
    node_count: int = 0
    connected_count: int = 0
    paired_count: int = 0
    nodes: list[GatewayCapabilityKnownNodeView] = Field(default_factory=list)


class GatewayMethodCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class GatewayNodePendingActionView(BaseModel):
    id: str
    command: str
    params_json: str | None = Field(default=None, alias="paramsJSON")
    enqueued_at_ms: int = Field(alias="enqueuedAtMs")


class GatewayNodePendingActionPullView(BaseModel):
    node_id: str = Field(alias="nodeId")
    actions: list[GatewayNodePendingActionView] = Field(default_factory=list)


class GatewayNodePendingActionAckRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class GatewayNodePendingActionAckView(BaseModel):
    node_id: str = Field(alias="nodeId")
    acked_ids: list[str] = Field(default_factory=list, alias="ackedIds")
    remaining_count: int = Field(default=0, alias="remainingCount")


GatewayNodePendingWorkType = Literal["status.request", "location.request"]
GatewayNodePendingWorkPriority = Literal["default", "normal", "high"]


class GatewayNodePendingWorkItemView(BaseModel):
    id: str
    type: GatewayNodePendingWorkType
    priority: GatewayNodePendingWorkPriority
    created_at_ms: int = Field(alias="createdAtMs")
    expires_at_ms: int | None = Field(default=None, alias="expiresAtMs")
    payload: dict[str, Any] | None = None


class GatewayNodePendingWorkDrainView(BaseModel):
    node_id: str = Field(alias="nodeId")
    revision: int = 0
    items: list[GatewayNodePendingWorkItemView] = Field(default_factory=list)
    has_more: bool = Field(default=False, alias="hasMore")


class GatewayNodePendingWorkEnqueueRequest(BaseModel):
    type: GatewayNodePendingWorkType
    priority: GatewayNodePendingWorkPriority | None = None
    expires_in_ms: int | None = Field(default=None, alias="expiresInMs")
    payload: dict[str, Any] | None = None
    wake: bool | None = None


class GatewayNodePendingWorkEnqueueView(BaseModel):
    node_id: str = Field(alias="nodeId")
    revision: int = 0
    queued: GatewayNodePendingWorkItemView
    wake_triggered: bool = Field(default=False, alias="wakeTriggered")


class GatewayCapabilityBrowserLaneView(BaseModel):
    instance_id: int
    instance_name: str
    connected: bool = False
    level: SignalLevel = "info"
    ready: bool = False
    method_count: int = 0
    service_count: int = 0
    node_host_command_count: int = 0
    node_host_cap_count: int = 0
    methods: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    node_host_commands: list[str] = Field(default_factory=list)
    node_host_caps: list[str] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    servers: list[str] = Field(default_factory=list)
    summary: str


class GatewayCapabilityBrowserRuntimeView(BaseModel):
    headline: str
    summary: str
    status: SignalLevel = "info"
    lane_count: int = 0
    connected_lane_count: int = 0
    ready_lane_count: int = 0
    method_count: int = 0
    service_count: int = 0
    node_host_command_count: int = 0
    node_host_cap_count: int = 0
    plugin_count: int = 0
    server_count: int = 0
    methods: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    node_host_commands: list[str] = Field(default_factory=list)
    node_host_caps: list[str] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    servers: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    lanes: list[GatewayCapabilityBrowserLaneView] = Field(default_factory=list)


class BrowserToolStatusView(BaseModel):
    available: bool
    command: str | None = None
    summary: str


class BrowserSurfaceSummaryView(BaseModel):
    status: str
    headline: str
    summary: str


class BrowserPostureView(BaseModel):
    status: SignalLevel = "info"
    headline: str
    summary: str
    control_plane_url: str
    local_agent_browser: BrowserToolStatusView
    saved_launch: BrowserSurfaceSummaryView | None = None
    saved_launch_browser_runtime: GatewayCapabilityBrowserRuntimeView | None = None
    live_gateway: BrowserSurfaceSummaryView | None = None
    live_gateway_browser_runtime: GatewayCapabilityBrowserRuntimeView | None = None
    recommended_action: str | None = None


class GatewayCapabilityInventoryView(BaseModel):
    headline: str
    summary: str
    app_count: int = 0
    plugin_count: int = 0
    mcp_server_count: int = 0
    service_count: int = 0
    tracked_ready_count: int = 0
    tracked_gap_count: int = 0
    tracked_count: int = 0
    observed_count: int = 0
    memory_status: SignalLevel = "info"
    memory_summary: str = ""
    memory_recommended_action: str | None = None
    memory_evidence: list[str] = Field(default_factory=list)
    memory_proof_reference: GatewayCapabilityMemoryProofReferenceView | None = None
    memory_proof_continuity: DashboardContinuityPacketView | None = None
    memory_proof_launchable: bool = False
    memory_proof_target_instance_id: int | None = None
    memory_proof_launch_label: str | None = None
    method_catalog: GatewayCapabilityMethodCatalogView | None = None
    event_catalog: GatewayCapabilityEventCatalogView | None = None
    node_catalog: GatewayCapabilityNodeCatalogView | None = None
    browser_runtime: GatewayCapabilityBrowserRuntimeView | None = None
    items: list[GatewayCapabilityInventoryItemView] = Field(default_factory=list)


class GatewayCapabilityApprovalPostureView(BaseModel):
    headline: str
    summary: str
    pause_on_approval: bool = True
    approval_count: int = 0
    lane_count_with_approvals: int = 0
    operator_api_key_count: int = 0
    recent_remote_request_count: int = 0


class GatewayCapabilityLaunchPolicyView(BaseModel):
    headline: str
    summary: str
    setup_mode: SetupMode = "local"
    setup_flow: SetupFlow = "quickstart"
    route_binding_mode: GatewayRouteBindingMode = "saved_lane"
    run_verification: bool = True
    use_builtin_agents: bool = True
    auto_commit: bool = False
    pause_on_approval: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = 2
    allow_failover: bool = True
    model: str = "gpt-5.4"
    max_turns: int | None = 4
    toolsets: list[str] = Field(default_factory=list)
    tool_policy: HermesToolPolicyView | None = None
    launch_route: LaunchRouteView | None = None


class GatewayCapabilityView(BaseModel):
    level: SignalLevel = "info"
    headline: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    connected_lane_health: GatewayCapabilityConnectedLaneHealthView
    inventory: GatewayCapabilityInventoryView
    approval_posture: GatewayCapabilityApprovalPostureView
    launch_policy: GatewayCapabilityLaunchPolicyView
    diagnostics: GatewayCapabilityDiagnosticsView
    checked_at: str


class GatewayMemoryProofRun(BaseModel):
    instance_id: int | None = None


class HermesToolPolicyView(BaseModel):
    toolsets: list[str] = Field(default_factory=list)
    capability_families: list[str] = Field(default_factory=list)
    headline: str
    summary: str
    enforcement: HermesToolPolicyEnforcement = "advisory"
    warnings: list[str] = Field(default_factory=list)


class HermesCapabilityItemView(BaseModel):
    key: str
    label: str
    status: HermesParityStatus = "advisory"
    summary: str
    capabilities: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommended: bool = False


class HermesCapabilityDeckView(BaseModel):
    headline: str
    summary: str
    ready_count: int = 0
    partial_count: int = 0
    advisory_count: int = 0
    missing_count: int = 0
    items: list[HermesCapabilityItemView] = Field(default_factory=list)


class HermesLearningPromotionCandidateView(BaseModel):
    fingerprint: str
    status: HermesPromotionStatus = "pending"
    title: str
    summary: str
    target_kind: HermesPromotionTargetKind
    target_id: int | None = None
    target_label: str
    recommended_toolsets: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    applied_at: str | None = None


class HermesPromotionLoopView(BaseModel):
    headline: str
    summary: str
    auto_apply: bool = True
    pending_count: int = 0
    applied_count: int = 0
    already_armed_count: int = 0
    items: list[HermesLearningPromotionCandidateView] = Field(default_factory=list)


class HermesUpdateView(BaseModel):
    headline: str
    summary: str
    enabled: bool = False
    repo_root: str | None = None
    startup_revision: str | None = None
    current_revision: str | None = None
    pending_revision: str | None = None
    pending_restart: bool = False
    restart_in_progress: bool = False
    safe_to_restart: bool = False
    last_checked_at: str | None = None
    last_restart_at: str | None = None
    last_error: str | None = None
    auto_restart: bool = False


class HermesRuntimeProfileView(BaseModel):
    headline: str
    summary: str
    hermes_source_path: str | None = None
    preferred_memory_provider: str = "openzues_recall"
    preferred_executor: str = "codex_desktop"
    learning_autopromote_enabled: bool = True
    plugin_discovery_enabled: bool = True
    channel_inventory_enabled: bool = True
    acp_inventory_enabled: bool = True
    executor_profiles: list[HermesExecutorProfileStateView] = Field(default_factory=list)
    promotion_history_count: int = 0
    last_learning_promotion_at: str | None = None
    last_learning_fingerprint: str | None = None


class HermesRuntimeProfileUpdate(BaseModel):
    preferred_memory_provider: str | None = None
    preferred_executor: str | None = None
    learning_autopromote_enabled: bool | None = None
    plugin_discovery_enabled: bool | None = None
    channel_inventory_enabled: bool | None = None
    acp_inventory_enabled: bool | None = None


class WorkspaceShellArmRequest(BaseModel):
    cwd: str | None = None
    auto_connect: bool = False


class DockerExecutorArmRequest(BaseModel):
    cwd: str | None = None
    image: str | None = None
    auto_connect: bool = False
    mount_workspace: bool = False


class DockerExecutorPreflightRequest(BaseModel):
    cwd: str | None = None
    image: str | None = None


class HermesExecutorProfileStateView(BaseModel):
    key: str
    label: str
    armed: bool = False
    cwd: str | None = None
    image: str | None = None
    mount_workspace: bool = False
    control_instance_id: int | None = None
    control_instance_name: str | None = None
    derived_from: str | None = None
    armed_at: str | None = None
    last_checked_at: str | None = None
    last_preflight_status: LaunchRouteStatus | None = None
    last_preflight_summary: str | None = None
    command_path: str | None = None
    docker_version: str | None = None
    daemon_version: str | None = None
    image_present: bool | None = None
    summary: str


class HermesExecutorArmResultView(BaseModel):
    headline: str
    summary: str
    executor_key: str
    executor_label: str
    cwd: str
    derived_from: str
    created: bool = False
    connected: bool = False
    instance: InstanceView
    image: str | None = None
    mount_workspace: bool | None = None


class HermesExecutorPreflightView(BaseModel):
    headline: str
    summary: str
    executor_key: str
    executor_label: str
    ok: bool = False
    status: LaunchRouteStatus = "repair"
    cwd: str | None = None
    image: str | None = None
    derived_from: str | None = None
    command_path: str | None = None
    docker_version: str | None = None
    daemon_version: str | None = None
    image_present: bool | None = None
    checked_at: str


class HermesDoctorView(BaseModel):
    level: SignalLevel = "info"
    headline: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    profile: HermesRuntimeProfileView
    promotion_loop: HermesPromotionLoopView
    memory: HermesCapabilityDeckView
    executors: HermesCapabilityDeckView
    plugins: HermesCapabilityDeckView
    delivery: HermesCapabilityDeckView
    acp: HermesCapabilityDeckView
    extras: HermesCapabilityDeckView
    updates: HermesUpdateView
    checked_at: str


class TaskBlueprintCreate(BaseModel):
    name: str
    summary: str | None = None
    objective_template: str
    conversation_target: ConversationTargetView | None = None
    instance_id: int | None = None
    project_id: int | None = None
    cadence_minutes: int | None = Field(default=None, ge=1)
    schedule_anchor_ms: int | None = Field(default=None, ge=0)
    schedule_kind: Literal["every", "at", "cron"] | None = None
    schedule_at: str | None = None
    schedule_cron_expr: str | None = None
    schedule_cron_tz: str | None = None
    schedule_cron_stagger_ms: int | None = Field(default=None, ge=0)
    cron_session_target: str | None = None
    cron_session_key: str | None = None
    cron_wake_mode: Literal["now", "next-heartbeat"] | None = None
    cron_delete_after_run: bool | None = None
    cron_payload_kind: Literal["agentTurn", "systemEvent"] | None = None
    cron_payload_text: str | None = None
    cron_payload_timeout_seconds: int | None = Field(default=None, ge=0)
    cron_payload_light_context: bool | None = None
    cron_payload_tools_allow: list[str] | None = None
    cron_delivery_mode: Literal["none", "announce", "webhook"] | None = None
    cron_delivery_channel: str | None = None
    cron_delivery_to: str | None = None
    cron_delivery_account_id: str | None = None
    cron_delivery_thread_id: str | int | None = None
    cron_delivery_best_effort: bool | None = None
    cron_delivery_failure_destination: dict[str, Any] | None = None
    cron_failure_alert: dict[str, Any] | Literal[False] | None = None
    cron_state: dict[str, Any] | None = None
    cron_notify_enabled: bool | None = None
    run_until_complete: bool = False
    continuation_cooldown_minutes: int = Field(default=10, ge=1)
    completion_marker: str | None = None
    cwd: str | None = None
    model: str = "gpt-5.4"
    reasoning_effort: str | None = None
    collaboration_mode: str | None = None
    max_turns: int | None = Field(default=None, ge=1)
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = False
    pause_on_approval: bool = True
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = Field(default=2, ge=0)
    reflex_cooldown_seconds: int = Field(default=900, ge=60)
    allow_failover: bool = True
    toolsets: list[str] = Field(default_factory=list)
    enabled: bool = True


class TaskBlueprintView(TaskBlueprintCreate):
    id: int
    last_launched_at: str | None = None
    last_status: str | None = None
    last_result_summary: str | None = None
    mission_draft: MissionDraftView | None = None
    tool_policy: HermesToolPolicyView | None = None
    created_at: datetime
    updated_at: datetime


class NotificationRouteCreate(BaseModel):
    name: str
    kind: NotificationRouteKind = "webhook"
    target: str
    events: list[str] = Field(default_factory=lambda: ["mission/completed", "mission/failed"])
    conversation_target: ConversationTargetView | None = None
    enabled: bool = True
    secret_header_name: str | None = None
    secret_token: str | None = None
    vault_secret_id: int | None = None


class NotificationRouteView(BaseModel):
    id: int
    name: str
    kind: NotificationRouteViewKind
    target: str
    events: list[str] = Field(default_factory=list)
    conversation_target: ConversationTargetView | None = None
    enabled: bool = True
    secret_header_name: str | None = None
    vault_secret_id: int | None = None
    vault_secret_label: str | None = None
    has_secret: bool = False
    secret_preview: str | None = None
    last_delivery_at: str | None = None
    last_result: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class NotificationRouteTestResultView(BaseModel):
    ok: bool
    route_id: int
    route_name: str
    target: str
    event_type: str
    summary: str
    error: str | None = None
    route: NotificationRouteView
    delivery: OutboundDeliveryView | None = None


class OutboundDeliveryReplayResultView(BaseModel):
    ok: bool
    delivery_id: int
    route_id: int
    route_name: str
    target: str
    event_type: str
    summary: str
    error: str | None = None
    route: NotificationRouteView
    delivery: OutboundDeliveryView | None = None


class OutboundDeliveryReplayBatchView(BaseModel):
    ok: bool = True
    summary: str
    attempted_count: int = 0
    replayed_count: int = 0
    failed_count: int = 0
    deferred_count: int = 0
    skipped_max_retries_count: int = 0
    deliveries: list[OutboundDeliveryReplayResultView] = Field(default_factory=list)


class OutboundRouteScopeView(BaseModel):
    route_id: int | None = None
    route_name: str
    route_kind: str
    route_target: str
    route_match: str | None = None


class OutboundDeliveryTransportView(BaseModel):
    runtime: str
    channel: str | None = None
    target: str | None = None
    account_id: str | None = None
    thread_id: str | None = None
    session_key: str | None = None


class OutboundDeliveryView(BaseModel):
    id: int
    route_id: int | None = None
    route_name: str
    route_kind: str
    route_target: str
    event_type: str
    session_key: str | None = None
    conversation_target: ConversationTargetView | None = None
    route_scope: OutboundRouteScopeView
    event_payload: dict[str, Any] | None = None
    request_idempotency_key: str | None = None
    delivery_message_id: str | None = None
    transport: OutboundDeliveryTransportView | None = None
    message_summary: str
    test_delivery: bool = False
    delivery_state: Literal["pending", "delivered", "failed"]
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    replay_ready: bool = False
    next_retry_at: datetime | None = None
    max_retries_reached: bool = False
    delivered_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class IntegrationCreate(BaseModel):
    name: str
    kind: str
    project_id: int | None = None
    base_url: str | None = None
    auth_scheme: str = "token"
    vault_secret_id: int | None = None
    secret_label: str | None = None
    secret_value: str | None = None
    notes: str | None = None
    enabled: bool = True


class IntegrationView(BaseModel):
    id: int
    name: str
    kind: str
    project_id: int | None = None
    base_url: str | None = None
    auth_scheme: str = "token"
    vault_secret_id: int | None = None
    vault_secret_label: str | None = None
    secret_label: str | None = None
    has_secret: bool = False
    secret_preview: str | None = None
    auth_status: IntegrationAuthStatus = "missing"
    auth_detail: str | None = None
    notes: str | None = None
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class VaultSecretCreate(BaseModel):
    label: str
    value: str = Field(min_length=1)
    kind: str = "token"
    notes: str | None = None


class VaultSecretView(BaseModel):
    id: int
    label: str
    kind: str
    notes: str | None = None
    secret_preview: str | None = None
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime


class SkillPinCreate(BaseModel):
    project_id: int
    name: str
    prompt_hint: str
    source: str | None = None
    enabled: bool = True


class SkillPinView(SkillPinCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class OnboardingBootstrapCreate(BaseModel):
    setup_mode: SetupMode = "local"
    setup_flow: SetupFlow = "quickstart"
    use_mempalace: bool = False
    instance_mode: BootstrapInstanceMode = "quick_connect_desktop"
    instance_id: int | None = None
    instance_name: str = "Local Codex Desktop"
    project_path: str
    project_label: str | None = None
    team_name: str | None = None
    team_slug: str | None = None
    team_description: str | None = None
    operator_name: str
    operator_email: str | None = None
    operator_role: OperatorRole = "operator"
    bootstrap_roles: list[str] | None = None
    bootstrap_scopes: list[str] | None = None
    issue_api_key: bool = True
    vault_secret_label: str | None = None
    vault_secret_value: str | None = None
    vault_secret_kind: str = "token"
    vault_secret_notes: str | None = None
    integration_name: str | None = None
    integration_kind: str | None = None
    integration_base_url: str | None = None
    integration_auth_scheme: str = "token"
    integration_notes: str | None = None
    skill_name: str | None = None
    skill_prompt_hint: str | None = None
    skill_source: str | None = None
    task_name: str
    task_summary: str | None = None
    objective_template: str
    conversation_target: ConversationTargetView | None = None
    cadence_minutes: int = Field(default=180, ge=1)
    completion_marker: str | None = None
    model: str = "gpt-5.4"
    max_turns: int | None = Field(default=4, ge=1)
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = False
    pause_on_approval: bool = True
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = Field(default=2, ge=0)
    reflex_cooldown_seconds: int = Field(default=900, ge=60)
    allow_failover: bool = True
    toolsets: list[str] = Field(default_factory=list)
    enabled: bool = True


class OnboardingBootstrapResourceView(BaseModel):
    kind: str
    id: int
    label: str
    created: bool = False
    detail: str | None = None


class OnboardingBootstrapResultView(BaseModel):
    headline: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    next_entrypoint: str
    instance: OnboardingBootstrapResourceView | None = None
    project: OnboardingBootstrapResourceView
    team: OnboardingBootstrapResourceView
    operator: OnboardingBootstrapResourceView
    vault_secret: OnboardingBootstrapResourceView | None = None
    integration: OnboardingBootstrapResourceView | None = None
    skill_pin: OnboardingBootstrapResourceView | None = None
    task_blueprint: OnboardingBootstrapResourceView
    memory_task_blueprint: OnboardingBootstrapResourceView | None = None
    api_key: str | None = None
    mission_draft: MissionDraftView | None = None
    launch_route: LaunchRouteView | None = None


class GatewayBootstrapResourceView(BaseModel):
    id: int
    label: str
    detail: str | None = None
    connected: bool | None = None


class GatewayBootstrapRuntimeInventoryView(BaseModel):
    headline: str
    summary: str
    app_count: int = 0
    plugin_count: int = 0
    mcp_server_count: int = 0
    service_count: int = 0
    base_method_count: int = 0
    resolved_method_count: int = 0
    app_names: list[str] = Field(default_factory=list)
    plugin_names: list[str] = Field(default_factory=list)
    mcp_server_names: list[str] = Field(default_factory=list)
    service_names: list[str] = Field(default_factory=list)
    base_methods: list[str] = Field(default_factory=list)
    resolved_methods: list[str] = Field(default_factory=list)
    method_catalog: GatewayCapabilityMethodCatalogView | None = None
    browser_runtime: GatewayCapabilityBrowserRuntimeView | None = None


class ConversationTargetView(BaseModel):
    channel: str
    account_id: str | None = None
    peer_kind: ConversationTargetPeerKind | None = None
    peer_id: str | None = None
    summary: str | None = None

    @model_validator(mode="after")
    def _populate_summary(self) -> ConversationTargetView:
        channel = str(self.channel or "").strip().lower()
        account_id = str(self.account_id or "").strip() or None
        peer_id = str(self.peer_id or "").strip() or None
        peer_kind = self.peer_kind if peer_id else None
        summary = str(self.summary or "").strip() or None
        if not summary and channel:
            parts = [channel]
            if account_id:
                parts.append(f"account {account_id}")
            if peer_kind and peer_id:
                parts.append(f"{peer_kind} {peer_id}")
            summary = " · ".join(parts)
        self.channel = channel
        self.account_id = account_id
        self.peer_kind = peer_kind
        self.peer_id = peer_id if peer_kind else None
        self.summary = summary
        return self


class LaunchRouteConversationReuseView(BaseModel):
    reusable: bool = False
    summary: str
    mission_id: int | None = None
    mission_name: str | None = None
    mission_status: MissionStatus | None = None
    thread_id: str | None = None
    instance_id: int | None = None
    instance_name: str | None = None
    updated_at: str | None = None


class LaunchRouteView(BaseModel):
    status: LaunchRouteStatus
    mode: LaunchRouteBindingMode
    matched_by: LaunchRouteMatch
    headline: str
    summary: str
    session_key: str
    main_session_key: str
    last_route_policy: LaunchRoutePolicy
    conversation_target: ConversationTargetView | None = None
    warnings: list[str] = Field(default_factory=list)
    preferred_instance: GatewayBootstrapResourceView | None = None
    resolved_instance: GatewayBootstrapResourceView | None = None
    candidates: list[GatewayBootstrapResourceView] = Field(default_factory=list)
    last_resolved_at: str | None = None
    conversation_reuse: LaunchRouteConversationReuseView | None = None


class GatewayBootstrapUpdate(BaseModel):
    setup_mode: SetupMode = "local"
    setup_flow: SetupFlow = "quickstart"
    route_binding_mode: GatewayRouteBindingMode | None = None
    preferred_instance_id: int | None = None
    preferred_project_id: int | None = None
    team_id: int | None = None
    operator_id: int | None = None
    task_blueprint_id: int | None = None
    default_cwd: str | None = None
    bootstrap_roles: list[str] | None = None
    bootstrap_scopes: list[str] | None = None
    model: str = "gpt-5.4"
    max_turns: int | None = Field(default=4, ge=1)
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = False
    pause_on_approval: bool = True
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = Field(default=2, ge=0)
    reflex_cooldown_seconds: int = Field(default=900, ge=60)
    allow_failover: bool = True
    toolsets: list[str] = Field(default_factory=list)


class GatewayBootstrapView(BaseModel):
    status: GatewayBootstrapStatus
    headline: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    setup_mode: SetupMode = "local"
    setup_flow: SetupFlow = "quickstart"
    route_binding_mode: GatewayRouteBindingMode = "saved_lane"
    instance: GatewayBootstrapResourceView | None = None
    project: GatewayBootstrapResourceView | None = None
    integration: GatewayBootstrapResourceView | None = None
    team: GatewayBootstrapResourceView | None = None
    operator: GatewayBootstrapResourceView | None = None
    task_blueprint: GatewayBootstrapResourceView | None = None
    default_cwd: str | None = None
    bootstrap_roles: list[str] = Field(default_factory=list)
    bootstrap_scopes: list[str] = Field(default_factory=list)
    model: str = "gpt-5.4"
    max_turns: int | None = 4
    use_builtin_agents: bool = True
    run_verification: bool = True
    auto_commit: bool = False
    pause_on_approval: bool = True
    allow_auto_reflexes: bool = True
    auto_recover: bool = True
    auto_recover_limit: int = 2
    reflex_cooldown_seconds: int = 900
    allow_failover: bool = True
    toolsets: list[str] = Field(default_factory=list)
    tool_policy: HermesToolPolicyView | None = None
    launch_defaults_summary: str
    launch_route: LaunchRouteView | None = None
    runtime_inventory: GatewayBootstrapRuntimeInventoryView | None = None


class ControlUiGatewayWebchatConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chat_history_max_chars: int | None = Field(
        default=None,
        alias="chatHistoryMaxChars",
        ge=1,
        le=500_000,
    )


class ControlUiGatewayAgentSubagentsConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    allow_agents: list[str] = Field(default_factory=list, alias="allowAgents")
    max_spawn_depth: int | None = Field(
        default=None,
        alias="maxSpawnDepth",
        ge=1,
        le=5,
    )
    max_children_per_agent: int | None = Field(
        default=None,
        alias="maxChildrenPerAgent",
        ge=1,
        le=20,
    )
    run_timeout_seconds: int | None = Field(
        default=None,
        alias="runTimeoutSeconds",
        ge=0,
    )
    require_agent_id: bool = Field(default=False, alias="requireAgentId")


class ControlUiGatewayAgentSandboxConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal["off", "non-main", "all"] | None = None
    backend: str | None = None
    workspace_access: Literal["none", "ro", "rw"] | None = Field(
        default=None,
        alias="workspaceAccess",
    )
    session_tools_visibility: Literal["spawned", "all"] | None = Field(
        default=None,
        alias="sessionToolsVisibility",
    )
    scope: Literal["session", "agent", "shared"] | None = None
    workspace_root: str | None = Field(default=None, alias="workspaceRoot")
    docker: dict[str, Any] | None = None
    ssh: dict[str, Any] | None = None
    browser: dict[str, Any] | None = None
    prune: dict[str, Any] | None = None


class ControlUiToolAllowDenyConfigView(BaseModel):
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class ControlUiGatewayAgentDefaultsConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subagents: ControlUiGatewayAgentSubagentsConfigView | None = None
    sandbox: ControlUiGatewayAgentSandboxConfigView | None = None
    tools: ControlUiToolAllowDenyConfigView | None = None
    models: dict[str, dict[str, Any]] | None = None
    model: dict[str, Any] | str | None = None
    image_model: dict[str, Any] | str | None = Field(default=None, alias="imageModel")
    memory_search: dict[str, Any] | None = Field(default=None, alias="memorySearch")
    heartbeat: dict[str, Any] | None = None


class ControlUiGatewayAgentConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str | None = None
    default: bool | None = None
    workspace: str | None = None
    agent_dir: str | None = Field(default=None, alias="agentDir")
    subagents: ControlUiGatewayAgentSubagentsConfigView | None = None
    sandbox: ControlUiGatewayAgentSandboxConfigView | None = None
    tools: ControlUiToolAllowDenyConfigView | None = None


class ControlUiGatewayAgentsConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    defaults: ControlUiGatewayAgentDefaultsConfigView | None = None
    agent_list: list[ControlUiGatewayAgentConfigView] | None = Field(
        default=None,
        alias="list",
    )


class ControlUiGatewayToolsConfigView(ControlUiToolAllowDenyConfigView):
    model_config = ConfigDict(populate_by_name=True)


class ControlUiGatewayConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    bind: str | None = None
    port: int | None = Field(default=None, ge=1, le=65_535)
    custom_bind_host: str | None = Field(default=None, alias="customBindHost")
    control_ui: dict[str, Any] | None = Field(default=None, alias="controlUi")
    webchat: ControlUiGatewayWebchatConfigView | None = None
    agents: ControlUiGatewayAgentsConfigView | None = None
    tools: ControlUiGatewayToolsConfigView | None = None


class ControlUiSessionAgentToAgentConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    max_ping_pong_turns: int | None = Field(
        default=None,
        alias="maxPingPongTurns",
        ge=0,
        le=5,
    )


class ControlUiSessionThreadBindingsConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool | None = None
    idle_hours: float | None = Field(default=None, alias="idleHours", ge=0)
    max_age_hours: float | None = Field(default=None, alias="maxAgeHours", ge=0)


class ControlUiSessionConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_to_agent: ControlUiSessionAgentToAgentConfigView | None = Field(
        default=None,
        alias="agentToAgent",
    )
    thread_bindings: ControlUiSessionThreadBindingsConfigView | None = Field(
        default=None,
        alias="threadBindings",
    )


class ControlUiToolsAgentToAgentConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    allow: list[str] = Field(default_factory=list)


class ControlUiToolsSessionsConfigView(BaseModel):
    visibility: Literal["self", "tree", "agent", "all"] | None = None


class ControlUiToolsConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    agent_to_agent: ControlUiToolsAgentToAgentConfigView | None = Field(
        default=None,
        alias="agentToAgent",
    )
    sessions: ControlUiToolsSessionsConfigView | None = None
    web: dict[str, Any] | None = None
    media: dict[str, Any] | None = None


class ControlUiBootstrapConfigView(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_path: str = Field(default="", alias="basePath")
    assistant_name: str = Field(alias="assistantName")
    assistant_avatar: str = Field(alias="assistantAvatar")
    assistant_agent_id: str = Field(alias="assistantAgentId")
    server_version: str | None = Field(default=None, alias="serverVersion")
    local_media_preview_roots: list[str] = Field(
        default_factory=list,
        alias="localMediaPreviewRoots",
    )
    embed_sandbox: Literal["strict", "scripts", "trusted"] = Field(
        default="scripts",
        alias="embedSandbox",
    )
    allow_external_embed_urls: bool = Field(default=False, alias="allowExternalEmbedUrls")
    agents: ControlUiGatewayAgentsConfigView | None = None
    gateway: ControlUiGatewayConfigView | None = None
    session: ControlUiSessionConfigView | None = None
    tools: ControlUiToolsConfigView | None = None
    acp: dict[str, Any] | None = None
    plugins: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    messages: dict[str, Any] | None = None


class SetupFootprintResourceView(BaseModel):
    kind: str
    id: int
    label: str
    created: bool = False


class SetupFootprintView(BaseModel):
    instance: SetupFootprintResourceView | None = None
    project: SetupFootprintResourceView | None = None
    team: SetupFootprintResourceView | None = None
    operator: SetupFootprintResourceView | None = None
    vault_secret: SetupFootprintResourceView | None = None
    integration: SetupFootprintResourceView | None = None
    skill_pin: SetupFootprintResourceView | None = None
    task_blueprint: SetupFootprintResourceView | None = None
    memory_task_blueprint: SetupFootprintResourceView | None = None
    updated_at: datetime | None = None


class SetupWizardProbeView(BaseModel):
    status: Literal["ready", "warn", "missing"]
    headline: str
    summary: str


class SetupWizardSessionView(BaseModel):
    status: SetupWizardStatus
    headline: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    mode: SetupMode = "local"
    flow: SetupFlow = "quickstart"
    use_mempalace: bool = False
    recommended_mode: SetupMode = "local"
    recommended_flow: SetupFlow = "quickstart"
    instance_mode: BootstrapInstanceMode = "quick_connect_desktop"
    instance_id: int | None = None
    instance_name: str = "Local Codex Desktop"
    project_path: str | None = None
    project_label: str | None = None
    team_name: str | None = None
    operator_name: str | None = None
    operator_email: str | None = None
    bootstrap_roles: list[str] = Field(default_factory=list)
    bootstrap_scopes: list[str] = Field(default_factory=list)
    task_name: str | None = None
    cadence_minutes: int = 180
    model: str = "gpt-5.4"
    max_turns: int | None = 4
    objective_template: str | None = None
    conversation_target: ConversationTargetView | None = None
    toolsets: list[str] = Field(default_factory=list)
    local_probe: SetupWizardProbeView
    remote_probe: SetupWizardProbeView
    updated_at: datetime | None = None


class SetupWizardSessionUpdate(BaseModel):
    mode: SetupMode | None = None
    flow: SetupFlow | None = None
    use_mempalace: bool | None = None
    instance_mode: BootstrapInstanceMode | None = None
    instance_id: int | None = None
    instance_name: str | None = None
    project_path: str | None = None
    project_label: str | None = None
    team_name: str | None = None
    operator_name: str | None = None
    operator_email: str | None = None
    bootstrap_roles: list[str] | None = None
    bootstrap_scopes: list[str] | None = None
    task_name: str | None = None
    cadence_minutes: int | None = Field(default=None, ge=1)
    model: str | None = None
    max_turns: int | None = Field(default=None, ge=1)
    objective_template: str | None = None
    conversation_target: ConversationTargetView | None = None
    toolsets: list[str] | None = None


SetupLaunchHandoffStatus = Literal["ready", "staged", "repair", "bootstrap"]
SetupLaunchHandoffAction = Literal[
    "load_draft",
    "connect_lane",
    "repair_access",
    "restage_setup",
    "bootstrap",
]


class SetupLaunchHandoffView(BaseModel):
    status: SetupLaunchHandoffStatus
    headline: str
    summary: str
    recommended_action: SetupLaunchHandoffAction
    action_label: str
    warnings: list[str] = Field(default_factory=list)
    next_entrypoint: str
    instance: GatewayBootstrapResourceView | None = None
    project: GatewayBootstrapResourceView | None = None
    operator: GatewayBootstrapResourceView | None = None
    task_blueprint: GatewayBootstrapResourceView | None = None
    mission_draft: MissionDraftView | None = None
    launch_route: LaunchRouteView | None = None


class SetupStatusView(BaseModel):
    headline: str
    summary: str
    recommended_action: SetupRecommendedAction
    available_actions: list[SetupRecommendedAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_entrypoint: str
    handoff_summary: str
    launch_handoff: SetupLaunchHandoffView
    gateway_bootstrap: GatewayBootstrapView
    wizard_session: SetupWizardSessionView
    footprint: SetupFootprintView | None = None


class SetupResetRequest(BaseModel):
    scope: SetupResetScope = "config+creds+sessions"


class SetupResetResultView(BaseModel):
    headline: str
    summary: str
    scope: SetupResetScope
    warnings: list[str] = Field(default_factory=list)
    cleared: list[str] = Field(default_factory=list)
    preserved: list[str] = Field(default_factory=list)
    setup: SetupStatusView


class LaneSnapshotView(BaseModel):
    id: int
    instance_id: int
    instance_name: str | None = None
    snapshot_kind: str
    connected: bool
    transport: str | None = None
    model_count: int = 0
    skill_count: int = 0
    thread_count: int = 0
    approvals_pending_count: int = 0
    mission_id: int | None = None
    mission_name: str | None = None
    project_label: str | None = None
    thread_id: str | None = None
    mission_status: MissionStatus | None = None
    phase: str | None = None
    current_command: str | None = None
    command_burn: int = 0
    token_burn: int = 0
    last_checkpoint_summary: str | None = None
    continuity_state: ContinuityState | None = None
    continuity_score: int | None = None
    safest_handoff: str | None = None
    note: str | None = None
    created_at: datetime


class RemoteMissionCreate(BaseModel):
    name: str
    objective: str
    instance_id: int | None = None
    project_id: int | None = None
    task_blueprint_id: int | None = None
    cwd: str | None = None
    thread_id: str | None = None
    session_key: str | None = None
    conversation_target: ConversationTargetView | None = None
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
    toolsets: list[str] = Field(default_factory=list)
    start_immediately: bool = False
    dry_run: bool = False


class RemoteTaskTrigger(BaseModel):
    dry_run: bool = False


class MissionCreate(BaseModel):
    name: str
    objective: str
    instance_id: int
    project_id: int | None = None
    task_blueprint_id: int | None = None
    cwd: str | None = None
    thread_id: str | None = None
    session_key: str | None = None
    conversation_target: ConversationTargetView | None = None
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
    swarm_enabled: bool = False
    toolsets: list[str] = Field(default_factory=list)
    start_immediately: bool = True

    @field_validator("session_key")
    @classmethod
    def normalize_session_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class MissionDraftView(MissionCreate):
    tool_policy: HermesToolPolicyView | None = None
    preferred_memory_provider: str | None = None
    preferred_memory_provider_label: str | None = None
    preferred_executor: str | None = None
    preferred_executor_label: str | None = None
    runtime_profile_summary: str | None = None


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


class MissionToolEvidenceItemView(BaseModel):
    toolset: str
    status: Literal["observed", "unproven"] = "unproven"
    evidence_count: int = 0
    examples: list[str] = Field(default_factory=list)


class MissionToolEvidenceView(BaseModel):
    proof_ready: bool = False
    expected_toolsets: list[str] = Field(default_factory=list)
    observed_toolsets: list[str] = Field(default_factory=list)
    unproven_toolsets: list[str] = Field(default_factory=list)
    summary: str = "No tool evidence has been recorded yet."
    items: list[MissionToolEvidenceItemView] = Field(default_factory=list)


class MissionLiveTelemetryView(BaseModel):
    streaming: bool = False
    thread_status: str | None = None
    last_thread_event_at: str | None = None
    last_thread_event_age_seconds: int | None = None
    recent_event_count_30s: int = 0
    recent_event_count_5m: int = 0
    recent_output_delta_count_30s: int = 0
    recent_turn_activity_count_30s: int = 0
    token_rollup_pending: bool = False
    summary: str = "No live thread telemetry yet."


class MissionDelegationRoleView(BaseModel):
    name: str
    objective: str
    ownership: str
    trigger: str | None = None


class MissionDelegationBriefView(BaseModel):
    enabled: bool = False
    mode: Literal[
        "single_lane",
        "conductor_coder_auditor",
        "conductor_architect_planner_coder_auditor",
        "conductor_brainstorm_architect_planner_coder_auditor",
    ] = "single_lane"
    activation: Literal["disabled", "after_rebuild", "ready_now"] = "disabled"
    confidence: Literal["low", "medium", "high"] = "low"
    summary: str = "Built-in agents are disabled for this mission."
    rationale: str | None = None
    roles: list[MissionDelegationRoleView] = Field(default_factory=list)


class MissionView(BaseModel):
    id: int
    name: str
    objective: str
    status: MissionStatus
    instance_id: int
    instance_name: str | None = None
    project_id: int | None = None
    project_label: str | None = None
    task_blueprint_id: int | None = None
    thread_id: str | None = None
    session_key: str | None = None
    conversation_target: ConversationTargetView | None = None
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
    swarm_enabled: bool = False
    swarm: MissionSwarmRuntimeView | None = None
    toolsets: list[str] = Field(default_factory=list)
    tool_policy: HermesToolPolicyView | None = None
    preferred_memory_provider: str | None = None
    preferred_memory_provider_label: str | None = None
    preferred_executor: str | None = None
    preferred_executor_label: str | None = None
    runtime_profile_summary: str | None = None
    in_progress: bool = False
    phase: str | None = None
    current_command: str | None = None
    command_count: int = 0
    total_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    last_commentary: str | None = None
    commentary_summary: str | None = None
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
    charter_summary: str | None = None
    charter_focus_terms: list[str] = Field(default_factory=list)
    objective_gravity: int = Field(default=100, ge=0, le=100)
    scope_drift_level: ScopeDriftLevel = "aligned"
    scope_drift_summary: str | None = None
    live_telemetry: MissionLiveTelemetryView = Field(default_factory=MissionLiveTelemetryView)
    tool_evidence: MissionToolEvidenceView = Field(default_factory=MissionToolEvidenceView)
    delegation_brief: MissionDelegationBriefView = Field(default_factory=MissionDelegationBriefView)
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


class DashboardRecallItemView(BaseModel):
    mission_id: int
    mission_name: str
    project_id: int | None = None
    project_label: str | None = None
    status: MissionStatus
    phase: str | None = None
    updated_at: datetime
    freshness_minutes: int | None = None
    score: int | None = None
    match_source: Literal[
        "recent",
        "checkpoint",
        "summary",
        "commentary",
        "objective",
        "error",
        "memory_proof",
    ] = "recent"
    excerpt: str
    continuity_state: ContinuityState
    continuity_score: int = Field(ge=0, le=100)
    next_handoff: str
    continuity_path: str
    toolsets: list[str] = Field(default_factory=list)


class DashboardRecallView(BaseModel):
    mode: Literal["recent", "query"] = "recent"
    query: str | None = None
    headline: str
    summary: str
    preferred_memory_provider: str | None = None
    preferred_memory_provider_label: str | None = None
    total_matches: int = 0
    items: list[DashboardRecallItemView] = Field(default_factory=list)


class DashboardInterferenceVectorView(BaseModel):
    id: str
    kind: InterferenceKind
    level: SignalLevel
    scope_label: str
    project_id: int | None = None
    summary: str
    pressure: str
    treaty_prompt: str
    mission_ids: list[int] = Field(default_factory=list)
    task_ids: list[int] = Field(default_factory=list)
    operator_ids: list[int] = Field(default_factory=list)
    request_ids: list[int] = Field(default_factory=list)


class DashboardInterferenceView(BaseModel):
    headline: str
    summary: str
    vectors: list[DashboardInterferenceVectorView] = Field(default_factory=list)


class DashboardDreamView(BaseModel):
    id: str
    project_id: int
    project_label: str
    status: DreamStatus
    freshness_hours: int | None = None
    mission_count: int = 0
    checkpoint_count: int = 0
    headline: str
    summary: str
    anchors: list[str] = Field(default_factory=list)
    prune_notes: list[str] = Field(default_factory=list)
    memory_prompt: str
    action_label: str = "Load dream"
    mission_draft: MissionDraftView


class DashboardDreamDeckView(BaseModel):
    headline: str
    summary: str
    dreams: list[DashboardDreamView] = Field(default_factory=list)


class DashboardTaskView(BaseModel):
    id: int
    name: str
    summary: str
    status: TaskStatus
    cadence_label: str
    next_run_at: str | None = None
    project_label: str | None = None
    instance_name: str | None = None
    mission_id: int | None = None
    mission_name: str | None = None
    skill_count: int = 0
    integration_count: int = 0
    last_result_summary: str | None = None
    mission_draft: MissionDraftView


class DashboardTaskInboxItemView(BaseModel):
    id: str
    kind: str
    source: str
    urgency: SignalLevel
    lane_label: str | None = None
    project_label: str | None = None
    title: str
    summary: str
    recommended_action: str
    jump_label: str
    mission_id: int | None = None
    task_id: int | None = None
    playbook_id: int | None = None
    instance_id: int | None = None
    request_id: str | None = None
    freshness_minutes: int | None = None
    reflex: MissionReflexRun | None = None


class DashboardTaskInboxView(BaseModel):
    headline: str
    summary: str
    items: list[DashboardTaskInboxItemView] = Field(default_factory=list)
    tasks: list[DashboardTaskView] = Field(default_factory=list)


class DashboardEconomyScopeView(BaseModel):
    id: str
    project_id: int | None = None
    scope_label: str
    state: EconomyState
    score: int = Field(ge=0, le=100)
    summary: str
    arbitrage_edge: str
    capital_prompt: str
    mission_count: int = 0
    active_count: int = 0
    checkpoint_count: int = 0
    failure_count: int = 0
    approval_count: int = 0
    task_pressure_count: int = 0
    remote_pressure_count: int = 0
    drift_mission_count: int = 0
    objective_gravity: int = Field(default=100, ge=0, le=100)
    token_burn: int = 0
    command_burn: int = 0
    checkpoint_efficiency: float = 0.0


class DashboardEconomyView(BaseModel):
    headline: str
    summary: str
    scopes: list[DashboardEconomyScopeView] = Field(default_factory=list)


class RemoteRequestView(BaseModel):
    id: int
    team_id: int
    team_name: str | None = None
    operator_id: int
    operator_name: str | None = None
    operator_role: OperatorRole
    kind: RemoteRequestKind
    status: RemoteRequestStatus
    source: str
    source_ip: str | None = None
    user_agent: str | None = None
    target_kind: str | None = None
    target_id: int | None = None
    target_label: str | None = None
    idempotency_key: str | None = None
    summary: str
    error: str | None = None
    payload_preview: str | None = None
    result_preview: str | None = None
    requested_at: datetime
    resolved_at: datetime | None = None


class DashboardSkillbookView(BaseModel):
    project_id: int
    project_label: str
    skills: list[SkillPinView] = Field(default_factory=list)


class DashboardSkillRegistrySkillView(BaseModel):
    name: str
    source: str | None = None
    status: str | None = None
    lane_count: int = 0
    lanes: list[str] = Field(default_factory=list)
    successful_run_count: int = 0
    pinned_projects: list[str] = Field(default_factory=list)


class DashboardSkillRegistryLaneView(BaseModel):
    instance_id: int
    instance_name: str
    connected: bool
    cwd: str | None = None
    project_labels: list[str] = Field(default_factory=list)
    skill_count: int = 0
    relevant_skill_count: int = 0
    successful_run_count: int = 0
    gap_count: int = 0
    skills: list[DashboardSkillRegistrySkillView] = Field(default_factory=list)


class DashboardSkillRegistryProjectView(BaseModel):
    project_id: int
    project_label: str
    lane_count: int = 0
    mission_count: int = 0
    successful_run_count: int = 0
    pinned_skill_count: int = 0
    live_skill_count: int = 0
    matched_skill_count: int = 0
    missing_skills: list[str] = Field(default_factory=list)
    skills: list[DashboardSkillRegistrySkillView] = Field(default_factory=list)


class DashboardSkillGapView(BaseModel):
    mission_id: int
    mission_name: str
    lane_label: str | None = None
    project_label: str | None = None
    missing_skills: list[str] = Field(default_factory=list)
    recommended_action: str


class DashboardSkillsRegistryView(BaseModel):
    headline: str
    summary: str
    lanes: list[DashboardSkillRegistryLaneView] = Field(default_factory=list)
    projects: list[DashboardSkillRegistryProjectView] = Field(default_factory=list)
    gaps: list[DashboardSkillGapView] = Field(default_factory=list)


class DashboardIntegrationLaneView(BaseModel):
    instance_id: int
    instance_name: str
    connected: bool
    status: LaneCapabilityStatus
    match_types: list[IntegrationInventorySourceKind] = Field(default_factory=list)
    summary: str


class DashboardIntegrationInventoryItemView(BaseModel):
    id: str
    name: str
    kind: str
    tracked: bool = False
    source_kinds: list[IntegrationInventorySourceKind] = Field(default_factory=list)
    project_labels: list[str] = Field(default_factory=list)
    base_url: str | None = None
    auth_scheme: str | None = None
    auth_status: IntegrationAuthStatus | None = None
    readiness: IntegrationInventoryReadiness = "observed"
    level: SignalLevel = "info"
    lane_ready_count: int = 0
    lane_match_count: int = 0
    summary: str
    recommended_action: str
    notes: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    lanes: list[DashboardIntegrationLaneView] = Field(default_factory=list)


class DashboardIntegrationsInventoryView(BaseModel):
    headline: str
    summary: str
    ready_count: int = 0
    gap_count: int = 0
    tracked_count: int = 0
    observed_count: int = 0
    items: list[DashboardIntegrationInventoryItemView] = Field(default_factory=list)


class DashboardAuthPostureView(BaseModel):
    headline: str
    summary: str
    satisfied_count: int = 0
    missing_count: int = 0
    degraded_count: int = 0


class DashboardAccessPostureView(BaseModel):
    headline: str
    summary: str
    team_count: int = 0
    operator_count: int = 0
    api_key_count: int = 0
    recent_remote_request_count: int = 0


class DashboardOpsMeshView(BaseModel):
    headline: str
    summary: str
    task_inbox: DashboardTaskInboxView
    auth_posture: DashboardAuthPostureView
    access_posture: DashboardAccessPostureView
    integrations_inventory: DashboardIntegrationsInventoryView
    skills_registry: DashboardSkillsRegistryView
    skillbooks: list[DashboardSkillbookView] = Field(default_factory=list)
    teams: list[TeamView] = Field(default_factory=list)
    operators: list[OperatorView] = Field(default_factory=list)
    remote_requests: list[RemoteRequestView] = Field(default_factory=list)
    vault_secrets: list[VaultSecretView] = Field(default_factory=list)
    integrations: list[IntegrationView] = Field(default_factory=list)
    notification_routes: list[NotificationRouteView] = Field(default_factory=list)
    outbound_deliveries: list[OutboundDeliveryView] = Field(default_factory=list)
    lane_snapshots: list[LaneSnapshotView] = Field(default_factory=list)


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


class DashboardLearningReviewView(BaseModel):
    id: str
    level: SignalLevel
    title: str
    summary: str
    recommendation: str
    evidence_count: int = 0
    project_id: int | None = None
    project_label: str | None = None
    mission_id: int | None = None
    recommended_toolsets: list[str] = Field(default_factory=list)


class DashboardCortexView(BaseModel):
    headline: str
    summary: str
    doctrines: list[DashboardDoctrineView] = Field(default_factory=list)
    inoculations: list[DashboardInoculationView] = Field(default_factory=list)
    reviews: list[DashboardLearningReviewView] = Field(default_factory=list)


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


class DashboardControlChatView(BaseModel):
    headline: str
    summary: str
    input_placeholder: str
    messages: list[ControlChatMessageView] = Field(default_factory=list)


class DashboardAttentionQueueView(BaseModel):
    enabled: bool = True
    headline: str
    summary: str
    actions: list[AttentionQueueActionView] = Field(default_factory=list)


class DashboardView(BaseModel):
    brief: DashboardBriefView
    control_chat: DashboardControlChatView
    attention_queue: DashboardAttentionQueueView
    launchpad: DashboardLaunchpadView
    radar: DashboardRadarView
    browser_posture: BrowserPostureView | None = None
    gateway_capability: GatewayCapabilityView
    gateway_bootstrap: GatewayBootstrapView
    ops_mesh: DashboardOpsMeshView
    economy: DashboardEconomyView
    interference: DashboardInterferenceView
    continuity: DashboardContinuityView
    recall: DashboardRecallView
    dream_deck: DashboardDreamDeckView
    cortex: DashboardCortexView
    reflex_deck: DashboardReflexDeckView
    instances: list[InstanceView]
    missions: list[MissionView]
    projects: list[ProjectView]
    playbooks: list[PlaybookView]
    task_blueprints: list[TaskBlueprintView]
    integrations: list[IntegrationView]
    notification_routes: list[NotificationRouteView]
    skill_pins: list[SkillPinView]
    lane_snapshots: list[LaneSnapshotView]
    events: list[EventView]
