const state = {
  dashboard: null,
  diagnostics: null,
  setup: null,
  socket: null,
  refreshTimer: null,
  radarReserveExpanded: false,
  lastBootstrapResult: null,
};

const heroStatsEl = document.querySelector("#hero-stats");
const briefHeadlineEl = document.querySelector("#brief-headline");
const briefSummaryEl = document.querySelector("#brief-summary");
const briefActionsEl = document.querySelector("#brief-actions");
const chatHeadlineEl = document.querySelector("#chat-headline");
const chatSummaryEl = document.querySelector("#chat-summary");
const chatPresenceEl = document.querySelector("#chat-presence");
const opsChatEl = document.querySelector("#ops-chat");
const controlChatFormEl = document.querySelector("#control-chat-form");
const controlChatInputEl = document.querySelector("#control-chat-input");
const controlChatHintEl = document.querySelector("#control-chat-hint");
const launchpadHeadlineEl = document.querySelector("#launchpad-headline");
const launchpadSummaryEl = document.querySelector("#launchpad-summary");
const launchpadOpportunitiesEl = document.querySelector("#launchpad-opportunities");
const radarHeadlineEl = document.querySelector("#radar-headline");
const radarSummaryEl = document.querySelector("#radar-summary");
const radarSignalsEl = document.querySelector("#radar-signals");
const backstageSummaryEl = document.querySelector("#backstage-summary");
const backstageMissionCountEl = document.querySelector("#backstage-mission-count");
const backstageOpsCountEl = document.querySelector("#backstage-ops-count");
const backstageEventCountEl = document.querySelector("#backstage-event-count");
const opsShellSummaryEl = document.querySelector("#ops-shell-summary");
const opsTaskCountEl = document.querySelector("#ops-task-count");
const opsRouteCountEl = document.querySelector("#ops-route-count");
const opsIntegrationCountEl = document.querySelector("#ops-integration-count");
const opsSnapshotCountEl = document.querySelector("#ops-snapshot-count");
const taskInboxHeadlineEl = document.querySelector("#task-inbox-headline");
const taskInboxSummaryEl = document.querySelector("#task-inbox-summary");
const taskInboxItemsEl = document.querySelector("#task-inbox-items");
const authPostureHeadlineEl = document.querySelector("#auth-posture-headline");
const authPostureSummaryEl = document.querySelector("#auth-posture-summary");
const authSatisfiedCountEl = document.querySelector("#auth-satisfied-count");
const authMissingCountEl = document.querySelector("#auth-missing-count");
const authDegradedCountEl = document.querySelector("#auth-degraded-count");
const integrationsInventoryHeadlineEl = document.querySelector(
  "#integrations-inventory-headline",
);
const integrationsInventorySummaryEl = document.querySelector(
  "#integrations-inventory-summary",
);
const integrationsInventoryReadyCountEl = document.querySelector(
  "#integrations-inventory-ready-count",
);
const integrationsInventoryGapCountEl = document.querySelector(
  "#integrations-inventory-gap-count",
);
const integrationsInventoryObservedCountEl = document.querySelector(
  "#integrations-inventory-observed-count",
);
const integrationsInventoryListEl = document.querySelector("#integrations-inventory-list");
const accessPostureHeadlineEl = document.querySelector("#access-posture-headline");
const accessPostureSummaryEl = document.querySelector("#access-posture-summary");
const accessTeamCountEl = document.querySelector("#access-team-count");
const accessOperatorCountEl = document.querySelector("#access-operator-count");
const accessKeyCountEl = document.querySelector("#access-key-count");
const accessRequestCountEl = document.querySelector("#access-request-count");
const taskBlueprintsEl = document.querySelector("#task-blueprints");
const skillsRegistryHeadlineEl = document.querySelector("#skills-registry-headline");
const skillsRegistrySummaryEl = document.querySelector("#skills-registry-summary");
const skillsRegistryGapsEl = document.querySelector("#skills-registry-gaps");
const skillsRegistryProjectsEl = document.querySelector("#skills-registry-projects");
const skillsRegistryLanesEl = document.querySelector("#skills-registry-lanes");
const skillbooksEl = document.querySelector("#skillbooks");
const teamsListEl = document.querySelector("#teams-list");
const operatorsListEl = document.querySelector("#operators-list");
const remoteRequestsEl = document.querySelector("#remote-requests");
const vaultSecretsEl = document.querySelector("#vault-secrets");
const integrationsListEl = document.querySelector("#integrations-list");
const notificationRoutesEl = document.querySelector("#notification-routes");
const laneSnapshotsEl = document.querySelector("#lane-snapshots");
const continuityHeadlineEl = document.querySelector("#continuity-headline");
const continuitySummaryEl = document.querySelector("#continuity-summary");
const continuityPacketsEl = document.querySelector("#continuity-packets");
const dreamHeadlineEl = document.querySelector("#dream-headline");
const dreamSummaryEl = document.querySelector("#dream-summary");
const dreamsEl = document.querySelector("#dreams");
const cortexHeadlineEl = document.querySelector("#cortex-headline");
const cortexSummaryEl = document.querySelector("#cortex-summary");
const cortexDoctrinesEl = document.querySelector("#cortex-doctrines");
const cortexInoculationsEl = document.querySelector("#cortex-inoculations");
const reflexHeadlineEl = document.querySelector("#reflex-headline");
const reflexSummaryEl = document.querySelector("#reflex-summary");
const reflexesEl = document.querySelector("#reflexes");
const intelligenceShellEl = document.querySelector("#intelligence-shell");
const intelligenceShellSummaryEl = document.querySelector("#intelligence-shell-summary");
const intelligenceContinuityCountEl = document.querySelector("#intelligence-continuity-count");
const intelligenceDreamCountEl = document.querySelector("#intelligence-dream-count");
const intelligenceDoctrineCountEl = document.querySelector("#intelligence-doctrine-count");
const intelligenceInoculationCountEl = document.querySelector("#intelligence-inoculation-count");
const intelligenceReflexCountEl = document.querySelector("#intelligence-reflex-count");
const missionsEl = document.querySelector("#missions");
const missionPresetsEl = document.querySelector("#mission-presets");
const instancesEl = document.querySelector("#instances");
const taskFormEl = document.querySelector("#task-form");
const taskInstanceSelectEl = document.querySelector("#task-instance-select");
const taskProjectSelectEl = document.querySelector("#task-project-select");
const teamFormEl = document.querySelector("#team-form");
const operatorFormEl = document.querySelector("#operator-form");
const operatorTeamSelectEl = document.querySelector("#operator-team-select");
const skillPinFormEl = document.querySelector("#skill-pin-form");
const skillProjectSelectEl = document.querySelector("#skill-project-select");
const vaultSecretFormEl = document.querySelector("#vault-secret-form");
const integrationFormEl = document.querySelector("#integration-form");
const integrationProjectSelectEl = document.querySelector("#integration-project-select");
const integrationVaultSecretSelectEl = document.querySelector("#integration-vault-secret-select");
const notificationRouteFormEl = document.querySelector("#notification-route-form");
const notificationRouteVaultSecretSelectEl = document.querySelector(
  "#notification-route-vault-secret-select",
);
const onboardingHeadlineEl = document.querySelector("#onboarding-headline");
const onboardingSummaryEl = document.querySelector("#onboarding-summary");
const onboardingChecklistEl = document.querySelector("#onboarding-checklist");
const onboardingModeLabelEl = document.querySelector("#onboarding-mode-label");
const onboardingFlowPillEl = document.querySelector("#onboarding-flow-pill");
const onboardingModeSummaryEl = document.querySelector("#onboarding-mode-summary");
const gatewayBootstrapProfileEl = document.querySelector("#gateway-bootstrap-profile");
const onboardingResultEl = document.querySelector("#onboarding-result");
const onboardingFormEl = document.querySelector("#onboarding-form");
const onboardingSetupModeEl = document.querySelector("#onboarding-setup-mode");
const onboardingSetupFlowEl = document.querySelector("#onboarding-setup-flow");
const onboardingInstanceModeEl = document.querySelector("#onboarding-instance-mode");
const onboardingInstanceSelectEl = document.querySelector("#onboarding-instance-select");
const libraryShellEl = document.querySelector("#library-shell");
const libraryShellSummaryEl = document.querySelector("#library-shell-summary");
const libraryPlaybookCountEl = document.querySelector("#library-playbook-count");
const libraryProjectCountEl = document.querySelector("#library-project-count");
const diagnosticsEl = document.querySelector("#diagnostics");
const healthShellEl = document.querySelector("#health-shell");
const healthShellSummaryEl = document.querySelector("#health-shell-summary");
const healthShellStatusEl = document.querySelector("#health-shell-status");
const playbooksEl = document.querySelector("#playbooks");
const projectsEl = document.querySelector("#projects");
const eventsEl = document.querySelector("#events");
const activityShellEl = document.querySelector("#activity-shell");
const activityShellSummaryEl = document.querySelector("#activity-shell-summary");
const activityShellCountEl = document.querySelector("#activity-shell-count");
const toastEl = document.querySelector("#toast");
const eventFilterEl = document.querySelector("#event-filter");
const eventHideNoiseEl = document.querySelector("#event-hide-noise");
const instanceFormEl = document.querySelector("#instance-form");
const missionFormEl = document.querySelector("#mission-form");
const missionAdvancedEl = document.querySelector("#mission-advanced");
const missionInstanceSelectEl = document.querySelector("#mission-instance-select");
const missionProjectSelectEl = document.querySelector("#mission-project-select");
const transportSelectEl = document.querySelector("#transport-select");
const DISCLOSURE_SHELL_IDS = [
  "backstage-shell",
  "ops-shell",
  "intelligence-shell",
  "library-shell",
  "health-shell",
  "activity-shell",
];

const MISSION_PRESETS = [
  {
    id: "ship",
    name: "Ship Feature",
    description: "Build, verify, and keep going until a visible feature milestone lands.",
    objective:
      "Build the highest-leverage product improvement in this workspace, verify it, and keep iterating until you either reach a solid milestone or hit a real blocker.",
    model: "gpt-5.4",
    maxTurns: "6",
    useBuiltinAgents: true,
    runVerification: true,
    autoCommit: true,
    pauseOnApproval: true,
  },
  {
    id: "rescue",
    name: "Rescue Build",
    description: "Triage failing tests, runtime errors, and broken flows until the system is stable.",
    objective:
      "Triage the biggest reliability issue in this workspace, reproduce it, implement fixes, run verification, and continue until the product is stable again.",
    model: "gpt-5.4",
    maxTurns: "5",
    useBuiltinAgents: true,
    runVerification: true,
    autoCommit: false,
    pauseOnApproval: true,
  },
  {
    id: "map",
    name: "Map Codebase",
    description: "Create durable understanding before editing risky areas.",
    objective:
      "Map the codebase, identify the most important moving pieces, and produce a concise operator handoff that explains where to build next and where the risks live.",
    model: "gpt-5.4-mini",
    maxTurns: "3",
    useBuiltinAgents: true,
    runVerification: false,
    autoCommit: false,
    pauseOnApproval: true,
  },
  {
    id: "polish",
    name: "Polish UX",
    description: "Tighten visuals, interaction flow, and verification in one loop.",
    objective:
      "Improve the user experience in this workspace, focusing on hierarchy, clarity, and polish. Verify changes in-browser and keep iterating until the interface feels production-ready.",
    model: "gpt-5.4",
    maxTurns: "4",
    useBuiltinAgents: false,
    runVerification: true,
    autoCommit: true,
    pauseOnApproval: true,
  },
];

