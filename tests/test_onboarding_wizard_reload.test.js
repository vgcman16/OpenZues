const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

class FakeElement {
  constructor({ id = null, name = null, type = "text" } = {}) {
    this.id = id;
    this.name = name;
    this.type = type;
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.hidden = false;
    this.readOnly = false;
    this.required = false;
    this.dataset = {};
    this.textContent = "";
    this.innerHTML = "";
    this.className = "";
    this.title = "";
    this.attributes = new Map();
  }

  addEventListener() {}

  removeEventListener() {}

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
    if (name === "title") {
      this.title = String(value);
    }
  }

  removeAttribute(name) {
    this.attributes.delete(name);
    if (name === "title") {
      this.title = "";
    }
  }

  toggleAttribute(name, force) {
    if (force) {
      this.setAttribute(name, "");
      return;
    }
    this.removeAttribute(name);
  }

  closest() {
    return null;
  }

  querySelector() {
    return null;
  }
}

class FakeInputElement extends FakeElement {}

class FakeSelectElement extends FakeElement {}

class FakeTextAreaElement extends FakeElement {}

class FakeFormElement extends FakeElement {
  constructor({ id = null } = {}) {
    super({ id, type: "form" });
    this.fields = new Map();
  }

  register(field) {
    if (field.name) {
      this.fields.set(field.name, field);
    }
    return field;
  }

  querySelector(selector) {
    const nameMatch = selector.match(/name="([^"]+)"/);
    if (nameMatch) {
      return this.fields.get(nameMatch[1]) || null;
    }
    return null;
  }
}

