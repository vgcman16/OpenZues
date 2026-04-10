const state = {
  dashboard: null,
  diagnostics: null,
  socket: null,
  refreshTimer: null,
};

const heroStatsEl = document.querySelector("#hero-stats");
const briefHeadlineEl = document.querySelector("#brief-headline");
const briefSummaryEl = document.querySelector("#brief-summary");
const briefActionsEl = document.querySelector("#brief-actions");
const launchpadHeadlineEl = document.querySelector("#launchpad-headline");
const launchpadSummaryEl = document.querySelector("#launchpad-summary");
const launchpadOpportunitiesEl = document.querySelector("#launchpad-opportunities");
const radarHeadlineEl = document.querySelector("#radar-headline");
const radarSummaryEl = document.querySelector("#radar-summary");
const radarSignalsEl = document.querySelector("#radar-signals");
const cortexHeadlineEl = document.querySelector("#cortex-headline");
const cortexSummaryEl = document.querySelector("#cortex-summary");
const cortexDoctrinesEl = document.querySelector("#cortex-doctrines");
const cortexInoculationsEl = document.querySelector("#cortex-inoculations");
const reflexHeadlineEl = document.querySelector("#reflex-headline");
const reflexSummaryEl = document.querySelector("#reflex-summary");
const reflexesEl = document.querySelector("#reflexes");
const missionsEl = document.querySelector("#missions");
const missionPresetsEl = document.querySelector("#mission-presets");
const instancesEl = document.querySelector("#instances");
const diagnosticsEl = document.querySelector("#diagnostics");
const playbooksEl = document.querySelector("#playbooks");
const projectsEl = document.querySelector("#projects");
const eventsEl = document.querySelector("#events");
const toastEl = document.querySelector("#toast");
const eventFilterEl = document.querySelector("#event-filter");
const eventHideNoiseEl = document.querySelector("#event-hide-noise");
const instanceFormEl = document.querySelector("#instance-form");
const missionFormEl = document.querySelector("#mission-form");
const missionAdvancedEl = document.querySelector("#mission-advanced");
const missionInstanceSelectEl = document.querySelector("#mission-instance-select");
const missionProjectSelectEl = document.querySelector("#mission-project-select");
const transportSelectEl = document.querySelector("#transport-select");

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

function scheduleRefresh() {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => {
    loadDashboard().catch((error) => showToast(normalizeError(error), true));
  }, 250);
}