function showToast(message, isError = false) {
  toastEl.hidden = false;
  toastEl.textContent = message;
  toastEl.style.border = `1px solid ${isError ? "rgba(255,123,149,.45)" : "rgba(111,255,210,.4)"}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toastEl.hidden = true;
  }, 3200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function pill(label, tone = "") {
  return `<span class="pill ${tone}">${escapeHtml(label)}</span>`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function formatRelativeTimestamp(value) {
  if (!value) {
    return "No activity yet";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  const diffMinutes = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 60000));
  if (diffMinutes < 1) {
    return "just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  return `${Math.floor(diffHours / 24)}d ago`;
}

function summarizeCount(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function computeNextRunAt(lastRunAt, cadenceMinutes) {
  if (!cadenceMinutes) {
    return null;
  }
  if (!lastRunAt) {
    return new Date().toISOString();
  }
  const parsed = new Date(lastRunAt);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return new Date(parsed.getTime() + cadenceMinutes * 60000).toISOString();
}

function clipText(value, maxLength = 220) {
  const text = String(value ?? "").trim();
  if (!text) {
    return "";
  }
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

function chatActionButton(label, action, dataset = {}, extraClass = "") {
  const attrs = Object.entries(dataset)
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `data-${key}="${escapeHtml(String(value))}"`)
    .join(" ");
  return `<button type="button" class="${escapeHtml(extraClass)}" data-action="${escapeHtml(action)}"${attrs ? ` ${attrs}` : ""}>${escapeHtml(label)}</button>`;
}

function labelizeActionKind(value) {
  return String(value ?? "")
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function renderChatCard({ title, meta = [], body = "", note = "", actions = [] }) {
  return `
    <article class="chat-card">
      <div class="chat-card-head">
        <strong>${escapeHtml(title)}</strong>
        <div class="pill-row">${meta.filter(Boolean).join("")}</div>
      </div>
      ${body ? `<p>${escapeHtml(body)}</p>` : ""}
      ${note ? `<div class="small-muted">${escapeHtml(note)}</div>` : ""}
      ${actions.length ? `<div class="chat-actions">${actions.join("")}</div>` : ""}
    </article>
  `;
}

function renderControlChatEntry(message) {
  const isUser = message.role === "user";
  return renderChatMessage({
    stamp: isUser ? "YOU" : "OZ",
    lane: isUser ? "Directive" : "Zues",
    tone: isUser ? "user" : "assistant",
    compact: true,
    title: message.content,
    meta: [
      !isUser && message.action_kind
        ? pill(labelizeActionKind(message.action_kind), "ok")
        : "",
      message.mission_id ? pill(`mission ${message.mission_id}`) : "",
      !isUser && message.target_label ? pill(message.target_label) : "",
      `<span class="chat-age">${escapeHtml(formatRelativeTimestamp(message.created_at))}</span>`,
    ],
  });
}

function renderChatMessage({
  stamp = "OZ",
  lane = "",
  tone = "",
  compact = false,
  title,
  meta = [],
  body = "",
  note = "",
  code = "",
  items = [],
  cards = [],
  actions = [],
}) {
  return `
    <article class="chat-message ${compact ? "chat-compact " : ""}${tone ? `chat-${escapeHtml(tone)}` : ""}">
      <div class="chat-avatar">${escapeHtml(stamp)}</div>
      <div class="chat-bubble">
        <div class="chat-message-head">
          <div class="chat-heading">
            ${lane ? `<span class="chat-lane">${escapeHtml(lane)}</span>` : ""}
            <h3>${escapeHtml(title)}</h3>
          </div>
          <div class="chat-meta">${meta.filter(Boolean).join("")}</div>
        </div>
        ${body ? `<p class="chat-body">${escapeHtml(body)}</p>` : ""}
        ${note ? `<div class="chat-note">${escapeHtml(note)}</div>` : ""}
        ${code ? `<pre class="chat-code">${escapeHtml(code)}</pre>` : ""}
        ${
          items.length
            ? `<div class="chat-inline-list">${items
                .map((item) => `<span class="chat-inline-item">${escapeHtml(item)}</span>`)
                .join("")}</div>`
            : ""
        }
        ${cards.length ? `<div class="chat-card-grid">${cards.join("")}</div>` : ""}
        ${actions.length ? `<div class="chat-actions">${actions.join("")}</div>` : ""}
      </div>
    </article>
  `;
}

function disclosureKey(id) {
  return `openzues:${id}:open`;
}

function restoreDisclosureState() {
  DISCLOSURE_SHELL_IDS.forEach((id) => {
    const element = document.getElementById(id);
    if (!element) {
      return;
    }
    try {
      const saved = window.localStorage.getItem(disclosureKey(id));
      if (saved !== null) {
        element.open = saved === "1";
      }
    } catch {}
    element.addEventListener("toggle", () => {
      try {
        window.localStorage.setItem(disclosureKey(id), element.open ? "1" : "0");
      } catch {}
    });
  });
}

function toneForMissionStatus(status) {
  if (status === "active" || status === "completed") {
    return "ok";
  }
  if (status === "blocked" || status === "paused") {
    return "warn";
  }
  if (status === "failed") {
    return "bad";
  }
  return "";
}

function toneForSignal(level) {
  if (level === "critical") {
    return "bad";
  }
  if (level === "warn") {
    return "warn";
  }
  if (level === "ready") {
    return "ok";
  }
  return "";
}

function toneForRadarPosture(posture) {
  if (posture === "hot") {
    return "bad";
  }
  if (posture === "watch") {
    return "warn";
  }
  if (posture === "steady") {
    return "ok";
  }
  return "";
}

function toneForBriefStatus(status) {
  if (status === "blocked") {
    return "warn";
  }
  if (status === "active") {
    return "ok";
  }
  if (status === "mixed") {
    return "warn";
  }
  return "";
}

function toneForEconomyState(state) {
  if (state === "compounding") {
    return "ok";
  }
  if (state === "leaking") {
    return "bad";
  }
  if (state === "speculative") {
    return "warn";
  }
  return "";
}

function toneForContinuityState(state) {
  if (state === "anchored") {
    return "ok";
  }
  if (state === "fragile") {
    return "bad";
  }
  if (state === "warming") {
    return "warn";
  }
  return "";
}

function summarize(value) {
  return escapeHtml(JSON.stringify(value, null, 2));
}

function normalizeError(error) {
  return error instanceof Error ? error.message : String(error);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text);
      throw new Error(parsed.detail || text);
    } catch {
      throw new Error(text || `${response.status} ${response.statusText}`);
    }
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function loadDashboard() {
  state.dashboard = await api("/api/dashboard");
  render();
}

async function loadDiagnostics() {
  state.diagnostics = await api("/api/diagnostics");
  renderDiagnostics();
}

async function loadSetup() {
  state.setup = await api("/api/setup");
  renderOnboarding();
}

function scheduleRefresh() {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => {
    Promise.all([loadDashboard(), loadSetup()]).catch((error) =>
      showToast(normalizeError(error), true),
    );
  }, 250);
}

function renderHero() {
  const instances = state.dashboard?.instances ?? [];
  const missions = state.dashboard?.missions ?? [];
  const projects = state.dashboard?.projects ?? [];
  const radarSignals = state.dashboard?.radar?.signals ?? [];
  const attentionQueue = state.dashboard?.attention_queue;
  const connected = instances.filter((instance) => instance.connected).length;
  const approvals = instances.reduce(
    (total, instance) => total + instance.unresolved_requests.length,
    0,
  );
  const activeMissions = missions.filter((mission) => mission.status === "active").length;
  const blockedMissions = missions.filter((mission) => mission.status === "blocked").length;
  const readySignals = radarSignals.filter((signal) => signal.level === "ready").length;
  const stats = [
    {
      label: "Live Lanes",
      value: connected,
      note: `${summarizeCount(instances.length, "instance")} registered`,
    },
    {
      label: "Active Loops",
      value: activeMissions,
      note: `${summarizeCount(readySignals, "ready cue")} in reserve`,
    },
    {
      label: "Attention",
      value: blockedMissions,
      note: attentionQueue?.enabled
        ? `${summarizeCount(approvals, "approval")} pending | auto`
        : `${summarizeCount(approvals, "approval")} pending`,
    },
    {
      label: "Projects",
      value: projects.length,
      note: `${summarizeCount(missions.length, "mission")} tracked`,
    },
  ];

  heroStatsEl.innerHTML = stats
    .map(
      (stat) => `
        <article class="stat">
          <span class="stat-label">${escapeHtml(stat.label)}</span>
          <span class="stat-value">${escapeHtml(stat.value)}</span>
          <span class="stat-note">${escapeHtml(stat.note)}</span>
        </article>
      `,
    )
    .join("");
}

function booleanBadge(enabled, label) {
  return enabled ? pill(label, "ok") : "";
}

function renderBrief() {
  const brief = state.dashboard?.brief;
  if (!brief) {
    briefHeadlineEl.textContent = "Waiting for dashboard data...";
    briefSummaryEl.textContent = "";
    briefActionsEl.innerHTML = "";
    return;
  }
  briefHeadlineEl.textContent = brief.headline;
  briefSummaryEl.textContent = brief.summary;
  briefActionsEl.innerHTML = brief.next_actions.length
    ? brief.next_actions.map((action) => `<span class="brief-action">${escapeHtml(action)}</span>`).join("")
    : `<span class="brief-action">No immediate operator action needed.</span>`;
}

function renderLaunchpad() {
  const launchpad = state.dashboard?.launchpad;
  if (!launchpad) {
    launchpadHeadlineEl.textContent = "Synthesizing next runs...";
    launchpadSummaryEl.textContent = "";
    launchpadOpportunitiesEl.innerHTML = "";
    return;
  }

  launchpadHeadlineEl.textContent = launchpad.headline;
  launchpadSummaryEl.textContent = launchpad.summary;

  if (!launchpad.opportunities.length) {
    launchpadOpportunitiesEl.innerHTML = `
      <article class="ghost-card ghost-empty">
        <strong>No ghost launches yet.</strong>
        <p class="small-muted">
          Register a project or connect another lane and OpenZues will start suggesting mission
          drafts here.
        </p>
      </article>
    `;
    return;
  }

  launchpadOpportunitiesEl.innerHTML = launchpad.opportunities
    .map(
      (opportunity) => `
        <article class="ghost-card ghost-${escapeHtml(opportunity.impact)}">
          <div class="signal-meta">
            ${pill(opportunity.impact, opportunity.impact === "high" ? "ok" : opportunity.impact === "medium" ? "warn" : "")}
            ${pill(opportunity.kind)}
          </div>
          <h4>${escapeHtml(opportunity.title)}</h4>
          <p>${escapeHtml(opportunity.summary)}</p>
          <div class="ghost-why">${escapeHtml(opportunity.why_now)}</div>
          <div class="ghost-actions">
            <button
              type="button"
              class="ghost"
              data-action="apply-opportunity"
              data-opportunity-id="${opportunity.id}"
            >
              ${escapeHtml(opportunity.action_label || "Load draft")}
            </button>
            <button
              type="button"
              data-action="launch-opportunity"
              data-opportunity-id="${opportunity.id}"
            >
              Launch now
            </button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderChat() {
  if (!chatHeadlineEl || !chatSummaryEl || !chatPresenceEl || !opsChatEl) {
    return;
  }

  const dashboard = state.dashboard;
  if (!dashboard) {
    chatHeadlineEl.textContent = "Waiting for live mission context...";
    chatSummaryEl.textContent =
      "OpenZues will narrate mission state, autonomy pressure, and operator choices here.";
    chatPresenceEl.innerHTML = "";
    if (controlChatInputEl) {
      controlChatInputEl.placeholder = "Describe the next thing you want built, fixed, or verified";
    }
    if (controlChatHintEl) {
      controlChatHintEl.textContent =
        "Chat can decide when to wait, resume, recover, harden, or launch without making you work through manual action buttons first.";
    }
    opsChatEl.innerHTML = `
      <article class="chat-empty">
        <strong>No transcript yet.</strong>
        <p class="small-muted">
          Connect a Codex lane or launch a mission and the control plane will start writing the live
          conversation here.
        </p>
      </article>
    `;
    return;
  }

  const brief = dashboard.brief;
  const controlChat = dashboard.control_chat;
  const attentionQueue = dashboard.attention_queue;
  const radar = dashboard.radar;
  const launchpad = dashboard.launchpad;
  const opsMesh = dashboard.ops_mesh;
  const economy = dashboard.economy;
  const interference = dashboard.interference;
  const continuity = dashboard.continuity;
  const dreamDeck = dashboard.dream_deck;
  const cortex = dashboard.cortex;
  const reflexDeck = dashboard.reflex_deck;
  const missions = dashboard.missions ?? [];
  const instances = dashboard.instances ?? [];
  const events = dashboard.events ?? [];

  const connectedCount = instances.filter((instance) => instance.connected).length;
  const activeMissions = missions.filter((mission) => mission.status === "active");
  const blockedMissions = missions.filter((mission) => mission.status === "blocked");
  const pendingApprovals = instances.reduce(
    (total, instance) => total + instance.unresolved_requests.length,
    0,
  );
  const readyDreams = (dreamDeck?.dreams ?? []).filter((dream) => dream.status !== "forming").length;
  const dueTasks = (opsMesh?.task_inbox?.tasks ?? []).filter((task) =>
    ["due", "attention", "running"].includes(task.status),
  ).length;

  chatHeadlineEl.textContent = controlChat?.headline || brief?.headline || "Control plane transcript";
  chatSummaryEl.textContent =
    attentionQueue?.summary ||
    controlChat?.summary ||
    radar?.summary ||
    brief?.summary ||
    "Mission state will condense into the transcript.";
  if (controlChatInputEl && controlChat?.input_placeholder) {
    controlChatInputEl.placeholder = controlChat.input_placeholder;
  }
  if (controlChatHintEl) {
    controlChatHintEl.textContent =
      controlChat?.summary ||
    "Chat can decide when to wait, resume, recover, harden, or launch without making you work through manual action buttons first.";
  }
  chatPresenceEl.innerHTML = [
    pill(`${connectedCount} live lanes`, connectedCount ? "ok" : ""),
    pill(`${activeMissions.length} active loops`, activeMissions.length ? "ok" : ""),
    attentionQueue?.enabled ? pill("attention auto", "ok") : "",
    blockedMissions.length ? pill(`${blockedMissions.length} blocked`, "warn") : "",
    pendingApprovals ? pill(`${pendingApprovals} approvals`, "warn") : "",
    dueTasks ? pill(`${dueTasks} ops cues`, dueTasks > 1 ? "warn" : "ok") : "",
    readyDreams ? pill(`${readyDreams} memory passes`, "ok") : "",
  ]
    .filter(Boolean)
    .join("");

  const messages = [];

  if (controlChat?.messages?.length) {
    messages.push(...controlChat.messages.map((message) => renderControlChatEntry(message)));
  }

  if (attentionQueue?.actions?.length) {
    const latestAction = attentionQueue.actions[attentionQueue.actions.length - 1];
    messages.push(
      renderChatMessage({
        stamp: "AQ",
        lane: "Attention queue",
        tone: latestAction.status === "executed" ? "ok" : "warn",
        compact: true,
        title: attentionQueue.headline,
        meta: [
          pill(latestAction.status, latestAction.status === "executed" ? "ok" : "warn"),
          latestAction.action_kind ? pill(labelizeActionKind(latestAction.action_kind)) : "",
          `<span class="chat-age">${escapeHtml(formatRelativeTimestamp(latestAction.created_at))}</span>`,
        ],
        body: attentionQueue.summary,
      }),
    );
  }

  if (brief) {
    messages.push(
      renderChatMessage({
        stamp: "OZ",
        lane: "Control plane",
        tone: toneForBriefStatus(brief.status),
        title: brief.headline,
        meta: [pill(brief.status, toneForBriefStatus(brief.status))],
        body: brief.summary,
        items: brief.next_actions.length
          ? brief.next_actions
          : ["No immediate operator action needed."],
      }),
    );
  }

  if (radar) {
    const signalCards = (radar.signals ?? []).slice(0, 4).map((signal) =>
      renderChatCard({
        title: signal.title,
        meta: [
          pill(signal.level, toneForSignal(signal.level)),
          pill(signal.lane),
          signal.mission_id ? pill(`mission ${signal.mission_id}`) : "",
          signal.instance_id ? pill(`lane ${signal.instance_id}`) : "",
        ],
        body: signal.detail,
        note: signal.action
          ? signal.action
          : signal.freshness_minutes != null
            ? `Freshness ${signal.freshness_minutes}m`
            : "",
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "RD",
        lane: "Autonomy radar",
        tone: toneForRadarPosture(radar.posture),
        title: radar.posture === "steady" ? "Field is steady" : "Watch the field",
        meta: [pill(radar.posture, toneForRadarPosture(radar.posture))],
        body: radar.summary,
        cards: signalCards,
      }),
    );
  }

  if (launchpad?.opportunities?.length) {
    const opportunityCards = launchpad.opportunities.slice(0, 3).map((opportunity) =>
      renderChatCard({
        title: opportunity.title,
        meta: [
          pill(opportunity.impact, opportunity.impact === "high" ? "ok" : "warn"),
          pill(opportunity.kind),
        ],
        body: opportunity.summary,
        note: opportunity.why_now,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "GL",
        lane: "Ghost launches",
        tone: launchpad.opportunities.some((opportunity) => opportunity.impact === "high")
          ? "ok"
          : "warn",
        title: launchpad.headline,
        body: launchpad.summary,
        cards: opportunityCards,
      }),
    );
  }

  const missionPriority = {
    active: 0,
    blocked: 1,
    paused: 2,
    failed: 3,
    completed: 4,
  };
  const visibleMissions = [...missions]
    .sort((left, right) => {
      const priorityDelta =
        (missionPriority[left.status] ?? 9) - (missionPriority[right.status] ?? 9);
      if (priorityDelta !== 0) {
        return priorityDelta;
      }
      return new Date(right.last_activity_at || right.updated_at).getTime() -
        new Date(left.last_activity_at || left.updated_at).getTime();
    })
    .slice(0, 6);

  visibleMissions.forEach((mission) => {
    const progressSuffix = mission.max_turns
      ? `${mission.turns_completed}/${mission.max_turns} turns`
      : `${mission.turns_completed} turns complete`;
    const noteSegments = [
      mission.suggested_action ? `Operator next: ${clipText(mission.suggested_action, 180)}` : "",
      mission.last_error ? `Error: ${clipText(mission.last_error, 180)}` : "",
      mission.last_checkpoint ? `Handoff: ${clipText(mission.last_checkpoint, 180)}` : "",
    ].filter(Boolean);
    messages.push(
      renderChatMessage({
        stamp: `M${mission.id}`,
        lane: mission.instance_name || `Mission ${mission.id}`,
        tone: toneForMissionStatus(mission.status),
        title: mission.name,
        meta: [
          pill(mission.status, toneForMissionStatus(mission.status)),
          mission.phase ? pill(mission.phase) : "",
          mission.project_label ? pill(mission.project_label) : "",
          pill(mission.model),
          `<span class="chat-age">${escapeHtml(formatRelativeTimestamp(mission.last_activity_at))}</span>`,
        ],
        body: mission.last_commentary || mission.objective,
        note: noteSegments.join(" "),
        code: mission.current_command || "",
        items: [
          progressSuffix,
          `${formatNumber(mission.command_count)} commands`,
          `${formatNumber(mission.total_tokens)} tokens`,
          mission.thread_id ? `thread ${mission.thread_id}` : "thread pending",
        ],
      }),
    );
  });

  if (opsMesh) {
    const taskCards = (opsMesh.task_inbox?.items ?? []).slice(0, 3).map((item) =>
      renderChatCard({
        title: item.title,
        meta: [
          pill(item.source),
          pill(item.urgency, toneForInboxUrgency(item.urgency)),
          item.project_label ? pill(item.project_label) : "",
        ],
        body: item.summary,
        note: clipText(item.recommended_action, 160),
      }),
    );
    const remoteCards = (opsMesh.remote_requests ?? []).slice(-2).reverse().map((request) =>
      renderChatCard({
        title: request.target_label || request.kind,
        meta: [
          pill(request.kind),
          pill(request.status, toneForRemoteStatus(request.status)),
          request.operator_role ? pill(request.operator_role, toneForOperatorRole(request.operator_role)) : "",
        ],
        body: request.summary,
        note: [
          request.operator_name || "Unknown operator",
          request.team_name ? `via ${request.team_name}` : "",
          request.source_ip ? `from ${request.source_ip}` : "",
        ]
          .filter(Boolean)
          .join(" "),
      }),
    );

    if (taskCards.length || remoteCards.length) {
      messages.push(
        renderChatMessage({
          stamp: "OP",
          lane: "Ops mesh",
          tone:
            opsMesh.task_inbox.items.some((item) => item.urgency === "critical") ||
            opsMesh.auth_posture.degraded_count
              ? "warn"
              : "ok",
          title: opsMesh.headline,
          meta: [
            pill(
              `${opsMesh.task_inbox.items.length} inbox`,
              opsMesh.task_inbox.items.length ? "ok" : "",
            ),
            pill(
              `${opsMesh.remote_requests.length} remote`,
              opsMesh.remote_requests.length ? "warn" : "",
            ),
            pill(
              `${opsMesh.integrations.length} integrations`,
              opsMesh.integrations.length ? "ok" : "",
            ),
          ],
          body: opsMesh.summary,
          note: `${opsMesh.task_inbox.summary} ${opsMesh.access_posture.summary}`,
          cards: [...taskCards, ...remoteCards],
        }),
      );
    }
  }

  if (economy?.scopes?.length) {
    const economyCards = [...economy.scopes]
      .sort((left, right) => right.score - left.score)
      .slice(0, 3)
      .map((scope) =>
        renderChatCard({
          title: scope.scope_label,
          meta: [
            pill(scope.state, toneForEconomyState(scope.state)),
            pill(`score ${scope.score}`, scope.score >= 70 ? "ok" : scope.score <= 40 ? "bad" : "warn"),
          ],
          body: scope.summary,
          note: `${clipText(scope.arbitrage_edge, 110)} | ${formatNumber(scope.token_burn)} tokens | ${formatNumber(scope.command_burn)} commands`,
        }),
      );
    messages.push(
      renderChatMessage({
        stamp: "EC",
        lane: "Autonomy economy",
        tone: economy.scopes.some((scope) => scope.state === "leaking")
          ? "warn"
          : economy.scopes.some((scope) => scope.state === "compounding")
            ? "ok"
            : "",
        title: economy.headline,
        body: economy.summary,
        cards: economyCards,
      }),
    );
  }

  if (interference?.vectors?.length) {
    const interferenceCards = interference.vectors.slice(0, 3).map((vector) =>
      renderChatCard({
        title: vector.scope_label,
        meta: [
          pill(vector.kind),
          pill(vector.level, toneForSignal(vector.level)),
        ],
        body: vector.summary,
        note: `${clipText(vector.pressure, 120)} | ${clipText(vector.treaty_prompt, 110)}`,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "IF",
        lane: "Interference forecast",
        tone: interference.vectors.some((vector) => vector.level === "critical") ? "warn" : "",
        title: interference.headline,
        body: interference.summary,
        cards: interferenceCards,
      }),
    );
  }

  if (continuity?.packets?.length) {
    const continuityCards = continuity.packets.slice(0, 3).map((packet) =>
      renderChatCard({
        title: packet.mission_name,
        meta: [
          pill(packet.state, toneForContinuityState(packet.state)),
          pill(`score ${packet.score}`, packet.score >= 70 ? "ok" : packet.score <= 40 ? "bad" : "warn"),
          packet.project_label ? pill(packet.project_label) : "",
        ],
        body: packet.summary,
        note: `Anchor: ${clipText(packet.anchor, 90)} | Next handoff: ${clipText(packet.next_handoff, 90)}`,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "CT",
        lane: "Continuity deck",
        tone: continuity.packets.some((packet) => packet.state === "fragile") ? "warn" : "",
        title: continuity.headline,
        body: continuity.summary,
        cards: continuityCards,
      }),
    );
  }

  if (dreamDeck?.dreams?.length) {
    const dreamCards = dreamDeck.dreams.slice(0, 3).map((dream) =>
      renderChatCard({
        title: dream.project_label,
        meta: [
          pill(dream.status, toneForDreamStatus(dream.status)),
          pill(`${dream.checkpoint_count} checkpoints`, dream.checkpoint_count ? "ok" : ""),
        ],
        body: dream.headline,
        note: dream.summary,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "DR",
        lane: "Dream deck",
        tone: dreamDeck.dreams.some((dream) => dream.status === "fresh") ? "ok" : "",
        title: dreamDeck.headline,
        body: dreamDeck.summary,
        cards: dreamCards,
      }),
    );
  }

  if ((cortex?.doctrines?.length ?? 0) || (cortex?.inoculations?.length ?? 0)) {
    const doctrineCards = (cortex.doctrines ?? []).slice(0, 2).map((doctrine) =>
      renderChatCard({
        title: doctrine.project_label,
        meta: [
          pill(doctrine.confidence, doctrine.confidence === "strong" ? "ok" : doctrine.confidence === "solid" ? "warn" : ""),
          pill(doctrine.recommended_model),
        ],
        body: doctrine.summary,
        note: clipText(doctrine.rationale, 150),
      }),
    );
    const inoculationCards = (cortex.inoculations ?? []).slice(0, 2).map((inoculation) =>
      renderChatCard({
        title: inoculation.title,
        meta: [pill(inoculation.level, toneForSignal(inoculation.level)), pill("inoculation")],
        body: inoculation.summary,
        note: clipText(inoculation.prescription, 150),
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "CX",
        lane: "Autonomy cortex",
        tone: (cortex.inoculations ?? []).some((inoculation) => inoculation.level === "critical")
          ? "warn"
          : "",
        title: cortex.headline,
        body: cortex.summary,
        cards: [...doctrineCards, ...inoculationCards],
      }),
    );
  }

  if (reflexDeck?.reflexes?.length) {
    const reflexCards = reflexDeck.reflexes.slice(0, 3).map((reflex) =>
      renderChatCard({
        title: reflex.title,
        meta: [
          pill(reflex.level, toneForSignal(reflex.level)),
          pill(reflex.kind),
          reflex.project_label ? pill(reflex.project_label) : "",
        ],
        body: reflex.summary,
        note: `Targets ${reflex.mission_name}`,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "RF",
        lane: "Reflex deck",
        tone: reflexDeck.reflexes.some((reflex) => reflex.level === "critical") ? "warn" : "ok",
        title: reflexDeck.headline,
        body: reflexDeck.summary,
        cards: reflexCards,
      }),
    );
  }

  if (instances.length) {
    const instanceCards = instances.slice(0, 3).map((instance) =>
      renderChatCard({
        title: instance.name,
        meta: [
          pill(instance.connected ? "connected" : instance.error ? "error" : "idle", instance.connected ? "ok" : instance.error ? "bad" : ""),
          pill(instance.transport),
          instance.pid ? pill(`pid ${instance.pid}`) : "",
        ],
        body: instance.transport_note || "Ready for thread, turn, and command control.",
        note: `${instance.threads.length} threads | ${instance.models.length} models | ${instance.unresolved_requests.length} approvals`,
      }),
    );
    messages.push(
      renderChatMessage({
        stamp: "LN",
        lane: "Lane posture",
        tone: pendingApprovals ? "warn" : connectedCount ? "ok" : "",
        title: connectedCount ? "Connected Codex lanes are online" : "No active Codex lanes yet",
        body: connectedCount
          ? `${connectedCount} lane(s) are connected and feeding the control plane.`
          : "Use Quick Connect or create a connection in the rail to light the transcript up.",
        note: pendingApprovals
          ? `${pendingApprovals} approval request(s) are waiting in the connection dock.`
          : "No pending approval requests right now.",
        cards: instanceCards,
      }),
    );
  }

  const eventLines = events
    .filter((event) => !isNoiseEvent(event))
    .slice(-6)
    .map(
      (event) => {
        const repeatCount = Number(event.payload?.repeatCount ?? 1);
        return `[${formatRelativeTimestamp(event.created_at)}] ${event.method}${repeatCount > 1 ? ` x${repeatCount}` : ""}${event.thread_id ? ` | ${event.thread_id}` : ""}${event.instance_id ? ` | instance ${event.instance_id}` : ""}`;
      },
    );
  if (eventLines.length) {
    messages.push(
      renderChatMessage({
        stamp: "EV",
        lane: "Transport trail",
        tone: "",
        title: "Recent event trail",
        body: "The transcript stays high level, but the latest transport and thread milestones still surface here.",
        code: eventLines.join("\n"),
      }),
    );
  }

  opsChatEl.innerHTML = messages.join("");
}

function renderRadar() {
  const radar = state.dashboard?.radar;
  if (!radar) {
    radarHeadlineEl.textContent = "Scanning the mission field...";
    radarSummaryEl.textContent = "";
    radarSignalsEl.innerHTML = "";
    return;
  }

  const titles = {
    hot: "Autonomous attention queue is active",
    watch: "A few loops need steering",
    steady: "Autonomy lanes are stable",
  };
  radarHeadlineEl.textContent = titles[radar.posture] || "Autonomy Radar";
  radarSummaryEl.textContent = radar.summary;
  const reserveSignal = radar.signals.find((signal) => signal.id === "attention/handoff-backlog");
  if (!reserveSignal) {
    state.radarReserveExpanded = false;
  }
  const renderStandardSignal = (signal) => `
    <article class="signal signal-${escapeHtml(signal.level)}">
      <div class="signal-meta">
        ${pill(signal.level, toneForSignal(signal.level))}
        ${pill(signal.lane)}
        ${
          signal.freshness_minutes != null
            ? `<span class="signal-fresh">${escapeHtml(formatRelativeTimestamp(Date.now() - signal.freshness_minutes * 60000))}</span>`
            : ""
        }
      </div>
      <h4>${escapeHtml(signal.title)}</h4>
      <p>${escapeHtml(signal.detail)}</p>
      ${
        signal.action
          ? `<div class="signal-action">${escapeHtml(signal.action)}</div>`
          : `<div class="signal-action">No immediate action required.</div>`
      }
    </article>
  `;
  const renderReserveSignal = (signal) => {
    const reserveMissions = getReadyReserveMissions();
    const visibleMissions = state.radarReserveExpanded ? reserveMissions.slice(0, 8) : [];
    const hiddenCount = Math.max(0, reserveMissions.length - visibleMissions.length);
    return `
      <article class="signal signal-${escapeHtml(signal.level)} signal-reserve${state.radarReserveExpanded ? " signal-open" : ""}">
        <div class="signal-meta">
          ${pill(signal.level, toneForSignal(signal.level))}
          ${pill(signal.lane)}
          ${
            signal.freshness_minutes != null
              ? `<span class="signal-fresh">${escapeHtml(formatRelativeTimestamp(Date.now() - signal.freshness_minutes * 60000))}</span>`
              : ""
          }
        </div>
        <h4>${escapeHtml(signal.title)}</h4>
        <p>${escapeHtml(signal.detail)}</p>
        <div class="signal-action signal-action-stack">
          <span>${escapeHtml(signal.action || "No immediate action required.")}</span>
          <button
            type="button"
            class="signal-toggle"
            data-action="toggle-radar-reserve"
            aria-expanded="${state.radarReserveExpanded ? "true" : "false"}"
          >
            ${state.radarReserveExpanded ? "Hide reserve" : "Show reserve"}
          </button>
        </div>
        ${
          state.radarReserveExpanded
            ? `
              <div class="signal-reserve-list">
                ${visibleMissions
                  .map(
                    (mission) => `
                      <div class="signal-reserve-item">
                        <div class="signal-reserve-copy">
                          <strong>${escapeHtml(mission.name)}</strong>
                          <span>${escapeHtml(formatRelativeTimestamp(mission.last_activity_at || mission.updated_at))}</span>
                        </div>
                        <button
                          type="button"
                          class="ghost signal-inline-action"
                          data-action="open-mission"
                          data-mission-id="${mission.id}"
                        >
                          Open
                        </button>
                      </div>
                    `,
                  )
                  .join("")}
                ${
                  hiddenCount
                    ? `<div class="signal-reserve-footer">${escapeHtml(`${hiddenCount} more handoff${hiddenCount === 1 ? "" : "s"} stay available in the mission fleet.`)}</div>`
                    : ""
                }
              </div>
            `
            : ""
        }
      </article>
    `;
  };
  radarSignalsEl.innerHTML = radar.signals
    .map((signal) =>
      signal.id === "attention/handoff-backlog"
        ? renderReserveSignal(signal)
        : renderStandardSignal(signal),
    )
    .join("");
}

function getTaskById(taskId) {
  return (state.dashboard?.ops_mesh?.task_inbox?.tasks ?? []).find(
    (task) => String(task.id) === String(taskId),
  );
}

function getTaskInboxItemById(itemId) {
  return (state.dashboard?.ops_mesh?.task_inbox?.items ?? []).find((item) => item.id === itemId);
}

function getPlaybookById(playbookId) {
  return (state.dashboard?.playbooks ?? []).find(
    (playbook) => String(playbook.id) === String(playbookId),
  );
}

function getMissionById(missionId) {
  return (state.dashboard?.missions ?? []).find((mission) => String(mission.id) === String(missionId));
}

function getReadyReserveMissions() {
  return [...(state.dashboard?.missions ?? [])]
    .filter((mission) => ["paused", "completed"].includes(mission.status) && mission.last_checkpoint)
    .sort((left, right) => {
      const leftTime = new Date(left.last_activity_at || left.updated_at || 0).getTime();
      const rightTime = new Date(right.last_activity_at || right.updated_at || 0).getTime();
      return rightTime - leftTime;
    });
}

function openShell(shellId) {
  const shell = document.querySelector(`#${shellId}`);
  if (shell && "open" in shell) {
    shell.open = true;
  }
}

function focusCard(selector, shellId) {
  openShell(shellId);
  const element = document.querySelector(selector);
  if (!element) {
    throw new Error("That item is no longer visible on the dashboard.");
  }
  element.scrollIntoView({ behavior: "smooth", block: "center" });
}

function toneForTaskStatus(status) {
  if (status === "running" || status === "completed") {
    return "ok";
  }
  if (status === "attention") {
    return "bad";
  }
  if (status === "due") {
    return "warn";
  }
  return "";
}

function toneForInboxUrgency(urgency) {
  return toneForSignal(urgency);
}

function taskCardClassForInboxUrgency(urgency) {
  if (urgency === "critical" || urgency === "warn") {
    return "task-attention";
  }
  if (urgency === "ready") {
    return "task-due";
  }
  return "task-running";
}

function toneForAuthStatus(status) {
  if (status === "satisfied") {
    return "ok";
  }
  if (status === "missing") {
    return "warn";
  }
  if (status === "degraded") {
    return "bad";
  }
  return "";
}

function toneForIntegrationReadiness(readiness) {
  if (readiness === "ready") {
    return "ok";
  }
  if (readiness === "observed" || readiness === "disabled") {
    return "";
  }
  if (readiness === "auth_gap" || readiness === "lane_gap") {
    return "warn";
  }
  if (readiness === "degraded") {
    return "bad";
  }
  return "";
}

function toneForLaneCapabilityStatus(status) {
  if (status === "ready") {
    return "ok";
  }
  if (status === "auth_gap" || status === "missing") {
    return "warn";
  }
  if (status === "offline" || status === "degraded" || status === "disabled") {
    return "bad";
  }
  return "";
}

function toneForOperatorRole(role) {
  if (role === "owner" || role === "admin") {
    return "ok";
  }
  if (role === "operator") {
    return "warn";
  }
  return "";
}

function toneForRemoteStatus(status) {
  if (status === "completed") {
    return "ok";
  }
  if (status === "failed" || status === "denied") {
    return "bad";
  }
  if (status === "accepted" || status === "dry_run") {
    return "warn";
  }
  return "";
}

function revealApiKey(apiKey, label) {
  if (!apiKey) {
    return;
  }
  try {
    window.prompt(`Copy the one-time API key for ${label}`, apiKey);
  } catch {}
}

function syncVaultSecretOptions(opsMesh) {
  const secrets = opsMesh?.vault_secrets ?? [];
  const options = secrets
    .map((secret) => {
      const refs = secret.usage_count ? `, ${secret.usage_count} ref${secret.usage_count === 1 ? "" : "s"}` : "";
      const preview = secret.secret_preview ? ` ${secret.secret_preview}` : "";
      return `<option value="${secret.id}">${escapeHtml(`${secret.label}${preview}${refs}`)}</option>`;
    })
    .join("");
  const optionSets = [
    [integrationVaultSecretSelectEl, "Use an existing vault secret (optional)"],
    [notificationRouteVaultSecretSelectEl, "Use an existing vault secret (optional)"],
  ];
  optionSets.forEach(([element, placeholder]) => {
    if (!element) {
      return;
    }
    const selectedValue = element.value;
    element.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
    if (selectedValue && secrets.some((secret) => String(secret.id) === selectedValue)) {
      element.value = selectedValue;
    }
  });
}

function renderBootstrapResource(resource) {
  if (!resource) {
    return "";
  }
  const resourceKind = resource.kind || "saved";
  const created = Boolean(resource.created);
  return `
    <article class="bootstrap-resource">
      <div class="row">
        <strong>${escapeHtml(resource.label)}</strong>
        <div class="pill-row">
          ${pill(String(resourceKind).replaceAll("_", " "), created ? "ok" : "")}
          ${created ? pill("created", "ok") : pill("saved")}
        </div>
      </div>
      ${resource.detail ? `<p class="small-muted">${escapeHtml(resource.detail)}</p>` : ""}
    </article>
  `;
}

function renderBootstrapResult() {
  const result = state.lastBootstrapResult || state.setup?.launch_handoff;
  if (!onboardingResultEl) {
    return;
  }
  if (!result) {
    onboardingResultEl.innerHTML = "";
    return;
  }
  const resources = [
    result.instance,
    result.project,
    result.operator,
    result.task_blueprint,
  ].filter(Boolean);
  const sourceLabel = state.lastBootstrapResult ? "Launch Handoff" : "Saved Launch Handoff";
  const actionLabel = state.lastBootstrapResult ? "Load launch draft" : "Load saved launch draft";
  const actionKey = state.lastBootstrapResult ? "apply-bootstrap-draft" : "apply-setup-launch-draft";
  onboardingResultEl.innerHTML = `
    <article class="bootstrap-result">
      <div class="section-header">
        <div>
          <p class="eyebrow">${escapeHtml(sourceLabel)}</p>
          <h2>${escapeHtml(result.headline)}</h2>
        </div>
        <p class="panel-lede">${escapeHtml(result.summary)}</p>
      </div>
      ${
        result.warnings?.length
          ? `<div class="ops-note">${result.warnings.map((warning) => escapeHtml(warning)).join(" ")}</div>`
          : ""
      }
      <div class="bootstrap-resource-grid">
        ${resources.map((resource) => renderBootstrapResource(resource)).join("")}
      </div>
      <div class="chat-actions">
        ${result.mission_draft ? chatActionButton(actionLabel, actionKey) : ""}
      </div>
      <p class="small-muted">${escapeHtml(result.next_entrypoint || "")}</p>
    </article>
  `;
}

function renderGatewayBootstrapProfile() {
  if (!gatewayBootstrapProfileEl) {
    return;
  }
  const profile = state.dashboard?.gateway_bootstrap;
  if (!profile) {
    gatewayBootstrapProfileEl.innerHTML = "";
    return;
  }
  const resources = [
    profile.instance,
    profile.project,
    profile.team,
    profile.operator,
    profile.task_blueprint,
  ].filter(Boolean);
  gatewayBootstrapProfileEl.innerHTML = `
    <article class="bootstrap-result gateway-bootstrap-profile">
      <div class="section-header">
        <div>
          <p class="eyebrow">Gateway Profile</p>
          <h2>${escapeHtml(profile.headline)}</h2>
        </div>
        <p class="panel-lede">${escapeHtml(profile.summary)}</p>
      </div>
      ${
        profile.warnings?.length
          ? `<div class="ops-note">${profile.warnings.map((warning) => escapeHtml(warning)).join(" ")}</div>`
          : ""
      }
      <div class="bootstrap-resource-grid">
        ${resources.map((resource) => renderBootstrapResource(resource)).join("")}
      </div>
      <div class="pill-row bootstrap-policy-pills">
        ${pill(profile.status, profile.status === "ready" ? "ok" : profile.status === "degraded" ? "bad" : "warn")}
        ${pill(profile.setup_mode, profile.setup_mode === "remote" ? "warn" : "ok")}
        ${pill(profile.setup_flow)}
        ${pill(profile.model)}
        ${profile.max_turns ? pill(`max ${profile.max_turns} turns`) : ""}
        ${pill(profile.run_verification ? "verification on" : "verification off", profile.run_verification ? "ok" : "warn")}
        ${pill(profile.use_builtin_agents ? "agents on" : "agents off", profile.use_builtin_agents ? "ok" : "warn")}
        ${pill(profile.pause_on_approval ? "approval pause" : "no approval pause", profile.pause_on_approval ? "ok" : "warn")}
      </div>
      <p class="small-muted">${escapeHtml(profile.launch_defaults_summary)}</p>
    </article>
  `;
}

function applyWizardSessionToForm(force = false) {
  if (!onboardingFormEl) {
    return;
  }
  const wizard = state.setup?.wizard_session;
  if (!wizard) {
    return;
  }
  if (!force && onboardingFormEl.dataset.prefilled === "true") {
    return;
  }
  const setValue = (name, value) => {
    const field = onboardingFormEl.querySelector(`[name="${name}"]`);
    if (!field || value == null) {
      return;
    }
    field.value = String(value);
  };
  setValue("setup_mode", wizard.mode);
  setValue("setup_flow", wizard.flow);
  setValue("project_path", wizard.project_path);
  setValue("project_label", wizard.project_label);
  setValue("instance_mode", wizard.instance_mode);
  setValue("instance_id", wizard.instance_id ?? "");
  setValue("instance_name", wizard.instance_name);
  setValue("team_name", wizard.team_name);
  setValue("operator_name", wizard.operator_name);
  setValue("operator_email", wizard.operator_email);
  setValue("task_name", wizard.task_name);
  setValue("cadence_minutes", wizard.cadence_minutes);
  setValue("model", wizard.model);
  setValue("max_turns", wizard.max_turns ?? "");
  setValue("objective_template", wizard.objective_template);
  onboardingFormEl.dataset.prefilled = "true";
}

function renderOnboardingModeCallout(wizard) {
  if (!onboardingModeLabelEl || !onboardingFlowPillEl || !onboardingModeSummaryEl) {
    return;
  }
  if (!wizard) {
    onboardingModeLabelEl.textContent = "Local-first bootstrap";
    onboardingFlowPillEl.textContent = "QuickStart";
    onboardingModeSummaryEl.textContent =
      "This path reuses the existing control plane. It can stage or reuse a Desktop lane, register the workspace, issue remote operator access, vault a secret, pin a project skill, schedule the first recurring task, and preload the launch draft without inventing another config layer.";
    return;
  }
  onboardingModeLabelEl.textContent =
    wizard.mode === "remote" ? "Remote-first bootstrap" : "Local-first bootstrap";
  onboardingFlowPillEl.textContent = wizard.flow === "advanced" ? "Advanced" : "QuickStart";
  onboardingFlowPillEl.className = `pill ${wizard.mode === "remote" ? "warn" : "ok"}`;
  onboardingModeSummaryEl.textContent = wizard.summary;
}

function renderOnboarding() {
  const instances = state.dashboard?.instances ?? [];
  const projects = state.dashboard?.projects ?? [];
  const tasks = state.dashboard?.task_blueprints ?? [];
  const opsMesh = state.dashboard?.ops_mesh ?? {};
  const wizard = state.setup?.wizard_session;
  const teams = opsMesh.teams ?? [];
  const operators = opsMesh.operators ?? [];
  const secrets = opsMesh.vault_secrets ?? [];
  const connected = instances.filter((instance) => instance.connected).length;
  const apiKeyCount = opsMesh.access_posture?.api_key_count ?? 0;

  if (!onboardingHeadlineEl || !onboardingSummaryEl || !onboardingChecklistEl) {
    return;
  }

  applyWizardSessionToForm();
  renderOnboardingModeCallout(wizard);

  const allReady =
    connected > 0 && projects.length > 0 && operators.length > 0 && apiKeyCount > 0 && tasks.length > 0;
  if (allReady) {
    onboardingHeadlineEl.textContent = "QuickStart spine is in place";
    onboardingSummaryEl.textContent =
      "A live lane, workspace, remote access path, and recurring task already exist. Re-run bootstrap to tighten or extend the setup without rebuilding it by hand.";
  } else {
    onboardingHeadlineEl.textContent = "Bootstrap the first autonomous loop";
    onboardingSummaryEl.textContent =
      "Collapse lane setup, workspace registration, remote access, vaulting, skill pinning, and recurring task creation into one controlled pass.";
  }

  const checklist = [
    {
      label: wizard?.mode === "remote" ? "Lane Pool" : "Lane",
      detail:
        wizard?.mode === "remote"
          ? connected > 0
            ? `${connected} connected lane${connected === 1 ? "" : "s"} available for remote launches`
            : instances.length
              ? `${instances.length} saved lane${instances.length === 1 ? "" : "s"} can be bound later`
              : "No lane saved yet for the first remote launch"
          : connected > 0
            ? `${connected} connected lane${connected === 1 ? "" : "s"} ready`
            : instances.length
              ? `${instances.length} lane${instances.length === 1 ? "" : "s"} saved but not connected`
              : "No lane configured yet",
      tone:
        connected > 0
          ? "ok"
          : instances.length
            ? "warn"
            : wizard?.mode === "remote"
              ? "warn"
              : "bad",
    },
    {
      label: "Workspace",
      detail: projects.length ? `${projects.length} workspace${projects.length === 1 ? "" : "s"} registered` : "No workspace registered yet",
      tone: projects.length ? "ok" : "bad",
    },
    {
      label: "Remote Access",
      detail:
        apiKeyCount > 0
          ? `${apiKeyCount} operator key${apiKeyCount === 1 ? "" : "s"} active`
          : `${teams.length} team${teams.length === 1 ? "" : "s"}, ${operators.length} operator${operators.length === 1 ? "" : "s"} but no active key`,
      tone: apiKeyCount > 0 ? "ok" : operators.length ? "warn" : "bad",
    },
    {
      label: "Vault",
      detail: secrets.length ? `${secrets.length} secret${secrets.length === 1 ? "" : "s"} stored` : "No vault secret stored yet",
      tone: secrets.length ? "ok" : "warn",
    },
    {
      label: "Recurring Task",
      detail: tasks.length ? `${tasks.length} task blueprint${tasks.length === 1 ? "" : "s"} available` : "No recurring task saved yet",
      tone: tasks.length ? "ok" : "bad",
    },
  ];

  onboardingChecklistEl.innerHTML = checklist
    .map(
      (item) => `
        <article class="bootstrap-check">
          <div class="row">
            <strong>${escapeHtml(item.label)}</strong>
            ${pill(item.tone === "bad" ? "missing" : item.tone === "warn" ? "partial" : "ready", item.tone)}
          </div>
          <p class="small-muted">${escapeHtml(item.detail)}</p>
        </article>
      `,
    )
    .join("");

  renderGatewayBootstrapProfile();
  renderBootstrapResult();
  syncOnboardingMode();
}

function renderOpsMesh() {
  const opsMesh = state.dashboard?.ops_mesh;
  if (!opsMesh) {
    taskInboxHeadlineEl.textContent = "Operator inbox is quiet";
    taskInboxSummaryEl.textContent = "";
    if (taskInboxItemsEl) {
      taskInboxItemsEl.innerHTML = "";
    }
    if (authPostureHeadlineEl) {
      authPostureHeadlineEl.textContent = "Integration auth is idle";
    }
    if (authPostureSummaryEl) {
      authPostureSummaryEl.textContent = "Add integrations to start tracking credential posture.";
    }
    if (authSatisfiedCountEl) {
      authSatisfiedCountEl.textContent = "0 satisfied";
      authSatisfiedCountEl.className = "pill";
    }
    if (authMissingCountEl) {
      authMissingCountEl.textContent = "0 missing";
      authMissingCountEl.className = "pill";
    }
    if (authDegradedCountEl) {
      authDegradedCountEl.textContent = "0 degraded";
      authDegradedCountEl.className = "pill";
    }
    if (integrationsInventoryHeadlineEl) {
      integrationsInventoryHeadlineEl.textContent = "Integration inventory is idle";
    }
    if (integrationsInventorySummaryEl) {
      integrationsInventorySummaryEl.textContent =
        "Add tracked integrations or connect live lane capability catalogs to build the readiness map.";
    }
    if (integrationsInventoryReadyCountEl) {
      integrationsInventoryReadyCountEl.textContent = "0 ready";
      integrationsInventoryReadyCountEl.className = "pill";
    }
    if (integrationsInventoryGapCountEl) {
      integrationsInventoryGapCountEl.textContent = "0 gaps";
      integrationsInventoryGapCountEl.className = "pill";
    }
    if (integrationsInventoryObservedCountEl) {
      integrationsInventoryObservedCountEl.textContent = "0 observed";
      integrationsInventoryObservedCountEl.className = "pill";
    }
    if (integrationsInventoryListEl) {
      integrationsInventoryListEl.innerHTML = "";
    }
    if (accessPostureHeadlineEl) {
      accessPostureHeadlineEl.textContent = "Remote ingress is local-only";
    }
    if (accessPostureSummaryEl) {
      accessPostureSummaryEl.textContent =
        "No operator API keys are active yet. The browser workflow stays available, but external control is still closed.";
    }
    if (accessTeamCountEl) {
      accessTeamCountEl.textContent = "0 teams";
      accessTeamCountEl.className = "pill";
    }
    if (accessOperatorCountEl) {
      accessOperatorCountEl.textContent = "0 operators";
      accessOperatorCountEl.className = "pill";
    }
    if (accessKeyCountEl) {
      accessKeyCountEl.textContent = "0 keys";
      accessKeyCountEl.className = "pill";
    }
    if (accessRequestCountEl) {
      accessRequestCountEl.textContent = "0 remote requests";
      accessRequestCountEl.className = "pill";
    }
    taskBlueprintsEl.innerHTML = "";
    skillbooksEl.innerHTML = "";
    teamsListEl.innerHTML = "";
    operatorsListEl.innerHTML = "";
    remoteRequestsEl.innerHTML = "";
    if (vaultSecretsEl) {
      vaultSecretsEl.innerHTML = "";
    }
    integrationsListEl.innerHTML = "";
    notificationRoutesEl.innerHTML = "";
    laneSnapshotsEl.innerHTML = "";
    syncVaultSecretOptions(null);
    return;
  }

  taskInboxHeadlineEl.textContent = opsMesh.task_inbox.headline;
  taskInboxSummaryEl.textContent = opsMesh.task_inbox.summary;
  if (taskInboxItemsEl) {
    taskInboxItemsEl.innerHTML = opsMesh.task_inbox.items.length
      ? opsMesh.task_inbox.items
          .map(
            (item) => `
              <article class="task-card ${taskCardClassForInboxUrgency(item.urgency)}">
                <div class="row">
                  <strong>${escapeHtml(item.title)}</strong>
                  <div class="pill-row">
                    ${pill(item.source)}
                    ${pill(item.urgency, toneForInboxUrgency(item.urgency))}
                    ${item.lane_label ? pill(item.lane_label) : ""}
                    ${item.project_label ? pill(item.project_label) : ""}
                  </div>
                </div>
                <p>${escapeHtml(item.summary)}</p>
                <div class="small-muted">
                  ${
                    item.freshness_minutes != null
                      ? `Freshness ${escapeHtml(formatRelativeTimestamp(Date.now() - item.freshness_minutes * 60000))}.`
                      : "Live derived operator item."
                  }
                </div>
                <div class="ops-note">${escapeHtml(item.recommended_action)}</div>
                <div class="actions">
                  ${
                    item.mission_id
                      ? `<button type="button" class="ghost" data-action="open-mission" data-mission-id="${item.mission_id}">${escapeHtml(item.jump_label)}</button>`
                      : item.instance_id
                        ? `<button type="button" class="ghost" data-action="open-instance" data-instance-id="${item.instance_id}">${escapeHtml(item.jump_label)}</button>`
                        : item.playbook_id
                          ? `<button type="button" class="ghost" data-action="open-playbook" data-playbook-id="${item.playbook_id}">${escapeHtml(item.jump_label)}</button>`
                        : ""
                  }
                  ${
                    item.task_id
                      ? `<button type="button" class="ghost" data-action="apply-task" data-task-id="${item.task_id}">Load draft</button>`
                      : ""
                  }
                  ${
                    item.task_id
                      ? `<button type="button" data-action="run-task" data-task-id="${item.task_id}">Run now</button>`
                      : ""
                  }
                  ${
                    item.playbook_id
                      ? `<button type="button" data-action="run-playbook-now" data-playbook-id="${item.playbook_id}">Run now</button>`
                      : ""
                  }
                  ${
                    item.reflex
                      ? `<button type="button" data-action="fire-inbox-reflex" data-inbox-item-id="${escapeHtml(item.id)}">Fire reflex</button>`
                      : ""
                  }
                </div>
              </article>
            `,
          )
          .join("")
      : `
          <article class="task-card empty-state">
            <strong>No operator interrupts right now.</strong>
            <p class="small-muted">
              Approvals, fragile continuity, reflexes, and schedule pressure will surface here as soon as they need judgment.
            </p>
          </article>
        `;
  }
  if (authPostureHeadlineEl) {
    authPostureHeadlineEl.textContent = opsMesh.auth_posture.headline;
  }
  if (authPostureSummaryEl) {
    authPostureSummaryEl.textContent = opsMesh.auth_posture.summary;
  }
  if (authSatisfiedCountEl) {
    authSatisfiedCountEl.textContent = `${opsMesh.auth_posture.satisfied_count} satisfied`;
    authSatisfiedCountEl.className = opsMesh.auth_posture.satisfied_count ? "pill ok" : "pill";
  }
  if (authMissingCountEl) {
    authMissingCountEl.textContent = `${opsMesh.auth_posture.missing_count} missing`;
    authMissingCountEl.className = opsMesh.auth_posture.missing_count ? "pill warn" : "pill";
  }
  if (authDegradedCountEl) {
    authDegradedCountEl.textContent = `${opsMesh.auth_posture.degraded_count} degraded`;
    authDegradedCountEl.className = opsMesh.auth_posture.degraded_count ? "pill bad" : "pill";
  }
  if (integrationsInventoryHeadlineEl) {
    integrationsInventoryHeadlineEl.textContent = opsMesh.integrations_inventory.headline;
  }
  if (integrationsInventorySummaryEl) {
    integrationsInventorySummaryEl.textContent = opsMesh.integrations_inventory.summary;
  }
  if (integrationsInventoryReadyCountEl) {
    integrationsInventoryReadyCountEl.textContent = `${opsMesh.integrations_inventory.ready_count} ready`;
    integrationsInventoryReadyCountEl.className = opsMesh.integrations_inventory.ready_count
      ? "pill ok"
      : "pill";
  }
  if (integrationsInventoryGapCountEl) {
    integrationsInventoryGapCountEl.textContent = `${opsMesh.integrations_inventory.gap_count} gaps`;
    integrationsInventoryGapCountEl.className = opsMesh.integrations_inventory.gap_count
      ? "pill warn"
      : "pill";
  }
  if (integrationsInventoryObservedCountEl) {
    integrationsInventoryObservedCountEl.textContent = `${opsMesh.integrations_inventory.observed_count} observed`;
    integrationsInventoryObservedCountEl.className = opsMesh.integrations_inventory.observed_count
      ? "pill"
      : "pill";
  }
  if (integrationsInventoryListEl) {
    integrationsInventoryListEl.innerHTML = opsMesh.integrations_inventory.items.length
      ? opsMesh.integrations_inventory.items
          .map(
            (item) => `
              <article class="library-card">
                <div class="row">
                  <strong>${escapeHtml(item.name)}</strong>
                  <div class="pill-row">
                    ${pill(item.kind)}
                    ${pill(item.readiness, toneForIntegrationReadiness(item.readiness))}
                    ${item.tracked ? pill("tracked", "ok") : pill("observed")}
                    ${pill(`${item.lane_ready_count}/${item.lane_match_count} lanes`, item.lane_ready_count ? "ok" : item.lane_match_count ? "warn" : "")}
                  </div>
                </div>
                <div class="small-muted">
                  ${
                    item.project_labels.length
                      ? `Scope: ${escapeHtml(item.project_labels.join(", "))}. `
                      : "Scope: global or lane-observed. "
                  }
                  ${item.base_url ? `Endpoint ${escapeHtml(item.base_url)}. ` : ""}
                  ${
                    item.source_kinds.length
                      ? `Signals: ${escapeHtml(item.source_kinds.join(", ").replaceAll("_", " "))}.`
                      : ""
                  }
                </div>
                ${
                  item.auth_status
                    ? `<div class="small-muted">Auth ${escapeHtml(item.auth_status)}${item.auth_scheme ? ` via ${escapeHtml(item.auth_scheme)}` : ""}.</div>`
                    : ""
                }
                <div class="ops-note">${escapeHtml(item.summary)}</div>
                <div class="small-muted">${escapeHtml(item.recommended_action)}</div>
                ${
                  item.capabilities.length
                    ? `<div class="small-muted">Catalog: ${escapeHtml(item.capabilities.join(", "))}</div>`
                    : ""
                }
                ${
                  item.notes
                    ? `<div class="small-muted">Notes: ${escapeHtml(item.notes)}</div>`
                    : ""
                }
                ${
                  item.lanes.length
                    ? `<div class="stack">${item.lanes
                        .map(
                          (lane) => `
                            <div class="ops-chip">
                              <div>
                                <strong>${escapeHtml(lane.instance_name)}</strong>
                                <div class="small-muted">${escapeHtml(lane.summary)}</div>
                                ${
                                  lane.match_types.length
                                    ? `<div class="small-muted">${escapeHtml(lane.match_types.join(", ").replaceAll("_", " "))}</div>`
                                    : ""
                                }
                              </div>
                              <span class="pill ${toneForLaneCapabilityStatus(lane.status)}">${escapeHtml(lane.status)}</span>
                            </div>
                          `,
                        )
                        .join("")}</div>`
                    : `<div class="small-muted">No live lane is mapped to this capability yet.</div>`
                }
              </article>
            `,
          )
          .join("")
      : `
          <article class="library-card empty-state">
            <strong>No integration readiness map yet.</strong>
            <p class="small-muted">
              Track an integration or refresh a live lane catalog to start mapping capability readiness.
            </p>
          </article>
        `;
  }
  if (accessPostureHeadlineEl) {
    accessPostureHeadlineEl.textContent = opsMesh.access_posture.headline;
  }
  if (accessPostureSummaryEl) {
    accessPostureSummaryEl.textContent = opsMesh.access_posture.summary;
  }
  if (accessTeamCountEl) {
    accessTeamCountEl.textContent = `${opsMesh.access_posture.team_count} teams`;
    accessTeamCountEl.className = opsMesh.access_posture.team_count ? "pill ok" : "pill";
  }
  if (accessOperatorCountEl) {
    accessOperatorCountEl.textContent = `${opsMesh.access_posture.operator_count} operators`;
    accessOperatorCountEl.className = opsMesh.access_posture.operator_count ? "pill ok" : "pill";
  }
  if (accessKeyCountEl) {
    accessKeyCountEl.textContent = `${opsMesh.access_posture.api_key_count} keys`;
    accessKeyCountEl.className = opsMesh.access_posture.api_key_count ? "pill warn" : "pill";
  }
  if (accessRequestCountEl) {
    accessRequestCountEl.textContent = `${opsMesh.access_posture.recent_remote_request_count} remote requests`;
    accessRequestCountEl.className = opsMesh.access_posture.recent_remote_request_count ? "pill ok" : "pill";
  }
  syncVaultSecretOptions(opsMesh);

  taskBlueprintsEl.innerHTML = opsMesh.task_inbox.tasks.length
    ? opsMesh.task_inbox.tasks
        .map(
          (task) => `
            <article id="task-card-${task.id}" class="task-card task-${escapeHtml(task.status)}">
              <div class="row">
                <strong>${escapeHtml(task.name)}</strong>
                <div class="pill-row">
                  ${pill(task.status, toneForTaskStatus(task.status))}
                  ${pill(task.cadence_label)}
                  ${task.project_label ? pill(task.project_label) : ""}
                </div>
              </div>
              <p>${escapeHtml(task.summary)}</p>
              <div class="small-muted">
                ${
                  task.next_run_at
                    ? `Next run ${escapeHtml(formatRelativeTimestamp(task.next_run_at))}.`
                    : "No schedule attached."
                }
                ${task.instance_name ? ` Lane: ${escapeHtml(task.instance_name)}.` : ""}
                ${task.skill_count ? ` ${task.skill_count} skill hint(s).` : ""}
                ${task.integration_count ? ` ${task.integration_count} integration note(s).` : ""}
              </div>
              ${
                task.last_result_summary
                  ? `<div class="ops-note">${escapeHtml(task.last_result_summary)}</div>`
                  : ""
              }
              <div class="actions">
                <button type="button" class="ghost" data-action="apply-task" data-task-id="${task.id}">
                  Load draft
                </button>
                <button type="button" data-action="run-task" data-task-id="${task.id}">
                  Run now
                </button>
                <button type="button" class="danger" data-action="delete-task" data-task-id="${task.id}">
                  Delete
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="task-card empty-state">
          <strong>No task blueprints yet.</strong>
          <p class="small-muted">
            Save a repeated objective once and let OpenZues turn it into scheduled missions.
          </p>
        </article>
      `;

  if (skillsRegistryHeadlineEl) {
    skillsRegistryHeadlineEl.textContent = opsMesh.skills_registry.headline;
  }
  if (skillsRegistrySummaryEl) {
    skillsRegistrySummaryEl.textContent = opsMesh.skills_registry.summary;
  }
  if (skillsRegistryGapsEl) {
    skillsRegistryGapsEl.innerHTML = opsMesh.skills_registry.gaps.length
      ? opsMesh.skills_registry.gaps
          .map(
            (gap) => `
              <article class="library-card">
                <div class="row">
                  <strong>${escapeHtml(gap.mission_name)}</strong>
                  <div class="pill-row">
                    ${pill(`${gap.missing_skills.length} missing`, "bad")}
                    ${gap.project_label ? pill(gap.project_label, "warn") : ""}
                    ${gap.lane_label ? pill(gap.lane_label) : ""}
                  </div>
                </div>
                <div class="small-muted">
                  Missing ${escapeHtml(gap.missing_skills.join(", "))}.
                </div>
                <div class="ops-note">${escapeHtml(gap.recommended_action)}</div>
              </article>
            `,
          )
          .join("")
      : `
          <article class="library-card empty-state">
            <strong>No live skill gaps.</strong>
            <p class="small-muted">
              Active lanes appear to cover the pinned repo skills they are carrying.
            </p>
          </article>
        `;
  }

  if (skillsRegistryProjectsEl) {
    skillsRegistryProjectsEl.innerHTML = opsMesh.skills_registry.projects.length
      ? opsMesh.skills_registry.projects
          .map(
            (project) => `
              <article class="library-card">
                <div class="row">
                  <strong>${escapeHtml(project.project_label)}</strong>
                  <div class="pill-row">
                    ${pill(`${project.live_skill_count} live skills`, project.live_skill_count ? "ok" : "")}
                    ${pill(`${project.matched_skill_count}/${project.pinned_skill_count} pinned matched`, project.missing_skills.length ? "warn" : "ok")}
                    ${pill(`${project.successful_run_count} successful runs`, project.successful_run_count ? "ok" : "")}
                  </div>
                </div>
                <div class="small-muted">
                  ${project.lane_count} lane(s), ${project.mission_count} mission(s).
                  ${
                    project.missing_skills.length
                      ? ` Missing ${escapeHtml(project.missing_skills.join(", "))}.`
                      : " Pinned skills are covered on attached lanes."
                  }
                </div>
                ${
                  project.skills.length
                    ? `<div class="stack">${project.skills
                        .slice(0, 8)
                        .map(
                          (skill) => `
                            <div class="ops-chip">
                              <div>
                                <strong>${escapeHtml(skill.name)}</strong>
                                <div class="small-muted">
                                  ${escapeHtml(skill.lanes.join(", ") || "No lanes")} · ${escapeHtml(`${skill.successful_run_count} successful runs`)}
                                </div>
                                ${
                                  skill.source
                                    ? `<div class="small-muted">${escapeHtml(skill.source)}</div>`
                                    : ""
                                }
                              </div>
                            </div>
                          `,
                        )
                        .join("")}</div>`
                    : ""
                }
              </article>
            `,
          )
          .join("")
      : `
          <article class="library-card empty-state">
            <strong>No project registry yet.</strong>
            <p class="small-muted">
              Register a repo and connect a lane with live skills to see workspace coverage.
            </p>
          </article>
        `;
  }

  if (skillsRegistryLanesEl) {
    skillsRegistryLanesEl.innerHTML = opsMesh.skills_registry.lanes.length
      ? opsMesh.skills_registry.lanes
          .map(
            (lane) => `
              <article class="library-card">
                <div class="row">
                  <strong>${escapeHtml(lane.instance_name)}</strong>
                  <div class="pill-row">
                    ${pill(lane.connected ? "connected" : "offline", lane.connected ? "ok" : "bad")}
                    ${pill(`${lane.skill_count} skills`, lane.skill_count ? "ok" : "")}
                    ${pill(`${lane.relevant_skill_count} repo-matched`, lane.relevant_skill_count ? "warn" : "")}
                    ${lane.gap_count ? pill(`${lane.gap_count} gaps`, "bad") : ""}
                  </div>
                </div>
                <div class="small-muted">
                  ${
                    lane.project_labels.length
                      ? `Attached to ${escapeHtml(lane.project_labels.join(", "))}.`
                      : "No attached repo inferred yet."
                  }
                  ${lane.cwd ? ` Workspace: ${escapeHtml(lane.cwd)}.` : ""}
                </div>
                ${
                  lane.skills.length
                    ? `<div class="stack">${lane.skills
                        .slice(0, 10)
                        .map(
                          (skill) => `
                            <div class="ops-chip">
                              <div>
                                <strong>${escapeHtml(skill.name)}</strong>
                                <div class="small-muted">
                                  ${
                                    skill.pinned_projects.length
                                      ? `Relevant to ${escapeHtml(skill.pinned_projects.join(", "))}`
                                      : "No pinned repo match yet"
                                  }
                                </div>
                                ${
                                  skill.source
                                    ? `<div class="small-muted">${escapeHtml(skill.source)}</div>`
                                    : ""
                                }
                              </div>
                              ${
                                skill.successful_run_count
                                  ? `<span class="pill ok">${escapeHtml(`${skill.successful_run_count} runs`)}</span>`
                                  : ""
                              }
                            </div>
                          `,
                        )
                        .join("")}</div>`
                    : `<div class="small-muted">No live skills published on this lane yet.</div>`
                }
              </article>
            `,
          )
          .join("")
      : `
          <article class="library-card empty-state">
            <strong>No lanes in the skills registry yet.</strong>
            <p class="small-muted">
              Connect a lane and refresh its skill catalog to build the operator map.
            </p>
          </article>
        `;
  }

  skillbooksEl.innerHTML = opsMesh.skillbooks.length
    ? opsMesh.skillbooks
        .map(
          (skillbook) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(skillbook.project_label)}</strong>
                ${pill(`${skillbook.skills.length} skills`, "ok")}
              </div>
              <div class="stack">
                ${skillbook.skills
                  .map(
                    (skill) => `
                      <div class="ops-chip">
                        <div>
                          <strong>${escapeHtml(skill.name)}</strong>
                          <div class="small-muted">${escapeHtml(skill.prompt_hint)}</div>
                          ${
                            skill.source
                              ? `<div class="small-muted">${escapeHtml(skill.source)}</div>`
                              : ""
                          }
                        </div>
                        <button
                          type="button"
                          class="danger"
                          data-action="delete-skill-pin"
                          data-skill-pin-id="${skill.id}"
                        >
                          Remove
                        </button>
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No skillbooks yet.</strong>
          <p class="small-muted">
            Pin the skills you trust for each project and OpenZues will weave them into task drafts.
          </p>
        </article>
      `;

  teamsListEl.innerHTML = opsMesh.teams.length
    ? opsMesh.teams
        .map(
          (team) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(team.name)}</strong>
                <div class="pill-row">
                  ${pill(team.slug)}
                  ${pill(
                    summarizeCount(team.member_count, "member"),
                    team.member_count ? "ok" : "",
                  )}
                </div>
              </div>
              ${
                team.description
                  ? `<div class="ops-note">${escapeHtml(team.description)}</div>`
                  : `<div class="small-muted">Created ${escapeHtml(formatRelativeTimestamp(team.created_at))}.</div>`
              }
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No teams yet.</strong>
          <p class="small-muted">
            Create a team to group remote operators and keep access ownership explicit.
          </p>
        </article>
      `;

  operatorsListEl.innerHTML = opsMesh.operators.length
    ? opsMesh.operators
        .map(
          (operator) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(operator.name)}</strong>
                <div class="pill-row">
                  ${pill(operator.role, toneForOperatorRole(operator.role))}
                  ${operator.team_name ? pill(operator.team_name) : ""}
                  ${operator.enabled ? pill("enabled", "ok") : pill("disabled", "bad")}
                  ${operator.has_api_key ? pill(operator.api_key_preview || "key", "warn") : pill("no key")}
                </div>
              </div>
              <div class="small-muted">
                ${operator.email ? escapeHtml(operator.email) : "No email recorded."}
              </div>
              <div class="small-muted">
                ${
                  operator.api_key_last_used_at
                    ? `Last remote auth ${escapeHtml(formatRelativeTimestamp(operator.api_key_last_used_at))}.`
                    : "API key has not been used yet."
                }
              </div>
              <div class="actions">
                <button
                  type="button"
                  class="ghost"
                  data-action="issue-api-key"
                  data-operator-id="${operator.id}"
                  data-operator-name="${escapeHtml(operator.name)}"
                >
                  ${operator.has_api_key ? "Rotate key" : "Issue key"}
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No operators yet.</strong>
          <p class="small-muted">
            Add named operators so remote requests can be attributed to real roles instead of a shared secret.
          </p>
        </article>
      `;

  remoteRequestsEl.innerHTML = opsMesh.remote_requests.length
    ? [...opsMesh.remote_requests]
        .reverse()
        .map(
          (request) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(request.target_label || request.kind)}</strong>
                <div class="pill-row">
                  ${pill(request.kind)}
                  ${pill(request.status, toneForRemoteStatus(request.status))}
                  ${request.operator_role ? pill(request.operator_role, toneForOperatorRole(request.operator_role)) : ""}
                </div>
              </div>
              <div class="small-muted">
                ${escapeHtml(request.operator_name || "Unknown operator")}
                ${request.team_name ? ` on ${escapeHtml(request.team_name)}` : ""}
                ${
                  request.source_ip
                    ? ` from ${escapeHtml(request.source_ip)}`
                    : ""
                }.
                ${escapeHtml(formatRelativeTimestamp(request.requested_at))}
              </div>
              <div class="ops-note">${escapeHtml(request.summary)}</div>
              ${request.payload_preview ? `<pre>${escapeHtml(request.payload_preview)}</pre>` : ""}
              ${request.result_preview ? `<pre>${escapeHtml(request.result_preview)}</pre>` : ""}
              ${request.error ? `<div class="mission-alert">${escapeHtml(request.error)}</div>` : ""}
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No authenticated remote requests yet.</strong>
          <p class="small-muted">
            External task triggers and mission launches will appear here with operator and team attribution.
          </p>
        </article>
      `;

  if (vaultSecretsEl) {
    vaultSecretsEl.innerHTML = opsMesh.vault_secrets.length
      ? opsMesh.vault_secrets
          .map(
            (secret) => `
              <article class="library-card">
                <div class="row">
                  <strong>${escapeHtml(secret.label)}</strong>
                  <div class="pill-row">
                    ${pill(secret.kind)}
                    ${secret.secret_preview ? pill(secret.secret_preview, "warn") : ""}
                    ${pill(
                      summarizeCount(secret.usage_count, "reference"),
                      secret.usage_count ? "ok" : "",
                    )}
                  </div>
                </div>
                ${
                  secret.notes
                    ? `<div class="ops-note">${escapeHtml(secret.notes)}</div>`
                    : `<div class="small-muted">Ready to attach anywhere a vault-backed credential is needed.</div>`
                }
                <div class="actions">
                  <button
                    type="button"
                    class="danger"
                    data-action="delete-vault-secret"
                    data-vault-secret-id="${secret.id}"
                  >
                    Delete
                  </button>
                </div>
              </article>
            `,
          )
          .join("")
      : `
          <article class="library-card empty-state">
            <strong>No vault secrets saved yet.</strong>
            <p class="small-muted">
              Create a reusable secret here, then attach it to integrations and notification routes.
            </p>
          </article>
        `;
  }

  integrationsListEl.innerHTML = opsMesh.integrations.length
    ? opsMesh.integrations
        .map(
          (integration) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(integration.name)}</strong>
                <div class="pill-row">
                  ${pill(integration.kind)}
                  ${pill(integration.auth_scheme)}
                  ${integration.project_id ? pill(`project ${integration.project_id}`) : pill("global")}
                  ${pill(integration.auth_status, toneForAuthStatus(integration.auth_status))}
                  ${integration.has_secret ? pill(integration.secret_preview || "secret", "warn") : ""}
                </div>
              </div>
              <div class="small-muted">
                ${
                  integration.base_url
                    ? escapeHtml(integration.base_url)
                    : "No base URL recorded."
                }
              </div>
              ${
                integration.vault_secret_label
                  ? `<div class="small-muted">Vault secret: ${escapeHtml(integration.vault_secret_label)}</div>`
                  : integration.secret_label
                    ? `<div class="small-muted">Secret label: ${escapeHtml(integration.secret_label)}</div>`
                    : ""
              }
              ${
                integration.auth_detail
                  ? `<div class="ops-note">${escapeHtml(integration.auth_detail)}</div>`
                  : ""
              }
              ${
                integration.notes
                  ? `<div class="ops-note">${escapeHtml(integration.notes)}</div>`
                  : ""
              }
              <div class="actions">
                <button
                  type="button"
                  class="danger"
                  data-action="delete-integration"
                  data-integration-id="${integration.id}"
                >
                  Delete
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No integrations recorded yet.</strong>
          <p class="small-muted">
            Track the systems around each repo so tasks and operators inherit the surrounding context.
          </p>
        </article>
      `;

  notificationRoutesEl.innerHTML = opsMesh.notification_routes.length
    ? opsMesh.notification_routes
        .map(
          (route) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(route.name)}</strong>
                <div class="pill-row">
                  ${pill(route.kind)}
                  ${route.enabled ? pill("enabled", "ok") : pill("disabled")}
                  ${route.has_secret ? pill(route.secret_preview || "secret", "warn") : ""}
                </div>
              </div>
              <div class="small-muted">${escapeHtml(route.target)}</div>
              ${
                route.secret_header_name
                  ? `<div class="small-muted">Header: ${escapeHtml(route.secret_header_name)}</div>`
                  : ""
              }
              ${
                route.vault_secret_label
                  ? `<div class="small-muted">Vault secret: ${escapeHtml(route.vault_secret_label)}</div>`
                  : ""
              }
              <div class="pill-row">
                ${route.events.map((eventName) => pill(eventName)).join("")}
              </div>
              ${
                route.last_result
                  ? `<div class="ops-note">${escapeHtml(route.last_result)}</div>`
                  : ""
              }
              ${
                route.last_error
                  ? `<div class="mission-alert">${escapeHtml(route.last_error)}</div>`
                  : ""
              }
              <div class="actions">
                <button
                  type="button"
                  class="danger"
                  data-action="delete-route"
                  data-route-id="${route.id}"
                >
                  Delete
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No notification routes yet.</strong>
          <p class="small-muted">
            Add a webhook route to push task and mission events into Slack, Discord, or your own gateway.
          </p>
        </article>
      `;

  laneSnapshotsEl.innerHTML = opsMesh.lane_snapshots.length
    ? opsMesh.lane_snapshots
        .map(
          (snapshot) => `
            <article class="library-card">
              <div class="row">
                <strong>${escapeHtml(snapshot.instance_name || `Instance ${snapshot.instance_id}`)}</strong>
                <div class="pill-row">
                  ${pill(snapshot.snapshot_kind)}
                  ${snapshot.connected ? pill("connected", "ok") : pill("offline", "bad")}
                </div>
              </div>
              <div class="small-muted">
                ${escapeHtml(formatRelativeTimestamp(snapshot.created_at))}
                ${snapshot.transport ? ` • ${escapeHtml(snapshot.transport)}` : ""}
              </div>
              <div class="pill-row">
                ${pill(`${snapshot.model_count} models`)}
                ${pill(`${snapshot.skill_count} skills`)}
                ${pill(`${snapshot.thread_count} threads`)}
                ${snapshot.approvals_pending_count ? pill(`${snapshot.approvals_pending_count} approvals`, "warn") : ""}
              </div>
              ${
                snapshot.mission_name
                  ? `
                    <div class="ops-chip">
                      <div>
                        <strong>${escapeHtml(snapshot.mission_name)}</strong>
                        <div class="small-muted">
                          ${
                            snapshot.project_label
                              ? escapeHtml(snapshot.project_label)
                              : "No project attached."
                          }
                          ${snapshot.thread_id ? ` • ${escapeHtml(snapshot.thread_id)}` : ""}
                        </div>
                      </div>
                      <div class="pill-row">
                        ${snapshot.mission_status ? pill(snapshot.mission_status, toneForMissionStatus(snapshot.mission_status)) : ""}
                        ${snapshot.phase ? pill(snapshot.phase) : ""}
                        ${
                          snapshot.continuity_state
                            ? pill(
                                `${snapshot.continuity_state}${snapshot.continuity_score != null ? ` ${snapshot.continuity_score}` : ""}`,
                                snapshot.continuity_state === "anchored"
                                  ? "ok"
                                  : snapshot.continuity_state === "warming"
                                    ? "warn"
                                    : "bad",
                              )
                            : ""
                        }
                      </div>
                    </div>
                  `
                  : ""
              }
              ${
                snapshot.current_command
                  ? `
                    <article class="mission-focus stack">
                      <div class="row">
                        <strong>Current command</strong>
                        <span class="mission-freshness">live</span>
                      </div>
                      <pre>${escapeHtml(snapshot.current_command)}</pre>
                    </article>
                  `
                  : ""
              }
              ${
                snapshot.mission_name
                  ? `
                    <div class="pill-row">
                      ${pill(`${formatNumber(snapshot.command_burn)} commands`)}
                      ${pill(`${formatNumber(snapshot.token_burn)} tokens`)}
                    </div>
                  `
                  : ""
              }
              ${
                snapshot.last_checkpoint_summary
                  ? `<div class="ops-note">${escapeHtml(snapshot.last_checkpoint_summary)}</div>`
                  : ""
              }
              ${
                snapshot.safest_handoff
                  ? `<div class="small-muted">Safest handoff: ${escapeHtml(snapshot.safest_handoff)}</div>`
                  : ""
              }
              ${
                snapshot.note ? `<div class="ops-note">${escapeHtml(snapshot.note)}</div>` : ""
              }
            </article>
          `,
        )
        .join("")
    : `
        <article class="library-card empty-state">
          <strong>No lane snapshots yet.</strong>
          <p class="small-muted">
            OpenZues will capture lane history over time, and you can also force a snapshot from the connection card.
          </p>
        </article>
      `;
}

function renderContinuity() {
  const continuity = state.dashboard?.continuity;
  if (!continuity) {
    continuityHeadlineEl.textContent = "Packaging relay packets...";
    continuitySummaryEl.textContent = "";
    continuityPacketsEl.innerHTML = "";
    return;
  }

  continuityHeadlineEl.textContent = continuity.headline;
  continuitySummaryEl.textContent = continuity.summary;

  continuityPacketsEl.innerHTML = continuity.packets.length
    ? continuity.packets
        .map(
          (packet) => `
            <article class="continuity-card continuity-${escapeHtml(packet.state)}">
              <div class="signal-meta">
                ${pill(packet.state, packet.state === "anchored" ? "ok" : packet.state === "warming" ? "warn" : "bad")}
                ${pill(`${packet.score}/100`)}
                ${packet.project_label ? pill(packet.project_label) : ""}
                ${
                  packet.freshness_minutes != null
                    ? `<span class="signal-fresh">${escapeHtml(formatRelativeTimestamp(Date.now() - packet.freshness_minutes * 60000))}</span>`
                    : ""
                }
              </div>
              <h4>${escapeHtml(packet.mission_name)}</h4>
              <p>${escapeHtml(packet.summary)}</p>
              <div class="continuity-rail">
                <div>
                  <strong>Anchor</strong>
                  <p>${escapeHtml(packet.anchor)}</p>
                </div>
                <div>
                  <strong>Drift</strong>
                  <p>${escapeHtml(packet.drift)}</p>
                </div>
                <div>
                  <strong>Next Handoff</strong>
                  <p>${escapeHtml(packet.next_handoff)}</p>
                </div>
              </div>
              ${
                packet.drift_signatures?.length
                  ? `<div class="signal-meta">${packet.drift_signatures
                      .map((signature) => pill(signature, packet.state === "fragile" ? "bad" : "warn"))
                      .join("")}</div>`
                  : ""
              }
              <details class="continuity-detail">
                <summary>Relay prompt</summary>
                <pre>${escapeHtml(packet.relay_prompt)}</pre>
              </details>
            </article>
          `,
        )
        .join("")
    : `
        <article class="continuity-card empty-state">
          <strong>No relay packets yet.</strong>
          <p class="small-muted">
            Once a mission starts building thread memory or checkpoints, OpenZues will compress its current truth here.
          </p>
        </article>
      `;
}

function getDreamById(dreamId) {
  return (state.dashboard?.dream_deck?.dreams ?? []).find((dream) => dream.id === dreamId);
}

function toneForDreamStatus(status) {
  if (status === "fresh") {
    return "ok";
  }
  if (status === "ready") {
    return "warn";
  }
  return "";
}

function renderDreams() {
  const dreamDeck = state.dashboard?.dream_deck;
  if (!dreamDeck) {
    dreamHeadlineEl.textContent = "Distilling project memory...";
    dreamSummaryEl.textContent = "";
    dreamsEl.innerHTML = "";
    return;
  }

  dreamHeadlineEl.textContent = dreamDeck.headline;
  dreamSummaryEl.textContent = dreamDeck.summary;

  dreamsEl.innerHTML = dreamDeck.dreams.length
    ? dreamDeck.dreams
        .map(
          (dream) => `
            <article class="dream-card dream-${escapeHtml(dream.status)}">
              <div class="signal-meta">
                ${pill(dream.status, toneForDreamStatus(dream.status))}
                ${pill(dream.project_label)}
                ${pill(`${dream.mission_count} runs`)}
                ${pill(`${dream.checkpoint_count} checkpoints`, "ok")}
                ${
                  dream.freshness_hours != null
                    ? `<span class="signal-fresh">${escapeHtml(
                        formatRelativeTimestamp(Date.now() - dream.freshness_hours * 3600000),
                      )}</span>`
                    : ""
                }
              </div>
              <h4>${escapeHtml(dream.headline)}</h4>
              <p>${escapeHtml(dream.summary)}</p>
              ${
                dream.anchors?.length
                  ? `
                    <div class="dream-rail">
                      <strong>Anchor Signal</strong>
                      <ul class="dream-list">
                        ${dream.anchors.map((anchor) => `<li>${escapeHtml(anchor)}</li>`).join("")}
                      </ul>
                    </div>
                  `
                  : ""
              }
              ${
                dream.prune_notes?.length
                  ? `
                    <div class="dream-rail">
                      <strong>Prune Notes</strong>
                      <ul class="dream-list">
                        ${dream.prune_notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
                      </ul>
                    </div>
                  `
                  : ""
              }
              <details class="dream-detail">
                <summary>Memory prompt</summary>
                <pre>${escapeHtml(dream.memory_prompt)}</pre>
              </details>
              <div class="dream-actions">
                <button
                  type="button"
                  class="ghost"
                  data-action="apply-dream"
                  data-dream-id="${escapeHtml(dream.id)}"
                >
                  ${escapeHtml(dream.action_label || "Load dream")}
                </button>
                <button
                  type="button"
                  data-action="launch-dream"
                  data-dream-id="${escapeHtml(dream.id)}"
                >
                  Launch dream
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="dream-card empty-state">
          <strong>No dream candidates yet.</strong>
          <p class="small-muted">
            Once a workspace accumulates enough checkpointed mission history, OpenZues will synthesize a consolidation run here.
          </p>
        </article>
      `;
}

function renderCortex() {
  const cortex = state.dashboard?.cortex;
  if (!cortex) {
    cortexHeadlineEl.textContent = "Learning from recent runs...";
    cortexSummaryEl.textContent = "";
    cortexDoctrinesEl.innerHTML = "";
    cortexInoculationsEl.innerHTML = "";
    return;
  }

  cortexHeadlineEl.textContent = cortex.headline;
  cortexSummaryEl.textContent = cortex.summary;

  cortexDoctrinesEl.innerHTML = cortex.doctrines.length
    ? cortex.doctrines
        .map(
          (doctrine) => `
            <article class="cortex-card doctrine-card">
              <div class="signal-meta">
                ${pill(doctrine.confidence, doctrine.confidence === "strong" ? "ok" : doctrine.confidence === "solid" ? "warn" : "")}
                ${pill(`${doctrine.mission_count} runs`)}
                ${pill(`${doctrine.checkpoint_count} checkpoints`, "ok")}
              </div>
              <h4>${escapeHtml(doctrine.project_label)}</h4>
              <p>${escapeHtml(doctrine.summary)}</p>
              <div class="cortex-readout">
                ${pill(doctrine.recommended_model)}
                ${
                  doctrine.recommended_max_turns != null
                    ? pill(`${doctrine.recommended_max_turns} turns`)
                    : ""
                }
                ${doctrine.run_verification ? pill("verify", "ok") : pill("light loop")}
                ${doctrine.auto_commit ? pill("commit", "ok") : pill("hold commits", "warn")}
                ${doctrine.use_builtin_agents ? pill("agents", "ok") : ""}
              </div>
              <div class="small-muted">${escapeHtml(doctrine.rationale)}</div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="cortex-card empty-state">
          <strong>No doctrine yet.</strong>
          <p class="small-muted">
            As missions accumulate, OpenZues will learn which loop shape each workspace responds to best.
          </p>
        </article>
      `;

  cortexInoculationsEl.innerHTML = cortex.inoculations.length
    ? cortex.inoculations
        .map(
          (inoculation) => `
            <article class="cortex-card inoculation-card inoculation-${escapeHtml(inoculation.level)}">
              <div class="signal-meta">
                ${pill(inoculation.level, toneForSignal(inoculation.level))}
                ${pill("inoculation")}
              </div>
              <h4>${escapeHtml(inoculation.title)}</h4>
              <p>${escapeHtml(inoculation.summary)}</p>
              <div class="cortex-prescription">${escapeHtml(inoculation.prescription)}</div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="cortex-card empty-state">
          <strong>No inoculations yet.</strong>
          <p class="small-muted">
            Once OpenZues sees a few real autonomy patterns, it will start hardening future runs here.
          </p>
        </article>
      `;
}

function getReflexById(reflexId) {
  return (state.dashboard?.reflex_deck?.reflexes ?? []).find((reflex) => reflex.id === reflexId);
}

function renderReflexes() {
  const reflexDeck = state.dashboard?.reflex_deck;
  if (!reflexDeck) {
    reflexHeadlineEl.textContent = "Synthesizing intervention prompts...";
    reflexSummaryEl.textContent = "";
    reflexesEl.innerHTML = "";
    return;
  }

  reflexHeadlineEl.textContent = reflexDeck.headline;
  reflexSummaryEl.textContent = reflexDeck.summary;

  reflexesEl.innerHTML = reflexDeck.reflexes.length
    ? reflexDeck.reflexes
        .map(
          (reflex) => `
            <article class="reflex-card reflex-${escapeHtml(reflex.level)}">
              <div class="signal-meta">
                ${pill(reflex.level, toneForSignal(reflex.level))}
                ${pill(reflex.kind)}
                ${reflex.project_label ? pill(reflex.project_label) : ""}
              </div>
              <h4>${escapeHtml(reflex.title)}</h4>
              <p>${escapeHtml(reflex.summary)}</p>
              <div class="small-muted">
                Targets mission: <strong>${escapeHtml(reflex.mission_name)}</strong>
              </div>
              <div class="reflex-actions">
                <button
                  type="button"
                  data-action="fire-reflex"
                  data-reflex-id="${escapeHtml(reflex.id)}"
                >
                  ${escapeHtml(reflex.action_label || "Fire reflex")}
                </button>
              </div>
            </article>
          `,
        )
        .join("")
    : `
        <article class="reflex-card empty-state">
          <strong>No reflexes armed yet.</strong>
          <p class="small-muted">
            Once a connected mission starts drifting or stalling, OpenZues will synthesize corrective prompts here.
          </p>
        </article>
      `;
}

function renderPresets() {
  missionPresetsEl.innerHTML = MISSION_PRESETS.map(
    (preset) => `
      <button
        type="button"
        class="preset-chip"
        data-action="apply-mission-preset"
        data-preset-id="${preset.id}"
        title="${escapeHtml(preset.description)}"
      >
        ${escapeHtml(preset.name)}
      </button>
    `,
  ).join("");
}

function applyMissionPreset(presetId) {
  const preset = MISSION_PRESETS.find((item) => item.id === presetId);
  if (!preset) {
    return;
  }
  missionFormEl.querySelector('input[name="task_blueprint_id"]').value = "";
  missionFormEl.querySelector('input[name="name"]').value = preset.name;
  missionFormEl.querySelector('textarea[name="objective"]').value = preset.objective;
  missionFormEl.querySelector('input[name="model"]').value = preset.model;
  missionFormEl.querySelector('input[name="max_turns"]').value = preset.maxTurns;
  missionFormEl.querySelector('input[name="use_builtin_agents"]').checked = preset.useBuiltinAgents;
  missionFormEl.querySelector('input[name="run_verification"]').checked = preset.runVerification;
  missionFormEl.querySelector('input[name="auto_commit"]').checked = preset.autoCommit;
  missionFormEl.querySelector('input[name="pause_on_approval"]').checked = preset.pauseOnApproval;
  missionFormEl.querySelector('input[name="allow_auto_reflexes"]').checked = true;
  missionFormEl.querySelector('input[name="auto_recover"]').checked = true;
  missionFormEl.querySelector('input[name="allow_failover"]').checked = true;
  missionFormEl.querySelector('input[name="auto_recover_limit"]').value = 2;
  missionFormEl.querySelector('input[name="reflex_cooldown_seconds"]').value = 900;
  missionFormEl.querySelector('input[name="start_immediately"]').checked = true;
  missionAdvancedEl.open = true;
  showToast(`Loaded preset: ${preset.name}`);
}

function resetMissionForm() {
  missionFormEl.reset();
  missionFormEl.querySelector('input[name="task_blueprint_id"]').value = "";
  missionFormEl.querySelector('input[name="use_builtin_agents"]').checked = true;
  missionFormEl.querySelector('input[name="run_verification"]').checked = true;
  missionFormEl.querySelector('input[name="auto_commit"]').checked = true;
  missionFormEl.querySelector('input[name="pause_on_approval"]').checked = true;
  missionFormEl.querySelector('input[name="allow_auto_reflexes"]').checked = true;
  missionFormEl.querySelector('input[name="auto_recover"]').checked = true;
  missionFormEl.querySelector('input[name="allow_failover"]').checked = true;
  missionFormEl.querySelector('input[name="auto_recover_limit"]').value = 2;
  missionFormEl.querySelector('input[name="reflex_cooldown_seconds"]').value = 900;
  missionFormEl.querySelector('input[name="start_immediately"]').checked = true;
  missionAdvancedEl.open = false;
}

function getOpportunityById(opportunityId) {
  return (state.dashboard?.launchpad?.opportunities ?? []).find(
    (opportunity) => opportunity.id === opportunityId,
  );
}

function applyMissionDraft(draft) {
  missionFormEl.querySelector('input[name="name"]').value = draft.name || "";
  missionFormEl.querySelector('textarea[name="objective"]').value = draft.objective || "";
  missionFormEl.querySelector('input[name="task_blueprint_id"]').value =
    draft.task_blueprint_id || "";
  missionFormEl.querySelector('input[name="model"]').value = draft.model || "gpt-5.4";
  missionFormEl.querySelector('input[name="thread_id"]').value = draft.thread_id || "";
  missionFormEl.querySelector('input[name="max_turns"]').value = draft.max_turns || "";
  missionFormEl.querySelector('input[name="auto_recover_limit"]').value = draft.auto_recover_limit || 2;
  missionFormEl.querySelector('input[name="reflex_cooldown_seconds"]').value =
    draft.reflex_cooldown_seconds || 900;
  missionFormEl.querySelector('input[name="use_builtin_agents"]').checked = !!draft.use_builtin_agents;
  missionFormEl.querySelector('input[name="run_verification"]').checked = !!draft.run_verification;
  missionFormEl.querySelector('input[name="auto_commit"]').checked = !!draft.auto_commit;
  missionFormEl.querySelector('input[name="pause_on_approval"]').checked = !!draft.pause_on_approval;
  missionFormEl.querySelector('input[name="allow_auto_reflexes"]').checked = !!draft.allow_auto_reflexes;
  missionFormEl.querySelector('input[name="auto_recover"]').checked = !!draft.auto_recover;
  missionFormEl.querySelector('input[name="allow_failover"]').checked = draft.allow_failover !== false;
  missionFormEl.querySelector('input[name="start_immediately"]').checked = !!draft.start_immediately;
  if (draft.instance_id != null) {
    missionInstanceSelectEl.value = String(draft.instance_id);
  }
  missionProjectSelectEl.value = draft.project_id != null ? String(draft.project_id) : "";
  missionAdvancedEl.open = Boolean(
    draft.thread_id || draft.max_turns || draft.model !== "gpt-5.4" || !draft.auto_commit,
  );
}

function syncOnboardingMode() {
  if (!onboardingInstanceModeEl || !onboardingInstanceSelectEl) {
    return;
  }
  const isRemote = onboardingSetupModeEl?.value === "remote";
  if (onboardingSetupFlowEl) {
    if (isRemote) {
      onboardingSetupFlowEl.value = "advanced";
    }
    onboardingSetupFlowEl.disabled = isRemote;
  }
  if (isRemote) {
    onboardingInstanceModeEl.value = "existing";
  }
  onboardingInstanceModeEl.hidden = isRemote;
  const instanceNameField = onboardingFormEl?.querySelector('input[name="instance_name"]');
  if (instanceNameField) {
    instanceNameField.hidden = isRemote;
    instanceNameField.disabled = isRemote;
  }
  const useExisting = isRemote || onboardingInstanceModeEl.value === "existing";
  onboardingInstanceSelectEl.hidden = !useExisting;
  onboardingInstanceSelectEl.toggleAttribute("required", useExisting && !isRemote);
}

function syncMissionOptions() {
  const instances = state.dashboard?.instances ?? [];
  const projects = state.dashboard?.projects ?? [];
  const teams = state.dashboard?.ops_mesh?.teams ?? [];
  const selectedInstance = missionInstanceSelectEl.value;
  const selectedProject = missionProjectSelectEl.value;
  const selectedTaskInstance = taskInstanceSelectEl.value;
  const selectedTaskProject = taskProjectSelectEl.value;
  const selectedOperatorTeam = operatorTeamSelectEl.value;
  const selectedSkillProject = skillProjectSelectEl.value;
  const selectedIntegrationProject = integrationProjectSelectEl.value;
  const selectedBootstrapInstance = onboardingInstanceSelectEl?.value;
  const instanceOptions = instances.length
    ? instances
        .map(
          (instance) =>
            `<option value="${instance.id}">${escapeHtml(
              `${instance.name}${instance.connected ? " (connected)" : ""}`,
            )}</option>`,
        )
        .join("")
    : `<option value="">No connections yet</option>`;
  missionInstanceSelectEl.innerHTML = instanceOptions;
  if (selectedInstance && instances.some((instance) => String(instance.id) === selectedInstance)) {
    missionInstanceSelectEl.value = selectedInstance;
  }
  taskInstanceSelectEl.innerHTML = `
    <option value="">Auto-select connected lane</option>
    ${instances
      .map(
        (instance) =>
          `<option value="${instance.id}">${escapeHtml(
            `${instance.name}${instance.connected ? " (connected)" : ""}`,
          )}</option>`,
      )
      .join("")}
  `;
  if (
    selectedTaskInstance &&
    instances.some((instance) => String(instance.id) === selectedTaskInstance)
  ) {
    taskInstanceSelectEl.value = selectedTaskInstance;
  }
  if (onboardingInstanceSelectEl) {
    const remoteMode = onboardingSetupModeEl?.value === "remote";
    onboardingInstanceSelectEl.innerHTML = instances.length
      ? `
        <option value="">${remoteMode ? "No default lane yet" : "Select an existing lane"}</option>
        ${instances
          .map(
            (instance) =>
              `<option value="${instance.id}">${escapeHtml(
                `${instance.name}${instance.connected ? " (connected)" : ""}`,
              )}</option>`,
          )
          .join("")}
      `
      : `<option value="">No lanes available yet</option>`;
    if (
      selectedBootstrapInstance &&
      instances.some((instance) => String(instance.id) === selectedBootstrapInstance)
    ) {
      onboardingInstanceSelectEl.value = selectedBootstrapInstance;
    }
  }
  missionProjectSelectEl.innerHTML = `
    <option value="">Project (optional)</option>
    ${projects
      .map(
        (project) =>
          `<option value="${project.id}">${escapeHtml(project.label)}</option>`,
        )
        .join("")}
  `;
  if (selectedProject && projects.some((project) => String(project.id) === selectedProject)) {
    missionProjectSelectEl.value = selectedProject;
  }
  const projectOptions = projects
    .map(
      (project) => `<option value="${project.id}">${escapeHtml(project.label)}</option>`,
    )
    .join("");
  taskProjectSelectEl.innerHTML = `
    <option value="">Project (optional)</option>
    ${projectOptions}
  `;
  if (selectedTaskProject && projects.some((project) => String(project.id) === selectedTaskProject)) {
    taskProjectSelectEl.value = selectedTaskProject;
  }
  skillProjectSelectEl.innerHTML = `
    <option value="">Select project</option>
    ${projectOptions}
  `;
  if (
    selectedSkillProject &&
    projects.some((project) => String(project.id) === selectedSkillProject)
  ) {
    skillProjectSelectEl.value = selectedSkillProject;
  }
  integrationProjectSelectEl.innerHTML = `
    <option value="">Global integration</option>
    ${projectOptions}
  `;
  if (
    selectedIntegrationProject &&
    projects.some((project) => String(project.id) === selectedIntegrationProject)
  ) {
    integrationProjectSelectEl.value = selectedIntegrationProject;
  }
  operatorTeamSelectEl.innerHTML = teams.length
    ? teams
        .map(
          (team) =>
            `<option value="${team.id}">${escapeHtml(
              `${team.name} (${team.member_count} member${team.member_count === 1 ? "" : "s"})`,
            )}</option>`,
        )
        .join("")
    : `<option value="">Create a team first</option>`;
  if (selectedOperatorTeam && teams.some((team) => String(team.id) === selectedOperatorTeam)) {
    operatorTeamSelectEl.value = selectedOperatorTeam;
  }
  syncOnboardingMode();
}

function renderDiagnostics() {
  const diagnostics = state.diagnostics?.checks ?? [];
  if (!diagnostics.length) {
    diagnosticsEl.innerHTML = `<article class="diagnostic empty-state"><p>No diagnostics yet.</p></article>`;
    if (healthShellStatusEl) {
      healthShellStatusEl.textContent = "checking";
      healthShellStatusEl.className = "pill";
    }
    if (healthShellSummaryEl) {
      healthShellSummaryEl.textContent = "Expand when you need diagnostics or environment repair clues.";
    }
    return;
  }
  diagnosticsEl.innerHTML = diagnostics
    .map(
      (check) => `
        <article class="diagnostic diagnostic-row ${escapeHtml(check.status)}">
          <div class="diagnostic-core">
            <div>
              <strong>${escapeHtml(check.label)}</strong>
              <div class="small-muted">${escapeHtml(check.detail)}</div>
              ${check.value ? `<div class="rail-code">${escapeHtml(check.value)}</div>` : ""}
            </div>
            ${pill(check.status, check.status === "ok" ? "ok" : check.status === "fail" ? "bad" : "warn")}
          </div>
          ${check.action ? `<div class="action-text">${escapeHtml(check.action)}</div>` : ""}
        </article>
      `,
    )
    .join("");

  const failCount = diagnostics.filter((check) => check.status === "fail").length;
  const warnCount = diagnostics.filter((check) => check.status === "warn").length;
  const okCount = diagnostics.filter((check) => check.status === "ok").length;
  if (healthShellStatusEl) {
    if (failCount) {
      healthShellStatusEl.textContent = summarizeCount(failCount, "fail", "fails");
      healthShellStatusEl.className = "pill bad";
    } else if (warnCount) {
      healthShellStatusEl.textContent = summarizeCount(warnCount, "warn");
      healthShellStatusEl.className = "pill warn";
    } else {
      healthShellStatusEl.textContent = summarizeCount(okCount, "ok");
      healthShellStatusEl.className = "pill ok";
    }
  }
  if (healthShellSummaryEl) {
    if (failCount) {
      healthShellSummaryEl.textContent =
        "Environment issues are present. Expand this dock when you need the exact repair path.";
    } else if (warnCount) {
      healthShellSummaryEl.textContent =
        "The environment is mostly healthy, with a few things worth watching before a long run.";
    } else {
      healthShellSummaryEl.textContent =
        "System posture is healthy. The dock can stay collapsed until you need details.";
    }
  }
}

function renderShellChrome() {
  const opsMesh = state.dashboard?.ops_mesh;
  const missions = state.dashboard?.missions ?? [];
  const tasks = opsMesh?.task_inbox?.tasks ?? [];
  const inboxItems = opsMesh?.task_inbox?.items ?? [];
  const remoteRequests = opsMesh?.remote_requests ?? [];
  const routes = opsMesh?.notification_routes ?? [];
  const meshIntegrations = opsMesh?.integrations ?? [];
  const authPosture = opsMesh?.auth_posture;
  const accessPosture = opsMesh?.access_posture;
  const snapshots = opsMesh?.lane_snapshots ?? [];
  const continuityPackets = state.dashboard?.continuity?.packets ?? [];
  const dreams = state.dashboard?.dream_deck?.dreams ?? [];
  const doctrines = state.dashboard?.cortex?.doctrines ?? [];
  const inoculations = state.dashboard?.cortex?.inoculations ?? [];
  const reflexes = state.dashboard?.reflex_deck?.reflexes ?? [];
  const playbooks = state.dashboard?.playbooks ?? [];
  const projects = state.dashboard?.projects ?? [];
  const events = state.dashboard?.events ?? [];

  if (opsTaskCountEl) {
    opsTaskCountEl.textContent = summarizeCount(inboxItems.length, "item");
    opsTaskCountEl.className = inboxItems.some((item) => item.urgency === "critical")
      ? "pill bad"
      : inboxItems.some((item) => item.urgency === "warn")
        ? "pill warn"
        : inboxItems.length
          ? "pill ok"
          : "pill";
  }
  if (opsRouteCountEl) {
    opsRouteCountEl.textContent = summarizeCount(routes.length, "route");
    opsRouteCountEl.className = routes.length ? "pill ok" : "pill";
  }
  if (opsIntegrationCountEl) {
    opsIntegrationCountEl.textContent = summarizeCount(meshIntegrations.length, "integration");
    opsIntegrationCountEl.className = authPosture?.degraded_count
      ? "pill bad"
      : authPosture?.missing_count
        ? "pill warn"
        : meshIntegrations.length
          ? "pill ok"
          : "pill";
  }
  if (opsSnapshotCountEl) {
    opsSnapshotCountEl.textContent = summarizeCount(snapshots.length, "snapshot");
    opsSnapshotCountEl.className = snapshots.length ? "pill warn" : "pill";
  }
  if (opsShellSummaryEl) {
    if (inboxItems.some((item) => item.urgency === "critical")) {
      opsShellSummaryEl.textContent =
        "The operator inbox has critical work waiting across approvals, lane health, or failed missions.";
    } else if (tasks.some((task) => task.status === "attention")) {
      opsShellSummaryEl.textContent =
        "A recurring workflow needs attention before the always-on layer can be trusted again.";
    } else if (inboxItems.some((item) => item.urgency === "warn")) {
      opsShellSummaryEl.textContent =
        "The sidecar is surfacing derived watch items so you can steer lanes before they hard-block.";
    } else if (tasks.some((task) => task.status === "due" || task.status === "running")) {
      opsShellSummaryEl.textContent =
        "Scheduled work is in motion. This layer now owns repeated objectives, outward alerts, and lane memory.";
    } else if (authPosture?.degraded_count) {
      opsShellSummaryEl.textContent =
        "At least one integration points at a broken vault credential and needs operator repair.";
    } else if (accessPosture?.recent_remote_request_count) {
      opsShellSummaryEl.textContent =
        "Remote ingress is active alongside the recurring ops mesh, with authenticated external requests landing in the ledger.";
    } else if (accessPosture?.api_key_count) {
      opsShellSummaryEl.textContent =
        "Remote operator access is armed, but it stays tucked behind explicit teams, roles, and API-key audit records.";
    } else if (authPosture?.missing_count) {
      opsShellSummaryEl.textContent =
        "Integration inventory exists, but some entries still need credentials attached from the vault.";
    } else if (tasks.length || inboxItems.length || routes.length || meshIntegrations.length || snapshots.length) {
      opsShellSummaryEl.textContent =
        "The operational mesh is configured and ready, but it stays tucked away until you need to steer it.";
    } else {
      opsShellSummaryEl.textContent =
        "Add recurring work, notification routes, integrations, and lane history here without cluttering the main launch deck.";
    }
  }

  if (intelligenceContinuityCountEl) {
    intelligenceContinuityCountEl.textContent = summarizeCount(continuityPackets.length, "packet");
    intelligenceContinuityCountEl.className = continuityPackets.length ? "pill warn" : "pill";
  }
  if (intelligenceDreamCountEl) {
    intelligenceDreamCountEl.textContent = summarizeCount(dreams.length, "dream");
    intelligenceDreamCountEl.className = dreams.length ? "pill ok" : "pill";
  }
  if (intelligenceDoctrineCountEl) {
    intelligenceDoctrineCountEl.textContent = summarizeCount(doctrines.length, "doctrine");
    intelligenceDoctrineCountEl.className = doctrines.length ? "pill ok" : "pill";
  }
  if (intelligenceInoculationCountEl) {
    intelligenceInoculationCountEl.textContent = summarizeCount(inoculations.length, "inoculation");
    intelligenceInoculationCountEl.className = inoculations.length ? "pill warn" : "pill";
  }
  if (intelligenceReflexCountEl) {
    intelligenceReflexCountEl.textContent = summarizeCount(reflexes.length, "reflex");
    intelligenceReflexCountEl.className = reflexes.length ? "pill ok" : "pill";
  }
  if (intelligenceShellSummaryEl) {
    const fragilePackets = continuityPackets.filter((packet) => packet.state === "fragile").length;
    const readyDreams = dreams.filter((dream) => dream.status !== "forming").length;
    if (fragilePackets) {
      intelligenceShellSummaryEl.textContent =
        "Relay packets are flagging fragile mission memory. Expand this layer before a long unattended run.";
    } else if (readyDreams) {
      intelligenceShellSummaryEl.textContent =
        "Project memory is ripe for consolidation. Expand this layer to load or launch a dream pass.";
    } else if (reflexes.length) {
      intelligenceShellSummaryEl.textContent =
        "Intervention cues are armed. Expand this layer when you want to steer a live mission.";
    } else if (continuityPackets.length || dreams.length || doctrines.length || inoculations.length) {
      intelligenceShellSummaryEl.textContent =
        "Continuity, doctrine, and hardening signals are available, but they stay tucked away until you need guidance.";
    } else {
      intelligenceShellSummaryEl.textContent =
        "Collapsed by default so the main mission lane stays clean while intelligence is still forming.";
    }
  }

  if (libraryPlaybookCountEl) {
    libraryPlaybookCountEl.textContent = summarizeCount(playbooks.length, "playbook");
    libraryPlaybookCountEl.className = playbooks.length ? "pill ok" : "pill";
  }
  if (libraryProjectCountEl) {
    libraryProjectCountEl.textContent = summarizeCount(projects.length, "project");
    libraryProjectCountEl.className = projects.length ? "pill ok" : "pill";
  }
  if (libraryShellSummaryEl) {
    if (playbooks.length || projects.length) {
      libraryShellSummaryEl.textContent =
        "Workspace setup is available on demand, without competing with the live mission surface.";
    } else {
      libraryShellSummaryEl.textContent =
        "Keep setup and reusable operator routines close, but out of the main mission lane.";
    }
  }

  if (activityShellCountEl) {
    activityShellCountEl.textContent = summarizeCount(events.length, "event");
    activityShellCountEl.className = events.length ? "pill ok" : "pill";
  }
  if (activityShellSummaryEl) {
    activityShellSummaryEl.textContent = events.length
      ? "The ledger is hidden until you need a full trail of mission, thread, and transport activity."
      : "The event stream will appear here when live activity starts landing.";
  }

  if (backstageMissionCountEl) {
    backstageMissionCountEl.textContent = summarizeCount(missions.length, "mission");
    backstageMissionCountEl.className = missions.some((mission) => mission.status === "blocked")
      ? "pill warn"
      : missions.some((mission) => mission.status === "active")
        ? "pill ok"
        : "pill";
  }
  if (backstageOpsCountEl) {
    const opsCount = tasks.length + remoteRequests.length + meshIntegrations.length + routes.length;
    backstageOpsCountEl.textContent = summarizeCount(opsCount, "ops item");
    backstageOpsCountEl.className = opsCount ? "pill ok" : "pill";
  }
  if (backstageEventCountEl) {
    backstageEventCountEl.textContent = summarizeCount(events.length, "event");
    backstageEventCountEl.className = events.length ? "pill warn" : "pill";
  }
  if (backstageSummaryEl) {
    if (missions.some((mission) => mission.status === "blocked")) {
      backstageSummaryEl.textContent =
        "A mission is blocked, so the structured lane is ready when you need full telemetry and manual controls.";
    } else if (remoteRequests.length || events.length) {
      backstageSummaryEl.textContent =
        "The transcript is leading, while the full mission cards and ledgers stay one layer down for inspection.";
    } else {
      backstageSummaryEl.textContent =
        "Keep the dense grid behind the transcript until you need full cards, ledgers, and admin forms.";
    }
  }
}

function renderMissions() {
  const missions = state.dashboard?.missions ?? [];
  if (!missions.length) {
    missionsEl.innerHTML = `
      <article class="mission empty-state">
        <strong>No missions running yet.</strong>
        <p class="small-muted">
          Launch a goal from the deck and OpenZues will keep nudging Codex forward, capture
          checkpoint handoffs, and surface the next operator decision in the radar band.
        </p>
      </article>
    `;
    return;
  }

  missionsEl.innerHTML = missions
    .map((mission) => {
      const progressSuffix = mission.max_turns
        ? `${mission.turns_completed}/${mission.max_turns}`
        : `${mission.turns_completed} complete`;
      const progressPercent = mission.max_turns
        ? Math.max(6, Math.min(100, Math.round((mission.turns_completed / mission.max_turns) * 100)))
        : mission.turns_completed
          ? Math.min(100, 18 + mission.turns_completed * 12)
          : 6;
      const checkpoints = mission.checkpoints?.length
        ? mission.checkpoints
            .map(
              (checkpoint) => `
                <article class="checkpoint stack">
                  <div class="row">
                    ${pill(checkpoint.kind, checkpoint.kind === "error" ? "bad" : checkpoint.kind === "approval" ? "warn" : "ok")}
                    <span class="mission-freshness">${escapeHtml(formatRelativeTimestamp(checkpoint.created_at))}</span>
                  </div>
                  <pre>${escapeHtml(checkpoint.summary)}</pre>
                </article>
              `,
            )
            .join("")
        : `<p class="mono">No checkpoints yet.</p>`;

      return `
        <article id="mission-card-${mission.id}" class="mission stack phase-${escapeHtml(mission.phase || "ready")}">
          <div class="mission-kicker">
            ${pill(mission.status, toneForMissionStatus(mission.status))}
            ${mission.phase ? pill(mission.phase) : ""}
            ${mission.in_progress ? pill("turn running", "ok") : pill("idle")}
            ${mission.instance_name ? pill(mission.instance_name) : pill(`instance ${mission.instance_id}`)}
            ${mission.project_label ? pill(mission.project_label) : ""}
            ${pill(mission.model)}
            <span class="mission-freshness">${escapeHtml(formatRelativeTimestamp(mission.last_activity_at))}</span>
          </div>

          <div class="mission-title-row">
            <div class="stack">
              <h3>${escapeHtml(mission.name)}</h3>
              <p class="mission-objective">${escapeHtml(mission.objective)}</p>
            </div>
            <div class="actions mission-actions">
              ${
                mission.status === "active" || mission.status === "blocked"
                  ? `<button type="button" class="ghost" data-action="pause-mission" data-mission-id="${mission.id}">Pause</button>`
                  : `<button type="button" data-action="resume-mission" data-mission-id="${mission.id}">Resume</button>`
              }
              <button type="button" class="ghost" data-action="run-mission-now" data-mission-id="${mission.id}">Run now</button>
              <button type="button" class="ghost" data-action="complete-mission" data-mission-id="${mission.id}">Complete</button>
              <button type="button" class="danger" data-action="delete-mission" data-mission-id="${mission.id}">Delete</button>
            </div>
          </div>

          <div class="mission-progress">
            <div class="mission-progress-bar" style="width:${progressPercent}%"></div>
          </div>

          <div class="mission-body">
            <div class="mission-column-main">
              <article class="mission-focus stack">
                <div class="row">
                  <strong>Operator next</strong>
                  <span class="mission-freshness">${escapeHtml(progressSuffix)}</span>
                </div>
                <div>${escapeHtml(mission.suggested_action || "No action needed right now.")}</div>
              </article>

              ${
                mission.last_error
                  ? `<div class="mission-alert">${escapeHtml(mission.last_error)}</div>`
                  : ""
              }

              ${
                mission.current_command
                  ? `
                    <article class="mission-focus stack">
                      <div class="row">
                        <strong>Current command</strong>
                        <span class="mission-freshness">live</span>
                      </div>
                      <pre>${escapeHtml(mission.current_command)}</pre>
                    </article>
                  `
                  : ""
              }

              ${
                mission.last_commentary
                  ? `
                    <article class="mission-focus stack">
                      <div class="row">
                        <strong>Live commentary</strong>
                        <span class="mission-freshness">${escapeHtml(formatRelativeTimestamp(mission.last_activity_at))}</span>
                      </div>
                      <div class="mission-commentary">${escapeHtml(mission.last_commentary)}</div>
                    </article>
                  `
                  : ""
              }

              ${
                mission.last_checkpoint
                  ? `
                    <article class="mission-focus stack">
                      <div class="row">
                        <strong>Latest handoff</strong>
                        <span class="mission-freshness">${escapeHtml(formatRelativeTimestamp(mission.last_activity_at))}</span>
                      </div>
                      <pre>${escapeHtml(mission.last_checkpoint)}</pre>
                    </article>
                  `
                  : ""
              }

              <article class="mission-focus stack">
                <div class="row">
                  <strong>Mission memory</strong>
                  <span class="mission-freshness">${escapeHtml(formatRelativeTimestamp(mission.last_activity_at))}</span>
                </div>
                <div class="checkpoint-list">${checkpoints}</div>
              </article>
            </div>

            <aside class="mission-column-side">
              <article class="mini-stat">
                <span class="mini-stat-label">Thread</span>
                <span class="mono">${escapeHtml(mission.thread_id || "Not created yet")}</span>
              </article>

              <article class="mini-stat">
                <span class="mini-stat-label">Cycles</span>
                <span>${escapeHtml(progressSuffix)}</span>
              </article>

              <article class="mini-stat">
                <span class="mini-stat-label">Mission telemetry</span>
                <div class="telemetry-grid">
                  <span>${formatNumber(mission.command_count)} commands</span>
                  <span>${formatNumber(mission.total_tokens)} tokens</span>
                  <span>${formatNumber(mission.output_tokens)} output</span>
                  <span>${formatNumber(mission.reasoning_tokens)} reasoning</span>
                </div>
              </article>

              <article class="mini-stat">
                <span class="mini-stat-label">Policies</span>
                <div class="mission-pills">
                  ${booleanBadge(mission.use_builtin_agents, "agents")}
                  ${booleanBadge(mission.run_verification, "verify")}
                  ${booleanBadge(mission.auto_commit, "commit")}
                  ${booleanBadge(mission.pause_on_approval, "pause approvals")}
                  ${booleanBadge(mission.allow_auto_reflexes, "auto reflex")}
                  ${booleanBadge(mission.auto_recover, "auto recover")}
                  ${booleanBadge(mission.allow_failover, "lane failover")}
                  ${mission.last_reflex_kind ? pill(`last ${mission.last_reflex_kind}`, "warn") : ""}
                </div>
              </article>

              <article class="mini-stat">
                <span class="mini-stat-label">Governor</span>
                <div class="telemetry-grid">
                  <span>recover limit: ${formatNumber(mission.auto_recover_limit)}</span>
                  <span>reflex cooldown: ${formatNumber(mission.reflex_cooldown_seconds)}s</span>
                  <span>
                    ${escapeHtml(
                      mission.last_reflex_at
                        ? `last reflex ${formatRelativeTimestamp(mission.last_reflex_at)}`
                        : "no reflex fired yet",
                    )}
                  </span>
                </div>
              </article>
            </aside>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderInstances() {
  const instances = state.dashboard?.instances ?? [];
  if (!instances.length) {
    instancesEl.innerHTML = `<article class="instance empty-state"><p>No connections yet.</p></article>`;
    return;
  }

  instancesEl.innerHTML = instances
    .map((instance) => {
      const statusTone = instance.connected ? "ok" : instance.error ? "bad" : "warn";
      const statusText = instance.connected ? "Connected" : instance.error ? "Error" : "Idle";
      const requestCards = instance.unresolved_requests.length
        ? instance.unresolved_requests
            .map(
              (request) => `
                <article class="request stack">
                  <div class="row">
                    <strong>${escapeHtml(request.method)}</strong>
                    ${pill(`request ${request.request_id}`, "warn")}
                  </div>
                  <pre>${summarize(request.payload)}</pre>
                  <textarea data-request-editor="${instance.id}:${request.request_id}">{}</textarea>
                  <div class="actions">
                    <button
                      type="button"
                      data-action="resolve-request"
                      data-instance-id="${instance.id}"
                      data-request-id="${request.request_id}"
                    >
                      Send Response
                    </button>
                  </div>
                </article>
              `,
            )
            .join("")
        : `<p class="mono">No pending approvals.</p>`;

      const threadRows = instance.threads.length
        ? instance.threads
            .slice(0, 8)
            .map((thread) => {
              const title = thread.title || thread.name || thread.id;
              return `<div class="row"><span>${escapeHtml(title)}</span><span class="mono">${escapeHtml(thread.id || "")}</span></div>`;
            })
            .join("")
        : `<p class="mono">No threads loaded.</p>`;

      const modelOptions = (instance.models.length ? instance.models : [{ id: "gpt-5.4" }])
        .map((model) => {
          const identifier = model.id || model.slug || "gpt-5.4";
          return `<option value="${escapeHtml(identifier)}">${escapeHtml(identifier)}</option>`;
        })
        .join("");

      return `
        <article id="instance-card-${instance.id}" class="instance stack">
          <div class="instance-top">
            <div>
              <div class="instance-meta">
                ${pill(statusText, statusTone)}
                ${pill(instance.transport)}
                ${instance.resolved_transport ? pill(`via ${instance.resolved_transport}`) : ""}
                ${instance.pid ? pill(`pid ${instance.pid}`) : ""}
              </div>
              <h3>${escapeHtml(instance.name)}</h3>
              ${
                instance.transport_note
                  ? `<div class="small-muted wrap-text">${escapeHtml(instance.transport_note)}</div>`
                  : `<div class="small-muted">Ready for direct thread, turn, and command control.</div>`
              }
            </div>
            <div class="actions">
              ${
                instance.connected
                  ? `<button type="button" class="ghost" data-action="disconnect" data-instance-id="${instance.id}">Disconnect</button>`
                  : `<button type="button" data-action="connect" data-instance-id="${instance.id}">Connect</button>`
              }
              <button type="button" class="ghost" data-action="capture-snapshot" data-instance-id="${instance.id}">Snapshot</button>
              <button type="button" class="ghost" data-action="refresh-instance" data-instance-id="${instance.id}">Refresh</button>
            </div>
          </div>

          <div class="instance-ribbon">
            <span class="ribbon-item">${summarizeCount(instance.models.length, "model")}</span>
            <span class="ribbon-item">${summarizeCount(instance.skills.length, "skill")}</span>
            <span class="ribbon-item">${summarizeCount(instance.apps.length, "app")}</span>
            <span class="ribbon-item">${summarizeCount(instance.plugins.length, "plugin")}</span>
            <span class="ribbon-item">${summarizeCount(instance.unresolved_requests.length, "approval")}</span>
          </div>

          ${
            instance.error
              ? `<div class="pill-row">${pill(instance.error, "bad")}</div>`
              : ""
          }
          ${
            instance.resolved_command
              ? `<div class="rail-code mono-wrap">launcher: ${escapeHtml(instance.resolved_command)}${instance.resolved_args ? ` ${escapeHtml(instance.resolved_args)}` : ""}</div>`
              : ""
          }

          <details class="instance-detail">
            <summary>Live Context</summary>
            <div class="stack detail-body">
              <div class="subgrid">
                <div class="stack">
                  <strong>Catalog</strong>
                  <div class="pill-row">
                    ${pill(`${instance.models.length} models`)}
                    ${pill(`${instance.skills.length} skills`)}
                    ${pill(`${instance.apps.length} apps`)}
                    ${pill(`${instance.plugins.length} plugins`)}
                    ${pill(`${instance.mcp_servers.length} MCP servers`)}
                  </div>
                  <pre>${summarize(instance.auth_state || { message: "Not fetched yet." })}</pre>
                </div>
                <div class="stack">
                  <strong>Threads</strong>
                  <div class="stack">${threadRows}</div>
                </div>
              </div>
            </div>
          </details>

          <details class="instance-detail">
            <summary>Manual Controls</summary>
            <div class="stack detail-body">
              <div class="subgrid">
                <form class="stack" data-action-form="new-thread" data-instance-id="${instance.id}">
                  <strong>Start Thread</strong>
                  <select name="model">${modelOptions}</select>
                  <input name="cwd" type="text" placeholder="${escapeHtml(instance.cwd || "Working directory")}" />
                  <input name="reasoning_effort" type="text" placeholder="reasoning effort (optional)" />
                  <input name="collaboration_mode" type="text" placeholder="collaboration mode (optional)" />
                  <button type="submit">Create Thread</button>
                </form>

                <form class="stack" data-action-form="start-turn" data-instance-id="${instance.id}">
                  <strong>Start Turn</strong>
                  <input name="thread_id" type="text" placeholder="Thread ID" required />
                  <textarea name="text" placeholder="What should Codex do?" required></textarea>
                  <input name="cwd" type="text" placeholder="${escapeHtml(instance.cwd || "Working directory")}" />
                  <div class="actions">
                    <button type="submit">Send Turn</button>
                    <button type="button" class="ghost" data-action="interrupt-turn" data-instance-id="${instance.id}">Interrupt</button>
                  </div>
                </form>
              </div>

              <div class="subgrid">
                <form class="stack" data-action-form="command" data-instance-id="${instance.id}">
                  <strong>Run Command</strong>
                  <input name="command" type="text" placeholder="git status --short --branch" required />
                  <input name="cwd" type="text" placeholder="${escapeHtml(instance.cwd || "Working directory")}" />
                  <button type="submit">Execute</button>
                </form>

                <form class="stack" data-action-form="review" data-instance-id="${instance.id}">
                  <strong>Start Review</strong>
                  <input name="thread_id" type="text" placeholder="Thread ID" required />
                  <button type="submit">Review Thread</button>
                  <small class="mono">Kicks off the App Server review flow.</small>
                </form>
              </div>
            </div>
          </details>

          <div class="request-band">
            <strong>Pending Requests</strong>
            ${requestCards}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderPlaybooks() {
  const playbooks = state.dashboard?.playbooks ?? [];
  if (!playbooks.length) {
    playbooksEl.innerHTML = `<article class="playbook empty-state"><p>No playbooks yet.</p></article>`;
    return;
  }

  playbooksEl.innerHTML = playbooks
    .map(
      (playbook) => {
        const nextRunAt = computeNextRunAt(playbook.last_run_at, playbook.cadence_minutes);
        const defaultVariables = JSON.stringify(playbook.default_variables || {}, null, 2);
        return `
        <article id="playbook-card-${playbook.id}" class="playbook library-card">
          <div class="row">
            <strong>${escapeHtml(playbook.name)}</strong>
            <div class="playbook-meta">
              ${pill(playbook.kind)}
              ${playbook.instance_id ? pill(`instance ${playbook.instance_id}`) : pill("instance at run time", "warn")}
              ${playbook.thread_id ? pill(`thread ${playbook.thread_id}`) : ""}
              ${playbook.cadence_minutes ? pill(`every ${playbook.cadence_minutes}m`, "ok") : pill("manual only")}
              ${playbook.last_status ? pill(playbook.last_status, playbook.last_status === "failed" ? "bad" : "ok") : ""}
            </div>
          </div>
          ${playbook.description ? `<div class="small-muted">${escapeHtml(playbook.description)}</div>` : ""}
          <div class="small-muted">
            ${
              nextRunAt
                ? `Next run ${escapeHtml(formatRelativeTimestamp(nextRunAt))}.`
                : "No recurring schedule attached."
            }
            ${
              playbook.last_run_at
                ? ` Last run ${escapeHtml(formatRelativeTimestamp(playbook.last_run_at))}.`
                : ""
            }
          </div>
          ${
            playbook.last_result_summary
              ? `<div class="ops-note">${escapeHtml(playbook.last_result_summary)}</div>`
              : ""
          }
          <pre>${escapeHtml(playbook.template)}</pre>
          <div class="subgrid">
            <input
              data-playbook-instance="${playbook.id}"
              type="number"
              min="1"
              placeholder="Override instance ID"
            />
            <input
              data-playbook-thread="${playbook.id}"
              type="text"
              placeholder="Override thread ID"
            />
          </div>
          <input
            data-playbook-cwd="${playbook.id}"
            type="text"
            placeholder="Override cwd"
          />
          <textarea
            data-playbook-vars="${playbook.id}"
            placeholder='Variables as JSON, e.g. {"branch":"main","goal":"triage failing tests"}'
          >${escapeHtml(defaultVariables)}</textarea>
          <div class="actions">
            <button type="button" data-action="run-playbook" data-playbook-id="${playbook.id}">
              Run
            </button>
            <button type="button" class="danger" data-action="delete-playbook" data-playbook-id="${playbook.id}">
              Delete
            </button>
          </div>
        </article>
      `;
      },
    )
    .join("");
}

function renderProjects() {
  const projects = state.dashboard?.projects ?? [];
  if (!projects.length) {
    projectsEl.innerHTML = `<article class="project empty-state"><p>No projects registered yet.</p></article>`;
    return;
  }

  projectsEl.innerHTML = projects
    .map(
      (project) => `
        <article class="project library-card">
          <div class="row">
            <strong>${escapeHtml(project.label)}</strong>
            <div class="project-meta">
              ${project.exists ? pill("exists", "ok") : pill("missing", "bad")}
              ${project.is_git_repo ? pill("git", "ok") : pill("not git", "warn")}
              ${project.branch ? pill(project.branch) : ""}
            </div>
          </div>
          <p class="mono">${escapeHtml(project.path)}</p>
          ${project.git_status ? `<pre>${escapeHtml(project.git_status)}</pre>` : ""}
          <div class="stack">
            <strong>Recent commits</strong>
            ${
              project.recent_commits.length
                ? project.recent_commits.map((commit) => `<div>${escapeHtml(commit.summary)}</div>`).join("")
                : `<p class="mono">No commit data.</p>`
            }
          </div>
          <div class="stack">
            <strong>Pull requests</strong>
            ${
              project.pull_requests.length
                ? project.pull_requests
                    .map(
                      (pr) =>
                        `<a href="${escapeHtml(pr.url)}" target="_blank" rel="noreferrer">${escapeHtml(`#${pr.number} ${pr.title}`)}</a>`,
                    )
                    .join("")
                : `<p class="mono">No PR data.</p>`
            }
          </div>
        </article>
      `,
    )
    .join("");
}

function isNoiseEvent(event) {
  return (
    event.method === "server/stderr" ||
    event.method === "thread/tokenUsage/updated" ||
    event.method === "item/started" ||
    event.method.endsWith("/delta")
  );
}

function renderEvents() {
  const events = state.dashboard?.events ?? [];
  const filter = eventFilterEl.value.trim().toLowerCase();
  const filtered = events.filter((event) => {
    if (eventHideNoiseEl.checked && isNoiseEvent(event)) {
      return false;
    }
    if (!filter) {
      return true;
    }
    const haystack = JSON.stringify(event).toLowerCase();
    return haystack.includes(filter);
  });
  if (!filtered.length) {
    eventsEl.innerHTML = `<article class="event empty-state"><p>No events match the current filter.</p></article>`;
    return;
  }
  eventsEl.innerHTML = filtered
    .slice(-80)
    .reverse()
    .map(
      (event) => `
        <article class="event">
          <div class="event-top">
            <div class="event-meta">
              ${pill(event.method, "ok")}
              ${
                Number(event.payload?.repeatCount ?? 1) > 1
                  ? pill(`x${Number(event.payload.repeatCount)}`, "warn")
                  : ""
              }
              ${event.thread_id ? pill(event.thread_id) : ""}
              ${event.instance_id ? pill(`instance ${event.instance_id}`) : ""}
            </div>
            <span class="event-time">${escapeHtml(formatRelativeTimestamp(event.created_at))}</span>
          </div>
          <pre>${summarize(event.payload)}</pre>
        </article>
      `,
    )
    .join("");
}

function render() {
  renderHero();
  renderBrief();
  renderChat();
  renderLaunchpad();
  renderRadar();
  renderOnboarding();
  renderOpsMesh();
  renderContinuity();
  renderDreams();
  renderCortex();
  renderReflexes();
  renderPresets();
  renderMissions();
  renderInstances();
  renderPlaybooks();
  renderProjects();
  renderShellChrome();
  renderEvents();
  syncMissionOptions();
}

async function submitJson(url, payload, method = "POST") {
  const result = await api(url, {
    method,
    body: JSON.stringify(payload),
  });
  await Promise.all([loadDashboard(), loadSetup()]);
  return result;
}

function parseCommandLine(input) {
  return input
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function parseVariables(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  return JSON.parse(trimmed);
}

function parseCsvList(text) {
  return String(text || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function syncTransportFields() {
  const transport = transportSelectEl.value;
  document.querySelectorAll("[data-transport-visible]").forEach((element) => {
    const visibleValues = element.dataset.transportVisible.split(/\s+/);
    element.hidden = !visibleValues.includes(transport);
  });
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadDiagnostics(), loadSetup()]);
}

document.querySelector("#refresh-dashboard").addEventListener("click", () => {
  Promise.all([loadDashboard(), loadSetup()]).catch((error) =>
    showToast(normalizeError(error), true),
  );
});

document.querySelector("#refresh-diagnostics").addEventListener("click", () => {
  loadDiagnostics().catch((error) => showToast(normalizeError(error), true));
});

eventFilterEl.addEventListener("input", () => renderEvents());
eventHideNoiseEl.addEventListener("input", () => renderEvents());

if (controlChatFormEl) {
  controlChatFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = String(form.get("text") || "").trim();
    if (!text) {
      showToast("Write a message before sending it to Zues.", true);
      return;
    }
    try {
      const result = await submitJson("/api/control-chat", { text });
      event.currentTarget.reset();
      if (controlChatInputEl && state.dashboard?.control_chat?.input_placeholder) {
        controlChatInputEl.placeholder = state.dashboard.control_chat.input_placeholder;
      }
      controlChatInputEl?.focus();
      showToast(result?.assistant?.content || "Zues handled the request.");
    } catch (error) {
      showToast(normalizeError(error), true);
    }
  });
}

instanceFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/instances", {
      name: form.get("name"),
      transport: form.get("transport"),
      command: form.get("command") || null,
      args: form.get("args") || null,
      websocket_url: form.get("websocket_url") || null,
      cwd: form.get("cwd") || null,
      auto_connect: form.get("auto_connect") === "on",
    });
    event.currentTarget.reset();
    syncTransportFields();
    showToast("Connection created.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

missionFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/missions", {
      name: form.get("name"),
      objective: form.get("objective"),
      instance_id: Number(form.get("instance_id")),
      project_id: form.get("project_id") ? Number(form.get("project_id")) : null,
      task_blueprint_id: form.get("task_blueprint_id")
        ? Number(form.get("task_blueprint_id"))
        : null,
      cwd: null,
      thread_id: form.get("thread_id") || null,
      model: form.get("model") || "gpt-5.4",
      reasoning_effort: null,
      collaboration_mode: null,
      max_turns: form.get("max_turns") ? Number(form.get("max_turns")) : null,
      use_builtin_agents: form.get("use_builtin_agents") === "on",
      run_verification: form.get("run_verification") === "on",
      auto_commit: form.get("auto_commit") === "on",
      pause_on_approval: form.get("pause_on_approval") === "on",
      allow_auto_reflexes: form.get("allow_auto_reflexes") === "on",
      auto_recover: form.get("auto_recover") === "on",
      allow_failover: form.get("allow_failover") === "on",
      auto_recover_limit: form.get("auto_recover_limit")
        ? Number(form.get("auto_recover_limit"))
        : 2,
      reflex_cooldown_seconds: form.get("reflex_cooldown_seconds")
        ? Number(form.get("reflex_cooldown_seconds"))
        : 900,
      start_immediately: form.get("start_immediately") === "on",
    });
    resetMissionForm();
    showToast("Mission launched.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

document.querySelector("#quick-connect-desktop").addEventListener("click", async () => {
  try {
    await submitJson("/api/instances/quick-connect/desktop", {});
    showToast("Codex Desktop connected.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

transportSelectEl.addEventListener("change", () => {
  syncTransportFields();
});

async function persistSetupWizardSelection() {
  if (!onboardingSetupModeEl || !onboardingSetupFlowEl) {
    return;
  }
  const result = await submitJson(
    "/api/setup/wizard",
    {
      mode: onboardingSetupModeEl.value,
      flow: onboardingSetupFlowEl.value,
    },
    "PUT",
  );
  state.setup = state.setup || {};
  state.setup.wizard_session = result;
  if (onboardingFormEl) {
    onboardingFormEl.dataset.prefilled = "";
  }
  renderOnboarding();
}

if (onboardingSetupModeEl) {
  onboardingSetupModeEl.addEventListener("change", () => {
    syncOnboardingMode();
    persistSetupWizardSelection().catch((error) => showToast(normalizeError(error), true));
  });
}

if (onboardingSetupFlowEl) {
  onboardingSetupFlowEl.addEventListener("change", () => {
    syncOnboardingMode();
    persistSetupWizardSelection().catch((error) => showToast(normalizeError(error), true));
  });
}

if (onboardingInstanceModeEl) {
  onboardingInstanceModeEl.addEventListener("change", () => {
    syncOnboardingMode();
  });
}

if (onboardingFormEl) {
  onboardingFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const setupMode = onboardingSetupModeEl?.value || "local";
      const setupFlow = onboardingSetupFlowEl?.value || "quickstart";
      const result = await submitJson("/api/onboarding/bootstrap", {
        setup_mode: setupMode,
        setup_flow: setupMode === "remote" ? "advanced" : setupFlow,
        instance_mode: setupMode === "remote" ? "existing" : form.get("instance_mode"),
        instance_id: form.get("instance_id") ? Number(form.get("instance_id")) : null,
        instance_name: form.get("instance_name") || "Local Codex Desktop",
        project_path: form.get("project_path"),
        project_label: form.get("project_label") || null,
        team_name: form.get("team_name") || null,
        team_slug: null,
        team_description: null,
        operator_name: form.get("operator_name"),
        operator_email: form.get("operator_email") || null,
        operator_role: "operator",
        issue_api_key: form.get("issue_api_key") === "on",
        vault_secret_label: form.get("vault_secret_label") || null,
        vault_secret_value: form.get("vault_secret_value") || null,
        vault_secret_kind: "token",
        vault_secret_notes: null,
        integration_name: form.get("integration_name") || null,
        integration_kind: form.get("integration_kind") || null,
        integration_base_url: form.get("integration_base_url") || null,
        integration_auth_scheme: "token",
        integration_notes: null,
        skill_name: form.get("skill_name") || null,
        skill_prompt_hint: form.get("skill_prompt_hint") || null,
        skill_source: form.get("skill_source") || null,
        task_name: form.get("task_name"),
        task_summary: null,
        objective_template: form.get("objective_template"),
        cadence_minutes: form.get("cadence_minutes") ? Number(form.get("cadence_minutes")) : 180,
        completion_marker: null,
        model: form.get("model") || "gpt-5.4",
        max_turns: form.get("max_turns") ? Number(form.get("max_turns")) : 4,
        use_builtin_agents: form.get("use_builtin_agents") === "on",
        run_verification: form.get("run_verification") === "on",
        auto_commit: form.get("auto_commit") === "on",
        pause_on_approval: form.get("pause_on_approval") === "on",
        allow_auto_reflexes: true,
        auto_recover: true,
        auto_recover_limit: 2,
        reflex_cooldown_seconds: 900,
        allow_failover: true,
        enabled: form.get("enabled") === "on",
      });
      state.lastBootstrapResult = result;
      render();
      if (result.mission_draft) {
        applyMissionDraft(result.mission_draft);
      }
      if (result.api_key) {
        revealApiKey(result.api_key, result.operator?.label || "operator");
      }
      showToast(result.headline || "Bootstrap complete.");
    } catch (error) {
      showToast(normalizeError(error), true);
    }
  });
}

document.querySelector("#playbook-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/playbooks", {
      name: form.get("name"),
      description: form.get("description") || null,
      kind: form.get("kind"),
      template: form.get("template"),
      instance_id: form.get("instance_id") ? Number(form.get("instance_id")) : null,
      cadence_minutes: form.get("cadence_minutes") ? Number(form.get("cadence_minutes")) : null,
      enabled: form.get("enabled") === "on",
      cwd: form.get("cwd") || null,
      model: form.get("model") || null,
      thread_id: form.get("thread_id") || null,
      default_variables: parseVariables(form.get("default_variables") || "{}"),
      reasoning_effort: null,
      collaboration_mode: null,
      timeout_ms: 10000,
    });
    event.currentTarget.reset();
    showToast("Playbook saved.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

document.querySelector("#project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/projects", {
      path: form.get("path"),
      label: form.get("label") || null,
    });
    event.currentTarget.reset();
    showToast("Project added.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

teamFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/teams", {
      name: form.get("name"),
      slug: form.get("slug") || null,
      description: form.get("description") || null,
    });
    event.currentTarget.reset();
    showToast("Team created.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

operatorFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const result = await submitJson("/api/operators", {
      team_id: form.get("team_id") ? Number(form.get("team_id")) : null,
      name: form.get("name"),
      email: form.get("email") || null,
      role: form.get("role") || "operator",
      enabled: form.get("enabled") === "on",
      issue_api_key: form.get("issue_api_key") === "on",
    });
    event.currentTarget.reset();
    showToast("Operator created.");
    if (result?.api_key) {
      revealApiKey(result.api_key, result.operator?.name || "operator");
    }
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

taskFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/tasks", {
      name: form.get("name"),
      summary: form.get("summary") || null,
      objective_template: form.get("objective_template"),
      instance_id: form.get("instance_id") ? Number(form.get("instance_id")) : null,
      project_id: form.get("project_id") ? Number(form.get("project_id")) : null,
      cadence_minutes: form.get("cadence_minutes") ? Number(form.get("cadence_minutes")) : null,
      cwd: null,
      model: form.get("model") || "gpt-5.4",
      reasoning_effort: null,
      collaboration_mode: null,
      max_turns: form.get("max_turns") ? Number(form.get("max_turns")) : null,
      use_builtin_agents: form.get("use_builtin_agents") === "on",
      run_verification: form.get("run_verification") === "on",
      auto_commit: form.get("auto_commit") === "on",
      pause_on_approval: form.get("pause_on_approval") === "on",
      allow_auto_reflexes: true,
      auto_recover: true,
      auto_recover_limit: 2,
      reflex_cooldown_seconds: 900,
      allow_failover: true,
      enabled: form.get("enabled") === "on",
    });
    event.currentTarget.reset();
    showToast("Task blueprint saved.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

skillPinFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/skill-pins", {
      project_id: Number(form.get("project_id")),
      name: form.get("name"),
      prompt_hint: form.get("prompt_hint"),
      source: form.get("source") || null,
      enabled: true,
    });
    event.currentTarget.reset();
    showToast("Skill pinned.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

vaultSecretFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/vault-secrets", {
      label: form.get("label"),
      kind: form.get("kind") || "token",
      value: form.get("value"),
      notes: form.get("notes") || null,
    });
    event.currentTarget.reset();
    showToast("Vault secret saved.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

integrationFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await submitJson("/api/integrations", {
      name: form.get("name"),
      kind: form.get("kind"),
      project_id: form.get("project_id") ? Number(form.get("project_id")) : null,
      base_url: form.get("base_url") || null,
      auth_scheme: form.get("auth_scheme") || "token",
      vault_secret_id: form.get("vault_secret_id") ? Number(form.get("vault_secret_id")) : null,
      secret_label: form.get("secret_label") || null,
      secret_value: form.get("secret_value") || null,
      notes: form.get("notes") || null,
      enabled: form.get("enabled") === "on",
    });
    event.currentTarget.reset();
    showToast("Integration saved.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

notificationRouteFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const events = parseCsvList(form.get("events"));
    await submitJson("/api/notification-routes", {
      name: form.get("name"),
      kind: "webhook",
      target: form.get("target"),
      events: events.length
        ? events
        : ["ops/inbox/*", "mission/completed", "mission/failed", "task/*"],
      enabled: form.get("enabled") === "on",
      secret_header_name: form.get("secret_header_name") || null,
      vault_secret_id: form.get("vault_secret_id") ? Number(form.get("vault_secret_id")) : null,
      secret_token: form.get("secret_token") || null,
    });
    event.currentTarget.reset();
    showToast("Notification route saved.");
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) {
    return;
  }
  if (target.dataset.action === "toggle-radar-reserve") {
    state.radarReserveExpanded = !state.radarReserveExpanded;
    renderRadar();
    return;
  }
  const instanceId = target.dataset.instanceId;
  try {
    if (target.dataset.action === "apply-mission-preset") {
      applyMissionPreset(target.dataset.presetId);
    }
    if (target.dataset.action === "apply-bootstrap-draft") {
      if (!state.lastBootstrapResult?.mission_draft) {
        throw new Error("The bootstrap draft is no longer available.");
      }
      applyMissionDraft(state.lastBootstrapResult.mission_draft);
      showToast("Loaded the bootstrap launch draft.");
    }
    if (target.dataset.action === "apply-setup-launch-draft") {
      if (!state.setup?.launch_handoff?.mission_draft) {
        throw new Error("The saved launch draft is no longer available.");
      }
      applyMissionDraft(state.setup.launch_handoff.mission_draft);
      showToast("Loaded the saved launch draft.");
    }
    if (target.dataset.action === "apply-task") {
      const task = getTaskById(target.dataset.taskId);
      if (!task) {
        throw new Error("That task blueprint is no longer available.");
      }
      applyMissionDraft(task.mission_draft);
      showToast(`Loaded task draft: ${task.name}`);
    }
    if (target.dataset.action === "run-task") {
      await submitJson(`/api/tasks/${target.dataset.taskId}/run`, {});
      showToast("Task launched.");
      resetMissionForm();
    }
    if (target.dataset.action === "open-mission") {
      const mission = getMissionById(target.dataset.missionId);
      if (!mission) {
        throw new Error("That mission is no longer available.");
      }
      focusCard(`#mission-card-${mission.id}`, "backstage-shell");
      showToast(`Moved to mission: ${mission.name}`);
    }
    if (target.dataset.action === "open-instance") {
      focusCard(`#instance-card-${target.dataset.instanceId}`, "health-shell");
      showToast("Moved to lane controls.");
    }
    if (target.dataset.action === "fire-inbox-reflex") {
      const item = getTaskInboxItemById(target.dataset.inboxItemId);
      if (!item?.reflex || !item.mission_id) {
        throw new Error("That inbox reflex is no longer available.");
      }
      await submitJson(`/api/missions/${item.mission_id}/reflex`, item.reflex);
      showToast(`Reflex fired into ${item.title}.`);
    }
    if (target.dataset.action === "delete-task") {
      await api(`/api/tasks/${target.dataset.taskId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Task blueprint deleted.");
    }
    if (target.dataset.action === "delete-vault-secret") {
      await api(`/api/vault-secrets/${target.dataset.vaultSecretId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Vault secret deleted.");
    }
    if (target.dataset.action === "apply-opportunity") {
      const opportunity = getOpportunityById(target.dataset.opportunityId);
      if (!opportunity) {
        throw new Error("That launch draft is no longer available.");
      }
      applyMissionDraft(opportunity.mission_draft);
      showToast(`Loaded ghost launch: ${opportunity.title}`);
    }
    if (target.dataset.action === "apply-dream") {
      const dream = getDreamById(target.dataset.dreamId);
      if (!dream) {
        throw new Error("That dream pass is no longer available.");
      }
      applyMissionDraft(dream.mission_draft);
      showToast(`Loaded dream: ${dream.project_label}`);
    }
    if (target.dataset.action === "launch-opportunity") {
      const opportunity = getOpportunityById(target.dataset.opportunityId);
      if (!opportunity) {
        throw new Error("That launch draft is no longer available.");
      }
      await submitJson("/api/missions", opportunity.mission_draft);
      showToast(`Launched: ${opportunity.title}`);
      resetMissionForm();
    }
    if (target.dataset.action === "launch-dream") {
      const dream = getDreamById(target.dataset.dreamId);
      if (!dream) {
        throw new Error("That dream pass is no longer available.");
      }
      await submitJson("/api/missions", dream.mission_draft);
      showToast(`Dream launched for ${dream.project_label}.`);
      resetMissionForm();
    }
    if (target.dataset.action === "fire-reflex") {
      const reflex = getReflexById(target.dataset.reflexId);
      if (!reflex) {
        throw new Error("That reflex is no longer available.");
      }
      await submitJson(`/api/missions/${reflex.mission_id}/reflex`, {
        kind: reflex.kind,
        title: reflex.title,
        prompt: reflex.prompt,
      });
      showToast(`Reflex fired into ${reflex.mission_name}.`);
    }
    if (target.dataset.action === "connect") {
      await submitJson(`/api/instances/${instanceId}/connect`, {});
      showToast("Connected.");
    }
    if (target.dataset.action === "disconnect") {
      await submitJson(`/api/instances/${instanceId}/disconnect`, {});
      showToast("Disconnected.");
    }
    if (target.dataset.action === "refresh-instance") {
      await submitJson(`/api/instances/${instanceId}/refresh`, {});
      showToast("Instance refreshed.");
    }
    if (target.dataset.action === "capture-snapshot") {
      await submitJson(`/api/instances/${instanceId}/snapshots`, {});
      showToast("Lane snapshot captured.");
    }
    if (target.dataset.action === "resolve-request") {
      const requestId = target.dataset.requestId;
      const editor = document.querySelector(`[data-request-editor="${instanceId}:${requestId}"]`);
      const result = editor.value.trim() ? JSON.parse(editor.value) : {};
      await submitJson(`/api/instances/${instanceId}/requests/${requestId}/resolve`, { result });
      showToast("Request response sent.");
    }
    if (target.dataset.action === "interrupt-turn") {
      const form = target.closest("form");
      const threadId = new FormData(form).get("thread_id");
      if (!threadId) {
        throw new Error("Enter a thread ID first.");
      }
      await submitJson(`/api/instances/${instanceId}/turns/${threadId}/interrupt`, {});
      showToast("Interrupt sent.");
    }
    if (target.dataset.action === "delete-playbook") {
      const playbookId = target.dataset.playbookId;
      await api(`/api/playbooks/${playbookId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Playbook deleted.");
    }
    if (target.dataset.action === "open-playbook") {
      const playbook = getPlaybookById(target.dataset.playbookId);
      if (!playbook) {
        throw new Error("That playbook is no longer available.");
      }
      focusCard(`#playbook-card-${playbook.id}`, "library-shell");
      showToast(`Moved to playbook: ${playbook.name}`);
    }
    if (target.dataset.action === "delete-skill-pin") {
      await api(`/api/skill-pins/${target.dataset.skillPinId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Skill pin removed.");
    }
    if (target.dataset.action === "issue-api-key") {
      const result = await submitJson(`/api/operators/${target.dataset.operatorId}/api-key`, {});
      revealApiKey(result?.api_key, target.dataset.operatorName || "operator");
      showToast("API key issued.");
    }
    if (target.dataset.action === "delete-integration") {
      await api(`/api/integrations/${target.dataset.integrationId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Integration deleted.");
    }
    if (target.dataset.action === "delete-route") {
      await api(`/api/notification-routes/${target.dataset.routeId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Notification route deleted.");
    }
    if (target.dataset.action === "run-playbook") {
      const playbookId = target.dataset.playbookId;
      const variables = parseVariables(
        document.querySelector(`[data-playbook-vars="${playbookId}"]`).value,
      );
      const payload = {
        instance_id: document.querySelector(`[data-playbook-instance="${playbookId}"]`).value
          ? Number(document.querySelector(`[data-playbook-instance="${playbookId}"]`).value)
          : null,
        thread_id: document.querySelector(`[data-playbook-thread="${playbookId}"]`).value || null,
        cwd: document.querySelector(`[data-playbook-cwd="${playbookId}"]`).value || null,
        variables,
      };
      const result = await submitJson(`/api/playbooks/${playbookId}/run`, payload);
      const threadSuffix = result.thread_id ? ` on ${result.thread_id}` : "";
      showToast(`Playbook ran${threadSuffix}.`);
    }
    if (target.dataset.action === "run-playbook-now") {
      const playbookId = target.dataset.playbookId;
      const result = await submitJson(`/api/playbooks/${playbookId}/run`, {
        instance_id: null,
        thread_id: null,
        cwd: null,
        variables: {},
      });
      const threadSuffix = result.thread_id ? ` on ${result.thread_id}` : "";
      showToast(`Playbook ran${threadSuffix}.`);
    }
    if (target.dataset.action === "pause-mission") {
      const missionId = target.dataset.missionId;
      await submitJson(`/api/missions/${missionId}/pause`, {});
      showToast("Mission paused.");
    }
    if (target.dataset.action === "resume-mission") {
      const missionId = target.dataset.missionId;
      await submitJson(`/api/missions/${missionId}/start`, {});
      showToast("Mission resumed.");
    }
    if (target.dataset.action === "run-mission-now") {
      const missionId = target.dataset.missionId;
      await submitJson(`/api/missions/${missionId}/run-now`, {});
      showToast("Mission ticked.");
    }
    if (target.dataset.action === "complete-mission") {
      const missionId = target.dataset.missionId;
      await submitJson(`/api/missions/${missionId}/complete`, {});
      showToast("Mission marked complete.");
    }
    if (target.dataset.action === "delete-mission") {
      const missionId = target.dataset.missionId;
      await api(`/api/missions/${missionId}`, { method: "DELETE" });
      await loadDashboard();
      showToast("Mission deleted.");
    }
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

document.addEventListener("submit", async (event) => {
  const formEl = event.target.closest("[data-action-form]");
  if (!formEl) {
    return;
  }
  event.preventDefault();
  const form = new FormData(formEl);
  const instanceId = formEl.dataset.instanceId;
  const action = formEl.dataset.actionForm;
  try {
    if (action === "new-thread") {
      await submitJson(`/api/instances/${instanceId}/threads`, {
        model: form.get("model"),
        cwd: form.get("cwd") || null,
        reasoning_effort: form.get("reasoning_effort") || null,
        collaboration_mode: form.get("collaboration_mode") || null,
      });
      showToast("Thread started.");
    }
    if (action === "start-turn") {
      await submitJson(`/api/instances/${instanceId}/turns`, {
        thread_id: form.get("thread_id"),
        text: form.get("text"),
        cwd: form.get("cwd") || null,
      });
      showToast("Turn started.");
    }
    if (action === "command") {
      const result = await submitJson(`/api/instances/${instanceId}/commands`, {
        command: parseCommandLine(form.get("command")),
        cwd: form.get("cwd") || null,
        timeout_ms: 10000,
        tty: false,
      });
      const exitCode = result.exitCode ?? result.exit_code;
      showToast(
        typeof exitCode === "number" ? `Command finished with exit code ${exitCode}.` : "Command executed.",
      );
    }
    if (action === "review") {
      await submitJson(`/api/instances/${instanceId}/reviews`, {
        thread_id: form.get("thread_id"),
      });
      showToast("Review started.");
    }
    formEl.reset();
  } catch (error) {
    showToast(normalizeError(error), true);
  }
});

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  state.socket.onmessage = () => scheduleRefresh();
  state.socket.onclose = () => {
    setTimeout(connectSocket, 1500);
  };
}

restoreDisclosureState();
refreshAll().catch((error) => showToast(normalizeError(error), true));
syncTransportFields();
syncOnboardingMode();
connectSocket();