class FakeStorage {
  constructor(seed = {}) {
    this.values = new Map(Object.entries(seed));
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

function createHarness({
  savedWizard = null,
  savedSelection = null,
  fetchImpl = async () => ({
    ok: true,
    status: 200,
    json: async () => ({}),
  }),
} = {}) {
  const form = new FakeFormElement({ id: "onboarding-form" });
  const byId = new Map();
  const byName = new Map();

  const register = (element) => {
    if (element.id) {
      byId.set(`#${element.id}`, element);
    }
    if (element.name) {
      form.register(element);
      byName.set(element.name, element);
    }
    return element;
  };

  const setupMode = register(
    new FakeSelectElement({ id: "onboarding-setup-mode", name: "setup_mode" }),
  );
  const setupFlow = register(
    new FakeSelectElement({ id: "onboarding-setup-flow", name: "setup_flow" }),
  );
  const instanceMode = register(
    new FakeSelectElement({ id: "onboarding-instance-mode", name: "instance_mode" }),
  );
  const instanceId = register(
    new FakeSelectElement({ id: "onboarding-instance-select", name: "instance_id" }),
  );
  const projectPath = register(new FakeInputElement({ name: "project_path" }));
  const projectLabel = register(new FakeInputElement({ name: "project_label" }));
  const instanceName = register(new FakeInputElement({ name: "instance_name" }));
  const operatorName = register(new FakeInputElement({ name: "operator_name" }));
  const operatorEmail = register(
    new FakeInputElement({ name: "operator_email", type: "email" }),
  );
  const teamName = register(new FakeInputElement({ name: "team_name" }));
  const taskName = register(new FakeInputElement({ name: "task_name" }));
  const cadenceMinutes = register(
    new FakeInputElement({ name: "cadence_minutes", type: "number" }),
  );
  const model = register(new FakeInputElement({ name: "model" }));
  const maxTurns = register(new FakeInputElement({ name: "max_turns", type: "number" }));
  const objectiveTemplate = register(new FakeTextAreaElement({ name: "objective_template" }));
  const toolsets = register(new FakeInputElement({ name: "toolsets" }));
  const integrationName = register(new FakeInputElement({ name: "integration_name" }));
  const integrationKind = register(new FakeInputElement({ name: "integration_kind" }));
  const integrationBaseUrl = register(new FakeInputElement({ name: "integration_base_url" }));
  const useMempalace = register(
    new FakeInputElement({ name: "use_mempalace", type: "checkbox" }),
  );

  projectPath.value = "";
  projectLabel.value = "";
  instanceName.value = "Local Codex Desktop";
  operatorName.value = "";
  operatorEmail.value = "";
  teamName.value = "";
  taskName.value = "";
  cadenceMinutes.value = "180";
  model.value = "gpt-5.4";
  maxTurns.value = "4";
  objectiveTemplate.value = "";
  toolsets.value = "";
  integrationName.value = "GitHub Inventory";
  integrationKind.value = "github";
  integrationBaseUrl.value = "https://api.github.com";

  const onboardingHeadline = register(new FakeElement({ id: "onboarding-headline" }));
  const onboardingSummary = register(new FakeElement({ id: "onboarding-summary" }));
  const onboardingChecklist = register(new FakeElement({ id: "onboarding-checklist" }));
  const onboardingModeLabel = register(new FakeElement({ id: "onboarding-mode-label" }));
  const onboardingFlowPill = register(new FakeElement({ id: "onboarding-flow-pill" }));
  const onboardingModeSummary = register(new FakeElement({ id: "onboarding-mode-summary" }));
  const onboardingResult = register(new FakeElement({ id: "onboarding-result" }));
  const onboardingWizardTrigger = register(
    new FakeElement({ id: "onboarding-wizard-trigger" }),
  );
  const onboardingSelectionFields = register(
    new FakeElement({ id: "onboarding-selection-fields" }),
  );
  const onboardingGuidedSelectionNote = register(
    new FakeElement({ id: "onboarding-guided-selection-note" }),
  );
  const gatewayCapabilitySummary = register(
    new FakeElement({ id: "gateway-capability-summary" }),
  );
  const gatewayBootstrapProfile = register(
    new FakeElement({ id: "gateway-bootstrap-profile" }),
  );
  const toast = register(new FakeElement({ id: "toast" }));

  register(form);

  const sessionStorage = new FakeStorage(
    {
      ...(savedWizard
        ? {
            "openzues.onboardingWizard": JSON.stringify(savedWizard),
          }
        : {}),
      ...(savedSelection
        ? {
            "openzues.onboardingSelection": JSON.stringify(savedSelection),
          }
        : {}),
    },
  );

  const document = {
    querySelector(selector) {
      if (byId.has(selector)) {
        return byId.get(selector);
      }
      if (selector.startsWith("#")) {
        const fallback = new FakeElement({ id: selector.slice(1) });
        byId.set(selector, fallback);
        return fallback;
      }
      return null;
    },
    querySelectorAll() {
      return [];
    },
    getElementById(id) {
      return byId.get(`#${id}`) || null;
    },
    addEventListener() {},
  };

  const window = {
    document,
    sessionStorage,
    localStorage: new FakeStorage(),
    location: {
      protocol: "http:",
      host: "localhost",
    },
    navigator: {},
    __OPENZUES_DISABLE_BOOT__: true,
    __OPENZUES_ENABLE_TEST_HOOKS__: true,
    addEventListener() {},
    removeEventListener() {},
  };

  const context = {
    window,
    document,
    console,
    fetch: fetchImpl,
    WebSocket: class {
      constructor() {
        throw new Error("WebSocket should not be constructed in tests");
      }
    },
    setTimeout: () => 0,
    clearTimeout() {},
    URLSearchParams,
    FormData: class {
      constructor(formElement) {
        this.values = new Map();
        if (!(formElement instanceof FakeFormElement)) {
          return;
        }
        for (const field of formElement.fields.values()) {
          if (!field?.name) {
            continue;
          }
          if (field.type === "checkbox") {
            if (field.checked) {
              this.values.set(field.name, "on");
            }
            continue;
          }
          this.values.set(field.name, field.value);
        }
      }

      get(name) {
        return this.values.has(name) ? this.values.get(name) : null;
      }

      has(name) {
        return this.values.has(name);
      }
    },
    HTMLInputElement: FakeInputElement,
    HTMLSelectElement: FakeSelectElement,
    HTMLTextAreaElement: FakeTextAreaElement,
    Error,
    Promise,
  };
  context.globalThis = context;
  window.window = window;

  const scriptPath = path.resolve(__dirname, "../src/openzues/web/static/app.js");
  const source = fs.readFileSync(scriptPath, "utf8");
  vm.runInNewContext(source, context, { filename: scriptPath });

  return {
    hooks: window.__OPENZUES_TEST_HOOKS__,
    elements: {
      onboardingChecklist,
      onboardingFlowPill,
      onboardingGuidedSelectionNote,
      onboardingHeadline,
      onboardingModeLabel,
      onboardingModeSummary,
      onboardingResult,
      onboardingSelectionFields,
      onboardingSummary,
      onboardingWizardTrigger,
      gatewayBootstrapProfile,
      gatewayCapabilitySummary,
      toast,
      setupMode,
      setupFlow,
      instanceMode,
      instanceId,
      projectPath,
      projectLabel,
      instanceName,
      operatorName,
      operatorEmail,
      teamName,
      taskName,
      cadenceMinutes,
      model,
      maxTurns,
      objectiveTemplate,
      toolsets,
      useMempalace,
      project_path: projectPath,
      project_label: projectLabel,
      instance_mode: instanceMode,
      instance_id: instanceId,
      instance_name: instanceName,
      operator_name: operatorName,
      operator_email: operatorEmail,
      team_name: teamName,
      task_name: taskName,
      cadence_minutes: cadenceMinutes,
      objective_template: objectiveTemplate,
      setup_mode: setupMode,
      setup_flow: setupFlow,
      use_mempalace: useMempalace,
      toolsets,
    },
    byName,
    sessionStorage,
  };
}

function makeWizardSession(overrides = {}) {
  return {
    mode: "local",
    flow: "quickstart",
    project_path: null,
    project_label: null,
    instance_mode: "quick_connect_desktop",
    instance_id: null,
    instance_name: "Local Codex Desktop",
    team_name: null,
    operator_name: null,
    operator_email: null,
    task_name: null,
    cadence_minutes: 180,
    model: "gpt-5.4",
    max_turns: 4,
    objective_template: "",
    conversation_target: null,
    toolsets: [],
    use_mempalace: false,
    summary: "Local-first bootstrap",
    updated_at: "2026-04-22T00:00:00Z",
    ...overrides,
  };
}

function makeDashboard(overrides = {}) {
  return {
    instances: [],
    projects: [],
    task_blueprints: [],
    missions: [],
    playbooks: [],
    events: [],
    ops_mesh: {
      headline: "Operator mesh is quiet",
      summary: "",
      task_inbox: {
        headline: "Operator inbox is quiet",
        summary: "",
        items: [],
        tasks: [],
      },
      auth_posture: {
        headline: "Auth posture is clear",
        summary: "",
        satisfied_count: 0,
        missing_count: 0,
        degraded_count: 0,
      },
      integrations_inventory: {
        headline: "Integration readiness is empty",
        summary: "",
        ready_count: 0,
        gap_count: 0,
        observed_count: 0,
        items: [],
      },
      access_posture: {
        headline: "Access posture is empty",
        summary: "",
        team_count: 0,
        operator_count: 0,
        api_key_count: 0,
        recent_remote_request_count: 0,
      },
      skills_registry: {
        headline: "Skills registry is idle",
        summary: "",
        gaps: [],
        projects: [],
        lanes: [],
      },
      skillbooks: [],
      teams: [],
      operators: [],
      remote_requests: [],
      vault_secrets: [],
      integrations: [],
      notification_routes: [],
      outbound_deliveries: [],
      lane_snapshots: [],
    },
    ...overrides,
  };
}

test("guided onboarding reload reapplies the saved draft and ownership locks", () => {
  const savedWizard = {
    sessionId: "wizard-123",
    step: {
      id: "step-operator-name",
      field: "operator_name",
      type: "text",
      title: "Operator Name",
      message: "Name the remote operator.",
      initialValue: "",
    },
    draft: {
      mode: "remote",
      flow: "advanced",
      project_path: "C:/workspace/OpenZues",
      operator_name: "Skull",
      task_name: "Parity Loop",
    },
  };
  const { hooks, elements } = createHarness({ savedWizard });
  hooks.state.setup = {
    wizard_session: makeWizardSession(),
  };

  hooks.applyWizardSessionToForm();
  const selection = hooks.getEffectiveOnboardingSelection();
  hooks.renderOnboardingSelectionOwnership(selection);
  hooks.syncOnboardingMode();
  const draft = hooks.collectOnboardingDraftValues({
    get(name) {
      const field = elements[name] || null;
      if (!field) {
        return null;
      }
      if (field.type === "checkbox") {
        return field.checked ? "on" : null;
      }
      return field.value;
    },
  });

  assert.equal(elements.setupMode.value, "remote");
  assert.equal(elements.setupFlow.value, "advanced");
  assert.equal(elements.projectPath.value, "C:/workspace/OpenZues");
  assert.equal(elements.operatorName.value, "Skull");
  assert.equal(elements.taskName.value, "Parity Loop");
  assert.equal(elements.operatorName.readOnly, true);
  assert.equal(elements.setupMode.disabled, true);
  assert.equal(elements.setupFlow.disabled, true);
  assert.equal(elements.onboardingSelectionFields.hidden, true);
  assert.equal(elements.onboardingGuidedSelectionNote.hidden, false);
  assert.match(elements.onboardingGuidedSelectionNote.textContent, /Remote \/ Advanced/);
  assert.equal(draft.mode, "remote");
  assert.equal(draft.flow, "advanced");
  assert.equal(draft.project_path, "C:/workspace/OpenZues");
  assert.equal(draft.operator_name, "Skull");
});

test("missing wizard status clears the stale reload overlay and session storage", async () => {
  const savedWizard = {
    sessionId: "wizard-expired",
    step: {
      id: "step-operator-name",
      field: "operator_name",
      type: "text",
      title: "Operator Name",
      message: "Name the remote operator.",
    },
    draft: {
      mode: "remote",
      project_path: "C:/workspace/OpenZues",
    },
  };
  const { hooks, sessionStorage } = createHarness({
    savedWizard,
    fetchImpl: async (url) => {
      if (String(url).includes("/api/onboarding/wizard/status")) {
        return {
          ok: false,
          status: 400,
          text: async () => JSON.stringify({ detail: "wizard not found" }),
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    },
  });

  await hooks.reconcileOnboardingWizardState();

  assert.equal(hooks.state.onboardingWizard, null);
  assert.equal(sessionStorage.getItem(hooks.ONBOARDING_WIZARD_STORAGE_KEY), null);
});

test("lost guided wizard restart carries the merged draft into the next step", async () => {
  const savedWizard = {
    sessionId: "wizard-expired",
    step: {
      id: "step-operator-name",
      field: "operator_name",
      type: "text",
      title: "Operator Name",
      message: "Name the remote operator.",
    },
    draft: {
      mode: "remote",
      flow: "advanced",
      project_path: "C:/workspace/OpenZues",
    },
  };
  const fetchCalls = [];
  const { hooks, elements, sessionStorage } = createHarness({
    savedWizard,
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push({
        url: String(url),
        method: options.method || "GET",
        body: options.body || null,
      });
      if (String(url) === "/api/onboarding/wizard/start") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            sessionId: "wizard-restarted",
            done: false,
            status: "running",
            step: {
              id: "step-task-name",
              field: "task_name",
              type: "text",
              title: "Task Name",
              message: "Name the recurring setup task.",
            },
          }),
        };
      }
      if (String(url) === "/api/dashboard") {
        return {
          ok: true,
          status: 200,
          json: async () => makeDashboard(),
        };
      }
      if (String(url) === "/api/setup") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            wizard_session: makeWizardSession({
              mode: "remote",
              flow: "advanced",
              project_path: "C:/workspace/OpenZues",
              operator_name: "Skull",
            }),
          }),
        };
      }
      if (String(url).startsWith("/api/onboarding/wizard/status")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "running",
          }),
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    },
  });
  hooks.state.setup = {
    wizard_session: makeWizardSession({
      mode: "remote",
      flow: "advanced",
      project_path: "C:/workspace/OpenZues",
    }),
  };

  await hooks.restartLostOnboardingWizard({
    ...savedWizard.draft,
    operator_name: "Skull",
  });

  const startCall = fetchCalls.find((call) => call.url === "/api/onboarding/wizard/start");
  assert.ok(startCall);
  const payload = JSON.parse(startCall.body);
  assert.equal(payload.project_path, "C:/workspace/OpenZues");
  assert.equal(payload.operator_name, "Skull");

  assert.equal(hooks.state.onboardingWizard.sessionId, "wizard-restarted");
  assert.equal(hooks.state.onboardingWizard.step.field, "task_name");
  assert.equal(hooks.state.onboardingWizard.draft.mode, "remote");
  assert.equal(hooks.state.onboardingWizard.draft.flow, "advanced");
  assert.equal(hooks.state.onboardingWizard.draft.project_path, "C:/workspace/OpenZues");
  assert.equal(hooks.state.onboardingWizard.draft.operator_name, "Skull");
  assert.equal(elements.operatorName.value, "Skull");
  assert.equal(elements.setupMode.value, "remote");
  assert.equal(elements.setupFlow.value, "advanced");

  const persistedWizard = JSON.parse(sessionStorage.getItem(hooks.ONBOARDING_WIZARD_STORAGE_KEY));
  assert.equal(persistedWizard.sessionId, "wizard-restarted");
  assert.equal(persistedWizard.step.field, "task_name");
  assert.equal(persistedWizard.draft.operator_name, "Skull");
});