function renderHero() {
  const instances = state.dashboard?.instances ?? [];
  const missions = state.dashboard?.missions ?? [];
  const projects = state.dashboard?.projects ?? [];
  const radarSignals = state.dashboard?.radar?.signals ?? [];
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
      note: `${summarizeCount(approvals, "approval")} pending`,
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

function renderRadar() {
  const radar = state.dashboard?.radar;
  if (!radar) {
    radarHeadlineEl.textContent = "Scanning the mission field...";
    radarSummaryEl.textContent = "";
    radarSignalsEl.innerHTML = "";
    return;
  }

  const titles = {
    hot: "Attention queue is active",
    watch: "A few loops need steering",
    steady: "Autonomy lanes are stable",
  };
  radarHeadlineEl.textContent = titles[radar.posture] || "Autonomy Radar";
  radarSummaryEl.textContent = radar.summary;
  radarSignalsEl.innerHTML = radar.signals
    .map(
      (signal) => `
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
      `,
    )
    .join("");
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
  missionFormEl.querySelector('input[name="auto_recover_limit"]').value = 2;
  missionFormEl.querySelector('input[name="reflex_cooldown_seconds"]').value = 900;
  missionFormEl.querySelector('input[name="start_immediately"]').checked = true;
  missionAdvancedEl.open = true;
  showToast(`Loaded preset: ${preset.name}`);
}

function resetMissionForm() {
  missionFormEl.reset();
  missionFormEl.querySelector('input[name="use_builtin_agents"]').checked = true;
  missionFormEl.querySelector('input[name="run_verification"]').checked = true;
  missionFormEl.querySelector('input[name="auto_commit"]').checked = true;
  missionFormEl.querySelector('input[name="pause_on_approval"]').checked = true;
  missionFormEl.querySelector('input[name="allow_auto_reflexes"]').checked = true;
  missionFormEl.querySelector('input[name="auto_recover"]').checked = true;
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
  missionFormEl.querySelector('input[name="start_immediately"]').checked = !!draft.start_immediately;
  if (draft.instance_id != null) {
    missionInstanceSelectEl.value = String(draft.instance_id);
  }
  missionProjectSelectEl.value = draft.project_id != null ? String(draft.project_id) : "";
  missionAdvancedEl.open = Boolean(
    draft.thread_id || draft.max_turns || draft.model !== "gpt-5.4" || !draft.auto_commit,
  );
}

function syncMissionOptions() {
  const instances = state.dashboard?.instances ?? [];
  const projects = state.dashboard?.projects ?? [];
  const selectedInstance = missionInstanceSelectEl.value;
  const selectedProject = missionProjectSelectEl.value;
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
}

function renderDiagnostics() {
  const diagnostics = state.diagnostics?.checks ?? [];
  if (!diagnostics.length) {
    diagnosticsEl.innerHTML = `<article class="diagnostic empty-state"><p>No diagnostics yet.</p></article>`;
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
        <article class="mission stack phase-${escapeHtml(mission.phase || "ready")}">
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
        <article class="instance stack">
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
      (playbook) => `
        <article class="playbook library-card">
          <div class="row">
            <strong>${escapeHtml(playbook.name)}</strong>
            <div class="playbook-meta">
              ${pill(playbook.kind)}
              ${playbook.instance_id ? pill(`instance ${playbook.instance_id}`) : pill("instance at run time", "warn")}
              ${playbook.thread_id ? pill(`thread ${playbook.thread_id}`) : ""}
            </div>
          </div>
          ${playbook.description ? `<div class="small-muted">${escapeHtml(playbook.description)}</div>` : ""}
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
          >{}</textarea>
          <div class="actions">
            <button type="button" data-action="run-playbook" data-playbook-id="${playbook.id}">
              Run
            </button>
            <button type="button" class="danger" data-action="delete-playbook" data-playbook-id="${playbook.id}">
              Delete
            </button>
          </div>
        </article>
      `,
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
  renderLaunchpad();
  renderRadar();
  renderCortex();
  renderReflexes();
  renderPresets();
  renderMissions();
  renderInstances();
  renderPlaybooks();
  renderProjects();
  renderEvents();
  syncMissionOptions();
}

async function submitJson(url, payload, method = "POST") {
  const result = await api(url, {
    method,
    body: JSON.stringify(payload),
  });
  await loadDashboard();
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

function syncTransportFields() {
  const transport = transportSelectEl.value;
  document.querySelectorAll("[data-transport-visible]").forEach((element) => {
    const visibleValues = element.dataset.transportVisible.split(/\s+/);
    element.hidden = !visibleValues.includes(transport);
  });
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadDiagnostics()]);
}

document.querySelector("#refresh-dashboard").addEventListener("click", () => {
  loadDashboard().catch((error) => showToast(normalizeError(error), true));
});

document.querySelector("#refresh-diagnostics").addEventListener("click", () => {
  loadDiagnostics().catch((error) => showToast(normalizeError(error), true));
});

eventFilterEl.addEventListener("input", () => renderEvents());
eventHideNoiseEl.addEventListener("input", () => renderEvents());

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
      cwd: form.get("cwd") || null,
      model: form.get("model") || null,
      thread_id: form.get("thread_id") || null,
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

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) {
    return;
  }
  const instanceId = target.dataset.instanceId;
  try {
    if (target.dataset.action === "apply-mission-preset") {
      applyMissionPreset(target.dataset.presetId);
    }
    if (target.dataset.action === "apply-opportunity") {
      const opportunity = getOpportunityById(target.dataset.opportunityId);
      if (!opportunity) {
        throw new Error("That launch draft is no longer available.");
      }
      applyMissionDraft(opportunity.mission_draft);
      showToast(`Loaded ghost launch: ${opportunity.title}`);
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

refreshAll().catch((error) => showToast(normalizeError(error), true));
syncTransportFields();
connectSocket();
