const state = {
  dashboard: null,
  socket: null,
  refreshTimer: null,
};

const heroStatsEl = document.querySelector("#hero-stats");
const instancesEl = document.querySelector("#instances");
const projectsEl = document.querySelector("#projects");
const eventsEl = document.querySelector("#events");
const toastEl = document.querySelector("#toast");

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

function summarize(value) {
  return escapeHtml(JSON.stringify(value, null, 2));
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
    throw new Error(text || `${response.status} ${response.statusText}`);
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

function scheduleRefresh() {
  clearTimeout(state.refreshTimer);
  state.refreshTimer = setTimeout(() => {
    loadDashboard().catch((error) => showToast(error.message, true));
  }, 250);
}

function renderHero() {
  const instances = state.dashboard?.instances ?? [];
  const projects = state.dashboard?.projects ?? [];
  const connected = instances.filter((instance) => instance.connected).length;
  const approvals = instances.reduce(
    (total, instance) => total + instance.unresolved_requests.length,
    0,
  );
  heroStatsEl.innerHTML = `
    <article class="stat">
      <span class="stat-label">Connected</span>
      <span class="stat-value">${connected}</span>
    </article>
    <article class="stat">
      <span class="stat-label">Projects</span>
      <span class="stat-value">${projects.length}</span>
    </article>
    <article class="stat">
      <span class="stat-label">Approvals</span>
      <span class="stat-value">${approvals}</span>
    </article>
  `;
}

function renderInstances() {
  const instances = state.dashboard?.instances ?? [];
  if (!instances.length) {
    instancesEl.innerHTML = `<article class="instance"><p>No connections yet.</p></article>`;
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
        .map((model) => `<option value="${escapeHtml(model.id || model.slug || "gpt-5.4")}">${escapeHtml(model.id || model.slug || "gpt-5.4")}</option>`)
        .join("");

      return `
        <article class="instance stack">
          <div class="instance-head">
            <div>
              <h3>${escapeHtml(instance.name)}</h3>
              <div class="instance-meta">
                ${pill(statusText, statusTone)}
                ${pill(instance.transport)}
                ${instance.pid ? pill(`pid ${instance.pid}`) : ""}
                ${instance.client_user_agent ? pill(instance.client_user_agent) : ""}
              </div>
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

          ${
            instance.error
              ? `<div class="pill-row">${pill(instance.error, "bad")}</div>`
              : ""
          }

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

          <div class="stack">
            <strong>Pending Requests</strong>
            ${requestCards}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderProjects() {
  const projects = state.dashboard?.projects ?? [];
  if (!projects.length) {
    projectsEl.innerHTML = `<article class="project"><p>No projects registered yet.</p></article>`;
    return;
  }

  projectsEl.innerHTML = projects
    .map(
      (project) => `
        <article class="project stack">
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

function renderEvents() {
  const events = state.dashboard?.events ?? [];
  if (!events.length) {
    eventsEl.innerHTML = `<article class="event"><p>No events yet.</p></article>`;
    return;
  }
  eventsEl.innerHTML = events
    .slice(-80)
    .reverse()
    .map(
      (event) => `
        <article class="event stack">
          <div class="event-meta">
            ${pill(event.method, "ok")}
            ${event.thread_id ? pill(event.thread_id) : ""}
            ${event.instance_id ? pill(`instance ${event.instance_id}`) : ""}
          </div>
          <pre>${summarize(event.payload)}</pre>
          <small class="mono">${escapeHtml(event.created_at)}</small>
        </article>
      `,
    )
    .join("");
}

function render() {
  renderHero();
  renderInstances();
  renderProjects();
  renderEvents();
}

async function submitJson(url, payload) {
  await api(url, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await loadDashboard();
}

function parseCommandLine(input) {
  return input
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

document.querySelector("#refresh-dashboard").addEventListener("click", () => {
  loadDashboard().catch((error) => showToast(error.message, true));
});

document.querySelector("#instance-form").addEventListener("submit", async (event) => {
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
    showToast("Connection created.");
  } catch (error) {
    showToast(error.message, true);
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
    showToast(error.message, true);
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) {
    return;
  }
  const instanceId = target.dataset.instanceId;
  try {
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
  } catch (error) {
    showToast(error.message, true);
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
      await submitJson(`/api/instances/${instanceId}/commands`, {
        command: parseCommandLine(form.get("command")),
        cwd: form.get("cwd") || null,
        timeout_ms: 10000,
        tty: false,
      });
      showToast("Command executed.");
    }
    if (action === "review") {
      await submitJson(`/api/instances/${instanceId}/reviews`, {
        thread_id: form.get("thread_id"),
      });
      showToast("Review started.");
    }
    formEl.reset();
  } catch (error) {
    showToast(error.message, true);
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

loadDashboard().catch((error) => showToast(error.message, true));
connectSocket();