test("selection-only onboarding choice survives an ignored backend save and reload", async () => {
  const fetchCalls = [];
  const { hooks, elements, sessionStorage } = createHarness({
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push({
        url: String(url),
        method: options.method || "GET",
        body: options.body || null,
      });
      if (String(url) === "/api/setup/wizard") {
        return {
          ok: true,
          status: 200,
          json: async () => makeWizardSession(),
        };
      }
      if (String(url) === "/api/dashboard") {
        return {
          ok: true,
          status: 200,
          json: async () => makeDashboard(),
        };
      }
      if (String(url) === "/api/setup") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            wizard_session: makeWizardSession(),
          }),
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    },
  });
  hooks.state.setup = {
    wizard_session: makeWizardSession(),
  };
  hooks.applyWizardSessionToForm();

  elements.setupMode.value = "remote";
  elements.setupFlow.value = "advanced";

  await hooks.persistSetupWizardSelection();

  const persistCall = fetchCalls.find((call) => call.url === "/api/setup/wizard");
  assert.ok(persistCall);
  assert.deepEqual(JSON.parse(persistCall.body), {
    mode: "remote",
    flow: "advanced",
    use_mempalace: false,
  });
  assert.equal(elements.setupMode.value, "remote");
  assert.equal(elements.setupFlow.value, "advanced");
  assert.equal(hooks.state.onboardingSelectionDraft.mode, "remote");
  assert.equal(hooks.state.onboardingSelectionDraft.flow, "advanced");

  const persistedSelection = JSON.parse(
    sessionStorage.getItem(hooks.ONBOARDING_SELECTION_STORAGE_KEY),
  );
  assert.equal(persistedSelection.mode, "remote");
  assert.equal(persistedSelection.flow, "advanced");

  const reloaded = createHarness({ savedSelection: persistedSelection });
  reloaded.hooks.state.setup = {
    wizard_session: makeWizardSession(),
  };
  reloaded.hooks.applyWizardSessionToForm();

  assert.equal(reloaded.elements.setupMode.value, "remote");
  assert.equal(reloaded.elements.setupFlow.value, "advanced");
});

test("selection-only guided restart carries the active mode and flow into wizard start", async () => {
  const fetchCalls = [];
  const { hooks, elements } = createHarness({
    savedSelection: {
      mode: "remote",
      flow: "advanced",
      use_mempalace: false,
    },
    fetchImpl: async (url, options = {}) => {
      fetchCalls.push({
        url: String(url),
        method: options.method || "GET",
        body: options.body || null,
      });
      if (String(url) === "/api/onboarding/wizard/start") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            sessionId: "wizard-selection-start",
            done: false,
            status: "running",
            step: {
              id: "step-operator-name",
              field: "operator_name",
              type: "text",
              title: "Operator Name",
              message: "Name the operator who should receive the remote ingress API key.",
            },
          }),
        };
      }
      if (String(url) === "/api/dashboard") {
        return {
          ok: true,
          status: 200,
          json: async () => makeDashboard(),
        };
      }
      if (String(url) === "/api/setup") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            wizard_session: makeWizardSession(),
          }),
        };
      }
      throw new Error(`Unexpected fetch: ${url}`);
    },
  });
  hooks.state.setup = {
    wizard_session: makeWizardSession(),
  };
  hooks.applyWizardSessionToForm();

  elements.setupMode.value = "remote";
  elements.setupFlow.value = "advanced";

  const draft = hooks.collectOnboardingDraftValues({
    get(name) {
      const field = elements[name] || null;
      if (!field) {
        return null;
      }
      if (field.type === "checkbox") {
        return field.checked ? "on" : null;
      }
      return field.value;
    },
  });
  const payload = hooks.buildOnboardingWizardDraftPayload(
    {
      get(name) {
        const field = elements[name] || null;
        if (!field) {
          return null;
        }
        if (field.type === "checkbox") {
          return field.checked ? "on" : null;
        }
        return field.value;
      },
    },
    draft,
  );
  assert.deepEqual(JSON.parse(JSON.stringify(payload)), {
    mode: "remote",
    flow: "advanced",
    instance_mode: "existing",
  });

  await hooks.restartLostOnboardingWizard(draft);

  const startCall = fetchCalls.find((call) => call.url === "/api/onboarding/wizard/start");
  assert.ok(startCall);
  assert.deepEqual(JSON.parse(startCall.body), {
    mode: "remote",
    flow: "advanced",
    instance_mode: "existing",
  });
});

test("guided remote lane selection updates and clears the draft lane binding", () => {
  const { hooks } = createHarness();
  const step = {
    id: "step-instance-id",
    field: "instance_id",
    type: "select",
    title: "Saved Lane",
    options: [
      {
        value: "",
        label: "Bind at launch time",
        instanceName: "Local Codex Desktop",
      },
      {
        value: "7",
        label: "Pinned Lane (connected)",
        instanceName: "Pinned Lane",
      },
    ],
  };

  const selected = hooks.mergeOnboardingWizardDraft(
    {
      mode: "remote",
      flow: "advanced",
      project_path: "C:/workspace/OpenZues",
      operator_name: "Skull",
    },
    step,
    "7",
  );
  assert.equal(selected.instance_mode, "existing");
  assert.equal(selected.instance_id, "7");
  assert.equal(selected.instance_name, "Pinned Lane");

  const cleared = hooks.mergeOnboardingWizardDraft(selected, step, "");
  assert.equal(cleared.instance_mode, "existing");
  assert.equal(cleared.instance_id, null);
  assert.equal(cleared.instance_name, "Local Codex Desktop");
});

test("guided onboarding note steps render a continue-only card", () => {
  const { hooks } = createHarness();
  hooks.setOnboardingWizardState({
    sessionId: "wizard-note",
    step: {
      id: "step-remote-lane-note",
      field: "remote_lane_note",
      type: "note",
      title: "Lane Binding Can Wait",
      message:
        "No saved lane is staged yet. Remote setup can still save the workspace, operator access, and recurring task now, then bind a lane when the first launch is ready.",
    },
    draft: {
      mode: "remote",
      flow: "advanced",
      project_path: "C:/workspace/OpenZues",
    },
  });

  const markup = hooks.renderOnboardingWizardStep();

  assert.match(markup, /Lane Binding Can Wait/);
  assert.match(markup, /Continue Guided Setup/);
  assert.doesNotMatch(markup, /name="value"/);
});

test("switching a local draft to remote clears the stale lane hint", () => {
  const { hooks, elements } = createHarness();
  hooks.state.setup = {
    wizard_session: makeWizardSession({
      mode: "local",
      flow: "quickstart",
      instance_mode: "existing",
      instance_id: 7,
      instance_name: "Pinned Local Lane",
      project_path: "C:/workspace/OpenZues",
      operator_name: "Skull",
      task_name: "Parity Loop",
      objective_template: "Ship the next verified slice.",
    }),
  };

  hooks.applyWizardSessionToForm();
  hooks.syncOnboardingMode();

  assert.equal(elements.instanceId.value, "7");
  assert.equal(elements.instanceName.value, "Pinned Local Lane");

  elements.setupMode.value = "remote";
  elements.setupFlow.value = "advanced";
  hooks.syncOnboardingMode();

  const draft = hooks.collectOnboardingDraftValues({
    get(name) {
      const field = elements[name] || null;
      if (!field) {
        return null;
      }
      if (field.type === "checkbox") {
        return field.checked ? "on" : null;
      }
      return field.value;
    },
  });

  assert.equal(elements.instanceId.value, "");
  assert.equal(elements.instanceName.value, "Local Codex Desktop");
  assert.equal(draft.mode, "remote");
  assert.equal(draft.instance_mode, "existing");
  assert.equal(draft.instance_id, null);
  assert.equal(draft.instance_name, "Local Codex Desktop");
});

async function main() {
  let failed = false;
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`ok - ${name}`);
    } catch (error) {
      failed = true;
      console.error(`not ok - ${name}`);
      console.error(error);
    }
  }
  if (failed) {
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}
